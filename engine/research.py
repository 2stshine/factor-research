"""Durable artifacts and context for repeatable agent research cycles."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from engine import dividends, epochs, fundamentals
from engine.factors import Factor, Registry
from engine.gate import RESEARCH_START, Result, RULESET_VERSION
from engine.panel import Panel


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (np.bool_, np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, pd.Period):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def serialize_result(result: Result) -> dict:
    return {
        "factor": result.factor,
        "definition_hash": result.definition_hash,
        "verdict": result.verdict.value,
        "metrics": {key: _jsonable(value) for key, value in result.metrics.items()},
        "labels": list(result.labels),
        "checks": [
            {
                "tier": check.tier,
                "name": check.name,
                "passed": None if check.passed is None else bool(check.passed),
                "value": _jsonable(check.value),
                "threshold": check.threshold,
                "note": check.note,
            }
            for check in result.checks
        ],
    }


def factor_relationships(
    panel: Panel,
    df: pd.DataFrame,
    factor: Factor,
    registry: Registry,
) -> list[dict]:
    """Median monthly investable-universe signal correlation with local factors."""
    target = f"f_{factor.name}"
    if target not in df:
        return []
    eligible = panel.investable.reindex(df.index).fillna(False)
    output = []
    for other in registry:
        other_col = f"f_{other.name}"
        if other.name == factor.name:
            continue
        if other_col in df:
            other_values = df[other_col]
        elif set(other.needs).issubset(df.columns):
            try:
                computed = other.compute(df) * other.predicted_sign
            except Exception:
                continue
            if not isinstance(computed, pd.Series) or not computed.index.equals(df.index):
                continue
            other_values = computed
        else:
            continue
        monthly = []
        sample = df.loc[
            eligible & df["ym"].ge(RESEARCH_START), ["ym", target]
        ].copy()
        sample[other_col] = other_values.reindex(sample.index)
        for _, group in sample.groupby("ym"):
            valid = group[[target, other_col]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(valid) < 30:
                continue
            rho = stats.spearmanr(valid[target], valid[other_col]).statistic
            if pd.notna(rho):
                monthly.append(float(rho))
        if monthly:
            median = float(np.median(monthly))
            output.append({
                "factor": other.name,
                "category": other.category,
                "median_spearman": median,
                "abs_median_spearman": abs(median),
                "months": len(monthly),
            })
    return sorted(output, key=lambda row: row["abs_median_spearman"], reverse=True)


def _read_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def assert_new_candidate(
    factor: Factor,
    research_spec: dict,
    *,
    research_dir: str | Path = "research",
    attempted_definition_hashes: set[str] | frozenset[str] = frozenset(),
) -> None:
    """Refuse accidental retests or in-place edits of an evaluated strategy."""
    if factor.definition_hash in attempted_definition_hashes:
        raise ValueError(
            f"시행 원장에 이미 평가한 definition hash입니다: {factor.definition_hash}"
        )
    history = _read_history(Path(research_dir) / "history.jsonl")
    strategy_file = research_spec.get("strategy_file")
    for row in history:
        if row.get("definition_hash") == factor.definition_hash:
            raise ValueError(
                f"이미 평가한 definition hash입니다: {factor.definition_hash} "
                f"({row.get('cycle_id')})"
            )
        if row.get("factor") == factor.name:
            raise ValueError(
                f"이미 평가한 factor 이름입니다: {factor.name}. 새 이름과 새 파일을 사용하세요."
            )
        if strategy_file and row.get("strategy_file") == strategy_file:
            raise ValueError(
                f"이미 평가한 전략 파일입니다: {strategy_file}. 기존 파일을 덮어쓰지 마세요."
            )


def _safe(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_context(
    panel: Panel,
    registry: Registry,
    *,
    research_dir: str | Path = "research",
    context_cutoff: str | None = None,
) -> Path:
    """Write the compact state that the next agent loop must read first."""
    root = Path(research_dir)
    context_dir = root / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    history = _read_history(root / "history.jsonl")
    finalized_cycles: dict[str, dict] = {}
    campaigns = epochs.context_rows(root)
    active_campaigns = []
    for campaign_row in campaigns:
        campaign = epochs.load_campaign(root, campaign_row["campaign_id"])
        if (
            campaign.get("protocol_version") == epochs.PROTOCOL_VERSION
            and campaign.get("status") in {
                "OPEN", "AWAITING_IMPLEMENTATION", "READY_FOR_CONFIRMATION",
            }
        ):
            active_campaigns.append(campaign)
        for reference in campaign["epochs"]:
            epoch = epochs.load_epoch(root, campaign["campaign_id"], reference["epoch_id"])
            if epoch["status"] != "CLOSED":
                continue
            for candidate in epoch["candidates"]:
                if candidate.get("cycle_id"):
                    finalized_cycles[candidate["cycle_id"]] = candidate
    if len(active_campaigns) > 1:
        raise ValueError("동시에 진행 중인 current-protocol campaign이 둘 이상입니다")
    context_campaign = active_campaigns[0] if active_campaigns else None
    df = panel.monthly
    visible_cutoff = pd.Timestamp(context_cutoff).normalize() if context_cutoff else None
    if context_campaign is not None:
        visible_cutoff = pd.Timestamp(
            context_campaign["discovery"]["data_cutoff"]
        ).normalize()
    if visible_cutoff is not None:
        df = df[
            pd.to_datetime(df["trade_date"]).dt.normalize().le(visible_cutoff)
        ].copy()
    if context_campaign is not None:
        discovery_signal_end = pd.Period(
            context_campaign["discovery"]["signal_end"], freq="M",
        )
    elif visible_cutoff is not None:
        discovery_signal_end = visible_cutoff.to_period("M") - 1
    else:
        discovery_signal_end = df["ym"].max()
    base_inputs = {
        "return_close", "market_cap", "adv20", "trading_value", "shares", "market",
        "adj_close", "amihud_illiquidity_1m", "amihud_observations_1m",
        "daily_volatility_252d", "daily_return_observations_252d",
        "max_daily_return_1m", "max_daily_return_observations_1m",
        "price_high_252d", "price_high_observations_252d",
    }
    available = sorted(
        (
            base_inputs
            | set(fundamentals.PIT_FEATURES)
            | set(dividends.PIT_FEATURES)
        )
        & set(df.columns)
    )
    lines = [
        "# Factor research context",
        "",
        "> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.",
        "",
        "## Frozen research state",
        "",
        f"- Silver source: `{panel.meta.get('source')}`",
        f"- Visible Silver data period: `{df['ym'].min()}` ~ `{df['ym'].max()}`",
        f"- Discovery signal evaluation period: `{RESEARCH_START}` ~ `{discovery_signal_end}`",
        f"- Discovery return-support cutoff: `{visible_cutoff.date() if visible_cutoff is not None else '-'}`",
        f"- Rows/months/assets: `{len(df):,}` / `{df['ym'].nunique()}` / `{df['asset_id'].nunique():,}`",
        f"- Return field: `{panel.meta.get('return_field')}`",
        f"- Return methodology: `{panel.meta.get('return_methodology')}`",
        f"- Gate ruleset: `{RULESET_VERSION}`",
        f"- Research protocol: `{epochs.PROTOCOL_VERSION}`",
        f"- Recorded autonomous cycles: `{len(history)}`",
        (
            f"- Active sealed campaign: `{context_campaign['campaign_id']}`; "
            "OOS rows and post-cutoff outcomes are hidden from strategy context"
            if context_campaign is not None else
            "- Active sealed campaign: `-`"
        ),
        f"- Strategy context cutoff: `{visible_cutoff.date() if visible_cutoff is not None else '-'}`",
        "",
        "## Sealed-OOS campaigns",
        "",
    ]
    if campaigns:
        lines += [
            "| campaign | status | discovery cutoff | OOS | OOS start | epochs | qualified | latest reflection |",
            "|---|---|---|---|---|---:|---:|---|",
        ]
        for row in campaigns:
            lines.append(
                f"| `{row['campaign_id']}` | {row['status']} | `{row['data_cutoff']}` | "
                f"{row['oos_status']} | `{row['oos_start']}` | {row['epochs']} | {row['qualified']} | "
                f"`{row['latest_reflection'] or '-'}` |"
            )
    else:
        lines.append("아직 campaign 없음. 새 연구는 campaign과 epoch을 먼저 사전등록한다.")
    lines += [
        "",
        "## Available strategy inputs",
        "",
        "| column | overall coverage | latest-month coverage |",
        "|---|---:|---:|",
    ]
    latest = df["ym"].eq(df["ym"].max())
    for column in available:
        lines.append(
            f"| `{column}` | {df[column].notna().mean():.1%} | {df.loc[latest, column].notna().mean():.1%} |"
        )
    lines += [
        "",
        "## Registered factors",
        "",
        "| factor | category | family | definition hash | inputs |",
        "|---|---|---|---|---|",
    ]
    for factor in registry:
        lines.append(
            f"| `{factor.name}` | {factor.category} | `{factor.family or factor.name}` | "
            f"`{factor.definition_hash}` | {_safe(', '.join(factor.needs) or '-')} |"
        )
    lines += ["", "## Prior autonomous cycles", ""]
    if not history:
        lines.append("아직 기록 없음.")
    else:
        lines += [
            "| cycle | factor | family | ruleset | verdict | failed checks | strongest relation | report |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in history[-30:]:
            active_campaign_id = (
                context_campaign["campaign_id"] if context_campaign else None
            )
            belongs_to_active_campaign = bool(
                active_campaign_id is not None
                and row.get("campaign_id") == active_campaign_id
            )
            exposed_after_cutoff = bool(
                visible_cutoff is not None
                and not belongs_to_active_campaign
                and row.get("data_cutoff")
                and pd.Timestamp(row["data_cutoff"]).normalize() > visible_cutoff
            )
            if exposed_after_cutoff:
                lines.append(
                    f"| `{row['cycle_id']}` | `{row['factor']}` | "
                    f"`{row.get('family') or row['factor']}` | "
                    f"`{row.get('ruleset_version') or '-'}` | WITHHELD_POST_CUTOFF | "
                    "봉인 경계 뒤 결과이므로 숨김 | - | - |"
                )
                continue
            finalized = finalized_cycles.get(row["cycle_id"], {})
            failed = ", ".join(
                finalized.get("failed_checks", row.get("failed_checks", []))
            ) or "-"
            relation = row.get("strongest_relationship") or {}
            relation_text = (
                f"{relation.get('factor')} ({relation.get('median_spearman', 0):.2f})"
                if relation else "-"
            )
            report = row.get("report") or "-"
            report_text = f"`{_safe(report)}`" if report != "-" else "-"
            lines.append(
                f"| `{row['cycle_id']}` | `{row['factor']}` | `{row.get('family') or row['factor']}` | "
                f"`{row.get('ruleset_version') or '-'}` | {finalized.get('verdict', row['verdict'])} | "
                f"{_safe(failed)} | "
                f"{_safe(relation_text)} | {report_text} |"
            )
    lines.append("")
    path = context_dir / "latest.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def record_cycle(
    panel: Panel,
    registry: Registry,
    factor: Factor,
    result: Result,
    research_spec: dict,
    relationships: list[dict],
    *,
    research_dir: str | Path = "research",
    campaign_id: str | None = None,
    epoch_id: str | None = None,
    phase: str = "full",
) -> tuple[Path, Path]:
    """Persist an immutable result bundle, append history, and refresh context."""
    root = Path(research_dir)
    history_path = root / "history.jsonl"
    history = _read_history(history_path)
    cycle_id = f"cycle-{len(history) + 1:04d}-{factor.name}"
    run_dir = root / "runs" / cycle_id
    if run_dir.exists():
        raise FileExistsError(f"연구 사이클이 이미 존재합니다: {run_dir}")
    run_dir.mkdir(parents=True)

    serialized = serialize_result(result)
    payload = {
        "cycle_id": cycle_id,
        "campaign_id": campaign_id,
        "epoch_id": epoch_id,
        "phase": phase,
        "ruleset_version": RULESET_VERSION,
        "research_start": str(RESEARCH_START),
        "data_cutoff": str(panel.monthly["trade_date"].max().date()),
        "factor": {
            "name": factor.name,
            "family": factor.family or factor.name,
            "category": factor.category,
            "definition_hash": factor.definition_hash,
            "predicted_sign": factor.predicted_sign,
            "params": factor.params,
            "rebalance_months": factor.rebalance_months,
            "needs": list(factor.needs),
            "source": factor.source,
        },
        "research_spec": research_spec,
        "evaluation": serialized,
        "relationships": relationships,
    }
    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_jsonable) + "\n",
        encoding="utf-8",
    )

    failed = [check for check in serialized["checks"] if check["passed"] is False]
    verdict_label = (
        f"PRE_FDR / {serialized['verdict']}"
        if phase == "discovery" else serialized["verdict"]
    )
    lines = [
        f"# {cycle_id}", "",
        f"- Verdict: **{verdict_label}**",
        f"- Research phase: **{phase.upper()}**",
        f"- Campaign / epoch: `{campaign_id or '-'}` / `{epoch_id or '-'}`",
        f"- OOS: **{'SEALED' if phase == 'discovery' else 'REVEALED'}**",
        f"- Definition hash: `{factor.definition_hash}`",
        f"- Data cutoff / ruleset: `{payload['data_cutoff']}` / `{RULESET_VERSION}`",
        f"- Common evaluation start: `{RESEARCH_START}`",
        f"- Strategy file: `{research_spec.get('strategy_file', '-')}`",
        (
            "- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인"
            if phase == "discovery"
            else "- Final confirmation decision: campaign confirmation artifact를 확인"
        ),
        "",
        "## Hypothesis", "",
        research_spec["thesis"], "",
        "## Mechanism", "",
        research_spec["mechanism"], "",
        "## Pre-registered falsification", "",
        research_spec["falsification"], "",
        "## Validation performed", "",
        (
            "동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. "
            "최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다."
            if phase == "discovery" else
            "동결된 campaign 후보를 봉인 OOS에서 한 번 확인했다."
        ), "",
        "| tier | check | pass | value | threshold |",
        "|---|---|---:|---:|---|",
    ]
    for check in serialized["checks"]:
        status = "PENDING" if check["passed"] is None else ("Y" if check["passed"] else "N")
        lines.append(
            f"| {check['tier']} | {_safe(check['name'])} | {status} | "
            f"{_safe(check['value'])} | {_safe(check['threshold'])} |"
        )
    lines += ["", "## Result", ""]
    if serialized["metrics"]:
        lines += ["| metric | value |", "|---|---:|"]
        for key, value in serialized["metrics"].items():
            lines.append(f"| `{key}` | {_safe(value)} |")
    else:
        lines.append("성과 계산 전에 조기 종료됨.")
    lines += ["", "### Failed checks", ""]
    lines += [f"- `{row['tier']}` {row['name']}: {row['value']} ({row['threshold']})" for row in failed] or ["- 없음"]
    lines += ["", "## Relationship with registered factors", ""]
    if relationships:
        lines += [
            "| factor | category | median monthly Spearman | months |",
            "|---|---|---:|---:|",
        ]
        for row in relationships[:15]:
            lines.append(
                f"| `{row['factor']}` | {row['category']} | {row['median_spearman']:.3f} | {row['months']} |"
            )
    else:
        lines.append("비교 가능한 기존 팩터 신호가 없음.")
    lines += [
        "", "## Expected relationship and data notes", "",
        f"- Expected relationship: {research_spec['expected_relationship']}",
        f"- Data notes: {research_spec['data_notes']}", "",
    ]
    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    history_row = {
        "cycle_id": cycle_id,
        "campaign_id": campaign_id,
        "epoch_id": epoch_id,
        "phase": phase,
        "factor": factor.name,
        "family": factor.family or factor.name,
        "definition_hash": factor.definition_hash,
        "verdict": serialized["verdict"],
        "data_cutoff": payload["data_cutoff"],
        "ruleset_version": RULESET_VERSION,
        "failed_checks": [row["name"] for row in failed],
        "metrics": {
            key: serialized["metrics"].get(key)
            for key in (
                "ic_full", "ic_investable", "rank_icir_investable",
                "ic_t_full", "ic_p_investable", "neutral_ic",
                "neutral_ic_retention", "oos_discovery_ic", "oos_ic",
                "oos_ic_retention", "oos_required_ic", "oos_ic_p",
                "turnover", "net", "net_ir",
            )
            if key in serialized["metrics"]
        },
        "strongest_relationship": relationships[0] if relationships else None,
        "strategy_file": research_spec.get("strategy_file"),
        "report": str(report_path),
    }
    root.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(history_row, ensure_ascii=False, default=_jsonable) + "\n")
    context_path = write_context(panel, registry, research_dir=root)
    return report_path, context_path
