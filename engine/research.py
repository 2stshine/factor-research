"""Durable artifacts and context for repeatable agent research cycles."""
from __future__ import annotations

import json
import hashlib
import io
import os
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from engine import dividends, epochs, fundamentals
from engine.factors import Factor, Registry
from engine.gate import Check, RESEARCH_START, Result, RULESET_VERSION, Verdict
from engine.panel import Panel
from engine import research_policy


_REGISTRY_SIGNAL_CACHE_SCHEMA = "registry-signal-cache-v1"
_REGISTRY_SNAPSHOT_SCHEMA = "epoch-comparison-registry-v1"


class RegistrySignalCacheError(ValueError):
    """A present registry cache is corrupt or bound to different inputs."""


def _canonical_json_bytes(value: dict) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _frame_identity_digest(df: pd.DataFrame) -> str:
    required = ["asset_id", "ym"]
    missing = [column for column in required if column not in df]
    if missing or not df.index.is_unique:
        raise ValueError(f"registry cache row identity 계약 오류: missing={missing}")
    identity = df[required].copy()
    if "trade_date" in df:
        identity["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime(
            "%Y-%m-%d"
        )
    identity["ym"] = identity["ym"].astype(str)
    digest = hashlib.sha256()
    digest.update(pd.util.hash_pandas_object(
        identity, index=True, categorize=True,
    ).values.tobytes())
    return digest.hexdigest()


def _cache_signal_bytes(values: pd.Series) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, values.to_numpy(dtype=np.float64), allow_pickle=False)
    return buffer.getvalue()


def _load_or_compute_registry_signal(
    factor: Factor,
    df: pd.DataFrame,
    *,
    compute_context,
    cache_root: Path | None,
    snapshot_digest: str | None,
    asset_identity_digest: str | None,
    frame_identity_digest: str,
) -> pd.Series:
    """Load one content-bound registry signal or compute and certify it once."""
    if cache_root is None:
        return research_policy.compute_factor(
            factor, df, context=compute_context,
        ) * factor.predicted_sign
    for label, value in (
        ("snapshot_digest", snapshot_digest),
        ("asset_identity_digest", asset_identity_digest),
    ):
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"registry cache {label}는 SHA-256이어야 합니다")
    directory = cache_root / str(snapshot_digest)
    stem = f"{factor.definition_hash}-{factor.predicted_sign:+d}"
    values_path = directory / f"{stem}.npy"
    manifest_path = directory / f"{stem}.json"
    if values_path.exists() != manifest_path.exists():
        raise RegistrySignalCacheError(
            f"registry signal cache pair가 불완전합니다: {stem}"
        )
    expected = {
        "schema_version": _REGISTRY_SIGNAL_CACHE_SCHEMA,
        "snapshot_digest": snapshot_digest,
        "asset_identity_digest": asset_identity_digest,
        "frame_identity_digest": frame_identity_digest,
        "row_count": int(len(df)),
        "factor": factor.name,
        "definition_hash": factor.definition_hash,
        "predicted_sign": factor.predicted_sign,
    }
    if values_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload = values_path.read_bytes()
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistrySignalCacheError(
                f"registry signal cache를 읽을 수 없습니다: {stem}"
            ) from exc
        if (
            {key: manifest.get(key) for key in expected} != expected
            or manifest.get("values_sha256")
            != hashlib.sha256(payload).hexdigest()
            or manifest.get("manifest_sha256")
            != hashlib.sha256(_canonical_json_bytes({
                key: value for key, value in manifest.items()
                if key != "manifest_sha256"
            })).hexdigest()
        ):
            raise RegistrySignalCacheError(
                f"registry signal cache binding이 다릅니다: {stem}"
            )
        try:
            array = np.load(io.BytesIO(payload), allow_pickle=False)
        except (OSError, ValueError) as exc:
            raise RegistrySignalCacheError(
                f"registry signal cache 배열이 손상되었습니다: {stem}"
            ) from exc
        if array.shape != (len(df),) or np.isinf(array).any():
            raise RegistrySignalCacheError(
                f"registry signal cache shape/유한성 오류: {stem}"
            )
        return pd.Series(array, index=df.index, dtype=float)

    values = research_policy.compute_factor(
        factor, df, context=compute_context,
    ) * factor.predicted_sign
    if not isinstance(values, pd.Series) or not values.index.equals(df.index):
        raise ValueError(f"registry signal 출력 계약 오류: {factor.name}")
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError(f"registry signal에 무한값이 있습니다: {factor.name}")
    payload = _cache_signal_bytes(numeric)
    manifest = {
        **expected,
        "values_sha256": hashlib.sha256(payload).hexdigest(),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        _canonical_json_bytes(manifest)
    ).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    nonce = f".{stem}.{os.getpid()}.tmp"
    values_tmp = directory / f"{nonce}.npy"
    manifest_tmp = directory / f"{nonce}.json"
    try:
        values_tmp.write_bytes(payload)
        manifest_tmp.write_bytes(_canonical_json_bytes(manifest))
        os.replace(values_tmp, values_path)
        os.replace(manifest_tmp, manifest_path)
    finally:
        values_tmp.unlink(missing_ok=True)
        manifest_tmp.unlink(missing_ok=True)
    return numeric


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


