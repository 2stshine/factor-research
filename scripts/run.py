#!/usr/bin/env python
"""팩터 리서치 CLI.

  python scripts/run.py build                 # 패널 캐시 생성 (한 번)
  python scripts/run.py null --campaign ID    # 같은 크기의 귀무 campaign 오류율 측정
  python scripts/research.py campaign-start --campaign ID
  python scripts/research.py evaluate --campaign ID --epoch EPOCH --factor FACTOR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import factors as F
from engine import dividends, epochs, fundamentals, gate, implementation, null, panel as P, publish, silver, trials
from engine.boundaries import CampaignWindow, validate_manifest

CACHE = Path(os.environ.get("CACHE_DIR", ".cache"))
TRIAL_DB = CACHE / "trials.sqlite3"


def _implementation_contract(
    factor: F.Factor,
) -> tuple[publish.ImplementationRef, dict, Path, dict]:
    """Authenticate one allowlisted TeamAlpha query and its research binding."""
    configured = os.environ.get("TEAMALPHA_DATA_DIR")
    data_repo = (
        Path(configured).expanduser()
        if configured
        else Path(__file__).resolve().parents[2] / "TeamAlpha-data"
    )
    manifest_path = data_repo / "pipeline/gold/factors/manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"TeamAlpha Gold 구현 manifest가 없습니다: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = manifest.get(factor.name)
    if spec is None:
        raise ValueError(f"TeamAlpha Gold 구현이 없는 팩터입니다: {factor.name}")
    if int(spec.get("predicted_sign", 0)) != factor.predicted_sign:
        raise ValueError(f"Gold manifest predicted_sign 불일치: {factor.name}")
    if spec.get("research_definition_hash") != factor.definition_hash:
        raise ValueError(f"Gold manifest research_definition_hash 불일치: {factor.name}")
    if spec.get("value_contract") != publish.VALUE_CONTRACT_ID:
        raise ValueError(f"Gold value/rank 계약 불일치: {factor.name}")
    relative = Path(spec["sql"])
    sql_path = (data_repo / relative).resolve()
    if data_repo.resolve() not in sql_path.parents or not sql_path.is_file():
        raise ValueError(f"허용된 Gold SQL 파일을 찾을 수 없습니다: {relative}")
    sql_text = sql_path.read_text(encoding="utf-8")
    implementation.validate_query_only_sql(sql_text)
    reference = publish.ImplementationRef(
        uri=f"repo://TeamAlpha-data/{relative.as_posix()}",
        sha256=hashlib.sha256(sql_path.read_bytes()).hexdigest(),
        research_definition_hash=factor.definition_hash,
    )
    binding = {
        "factor": factor.name,
        "definition_hash": factor.definition_hash,
        "predicted_sign": factor.predicted_sign,
        "value_contract": publish.VALUE_CONTRACT_ID,
        "implementation_uri": reference.uri,
        "implementation_sha256": reference.sha256,
        "manifest_entry_digest": implementation.manifest_entry_digest(spec),
    }
    return reference, spec, sql_path, binding


def _implementation_ref(factor: F.Factor) -> publish.ImplementationRef:
    """Bind a research factor to one allowlisted TeamAlpha Gold SQL file."""
    reference, _spec, _sql_path, _binding = _implementation_contract(factor)
    return reference


def _implementation_bindings(factors: list[F.Factor]) -> list[dict]:
    return [_implementation_contract(factor)[3] for factor in factors]


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
        dividend_history = silver.load_dividend_history(conn)
        fund = fundamentals.build(conn)
    # Materializing the Silver revision ledger is the expensive part of a build.
    # Cache every PIT feature produced from that same immutable ledger so a newly
    # pre-registered factor does not force another full RDS transfer merely
    # because it asks for a previously unused accounting column.
    available_features = sorted(set(fund.columns) - {"asset_id", "available_date"})
    df = fundamentals.attach(pan.monthly, fund, available_features)
    df = dividends.attach(df, dividend_history)
    df = df.sort_values(["Code", "ym"]).reset_index(drop=True)
    pan.monthly = df
    pan.meta["dividend_feature_contract"] = dividends.FEATURE_VERSION
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
    required = {
        "asset_id", "return_close", "total_return_close", "quality_run_id",
        "amihud_illiquidity_1m", "amihud_observations_1m",
        "daily_volatility_252d", "daily_return_observations_252d",
        "max_daily_return_1m", "max_daily_return_observations_1m",
        "price_high_252d", "price_high_observations_252d",
        dividends.DIVIDEND_CASH_TTM, dividends.DIVIDEND_EVENT_COUNT_TTM,
    }
    valid_return_contract = (
        panel.meta.get("return_field") == "total_return_close"
        and panel.meta.get("return_methodology") == silver.TOTAL_RETURN_METHOD
        and panel.meta.get("return_contract_status") == "CERTIFIED"
    )
    if (
        panel.meta.get("source") != "RDS public Silver"
        or not required.issubset(panel.monthly.columns)
        or not valid_return_contract
        or panel.meta.get("dividend_feature_contract") != dividends.FEATURE_VERSION
    ):
        raise SystemExit(
            "캐시가 구형이거나 배당 포함 총수익 계약이 없습니다. "
            "Silver 배당 rebuild 후 `uv run python scripts/run.py build`로 "
            "인증 캐시를 다시 만드세요."
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
    approved_keys = silver.load_approved_factor_keys(conn)
    values = silver.load_approved_values(conn)
    target = pd.MultiIndex.from_arrays([df["asset_id"], df["ym"]])
    output = {
        name: pd.Series(float("nan"), index=df.index, dtype=float)
        for name in approved_keys
    }
    if values.empty:
        return output
    values["ym"] = pd.to_datetime(values["as_of_date"]).dt.to_period("M")
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
    scoped = scoped.drop(
        columns=[column for column in scoped if str(column).startswith("f_")],
        errors="ignore",
    ).copy()
    last_day = pd.Timestamp(scoped["trade_date"].max())
    last_seen = scoped.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < last_day - pd.Timedelta(days=P.INACTIVE_DAYS)]
    # Later closure observations are expected to be appended before reveal.
    # Bind scoped evidence to stable source contracts, not mutable full-cache
    # metadata such as last_day/n_dead that lies beyond the frozen cutoff.
    meta = {
        key: pan.meta.get(key)
        for key in ("source", "return_field")
        if key in pan.meta
    }
    meta.update(meta_updates)
    output = P.Panel(monthly=scoped, dead=dead, meta=meta)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = P.forward_returns(output, terminal=terminal)
    return output


def _scope_snapshot_panel(pan: P.Panel, *, snapshot_cutoff: str) -> P.Panel:
    """Rebuild the exact completed Silver input frozen at campaign creation."""
    cutoff = pd.Timestamp(snapshot_cutoff).normalize()
    frame = pan.monthly
    scoped = frame[
        pd.to_datetime(frame["trade_date"]).dt.normalize().le(cutoff)
    ].copy()
    if scoped.empty or pd.Timestamp(scoped["trade_date"].max()).normalize() != cutoff:
        raise ValueError(
            "현재 캐시로 campaign snapshot을 정확히 재현할 수 없습니다: "
            f"cutoff={cutoff.date()}"
        )
    return _rebuild_scoped_panel(
        pan, scoped, campaign_snapshot_cutoff=str(cutoff.date()),
    )


def _scope_discovery_panel(
    pan: P.Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period | str,
) -> P.Panel:
    """Expose only the campaign snapshot to candidate code and discovery gates."""
    cutoff = pd.Timestamp(data_cutoff).normalize()
    start = pd.Period(oos_start, freq="M")
    CampaignWindow.create(
        discovery_data_cutoff=str(cutoff.date()),
        oos_start=start,
        oos_months=gate.TH["min_oos_months"],
    )
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


def _scope_confirmation_panel(
    pan: P.Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period | str,
    oos_end: pd.Period | str,
) -> P.Panel:
    """Build the fixed OOS snapshot without leaking later observations.

    Signal/return rows stop at ``required_month``.  The immediately following
    month is visible only to prove that the return month is closed and to decide
    whether a name that vanished at the OOS boundary is inactive.  Otherwise a
    disappearing stock's terminal return can be selectively lost.
    """
    window = CampaignWindow.create(
        discovery_data_cutoff=data_cutoff,
        oos_start=oos_start,
        oos_months=gate.TH["min_oos_months"],
    )
    window.validate_oos_end(oos_end)
    signal_end = window.oos_signal_end
    required_month = window.oos_return_end
    closure_month = window.closure_month
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
    scoped = scoped.drop(
        columns=[column for column in scoped if str(column).startswith("f_")],
        errors="ignore",
    ).copy()
    last_seen = observed.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < closure_as_of - pd.Timedelta(days=P.INACTIVE_DAYS)]
    meta = {
        key: pan.meta.get(key)
        for key in ("source", "return_field")
        if key in pan.meta
    }
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


def verify_implementations(campaign: dict, factors: list[F.Factor]) -> list[dict]:
    """Run read-only, discovery-only Python/Gold SQL parity for all qualifiers."""
    window = validate_manifest(
        campaign, expected_oos_months=gate.TH["min_oos_months"],
    )
    base_panel = _load()
    discovery_panel = _scope_discovery_panel(
        base_panel,
        data_cutoff=window.discovery_data_cutoff,
        oos_start=window.oos_signal_start,
    )
    snapshot_digest = P.snapshot_digest(discovery_panel)
    expected_digest = campaign["snapshot"]["discovery_input_digest"]
    if snapshot_digest != expected_digest:
        raise ValueError("campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다")

    start = gate.RESEARCH_START
    end = window.discovery_signal_end
    frame = discovery_panel.monthly
    in_scope = (
        discovery_panel.universe
        & frame["ym"].ge(start)
        & frame["ym"].le(end)
    )
    evidence_by_name: dict[str, dict] = {}
    prepared: list[tuple[F.Factor, dict, Path, dict, pd.DataFrame]] = []
    for factor in factors:
        binding: dict | None = None
        try:
            _reference, spec, sql_path, binding = _implementation_contract(factor)
        except Exception as exc:
            evidence_by_name[factor.name] = implementation.failure_evidence(
                factor,
                discovery_signal_start=start,
                discovery_signal_end=end,
                discovery_snapshot_digest=snapshot_digest,
                stage="contract",
                error=exc,
                binding=binding,
            )
            continue
        try:
            raw = factor.compute(frame.copy())
            if not isinstance(raw, pd.Series) or not raw.index.equals(frame.index):
                raise ValueError(f"Python factor가 입력 index의 Series를 반환하지 않습니다: {factor.name}")
            raw = pd.to_numeric(raw, errors="coerce")
            finite = pd.Series(
                pd.notna(raw) & (raw.abs() != float("inf")), index=raw.index,
            )
            valid = in_scope & finite
            python_frame = frame.loc[valid, ["asset_id", "trade_date"]].rename(
                columns={"trade_date": "as_of_date"},
            )
            python_frame["value"] = raw.loc[valid].astype(float).to_numpy()
        except Exception as exc:
            evidence_by_name[factor.name] = implementation.failure_evidence(
                factor,
                discovery_signal_start=start,
                discovery_signal_end=end,
                discovery_snapshot_digest=snapshot_digest,
                stage="python_compute",
                error=exc,
                binding=binding,
            )
            continue
        prepared.append((factor, spec, sql_path, binding, python_frame))

    if prepared:
        try:
            with silver.connect(read_only=True) as conn:
                for factor, spec, sql_path, binding, python_frame in prepared:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(sql_path.read_text(encoding="utf-8"), {
                                "start_month": f"{start}-01",
                                "end_month": f"{end}-01",
                            })
                            rows = cursor.fetchall()
                            columns = [column.name for column in cursor.description]
                        sql_frame = pd.DataFrame(rows, columns=columns)
                        evidence_by_name[factor.name] = implementation.compare_parity(
                            factor,
                            python_frame,
                            sql_frame,
                            implementation_uri=binding["implementation_uri"],
                            implementation_sha256=binding["implementation_sha256"],
                            manifest_spec=spec,
                            discovery_signal_start=start,
                            discovery_signal_end=end,
                            discovery_snapshot_digest=snapshot_digest,
                            atol=float(spec.get(
                                "parity_atol", implementation.DEFAULT_ATOL,
                            )),
                            rtol=float(spec.get(
                                "parity_rtol", implementation.DEFAULT_RTOL,
                            )),
                            allow_tolerance_equivalent_ranks=bool(spec.get(
                                "allow_tolerance_equivalent_ranks", False,
                            )),
                        )
                    except Exception as exc:
                        evidence_by_name[factor.name] = implementation.failure_evidence(
                            factor,
                            discovery_signal_start=start,
                            discovery_signal_end=end,
                            discovery_snapshot_digest=snapshot_digest,
                            stage="sql_execute_or_parity",
                            error=exc,
                            binding=binding,
                        )
        except Exception as exc:
            for factor, _spec, _sql_path, binding, _python_frame in prepared:
                if factor.name not in evidence_by_name:
                    evidence_by_name[factor.name] = implementation.failure_evidence(
                        factor,
                        discovery_signal_start=start,
                        discovery_signal_end=end,
                        discovery_snapshot_digest=snapshot_digest,
                        stage="database_connect",
                        error=exc,
                        binding=binding,
                    )
    return [evidence_by_name[factor.name] for factor in factors]


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
            gate.oos_effect_threshold_label(),
            failures,
        )
    discovery.checks.append(oos_check)
    if "oos_ic" in confirmation.series:
        discovery.series["oos_ic"] = confirmation.series["oos_ic"]
    return discovery


def _assert_confirmation_discovery_ics(results: list[gate.Result]) -> None:
    """Fail the whole batch before any sealed OOS value can be computed."""
    invalid = [
        result.factor
        for result in results
        if result.metrics.get("ic_investable") is None
        or not np.isfinite(result.metrics["ic_investable"])
        or result.metrics["ic_investable"] <= 0
    ]
    if invalid:
        raise ValueError(
            "인증된 Discovery 투자 가능 IC가 없거나 비양수입니다. "
            "부분 OOS 공개를 막기 위해 전체 confirmation을 중단합니다: "
            f"{invalid}"
        )


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
    discovery_snapshot_digest: str | None = None,
):
    if phase == "discovery" and (
        data_cutoff is None
        or oos_start is None
        or discovery_snapshot_digest is None
    ):
        raise ValueError(
            "epoch-1.5 discovery는 campaign의 동결 cutoff·OOS 시작월·discovery "
            "snapshot digest가 필수입니다. scripts/research.py campaign workflow를 "
            "사용하세요."
        )
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
        if P.snapshot_digest(pan) != discovery_snapshot_digest:
            raise ValueError(
                "campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다"
            )
    elif phase == "full" and oos_end is not None:
        if data_cutoff is None or frozen_oos is None:
            raise ValueError("봉인 confirmation에는 discovery cutoff와 OOS start가 필요합니다")
        pan = _scope_confirmation_panel(
            base_pan,
            data_cutoff=data_cutoff,
            oos_start=frozen_oos,
            oos_end=oos_end,
        )
        if frozen_discovery is not None:
            if data_cutoff is None or frozen_oos is None:
                raise ValueError("봉인 confirmation에는 discovery cutoff와 OOS start가 필요합니다")
            development_pan = _scope_discovery_panel(
                base_pan, data_cutoff=data_cutoff, oos_start=frozen_oos,
            )
            if (
                discovery_snapshot_digest is None
                or P.snapshot_digest(development_pan) != discovery_snapshot_digest
            ):
                raise ValueError(
                    "campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다"
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
            qualification_policy=scope.get("qualification_policy"),
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
                raise ValueError(
                    f"확정 discovery family에 없는 자동 통과 후보입니다: {result.factor}"
                )
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
            current_digest = gate.discovery_evidence_digest(
                result,
                ruleset_version=frozen.get("evidence_ruleset_version"),
            )
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
        _assert_confirmation_discovery_ics(authenticated_discovery)
        results = []
        for f, discovery_result in zip(targets, authenticated_discovery, strict=True):
            confirmation_result = gate.evaluate_oos(
                f, pan, df, oos_start=frozen_oos, oos_end=frozen_oos_end,
                data_cutoff=data_cutoff,
                discovery_ic=discovery_result.metrics.get("ic_investable"),
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
            qualification_policy=(calibration_scope or {}).get("qualification_policy"),
        )
    if record_ledger:
        for factor, result in zip(targets, results, strict=True):
            ledger.record(factor, result, data_cutoff=cutoff, ruleset_version=gate.RULESET_VERSION)
    return pan, df, targets, results


def cmd_gate(args):
    del args
    raise SystemExit(
        "전체 패널 gate는 봉인 OOS를 노출하므로 epoch-1.5에서 비활성화했습니다. "
        "scripts/research.py의 campaign-start → epoch-start → evaluate를 사용하세요."
    )


def cmd_null(args):
    load_registry()
    pan = _load()
    print(f"합성 귀무 campaign 측정 (종류당 {args.n}개 family)...")
    campaign = epochs.load_campaign("research", args.campaign)
    if campaign.get("protocol_version") != epochs.PROTOCOL_VERSION:
        raise SystemExit("현재 protocol로 만든 campaign만 귀무 보정할 수 있습니다")
    if campaign.get("ruleset_version") != gate.RULESET_VERSION:
        raise SystemExit("현재 ruleset으로 만든 campaign만 귀무 보정할 수 있습니다")
    if campaign.get("status") != "READY_FOR_CONFIRMATION":
        raise SystemExit("자동 기준 통과가 확정된 campaign만 귀무 보정할 수 있습니다")
    factors = [F.REGISTRY[row["name"]] for row in campaign["qualified_factors"]]
    bindings = _implementation_bindings(factors)
    snapshot = _scope_snapshot_panel(
        pan, snapshot_cutoff=campaign["snapshot"]["data_cutoff"],
    )
    epochs.assert_reveal_ready(
        "research", args.campaign, pan.monthly["trade_date"].max(),
        snapshot_digest=P.snapshot_digest(snapshot),
        current_bindings=bindings,
    )
    pan = _scope_confirmation_panel(
        pan,
        data_cutoff=campaign["discovery"]["data_cutoff"],
        oos_start=campaign["oos"]["start"],
        oos_end=campaign["oos"]["signal_end"],
    )
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
        research_data_cutoff=campaign["discovery"]["data_cutoff"],
        discovery_family_size=int(campaign["discovery_family_size"]),
        oos_family_size=len(campaign["qualified_factors"]),
        discovery_family_digest=campaign["discovery_family_digest"],
        oos_family_digest=campaign["oos_family_digest"],
        gold_family_digest=_signal_family_digest(approved),
        confirmation_snapshot_digest=P.snapshot_digest(pan),
        qualification_policy=campaign["qualification_policy"],
        existing=approved,
    )
    out.to_parquet(CACHE / "null_dist.parquet", index=False)


def cmd_publish(args):
    """Never recompute or write Gold outside the authenticated campaign flow."""
    del args
    raise SystemExit(
        "epoch-1.5 publish는 비활성화했습니다. campaign reveal 산출물을 사람 검토한 뒤 "
        "별도 승인 절차에서만 Gold를 적재하세요."
    )


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
