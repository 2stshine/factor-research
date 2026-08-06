#!/usr/bin/env python
"""팩터 리서치 CLI.

  python scripts/run.py build                 # 패널 캐시 생성 (한 번)
  python scripts/run.py null --campaign ID    # 같은 크기의 귀무 campaign 오류율 측정
  python scripts/run.py gate                  # 등록 팩터 전체 게이트 통과
  python scripts/run.py gate --factor qual_roe
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pickle
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import factors as F
from engine import epochs, fundamentals, gate, null, panel as P, publish, silver, trials

CACHE = Path(os.environ.get("CACHE_DIR", ".cache"))
TRIAL_DB = CACHE / "trials.sqlite3"


def load_registry():
    """Load stable builtins plus agent-authored candidates, idempotently."""
    import factors.builtin  # noqa: F401
    from factors.candidate_loader import load_candidates

    load_candidates(F.REGISTRY)
    return F.REGISTRY


def cmd_build(args):
    CACHE.mkdir(exist_ok=True)
    load_registry()
    with silver.connect(read_only=True) as conn:
        pan = P.build(conn)
        fund = fundamentals.build(conn)
    # Materializing the Silver revision ledger is the expensive part of a build.
    # Cache every PIT feature produced from that same immutable ledger so a newly
    # pre-registered factor does not force another full RDS transfer merely
    # because it asks for a previously unused accounting column.
    available_features = sorted(set(fund.columns) - {"asset_id", "available_date"})
    df = fundamentals.attach(pan.monthly, fund, available_features)
    df = df.sort_values(["Code", "ym"]).reset_index(drop=True)
    pan.monthly = df
    for tag, term in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        df[f"fwd_{tag}"] = P.forward_returns(pan, terminal=term)   # 인덱스 정렬 (위치대입 금지)
    df = F.compute_all(F.REGISTRY, df)
    pan.monthly = df
    with open(CACHE / "panel.pkl", "wb") as fh:
        pickle.dump(pan, fh)
    print(f"\n캐시 저장: {CACHE/'panel.pkl'}  ({len(df):,}행 × {len(F.REGISTRY)}팩터)")


def _load():
    with open(CACHE / "panel.pkl", "rb") as fh:
        panel = pickle.load(fh)
    required = {"asset_id", "return_close", "total_return_close", "quality_run_id"}
    if panel.meta.get("source") != "RDS public Silver" or not required.issubset(panel.monthly.columns):
        raise SystemExit(
            "캐시가 Bronze/v1 형식입니다. `uv run python scripts/run.py build`로 "
            "인증 Silver 캐시를 다시 만드세요."
        )
    return panel


def _ensure_factor_columns(pan, targets):
    """캐시에 없는 팩터만 즉석 계산한다.

    팩터 값은 build 때 캐시되지만, 새로 등록한 팩터는 컬럼이 없다.
    재무 컬럼(needs)이 이미 패널에 있으면 10분짜리 재빌드 없이 여기서 채운다.
    needs 가 부족하면 build 를 다시 돌려야 한다.
    """
    df = pan.monthly
    missing = [f for f in targets if f"f_{f.name}" not in df.columns]
    if not missing:
        return df
    lacking = {c for f in missing for c in f.needs if c not in df.columns}
    if lacking:
        raise SystemExit(
            f"패널에 없는 컬럼이 필요합니다: {sorted(lacking)}\n"
            f"  → uv run python scripts/run.py build  (재빌드 필요)")
    print(f"[gate] 신규 팩터 {len(missing)}개 즉석 계산: "
          f"{', '.join(f.name for f in missing)}")
    for f in missing:
        try:
            df[f"f_{f.name}"] = f.compute(df) * f.predicted_sign
        except Exception as exc:
            df[f"f_{f.name}"] = float("nan")
            print(f"  ⚠️  {f.name} 계산 실패: {type(exc).__name__}: {exc}")
    pan.monthly = df
    return df


def _approved_signals(conn, df: pd.DataFrame) -> dict[str, pd.Series]:
    values = silver.load_approved_values(conn)
    if values.empty:
        return {}
    values["ym"] = pd.to_datetime(values["as_of_date"]).dt.to_period("M")
    target = pd.MultiIndex.from_arrays([df["asset_id"], df["ym"]])
    output = {}
    for name, group in values.groupby("factor_key"):
        keyed = (group.sort_values("as_of_date")
                 .drop_duplicates(["asset_id", "ym"], keep="last")
                 .set_index(["asset_id", "ym"])["value"])
        output[str(name)] = pd.Series(keyed.reindex(target).to_numpy(dtype=float), index=df.index)
    return output


def _signal_family_digest(signals: dict[str, pd.Series]) -> str:
    digest = hashlib.sha256()
    for name in sorted(signals):
        digest.update(name.encode("utf-8"))
        digest.update(pd.util.hash_pandas_object(signals[name], index=True).values.tobytes())
    return digest.hexdigest()


def _rebuild_scoped_panel(
    pan: P.Panel,
    scoped: pd.DataFrame,
    **meta_updates,
) -> P.Panel:
    """Recompute dead membership and forward labels at the scoped boundary."""
    last_day = pd.Timestamp(scoped["trade_date"].max())
    last_seen = scoped.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < last_day - pd.Timedelta(days=P.INACTIVE_DAYS)]
    meta = dict(pan.meta)
    meta.update(meta_updates)
    output = P.Panel(monthly=scoped, dead=dead, meta=meta)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = P.forward_returns(output, terminal=terminal)
    return output


def _scope_discovery_panel(
    pan: P.Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period | str,
) -> P.Panel:
    """Expose only the campaign snapshot to candidate code and discovery gates."""
    cutoff = pd.Timestamp(data_cutoff).normalize()
    start = pd.Period(oos_start, freq="M")
    if start <= cutoff.to_period("M"):
        raise ValueError("campaign OOS는 data cutoff 다음 달 이후여야 합니다")
    frame = pan.monthly
    scoped = frame[
        pd.to_datetime(frame["trade_date"]).dt.normalize().le(cutoff)
        & frame["ym"].lt(start)
    ].copy()
    if scoped.empty or pd.Timestamp(scoped["trade_date"].max()).normalize() != cutoff:
        raise ValueError(
            "현재 캐시로 campaign cutoff를 정확히 재현할 수 없습니다: "
            f"cutoff={cutoff.date()}. campaign 생성 당시 Silver snapshot을 복구하세요."
        )
    return _rebuild_scoped_panel(
        pan, scoped,
        campaign_data_cutoff=str(cutoff.date()),
        campaign_oos_start=str(start),
    )


def _scope_confirmation_panel(pan: P.Panel, *, oos_end: pd.Period | str) -> P.Panel:
    """Build the fixed OOS snapshot without leaking later observations.

    Signal/return rows stop at ``required_month``.  The immediately following
    month is visible only to prove that the return month is closed and to decide
    whether a name that vanished at the OOS boundary is inactive.  Otherwise a
    disappearing stock's terminal return can be selectively lost.
    """
    signal_end = pd.Period(oos_end, freq="M")
    required_month = signal_end + 1
    closure_month = required_month + 1
    if pan.monthly["ym"].max() < closure_month:
        raise ValueError(
            f"OOS 수익률 월 {required_month}의 월말 확정에는 "
            f"다음 달({closure_month}) 관측이 필요합니다"
        )
    observed = pan.monthly[pan.monthly["ym"] <= closure_month].copy()
    if observed.empty or observed["ym"].max() != closure_month:
        raise ValueError(f"OOS 확정 월 {closure_month} 관측이 snapshot에 없습니다")
    closure_as_of = pd.Timestamp(observed["trade_date"].max()).normalize()
    inactive_ready_after = (
        signal_end.to_timestamp(how="end").normalize()
        + pd.Timedelta(days=P.INACTIVE_DAYS)
    )
    if closure_as_of <= inactive_ready_after:
        raise ValueError(
            "OOS 경계 비활성 종목을 판정하기에는 확정 월 관측일이 너무 이릅니다: "
            f"현재 {closure_as_of.date()}, 최소 {inactive_ready_after.date()} 이후"
        )
    scoped = observed[observed["ym"] <= required_month].copy()
    if scoped.empty or scoped["ym"].max() != required_month:
        raise ValueError(
            f"고정 OOS 마지막 수익률 월 {required_month}이 snapshot에 없습니다"
        )
    last_seen = observed.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < closure_as_of - pd.Timedelta(days=P.INACTIVE_DAYS)]
    meta = dict(pan.meta)
    meta.update({
        "confirmation_signal_end": str(signal_end),
        "confirmation_required_month": str(required_month),
        "confirmation_closure_month": str(closure_month),
        "confirmation_closure_as_of": str(closure_as_of.date()),
    })
    output = P.Panel(monthly=scoped, dead=dead, meta=meta)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = P.forward_returns(output, terminal=terminal)
    return output


def _merge_discovery_and_oos(
    discovery: gate.Result,
    confirmation: gate.Result,
) -> gate.Result:
    """Combine frozen-boundary development evidence with new OOS T4 only."""
    discovery.labels = [
        label for label in discovery.labels
        if label not in {"oos_sealed", "fdr_pending", "discovery_pass"}
    ]
    discovery.metrics["evaluation_phase"] = "full"
    discovery.metrics.update({
        key: value
        for key, value in confirmation.metrics.items()
        if key.startswith("oos_")
    })
    oos_check = next(
        (check for check in confirmation.checks if check.tier == "T4.1"),
        None,
    )
    if oos_check is None:
        failures = ", ".join(check.name for check in confirmation.failed) or "OOS 계산 불가"
        oos_check = gate.Check(
            "T4.1", "고정 OOS IC", False, None,
            f"months>={gate.TH['min_oos_months']} & IC>={gate.TH['oos_ic']}",
            failures,
        )
    discovery.checks.append(oos_check)
    if "oos_ic" in confirmation.series:
        discovery.series["oos_ic"] = confirmation.series["oos_ic"]
    return discovery


def _evaluate(
    args,
    *,
    phase: str = "discovery",
    oos_start: pd.Period | str | None = None,
    oos_end: pd.Period | str | None = None,
    data_cutoff: str | None = None,
    factor_names: list[str] | None = None,
    record_ledger: bool = True,
    defer_multiple_testing: bool = False,
    calibration_scope: dict | None = None,
    frozen_discovery: dict[str, dict] | None = None,
):
    load_registry()
    base_pan = _load()
    frozen_oos = pd.Period(oos_start, freq="M") if oos_start is not None else None
    frozen_oos_end = pd.Period(oos_end, freq="M") if oos_end is not None else None
    development_pan = None
    if phase == "discovery" and (data_cutoff is not None or oos_start is not None):
        if data_cutoff is None or oos_start is None:
            raise ValueError("campaign discovery에는 data_cutoff와 oos_start가 모두 필요합니다")
        pan = _scope_discovery_panel(
            base_pan, data_cutoff=data_cutoff, oos_start=oos_start,
        )
    elif phase == "full" and oos_end is not None:
        pan = _scope_confirmation_panel(base_pan, oos_end=oos_end)
        if frozen_discovery is not None:
            if data_cutoff is None or frozen_oos is None:
                raise ValueError("봉인 confirmation에는 discovery cutoff와 OOS start가 필요합니다")
            development_pan = _scope_discovery_panel(
                base_pan, data_cutoff=data_cutoff, oos_start=frozen_oos,
            )
    else:
        pan = base_pan
    df = pan.monthly
    if factor_names is not None:
        targets = [F.REGISTRY[name] for name in factor_names]
    else:
        targets = [F.REGISTRY[args.factor]] if args.factor else list(F.REGISTRY)
    development_df = development_pan.monthly if development_pan is not None else None
    ledger = trials.TrialLedger(TRIAL_DB)
    with silver.connect(read_only=True) as conn:
        approved = _approved_signals(conn, df)
        development_approved = (
            _approved_signals(conn, development_df)
            if development_df is not None else None
        )
        gold_trials = silver.load_gold_trial_history(conn)
    gold_family_digest = _signal_family_digest(approved)
    cutoff = str(df["trade_date"].max().date())
    confirmation_snapshot_digest = P.snapshot_digest(pan) if phase == "full" else None
    calibration = None
    if phase == "full":
        calibration_path = CACHE / "null_dist.parquet"
        calibration = pd.read_parquet(calibration_path) if calibration_path.exists() else None
        scope = calibration_scope or {}
        # This must run before factor columns are computed on the sealed OOS.
        # A missing/stale calibration is operationally recoverable and must not
        # consume the campaign's one-time confirmation reveal.
        gate.assert_null_calibration(
            calibration, data_cutoff=cutoff, oos_start=frozen_oos,
            discovery_family_size=scope.get("discovery_family_size"),
            oos_family_size=scope.get("oos_family_size"),
            discovery_family_digest=scope.get("discovery_family_digest"),
            oos_family_digest=scope.get("oos_family_digest"),
            gold_family_digest=gold_family_digest,
            confirmation_snapshot_digest=confirmation_snapshot_digest,
            research_data_cutoff=scope.get("research_data_cutoff"),
            oos_end=frozen_oos_end,
        )
    df = _ensure_factor_columns(pan, targets)
    development_df = (
        _ensure_factor_columns(development_pan, targets)
        if development_pan is not None else None
    )
    # Gold's legacy trial rows contain return Sharpe/p-values.  They still count
    # as attempted definitions, but must not enter v3's IC multiple testing.
    external = [
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ]
    summary = ledger.summary(
        [factor.definition_hash for factor in targets], external=external,
        ruleset_version=gate.RULESET_VERSION,
    )
    results: list[gate.Result] = []
    if development_pan is not None and development_df is not None:
        # First reproduce and authenticate every frozen discovery result.  No
        # OOS return may be evaluated until all recoverable snapshot/artifact
        # failures have been ruled out.
        for f in targets:
            existing = {
                name: values for name, values in (development_approved or {}).items()
                if name != f.name
            }
            results.append(gate.evaluate(
                f, development_pan, development_df, existing=existing,
                trial_count=summary.count, prior_sharpes=summary.sharpes,
                oos_start=frozen_oos, data_cutoff=data_cutoff, phase="discovery",
            ))
        if frozen_discovery is None:
            raise ValueError("봉인 confirmation에는 discovery artifact가 필요합니다")
        for result in results:
            frozen = frozen_discovery.get(result.definition_hash)
            if frozen is None:
                raise ValueError(f"동결 discovery family에 없는 survivor입니다: {result.factor}")
            current_p = result.metrics.get("ic_p_investable")
            frozen_p = frozen.get("pvalue")
            if (
                current_p is None or frozen_p is None
                or not pd.notna(current_p)
                or abs(float(current_p) - float(frozen_p)) > 1e-12
            ):
                raise ValueError(
                    f"동결 discovery p값을 재현하지 못했습니다: {result.factor}. "
                    "campaign 생성 당시 Silver snapshot을 복구하세요."
                )
            current_digest = gate.discovery_evidence_digest(result)
            if current_digest != frozen.get("discovery_evidence_digest"):
                raise ValueError(
                    f"동결 discovery 증거를 재현하지 못했습니다: {result.factor}. "
                    "campaign 생성 당시 Silver snapshot을 복구하세요."
                )
        gate.apply_multiple_testing(
            results,
            [
                (definition_hash, float(row["by_input_pvalue"]))
                for definition_hash, row in frozen_discovery.items()
            ],
            total_trials=len(frozen_discovery),
        )
        for result in results:
            expected_q = frozen_discovery[result.definition_hash].get("qvalue")
            actual_q = result.metrics.get("fdr_qvalue")
            if expected_q is None or abs(float(actual_q) - float(expected_q)) > 1e-12:
                raise ValueError(f"동결 discovery q값 재현 실패: {result.factor}")

        authenticated_discovery = results
        results = []
        for f, discovery_result in zip(targets, authenticated_discovery, strict=True):
            confirmation_result = gate.evaluate_oos(
                f, pan, df, oos_start=frozen_oos, oos_end=frozen_oos_end,
            )
            results.append(_merge_discovery_and_oos(
                discovery_result, confirmation_result,
            ))
    else:
        for f in targets:
            # A new version of an already-approved factor is compared with other
            # Gold families, not with its own currently active version.
            existing = {name: values for name, values in approved.items() if name != f.name}
            results.append(gate.evaluate(
                f, pan, df, existing=existing, trial_count=summary.count,
                prior_sharpes=summary.sharpes, oos_start=frozen_oos,
                oos_end=frozen_oos_end, data_cutoff=data_cutoff, phase=phase,
            ))
        gate.apply_multiple_testing(
            results, summary.pvalues, defer=defer_multiple_testing,
            total_trials=summary.ic_count,
        )
    if phase == "full":
        gate.apply_oos_multiple_testing(results)
        gate.apply_null_calibration(
            results, calibration, data_cutoff=cutoff, oos_start=frozen_oos,
            discovery_family_size=(calibration_scope or {}).get("discovery_family_size"),
            oos_family_size=(calibration_scope or {}).get("oos_family_size"),
            discovery_family_digest=(calibration_scope or {}).get("discovery_family_digest"),
            oos_family_digest=(calibration_scope or {}).get("oos_family_digest"),
            gold_family_digest=gold_family_digest,
            confirmation_snapshot_digest=confirmation_snapshot_digest,
            research_data_cutoff=(calibration_scope or {}).get("research_data_cutoff"),
            oos_end=frozen_oos_end,
        )
    if record_ledger:
        for factor, result in zip(targets, results, strict=True):
            ledger.record(factor, result, data_cutoff=cutoff, ruleset_version=gate.RULESET_VERSION)
    return pan, df, targets, results


def cmd_gate(args):
    _, _, _, results = _evaluate(args, phase="discovery")

    print("\n" + "=" * 104)
    print(f"{'팩터':24} {'판정':12} {'IC':>7} {'투자가능IC':>10} {'OOS':>8} {'회전율':>8}  실패 검사")
    print("-" * 104)
    order = {gate.Verdict.PROMOTE: 0, gate.Verdict.PROVISIONAL: 1, gate.Verdict.REJECT: 2}
    for r in sorted(results, key=lambda x: (order[x.verdict], -(x.metrics.get("ic_investable") or -99))):
        m = r.metrics
        icon = {"PROMOTE": "✅", "PROVISIONAL": "⚠️ ", "REJECT": "❌"}[r.verdict.value]
        fails = ", ".join(c.name for c in r.failed)[:44]
        print(f"{r.factor:24} {icon}{r.verdict.value:10} "
              f"{m.get('ic_full', float('nan')):>7.3f} "
              f"{m.get('ic_investable', float('nan')):>10.3f} "
              f"{'SEALED':>8} "
              f"{m.get('turnover', float('nan')):>7.0f}%  {fails}")

    n_p = sum(1 for r in results if r.verdict == gate.Verdict.PROMOTE)
    n_v = sum(1 for r in results if r.verdict == gate.Verdict.PROVISIONAL)
    print(f"\n  PROMOTE {n_p} / PROVISIONAL {n_v} / REJECT {len(results)-n_p-n_v}  (후보 {len(results)})")
    with open(CACHE / "gate_results.pkl", "wb") as fh:
        pickle.dump(results, fh)


def cmd_null(args):
    load_registry()
    pan = _load()
    print(f"합성 귀무 campaign 측정 (종류당 {args.n}개 family)...")
    campaign = epochs.load_campaign("research", args.campaign)
    if campaign.get("protocol_version") != epochs.PROTOCOL_VERSION:
        raise SystemExit("현재 protocol로 만든 campaign만 귀무 보정할 수 있습니다")
    if campaign.get("ruleset_version") != gate.RULESET_VERSION:
        raise SystemExit("현재 ruleset으로 만든 campaign만 귀무 보정할 수 있습니다")
    if campaign.get("status") != "FROZEN":
        raise SystemExit("survivor가 동결된 FROZEN campaign만 귀무 보정할 수 있습니다")
    pan = _scope_confirmation_panel(pan, oos_end=campaign["oos"]["signal_end"])
    ledger = trials.TrialLedger(TRIAL_DB)
    with silver.connect(read_only=True) as conn:
        gold_trials = silver.load_gold_trial_history(conn)
        approved = _approved_signals(conn, pan.monthly)
    summary = ledger.summary(external=[
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ], ruleset_version=gate.RULESET_VERSION)
    oos_start = pd.Period(campaign["oos"]["start"], freq="M")
    out = null.measure(
        pan, n=args.n, trial_count=summary.count,
        prior_sharpes=summary.sharpes, oos_start=oos_start,
        oos_end=pd.Period(campaign["oos"]["signal_end"], freq="M"),
        research_data_cutoff=campaign["data_cutoff"],
        discovery_family_size=int(campaign["discovery_family_size"]),
        oos_family_size=len(campaign["survivors"]),
        discovery_family_digest=campaign["discovery_family_digest"],
        oos_family_digest=campaign["oos_family_digest"],
        gold_family_digest=_signal_family_digest(approved),
        confirmation_snapshot_digest=P.snapshot_digest(pan),
        existing=approved,
    )
    out.to_parquet(CACHE / "null_dist.parquet", index=False)


def cmd_publish(args):
    """게이트 판정을 TeamAlpha-data 의 gold.factor 에 적재."""
    if args.apply:
        raise SystemExit(
            "epoch-1.2에서는 campaign reveal과 사람 검토 전 publish --apply를 허용하지 않습니다"
        )
    pan, df, targets, results = _evaluate(args, phase="discovery")
    cutoff = str(df["trade_date"].max().date())
    rows = []
    for f, r in zip(targets, results, strict=True):
        if args.only_approved and r.verdict != gate.Verdict.PROMOTE:
            continue
        rows.append(publish.build_row(
            f, r, n_trials=r.metrics.get("n_trials"),
            null_family_error_rate=r.metrics.get("null_family_error_rate"),
            data_cutoff=cutoff,
            approved_by=args.approved_by,
        ))

    print(f"\n적재 대상 {len(rows)}건  (모드: {'APPLY' if args.apply else 'DRY-RUN'})")
    for r in rows:
        ev = r["evaluation"]
        print(f"  {r['factor_key']:16} → {r['status']:10} "
              f"(verdict={ev['verdict']}, 실패={len(ev['failed_checks'])}건)")
    if not rows:
        print("  (없음)")
        return

    if args.apply:
        if any(row["status"] == "APPROVED" for row in rows) and not args.approved_by:
            raise SystemExit("APPROVED 적재에는 --approved-by '검토자 이름'이 필요합니다")
        conn = publish.connect()
        try:
            done = publish.publish(conn, rows, apply=True)
        finally:
            conn.close()
    else:
        done = publish.publish(None, rows, apply=False)   # dry-run 은 DB 불필요
    print()
    for d in done:
        print(f"  {d['factor_key']:16} v{d['version']}  {d['status']}"
              + (f"  factor_id={d['factor_id']}" if d["factor_id"] else ""))
    if not args.apply:
        print("\n  실제로 쓰려면 --apply")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    g = sub.add_parser("gate"); g.add_argument("--factor")
    n = sub.add_parser("null"); n.add_argument("--n", type=int, default=25)
    n.add_argument("--campaign", required=True, help="동결된 campaign manifest에 귀무 보정을 결박")
    p = sub.add_parser("publish")
    p.add_argument("--factor"); p.add_argument("--apply", action="store_true")
    p.add_argument("--approved-by", help="PROMOTE를 최종 확인한 사람")
    p.add_argument("--only-approved", action="store_true",
                   help="PROMOTE 만 적재 (기본은 판정 전체를 기록)")
    a = ap.parse_args()
    {"build": cmd_build, "gate": cmd_gate, "null": cmd_null,
     "publish": cmd_publish}[a.cmd](a)


if __name__ == "__main__":
    main()