def deserialize_result(payload: dict) -> Result:
    """Reconstruct a result only from the schema emitted by serialize_result."""
    if not isinstance(payload, dict):
        raise ValueError("동결 discovery evaluation 형식이 dict가 아닙니다")
    try:
        verdict = Verdict(payload["verdict"])
        checks = [
            Check(
                tier=str(row["tier"]),
                name=str(row["name"]),
                passed=row["passed"],
                value=row.get("value"),
                threshold=str(row.get("threshold", "")),
                note=str(row.get("note", "")),
            )
            for row in payload["checks"]
        ]
        result = Result(
            factor=str(payload["factor"]),
            definition_hash=str(payload["definition_hash"]),
            verdict=verdict,
            checks=checks,
            metrics=dict(payload["metrics"]),
            labels=[str(value) for value in payload["labels"]],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("동결 discovery evaluation schema가 손상되었습니다") from exc
    if any(check.passed not in {True, False, None} for check in result.checks):
        raise ValueError("동결 discovery check 상태가 올바르지 않습니다")
    return result


def discovery_result_artifact_binding(report: str | Path) -> dict:
    result_path = Path(report).with_name("result.json")
    if not result_path.is_file() or result_path.is_symlink():
        raise ValueError(f"discovery result artifact가 없습니다: {result_path}")
    payload = result_path.read_bytes()
    return {
        "discovery_result_artifact": str(result_path),
        "discovery_result_artifact_sha256": hashlib.sha256(payload).hexdigest(),
    }


def load_authenticated_discovery_result(
    frozen: dict,
    factor: Factor,
) -> Result:
    """Authenticate one frozen Discovery result without recomputing its gates."""
    path_value = frozen.get("discovery_result_artifact")
    expected_sha = frozen.get("discovery_result_artifact_sha256")
    if not isinstance(path_value, str) or not isinstance(expected_sha, str):
        raise ValueError("동결 discovery result artifact binding이 없습니다")
    path = Path(path_value)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"동결 discovery result artifact가 없습니다: {path}")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f"동결 discovery result artifact SHA가 다릅니다: {factor.name}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("동결 discovery result artifact JSON이 손상되었습니다") from exc
    result = deserialize_result(payload.get("evaluation"))
    strategy = payload.get("research_spec") or {}
    factor_payload = payload.get("factor") or {}
    if (
        payload.get("phase") != "discovery"
        or payload.get("ruleset_version") != RULESET_VERSION
        or result.factor != factor.name
        or result.definition_hash != factor.definition_hash
        or factor_payload.get("name") != factor.name
        or factor_payload.get("definition_hash") != factor.definition_hash
        or strategy.get("strategy_sha256") != frozen.get("strategy_sha256")
        or frozen.get("factor") != factor.name
        or frozen.get("definition_hash") != factor.definition_hash
    ):
        raise ValueError(f"동결 discovery result identity가 다릅니다: {factor.name}")
    current_p = result.metrics.get("ic_p_investable")
    frozen_p = frozen.get("pvalue")
    if (
        current_p is None or frozen_p is None
        or not np.isfinite(float(current_p))
        or abs(float(current_p) - float(frozen_p)) > 1e-12
    ):
        raise ValueError(f"동결 discovery p값 binding이 다릅니다: {factor.name}")
    from engine import gate

    digest = gate.discovery_evidence_digest(
        result,
        ruleset_version=frozen.get("evidence_ruleset_version"),
    )
    if digest != frozen.get("discovery_evidence_digest"):
        raise ValueError(f"동결 discovery T0-T3 digest가 다릅니다: {factor.name}")
    return result


