#!/usr/bin/env python
"""Run a non-confirmatory historical IS/OOS stability audit.

This command deliberately does not touch campaign manifests, the trial ledger,
research history, or Gold.  The historical holdout has already been exposed to
research, so its output is diagnostic evidence only and must never be recorded
as a campaign confirmation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import gate, silver
from scripts import run


AUDIT_ID = "retrospective-qualified-oos-20260807-003"
SOURCE_CAMPAIGN = "campaign-20260807-002"
DATA_CUTOFF = "2023-05-31"
OOS_START = pd.Period("2023-06", freq="M")
OOS_END = pd.Period("2026-05", freq="M")
EXPECTED_IS_START = pd.Period("2018-03", freq="M")
EXPECTED_IS_END = pd.Period("2023-04", freq="M")
EXPECTED_IS_MONTHS = 62
EXPECTED_OOS_MONTHS = 36

CANDIDATES = {
    "operating_return_on_capital_employed": "aa11ccad9cfd19c6",
    "return_kurtosis_24m": "be70b24e1222fb72",
    "turnover_volatility_12m": "07f156b1d7953440",
}

LABELS = [
    "NON_CONFIRMATORY_RETROSPECTIVE_AUDIT",
    "PSEUDO_OOS_ALREADY_EXPOSED",
    "DISCOVERY_CONTAMINATED",
    "NO_VERDICT_OR_PROMOTION_EFFECT",
]


def _authenticated_factor_frames(discovery, confirmation, targets):
    """Verify cache identity against live RDS before candidate computation."""
    with silver.connect(read_only=True) as conn:
        silver.verify_live_total_return_contract(
            conn,
            discovery.meta.get("return_contract_validation_evidence"),
        )
        run.P.verify_live_asset_identity(conn, discovery, cutoff=DATA_CUTOFF)
        run._verify_confirmation_live_identity(conn, confirmation)
        discovery = run._research_input_panel(discovery)
        confirmation = run._research_input_panel(confirmation)
        discovery_df = run._ensure_factor_columns(discovery, targets)
        confirmation_df = run._ensure_factor_columns(confirmation, targets)
        approved = run._approved_signals(conn, discovery_df)
    return discovery, confirmation, discovery_df, confirmation_df, approved


def _number(value):
    if value is None or not np.isfinite(value):
        return None
    return float(value)


def _fmt(value, digits: int = 3) -> str:
    value = _number(value)
    return "-" if value is None else f"{value:.{digits}f}"


def _flag(value: bool) -> str:
    return "Y" if value else "N"


def _check(result: gate.Result, tier: str, name: str):
    return next(
        (check for check in result.checks if check.tier == tier and check.name == name),
        None,
    )


def _current_campaign_evidence(root: Path) -> dict[str, dict]:
    output: dict[str, dict] = {}
    campaign = root / "research/campaigns" / SOURCE_CAMPAIGN / "epochs"
    for manifest_path in sorted(campaign.glob("epoch-*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        for candidate in manifest["candidates"]:
            cycle_id = candidate.get("cycle_id")
            if not cycle_id:
                continue
            result_path = root / "research/runs" / cycle_id / "result.json"
            result = json.loads(result_path.read_text())
            output[candidate["name"]] = {
                "cycle_id": cycle_id,
                "pre_fdr_verdict": candidate.get("pre_fdr_verdict"),
                "report": candidate.get("report"),
                "ic_investable": result["evaluation"]["metrics"].get("ic_investable"),
                "rank_icir_investable": result["evaluation"]["metrics"].get(
                    "rank_icir_investable"
                ),
            }
    return output


def _is_frame(panel, df: pd.DataFrame) -> pd.DataFrame:
    cutoff = pd.Timestamp(DATA_CUTOFF)
    mask = (
        panel.universe
        & df["ym"].ge(gate.RESEARCH_START)
        & pd.to_datetime(df["trade_date"]).dt.normalize().le(cutoff)
        & df["ym"].lt(cutoff.to_period("M"))
        & df["ym"].lt(OOS_START - 1)
    )
    work = df.loc[mask].copy()
    work["_eligible"] = panel.investable.loc[work.index].astype(bool)
    return work


def _oos_frame(panel, df: pd.DataFrame) -> pd.DataFrame:
    mask = panel.universe & df["ym"].ge(OOS_START) & df["ym"].le(OOS_END)
    work = df.loc[mask].copy()
    work["_eligible"] = panel.investable.loc[work.index].astype(bool)
    return work


def _period_summary(series: pd.Series) -> dict[str, float | int | None]:
    clean = pd.Series(series, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    mean, t_value, pvalue = gate._hac_mean_test(clean)
    std = float(clean.std(ddof=1)) if len(clean) > 1 else float("nan")
    return {
        "months": int(len(clean)),
        "ic": _number(mean),
        "ic_std": _number(std),
        "rank_icir": _number(mean / std if np.isfinite(std) and std > 0 else np.nan),
        "hac_t": _number(t_value),
        "hac_pvalue": _number(pvalue),
    }


def _write_report(path: Path, payload: dict) -> None:
    rows = payload["factors"]
    lines = [
        f"# {payload['audit_id']}",
        "",
        "> 이 결과는 이미 discovery에 노출된 과거 구간을 다시 나눈 회고 감사다.",
        "> campaign confirmation, 최종 OOS, Gold 승격 증거로 사용할 수 없다.",
        "",
        "## 고정 감사 계약",
        "",
        f"- Labels: `{', '.join(payload['labels'])}`",
        f"- Silver source: `{payload['silver_source']}`",
        f"- Ruleset: `{payload['ruleset_version']}`",
        f"- RDS Gold APPROVED: `{payload['approved_gold_factor_count']}`개 "
        f"({', '.join(payload['approved_gold_factors']) or '없음'})",
        f"- IS signal months: `{payload['split']['is_start']} ~ {payload['split']['is_end']}` "
        f"({payload['split']['is_months']}개월)",
        f"- Boundary embargo: `{payload['split']['embargo_month']}`",
        f"- Retrospective audit signal months: `{payload['split']['oos_start']} ~ "
        f"{payload['split']['oos_end']}` ({payload['split']['oos_months']}개월)",
        f"- 자동 기준 통과 후보 {payload['candidate_count']}개를 같은 분할에서 동시에 계산했고 결과에 따른 정의 수정은 없었다.",
        "- 기존 campaign manifest, verdict, history, trial ledger 및 Gold는 변경하지 않았다.",
        "",
        "## 원래 discovery와 과거 IS 재현",
        "",
        "| factor | original full IC | original | historical IS IC | IS ICIR | IS BY q | T5 | replay verdict | auto qualified |",
        "|---|---:|---|---:|---:|---:|---:|---|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['factor']}` | {_fmt(row['original_full_discovery']['ic_investable'])} | "
            f"{row['original_full_discovery']['pre_fdr_verdict']} | "
            f"{_fmt(row['historical_is']['ic_investable'])} | "
            f"{_fmt(row['historical_is']['rank_icir_investable'])} | "
            f"{_fmt(row['historical_is']['by_qvalue'])} | "
            f"{_flag(row['historical_is']['t5_pass'])} | "
            f"{row['historical_is']['verdict']} | {_flag(row['historical_is']['auto_qualified'])} |"
        )

    lines.extend([
        "",
        "## 후반기 성능 지속성",
        "",
        f"OOS IC 기준은 절대값 `{payload['thresholds']['oos_ic']}`와 Discovery 대비 유지율 "
        f"`{payload['thresholds']['oos_ic_retention']}`를 함께 표시한다. "
        f"관측기간은 `{payload['split']['oos_months']}`개월로 공식 최소 "
        f"`{payload['thresholds']['min_oos_months']}`개월을 충족한다. 표의 T4 effect+BY는 현재 "
        "수치 기준을 회고적으로 재현한 값일 뿐이며, 이미 노출된 구간이므로 공식 confirmation이나 "
        "Gold 승격 효력은 없다.",
        "",
        f"| factor | later IC | ICIR | OOS/IS | neutral IC | neutral/investable | positive years | qualified BY q | IC>={payload['thresholds']['oos_ic']} | retention>={payload['thresholds']['oos_ic_retention']} | T4 effect+BY |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        later = row["retrospective_later_period"]
        positive = f"{later['positive_years']}/{later['year_count']}"
        lines.append(
            f"| `{row['factor']}` | {_fmt(later['ic_investable'])} | "
            f"{_fmt(later['rank_icir_investable'])} | {_fmt(later['ic_retention'])} | "
            f"{_fmt(later['neutral_ic'])} | {_fmt(later['neutral_ic_retention'])} | "
            f"{positive} | "
            f"{_fmt(later['auto_qualified_by_qvalue'])} | "
            f"{_flag(later['absolute_effect_threshold_pass'])} | "
            f"{_flag(later['retention_threshold_pass'])} | "
            f"{_flag(later['t4_effect_and_by_pass'])} |"
        )

    lines.extend([
        "",
        "## 포트폴리오 진단값",
        "",
        "수익률·비용·회전율은 승격 기준이 아니라 상위 20% 동일가중 포트폴리오 진단값이다.",
        "",
        "| factor | gross %/yr | cost %/yr | net %/yr | net IR | turnover %/yr |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        diag = row["retrospective_later_period"]["portfolio_diagnostics"]
        lines.append(
            f"| `{row['factor']}` | {_fmt(diag.get('gross'))} | {_fmt(diag.get('cost'))} | "
            f"{_fmt(diag.get('net'))} | {_fmt(diag.get('net_ir'))} | "
            f"{_fmt(diag.get('turnover'), 1)} |"
        )

    years = sorted({year for row in rows for year in row["retrospective_later_period"]["yearly_ic"]})
    lines.extend([
        "",
        "## 연도별 후반기 IC",
        "",
        "| factor | " + " | ".join(years) + " |",
        "|---|" + "|".join("---:" for _ in years) + "|",
    ])
    for row in rows:
        values = row["retrospective_later_period"]["yearly_ic"]
        lines.append(
            f"| `{row['factor']}` | "
            + " | ".join(_fmt(values.get(year)) for year in years)
            + " |"
        )

    lines.extend([
        "",
        "## 해석 제한",
        "",
        "- 이 후반 구간은 후보 생성과 기존 discovery에 이미 포함됐으므로 진짜 미관측 표본이 아니다.",
        "- 따라서 이번 값은 지금 성능 지속성을 판단하는 회고 검증이며 기존 campaign의 공식 confirmation은 아니다.",
        "- T4 effect+BY는 OOS 효과·유지율·동시 후보 BY까지만 뜻한다. campaign 귀무 보정과 Gold SQL parity는 별도다.",
        "- 이 숫자를 보고 같은 후보의 부호·룩백·산식·표본을 수정하면 안 된다.",
        "- 다음 clean campaign부터 historical holdout과 자동 qualified 규칙을 결과 전에 고정해야 한다.",
        "",
    ])
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=f"research/audits/{AUDIT_ID}",
        help="새 감사 산출물 디렉터리; 기존 경로는 덮어쓰지 않음",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        raise SystemExit(f"레포 루트에서 실행하세요: {root}")
    output = (root / args.output).resolve()
    if output.exists():
        raise SystemExit(f"기존 감사 산출물을 덮어쓰지 않습니다: {output}")

    source_manifest = json.loads(
        (root / "research/campaigns" / SOURCE_CAMPAIGN / "manifest.json").read_text()
    )
    frozen_qualified = {
        row["name"]: row["definition_hash"]
        for row in source_manifest.get("qualified_factors", [])
    }
    if frozen_qualified != CANDIDATES:
        raise SystemExit("source campaign의 자동 통과 후보 family가 감사 계약과 다릅니다")
    discovery_family_size = int(source_manifest["discovery_family_size"])

    run.load_registry()
    targets = [run.F.REGISTRY[name] for name in CANDIDATES]
    actual_hashes = {factor.name: factor.definition_hash for factor in targets}
    if actual_hashes != CANDIDATES:
        raise SystemExit(
            "사전 고정한 후보 definition hash가 달라졌습니다:\n"
            + json.dumps(actual_hashes, indent=2, ensure_ascii=False)
        )

    base = run._load()
    if base.meta.get("source") != "RDS public Silver":
        raise SystemExit("인증된 RDS public Silver 캐시가 아닙니다")
    discovery = run._scope_discovery_panel(
        base, data_cutoff=DATA_CUTOFF, oos_start=OOS_START,
    )
    confirmation = run._scope_confirmation_panel(
        base,
        data_cutoff=DATA_CUTOFF,
        oos_start=OOS_START,
        oos_end=OOS_END,
    )
    (
        discovery, confirmation, discovery_df, confirmation_df, approved,
    ) = _authenticated_factor_frames(discovery, confirmation, targets)

    is_work = _is_frame(discovery, discovery_df)
    oos_work = _oos_frame(confirmation, confirmation_df)
    is_months = pd.PeriodIndex(is_work["ym"].unique()).sort_values()
    oos_months = pd.PeriodIndex(oos_work["ym"].unique()).sort_values()
    if (
        len(is_months) != EXPECTED_IS_MONTHS
        or is_months.min() != EXPECTED_IS_START
        or is_months.max() != EXPECTED_IS_END
    ):
        raise SystemExit(f"IS 경계 불일치: {is_months.min()}~{is_months.max()} / {len(is_months)}")
    if (
        len(oos_months) != EXPECTED_OOS_MONTHS
        or oos_months.min() != OOS_START
        or oos_months.max() != OOS_END
    ):
        raise SystemExit(f"후반기 경계 불일치: {oos_months.min()}~{oos_months.max()} / {len(oos_months)}")

    is_results = [
        gate.evaluate(
            factor,
            discovery,
            discovery_df,
            existing=approved,
            trial_count=len(targets),
            oos_start=OOS_START,
            data_cutoff=DATA_CUTOFF,
            phase="discovery",
        )
        for factor in targets
    ]
    gate.apply_multiple_testing(is_results, total_trials=discovery_family_size)
    auto_qualified_hashes = {
        result.definition_hash
        for result in is_results
        if result.verdict == gate.Verdict.PROVISIONAL
    }

    oos_results = [
        gate.evaluate_oos(
            factor,
            confirmation,
            confirmation_df,
            oos_start=OOS_START,
            oos_end=OOS_END,
            data_cutoff=DATA_CUTOFF,
            discovery_ic=is_result.metrics.get("ic_investable"),
        )
        for factor, is_result in zip(targets, is_results, strict=True)
    ]
    gate.apply_oos_multiple_testing(oos_results)
    all_oos_pvalues = {
        result.definition_hash: result.metrics.get("oos_ic_p", 1.0)
        for result in oos_results
    }
    all_oos_qvalues = gate.by_qvalues(all_oos_pvalues)
    qualified_oos_qvalues = gate.by_qvalues({
        definition_hash: all_oos_pvalues[definition_hash]
        for definition_hash in auto_qualified_hashes
    })

    current = _current_campaign_evidence(root)
    factor_rows = []
    for factor, is_result, oos_result in zip(targets, is_results, oos_results, strict=True):
        col = f"f_{factor.name}"
        local_is = is_work[is_work["_eligible"]]
        local_oos = oos_work[oos_work["_eligible"]].copy()
        is_series = gate._ic_series(local_is, col, "fwd_mid")
        oos_series = oos_result.series.get("oos_ic", pd.Series(dtype=float))
        is_stats = _period_summary(is_series)
        oos_stats = _period_summary(oos_series)

        neutral_source = oos_work.copy()
        neutral_source["_neutral"] = gate._neutralized_signal(
            neutral_source, col, factor.category
        )
        neutral_series = gate._ic_series(
            neutral_source[neutral_source["_eligible"]], "_neutral", "fwd_mid"
        )
        neutral_stats = _period_summary(neutral_series)
        neutral_retention = (
            neutral_stats["ic"] / oos_result.metrics.get("oos_ic")
            if neutral_stats["ic"] is not None
            and oos_result.metrics.get("oos_ic") is not None
            and np.isfinite(neutral_stats["ic"])
            and np.isfinite(oos_result.metrics["oos_ic"])
            and oos_result.metrics["oos_ic"] > 0
            else np.nan
        )

        portfolio = gate.backtest(
            oos_work,
            col,
            "fwd_mid",
            hold=factor.rebalance_months,
            min_months=EXPECTED_OOS_MONTHS,
        )
        diagnostics = gate._public_metrics(portfolio) if portfolio is not None else {}
        yearly_ic = {
            str(year): _number(group.mean())
            for year, group in oos_series.groupby(oos_series.index.year)
        }
        positive_years = sum(
            value is not None and value > 0 for value in yearly_ic.values()
        )
        oos_ic = oos_result.metrics.get("oos_ic")
        retention = oos_result.metrics.get("oos_ic_retention")
        effect_check = _check(oos_result, "T4.1", "고정 OOS IC")
        fdr_check = _check(oos_result, "T4.2", "OOS 다중검정 FDR")
        definition_hash = factor.definition_hash
        original = current[factor.name]
        t5_check = _check(is_result, "T5.1", "Gold 신호 직교성")
        if t5_check is None:
            t5_check = _check(is_result, "T5.1", "Gold 직교성")
        factor_rows.append({
            "factor": factor.name,
            "definition_hash": definition_hash,
            "original_full_discovery": {
                "cycle_id": original["cycle_id"],
                "pre_fdr_verdict": original["pre_fdr_verdict"],
                "ic_investable": _number(original["ic_investable"]),
                "rank_icir_investable": _number(original["rank_icir_investable"]),
                "report": original["report"],
            },
            "historical_is": {
                "months": int(len(is_series)),
                "ic_full": _number(is_result.metrics.get("ic_full")),
                "ic_investable": _number(is_result.metrics.get("ic_investable")),
                "rank_icir_investable": _number(
                    is_result.metrics.get("rank_icir_investable")
                ),
                "hac_pvalue": _number(is_result.metrics.get("ic_p_investable")),
                "by_qvalue": _number(is_result.metrics.get("fdr_qvalue")),
                "verdict": is_result.verdict.value,
                "auto_qualified": definition_hash in auto_qualified_hashes,
                "failed_checks": [check.name for check in is_result.failed],
                "t5_pass": bool(t5_check and t5_check.passed),
                "t5_value": _number(t5_check.value) if t5_check else None,
                "t5_note": t5_check.note if t5_check else "T5 check missing",
                "series_summary": is_stats,
            },
            "retrospective_later_period": {
                "months": int(oos_result.metrics.get("oos_months", 0)),
                "ic_full": _number(gate._ic_series(oos_work, col, "fwd_mid").mean()),
                "ic_investable": _number(oos_ic),
                "rank_icir_investable": oos_stats["rank_icir"],
                "hac_t": _number(oos_result.metrics.get("oos_ic_t")),
                "hac_pvalue": _number(oos_result.metrics.get("oos_ic_p")),
                "all_candidates_by_qvalue": _number(all_oos_qvalues.get(definition_hash)),
                "auto_qualified_by_qvalue": _number(
                    qualified_oos_qvalues.get(definition_hash)
                ),
                "ic_retention": _number(retention),
                "neutral_ic": neutral_stats["ic"],
                "neutral_ic_retention": _number(neutral_retention),
                "neutral_rank_icir": neutral_stats["rank_icir"],
                "oos_required_ic": _number(oos_result.metrics.get("oos_required_ic")),
                "absolute_effect_threshold_pass": bool(
                    oos_ic is not None
                    and np.isfinite(oos_ic)
                    and oos_ic >= gate.TH["oos_ic"]
                ),
                "retention_threshold_pass": bool(
                    retention is not None
                    and np.isfinite(retention)
                    and retention >= gate.TH["oos_ic_retention"]
                ),
                "rank_icir_threshold_pass": bool(
                    oos_stats["rank_icir"] is not None
                    and oos_stats["rank_icir"] >= gate.TH["min_rank_icir"]
                ),
                "neutral_threshold_pass": bool(
                    neutral_stats["ic"] is not None
                    and neutral_stats["ic"] >= gate.TH["neutral_ic"]
                    and np.isfinite(neutral_retention)
                    and neutral_retention >= gate.TH["neutral_ic_retention"]
                ),
                "t4_effect_and_by_pass": bool(
                    effect_check and effect_check.passed
                    and fdr_check and fdr_check.passed
                ),
                "t4_effect_threshold": (
                    effect_check.threshold if effect_check else None
                ),
                "yearly_ic": yearly_ic,
                "positive_years": positive_years,
                "year_count": len(yearly_ic),
                "portfolio_diagnostics": diagnostics,
            },
        })

    payload = {
        "audit_id": AUDIT_ID,
        "labels": LABELS,
        "created_for": "IS 성과가 후반기에도 유지되는지 확인",
        "silver_source": base.meta.get("source"),
        "ruleset_version": gate.RULESET_VERSION,
        "campaign_impact": "NONE",
        "gold_write": False,
        "trial_ledger_write": False,
        "split": {
            "data_cutoff": DATA_CUTOFF,
            "is_start": str(EXPECTED_IS_START),
            "is_end": str(EXPECTED_IS_END),
            "is_months": EXPECTED_IS_MONTHS,
            "embargo_month": str(OOS_START - 1),
            "oos_start": str(OOS_START),
            "oos_end": str(OOS_END),
            "oos_months": EXPECTED_OOS_MONTHS,
            "last_return_month": str(OOS_END + 1),
            "closure_month": str(OOS_END + 2),
        },
        "thresholds": {
            "min_ic": gate.TH["min_ic"],
            "min_rank_icir": gate.TH["min_rank_icir"],
            "neutral_ic": gate.TH["neutral_ic"],
            "neutral_ic_retention": gate.TH["neutral_ic_retention"],
            "oos_ic": gate.TH["oos_ic"],
            "oos_ic_retention": gate.TH["oos_ic_retention"],
            "min_oos_months": gate.TH["min_oos_months"],
            "fdr_q": gate.TH["fdr_q"],
        },
        "candidate_count": len(targets),
        "source_campaign": SOURCE_CAMPAIGN,
        "discovery_family_size": discovery_family_size,
        "approved_gold_factor_count": len(approved),
        "approved_gold_factors": sorted(approved),
        "historical_is_auto_qualified": [
            factor.name for factor in targets if factor.definition_hash in auto_qualified_hashes
        ],
        "factors": factor_rows,
    }

    output.mkdir(parents=True)
    (output / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    _write_report(output / "report.md", payload)
    print(f"감사 결과: {output / 'report.md'}")
    print(f"자동 IS qualified: {payload['historical_is_auto_qualified']}")
    print("Campaign/Gold/history/trial ledger write: 없음")


if __name__ == "__main__":
    main()
