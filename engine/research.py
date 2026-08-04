"""Durable artifacts and context for repeatable agent research cycles."""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

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
                "passed": bool(check.passed),
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
) -> None:
    """Refuse accidental retests or in-place edits of an evaluated strategy."""
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
) -> Path:
    """Write the compact state that the next agent loop must read first."""
    root = Path(research_dir)
    context_dir = root / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    history = _read_history(root / "history.jsonl")
    df = panel.monthly
    base_inputs = {
        "return_close", "market_cap", "adv20", "trading_value", "shares", "market",
    }
    factor_inputs = {need for factor in registry for need in factor.needs}
    available = sorted((base_inputs | factor_inputs) & set(df.columns))
    lines = [
        "# Factor research context",
        "",
        "> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.",
        "",
        "## Frozen research state",
        "",
        f"- Silver source: `{panel.meta.get('source')}`",
        f"- Silver data period: `{df['ym'].min()}` ~ `{df['ym'].max()}`",
        f"- Common evaluation period: `{RESEARCH_START}` ~ `{df['ym'].max()}`",
        f"- Rows/months/assets: `{len(df):,}` / `{df['ym'].nunique()}` / `{df['asset_id'].nunique():,}`",
        f"- Return field: `{panel.meta.get('return_field')}`",
        f"- Gate ruleset: `{RULESET_VERSION}`",
        f"- Recorded autonomous cycles: `{len(history)}`",
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
        "| factor | category | family | definition hash | hypothesis |",
        "|---|---|---|---|---|",
    ]
    for factor in registry:
        lines.append(
            f"| `{factor.name}` | {factor.category} | `{factor.family or factor.name}` | "
            f"`{factor.definition_hash}` | {_safe(factor.hypothesis)} |"
        )
    lines += ["", "## Prior autonomous cycles", ""]
    if not history:
        lines.append("아직 기록 없음.")
    else:
        lines += [
            "| cycle | factor | verdict | key result | failed checks | strongest relation |",
            "|---|---|---|---|---|---|",
        ]
        for row in history[-30:]:
            failed = ", ".join(row.get("failed_checks", [])) or "-"
            relation = row.get("strongest_relationship") or {}
            relation_text = (
                f"{relation.get('factor')} ({relation.get('median_spearman', 0):.2f})"
                if relation else "-"
            )
            metrics = row.get("metrics") or {}
            if metrics.get("ic_investable") is not None:
                key_result = f"IC={metrics.get('ic_investable'):.3f}"
                if metrics.get("oos_ic") is not None:
                    key_result += f", OOS IC={metrics.get('oos_ic'):.3f}"
            elif metrics.get("net") is not None and metrics.get("net_ir") is not None:
                key_result = f"net={metrics.get('net'):.2f}%, IR={metrics.get('net_ir'):.2f}"
            else:
                key_result = "IC 계산 전 조기종료"
            lines.append(
                f"| `{row['cycle_id']}` | `{row['factor']}` | {row['verdict']} | "
                f"{_safe(key_result)} | {_safe(failed)} | {_safe(relation_text)} |"
            )
    lines += [
        "",
        "## Next-loop constraints",
        "",
        "- 기존 definition hash를 재시험하지 않는다.",
        "- 결과를 보기 전에 가설·메커니즘·반증 기준과 전략 파일을 먼저 고정한다.",
        "- 실패한 정의를 덮어쓰지 않는다. 수정 아이디어는 새 이름 또는 새 버전 파일로 등록한다.",
        "- 게이트, 패널, 비용모형, OOS 시작점과 기존 결과를 후보에 유리하게 수정하지 않는다.",
        "- 한 루프에서는 후보 하나만 새로 만든다.",
        "- 후보 하나는 단일 경제 신호만 사용한다. 여러 팩터의 순위·점수를 가중합하지 않는다.",
        "- 수익률·IR은 진단값이며 승격 판정은 무결성·IC 최소요건·IC 강건성으로 한다.",
        "- `publish --apply`를 실행하지 않는다.",
        "",
    ]
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

    failed = [check for check in serialized["checks"] if not check["passed"]]
    lines = [
        f"# {cycle_id}", "",
        f"- Verdict: **{serialized['verdict']}**",
        f"- Definition hash: `{factor.definition_hash}`",
        f"- Data cutoff / ruleset: `{payload['data_cutoff']}` / `{RULESET_VERSION}`",
        f"- Common evaluation start: `{RESEARCH_START}`",
        f"- Strategy file: `{research_spec.get('strategy_file', '-')}`",
        "",
        "## Hypothesis", "",
        research_spec["thesis"], "",
        "## Mechanism", "",
        research_spec["mechanism"], "",
        "## Pre-registered falsification", "",
        research_spec["falsification"], "",
        "## Validation performed", "",
        "동일 Silver 월말 PIT 패널과 고정 유니버스에서 T0~T5 게이트를 순차 적용했다. "
        "앞 단계 hard fail 이후의 검사는 실행하지 않았다.", "",
        "| tier | check | pass | value | threshold |",
        "|---|---|---:|---:|---|",
    ]
    for check in serialized["checks"]:
        lines.append(
            f"| {check['tier']} | {_safe(check['name'])} | {'Y' if check['passed'] else 'N'} | "
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
                "ic_full", "ic_investable", "ic_t_full", "ic_p_investable",
                "oos_ic", "oos_ic_p", "turnover", "net", "net_ir",
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