def factor_relationships(
    panel: Panel,
    df: pd.DataFrame,
    factor: Factor,
    registry: Registry,
) -> list[dict]:
    """Median monthly investable-universe signal correlation with local factors."""
    research_policy.assert_research_input_frame(df)
    target = f"f_{factor.name}"
    if target not in df:
        return []
    eligible = panel.investable.reindex(df.index).fillna(False)
    output = []
    for other in registry:
        other_col = f"f_{other.name}"
        if other.name == factor.name:
            continue
        try:
            research_policy.assert_allowed_lookback(
                name=other.name, source=other.source, params=other.params,
            )
        except ValueError:
            continue
        if other_col in df:
            other_values = df[other_col]
        elif set(other.needs).issubset(df.columns):
            try:
                computed = (
                    research_policy.compute_factor(other, df)
                    * other.predicted_sign
                )
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


def factor_relationships_batch(
    panel: Panel,
    df: pd.DataFrame,
    factors: list[Factor],
    registry: Registry,
    *,
    cache_root: str | Path | None = None,
    snapshot_digest: str | None = None,
    asset_identity_digest: str | None = None,
) -> dict[str, list[dict]]:
    """Compute registry signals once and reuse them for an epoch batch.

    The cache is invocation-local and contains only the authenticated research
    view. Nothing is written to the panel cache or Gold. Only the rectangular
    target-by-registry block is evaluated: registry-by-registry pairs do not
    affect novelty. Pairwise finite-row filtering preserves the original
    Spearman/NaN sample, minimum count, and median statistic exactly.
    """
    research_policy.assert_research_input_frame(df)
    names = [factor.name for factor in factors]
    if len(names) != len(set(names)):
        raise ValueError("batch 관계 대상 팩터 이름은 고유해야 합니다")
    missing_targets = [name for name in names if f"f_{name}" not in df]
    if missing_targets:
        raise ValueError(
            f"batch 관계 계산에 대상 신호가 없습니다: {missing_targets}"
        )

    signals: dict[str, pd.Series] = {
        factor.name: pd.to_numeric(df[f"f_{factor.name}"], errors="coerce")
        for factor in factors
    }
    comparable: list[Factor] = []
    compute_context = None
    cache_path = Path(cache_root) if cache_root is not None else None
    frame_digest = _frame_identity_digest(df) if cache_path is not None else ""
    for other in registry:
        try:
            research_policy.assert_allowed_lookback(
                name=other.name, source=other.source, params=other.params,
            )
        except ValueError:
            continue
        column = f"f_{other.name}"
        if other.name in signals:
            comparable.append(other)
            continue
        if column in df:
            values = df[column]
        elif set(other.needs).issubset(df.columns):
            try:
                if compute_context is None:
                    compute_context = (
                        research_policy.build_factor_compute_context(df)
                    )
                values = _load_or_compute_registry_signal(
                    other,
                    df,
                    compute_context=compute_context,
                    cache_root=cache_path,
                    snapshot_digest=snapshot_digest,
                    asset_identity_digest=asset_identity_digest,
                    frame_identity_digest=frame_digest,
                )
            except RegistrySignalCacheError:
                raise
            except Exception:
                continue
            if not isinstance(values, pd.Series) or not values.index.equals(df.index):
                continue
        else:
            continue
        signals[other.name] = pd.to_numeric(values, errors="coerce")
        comparable.append(other)

    eligible = panel.investable.reindex(df.index).fillna(False)
    sample_mask = eligible & df["ym"].ge(RESEARCH_START)
    signal_frame = pd.DataFrame(
        {name: values.reindex(df.index) for name, values in signals.items()},
        index=df.index,
    ).replace([np.inf, -np.inf], np.nan)
    signal_frame.insert(0, "ym", df["ym"])
    signal_frame = signal_frame.loc[sample_mask]

    pair_values: dict[tuple[str, str], list[float]] = {
        (target, other.name): []
        for target in names
        for other in comparable
        if other.name != target
    }
    for _, month in signal_frame.groupby("ym", sort=True):
        arrays = {
            name: month[name].to_numpy(dtype=float, copy=False)
            for name in signals
        }
        for (target, other), values in pair_values.items():
            left, right = arrays[target], arrays[other]
            valid = np.isfinite(left) & np.isfinite(right)
            if int(valid.sum()) < 30:
                continue
            value = stats.spearmanr(left[valid], right[valid]).statistic
            if pd.notna(value):
                values.append(float(value))

    categories = {factor.name: factor.category for factor in registry}
    output: dict[str, list[dict]] = {}
    for target in names:
        rows = []
        for other in comparable:
            if other.name == target:
                continue
            monthly = pair_values[(target, other.name)]
            if not monthly:
                continue
            median = float(np.median(monthly))
            rows.append({
                "factor": other.name,
                "category": categories[other.name],
                "median_spearman": median,
                "abs_median_spearman": abs(median),
                "months": len(monthly),
            })
        output[target] = sorted(
            rows,
            key=lambda row: row["abs_median_spearman"],
            reverse=True,
        )
    return output


def _read_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def attempted_factor_names(research_dir: str | Path = "research") -> frozenset[str]:
    """Return factor names already committed to the append-only trial history."""
    return frozenset(
        str(row["factor"])
        for row in _read_history(Path(research_dir) / "history.jsonl")
        if isinstance(row.get("factor"), str) and row["factor"]
    )


def registry_snapshot(registry: Registry) -> dict:
    """Freeze the exact novelty-comparison registry for one epoch.

    Candidate files created for a later epoch must not expand an already
    running epoch's comparison set or invalidate its signal cache.  Existing
    definitions are still content-bound and may neither disappear nor change.
    """
    factors = [
        {
            "name": factor.name,
            "definition_hash": factor.definition_hash,
            "category": factor.category,
            "predicted_sign": factor.predicted_sign,
        }
        for factor in sorted(registry, key=lambda item: item.name)
    ]
    payload = {
        "schema_version": _REGISTRY_SNAPSHOT_SCHEMA,
        "factors": factors,
    }
    payload["registry_digest"] = hashlib.sha256(
        _canonical_json_bytes(payload)
    ).hexdigest()
    return payload


def bind_registry_snapshot(snapshot: dict, registry: Registry) -> list[Factor]:
    """Resolve only frozen definitions; ignore later additions, fail on drift."""
    if not isinstance(snapshot, dict):
        raise ValueError("epoch comparison registry snapshot이 없습니다")
    payload = dict(snapshot)
    observed_digest = payload.pop("registry_digest", None)
    if (
        payload.get("schema_version") != _REGISTRY_SNAPSHOT_SCHEMA
        or not isinstance(payload.get("factors"), list)
        or observed_digest != hashlib.sha256(
            _canonical_json_bytes(payload)
        ).hexdigest()
    ):
        raise ValueError("epoch comparison registry snapshot이 손상됐습니다")
    resolved: list[Factor] = []
    names: set[str] = set()
    for row in payload["factors"]:
        if not isinstance(row, dict) or set(row) != {
            "name", "definition_hash", "category", "predicted_sign",
        }:
            raise ValueError("epoch comparison registry row schema가 다릅니다")
        name = row.get("name")
        if not isinstance(name, str) or name in names or name not in registry:
            raise ValueError(f"epoch comparison registry factor가 없습니다: {name}")
        factor = registry[name]
        expected = {
            "name": factor.name,
            "definition_hash": factor.definition_hash,
            "category": factor.category,
            "predicted_sign": factor.predicted_sign,
        }
        if row != expected:
            raise ValueError(f"epoch comparison registry 정의가 바뀌었습니다: {name}")
        names.add(name)
        resolved.append(factor)
    return resolved


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


ACTIVE_CAMPAIGN_STATUSES = frozenset({
    "OPEN", "AWAITING_IMPLEMENTATION", "READY_FOR_CONFIRMATION",
})


def is_active_campaign(campaign: dict) -> bool:
    """Whether this campaign is the in-flight one under the current protocol."""
    return (
        campaign.get("protocol_version") == epochs.PROTOCOL_VERSION
        and campaign.get("status") in ACTIVE_CAMPAIGN_STATUSES
    )


def exposed_after_cutoff(
    row: dict,
    *,
    visible_cutoff,
    active_campaign_id: str | None,
) -> bool:
    """Whether this trial's results sit behind the seal for the current context.

    The single definition of the boundary. Anything that derives context from
    the trial ledger must call this rather than restate the comparison, so the
    boundary moves in one place.
    """
    belongs_to_active_campaign = bool(
        active_campaign_id is not None
        and row.get("campaign_id") == active_campaign_id
    )
    return bool(
        visible_cutoff is not None
        and not belongs_to_active_campaign
        and row.get("data_cutoff")
        and pd.Timestamp(row["data_cutoff"]).normalize() > visible_cutoff
    )


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
        if is_active_campaign(campaign):
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
    raw_df = panel.monthly
    visible_cutoff = pd.Timestamp(context_cutoff).normalize() if context_cutoff else None
    if context_campaign is not None:
        visible_cutoff = pd.Timestamp(
            context_campaign["discovery"]["data_cutoff"]
        ).normalize()
    if visible_cutoff is not None:
        raw_df = raw_df[
            pd.to_datetime(raw_df["trade_date"]).dt.normalize().le(visible_cutoff)
        ].copy()
    df = research_policy.research_input_frame(raw_df)
    if context_campaign is not None:
        discovery_signal_end = pd.Period(
            context_campaign["discovery"]["signal_end"], freq="M",
        )
    elif visible_cutoff is not None:
        discovery_signal_end = visible_cutoff.to_period("M") - 1
    else:
        discovery_signal_end = df["ym"].max()
    base_inputs = {
        "market_cap", "adv20", "trading_value", "shares", "market",
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
    raw_period_start = panel.meta.get("parent_panel_start", raw_df["ym"].min())
    raw_period_end = panel.meta.get("parent_panel_end", raw_df["ym"].max())
    lines = [
        "# Factor research context",
        "",
        "> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.",
        "",
        "## Frozen research state",
        "",
        f"- Silver source: `{panel.meta.get('source')}`",
        f"- Raw Silver period inside context boundary: `{raw_period_start}` ~ `{raw_period_end}`",
        f"- Visible Silver data period: `{df['ym'].min()}` ~ `{df['ym'].max()}`",
        f"- Research input floor: `{research_policy.RESEARCH_INPUT_START}`",
        f"- Maximum factor lookback: `{research_policy.MAX_FACTOR_LOOKBACK_MONTHS}` months",
        f"- Discovery signal evaluation period: `{RESEARCH_START}` ~ `{discovery_signal_end}`",
        f"- Discovery return-support cutoff: `{visible_cutoff.date() if visible_cutoff is not None else '-'}`",
        f"- Rows/months/assets: `{len(df):,}` / `{df['ym'].nunique()}` / `{df['asset_id'].nunique():,}`",
        (
            "- Historical feature return: "
            f"`{panel.meta.get('feature_price_field')}` / "
            f"`{panel.meta.get('feature_return_methodology')}`"
        ),
        (
            "- Forward-label return: "
            f"`{panel.meta.get('label_return_field')}` / "
            f"`{panel.meta.get('label_return_methodology')}` / "
            f"`{panel.meta.get('label_return_usage')}` / "
            f"revision=`{panel.meta.get('label_revision_semantics')}` / "
            f"candidate_access=`{panel.meta.get('label_candidate_access')}`"
        ),
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
            if exposed_after_cutoff(
                row,
                visible_cutoff=visible_cutoff,
                active_campaign_id=active_campaign_id,
            ):
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
        omitted = len(history) - 30
        if omitted > 0:
            lines += [
                "",
                f"> 위 표는 최근 30건만 담는다. 오래된 {omitted}건은 생략됐다. "
                "전문은 `research/history.jsonl`.",
            ]
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
