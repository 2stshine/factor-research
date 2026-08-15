"""Synthetic-null calibration of the *actual* T0-T5 gate."""
from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from engine import gate
from engine import panel as panel_engine
from engine.boundaries import CampaignWindow, QUALIFICATION_POLICY
from engine.factors import Factor
from engine.panel import Panel
from engine import research_policy


_CHECKPOINT_SCHEMA_VERSION = 2
_GENERATOR_SUITE = "null-v2"
_GENERATOR_KINDS = ("random", "ar1_095", "ar1_0999", "frozen")
_REBOUND_EVIDENCE_FIELDS = {
    "discovery_family_digest",
    "oos_family_digest",
}
_OUTPUT_COLUMNS = (
    "calibration_unit", "generator_suite", "qualification_policy", "kind",
    "replicate", "pass", "promoted_count", "revealed_count",
    "discovery_family_size", "oos_family_size", "discovery_family_digest",
    "oos_family_digest", "gold_family_digest", "confirmation_snapshot_digest",
    "null_definition_digest", "max_ic_investable", "fdr_q",
    "neutral_ic_retention_floor", "oos_ic_floor", "oos_ic_retention_floor",
    "max_gold_signal_corr_threshold", "min_gold_signal_corr_months", "seed",
    "gold_signal_count", "ruleset_version", "data_cutoff", "oos_start",
    "oos_end", "research_data_cutoff",
)


def _json_ready(value):
    """Convert NumPy-heavy RNG/output data to strict, stable JSON values."""
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, (np.bool_, np.integer, np.floating)):
        return _json_ready(value.item())
    if isinstance(value, (pd.Period, pd.Timestamp)):
        return str(value)
    if isinstance(value, float) and not np.isfinite(value):
        raise ValueError("귀무 보정 checkpoint에는 비유한 실수를 저장할 수 없습니다")
    return value


def _canonical_json(value) -> bytes:
    return json.dumps(
        _json_ready(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _existing_signal_digest(existing: dict[str, pd.Series] | None) -> str:
    digest = hashlib.sha256()
    for name, series in sorted((existing or {}).items()):
        digest.update(str(name).encode("utf-8"))
        digest.update(str(series.dtype).encode("utf-8"))
        digest.update(pd.util.hash_pandas_object(
            series, index=True, categorize=True,
        ).values.tobytes())
    return digest.hexdigest()


def _checkpoint_entry(kind: str, replicate: int, row: dict, rng) -> dict:
    entry = {
        "kind": kind,
        "replicate": replicate,
        "row": _json_ready(row),
        "rng_state": _json_ready(rng.bit_generator.state),
    }
    entry["sha256"] = hashlib.sha256(_canonical_json(entry)).hexdigest()
    return entry


def _checkpoint_header(signature: dict) -> dict:
    content = {
        "record": "header",
        "schema_version": _CHECKPOINT_SCHEMA_VERSION,
        "signature": signature,
    }
    return {
        **content,
        "sha256": hashlib.sha256(_canonical_json(content)).hexdigest(),
    }


def _write_jsonl_checkpoint(
    path: Path,
    signature: dict,
    entries: list[dict],
) -> None:
    """Create or migrate one checkpoint, then append only complete entries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            for record in (_checkpoint_header(signature), *entries):
                handle.write(_canonical_json(record) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _append_checkpoint(
    path: Path,
    signature: dict,
    entry: dict,
    prior_entries: list[dict],
) -> None:
    """Persist one family with one O_APPEND write and one durability sync."""
    if not path.exists():
        _write_jsonl_checkpoint(path, signature, [entry])
        return
    with path.open("rb") as handle:
        first_line = handle.readline()
    try:
        header = json.loads(first_line)
    except json.JSONDecodeError:
        header = None
    if isinstance(header, dict) and header.get("record") == "header":
        content = {key: value for key, value in header.items() if key != "sha256"}
        if (
            header.get("schema_version") != _CHECKPOINT_SCHEMA_VERSION
            or header.get("signature") != signature
            or header.get("sha256")
            != hashlib.sha256(_canonical_json(content)).hexdigest()
        ):
            raise ValueError("귀무 보정 checkpoint header가 실행 중 변경되었습니다")
        with path.open("ab", buffering=0) as handle:
            handle.write(_canonical_json(entry) + b"\n")
            os.fsync(handle.fileno())
        return
    raw = path.read_bytes()
    try:
        legacy = json.loads(raw)
    except json.JSONDecodeError:
        legacy = None
    if isinstance(legacy, dict):
        # A v1 file is migrated once. Subsequent families are append-only.
        _write_jsonl_checkpoint(path, signature, [*prior_entries, entry])
        return
    raise ValueError("귀무 보정 checkpoint 형식을 확인할 수 없습니다")


def _load_checkpoint(
    path: Path,
    *,
    signature: dict,
    expected_pairs: list[tuple[str, int]],
    legacy_signature: dict | None = None,
) -> tuple[list[dict], dict | None, list[dict]]:
    if not path.exists():
        return [], None, []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"귀무 보정 checkpoint를 읽을 수 없습니다: {path}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        if payload.get("schema_version") != 1:
            raise ValueError("귀무 보정 checkpoint schema가 현재 엔진과 다릅니다")
        if payload.get("signature") != legacy_signature:
            raise ValueError("귀무 보정 checkpoint 범위 또는 실행 입력이 현재 요청과 다릅니다")
        entries = payload.get("entries")
    else:
        if not raw.endswith(b"\n"):
            raw = raw.rpartition(b"\n")[0] + b"\n"
            if raw == b"\n":
                raise ValueError("귀무 보정 checkpoint header가 손상되었습니다")
            with path.open("r+b") as handle:
                handle.truncate(len(raw))
                handle.flush()
                os.fsync(handle.fileno())
        try:
            records = [
                json.loads(line)
                for line in raw.decode("utf-8").splitlines()
                if line
            ]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("귀무 보정 checkpoint JSONL이 손상되었습니다") from exc
        if not records:
            raise ValueError("귀무 보정 checkpoint header가 없습니다")
        header, *entries = records
        content = {key: value for key, value in header.items() if key != "sha256"}
        if (
            set(header) != {"record", "schema_version", "signature", "sha256"}
            or header.get("record") != "header"
            or header.get("schema_version") != _CHECKPOINT_SCHEMA_VERSION
            or header.get("signature") != signature
            or header.get("sha256")
            != hashlib.sha256(_canonical_json(content)).hexdigest()
        ):
            raise ValueError("귀무 보정 checkpoint header 범위 또는 무결성이 다릅니다")
    if not isinstance(entries, list) or len(entries) > len(expected_pairs):
        raise ValueError("귀무 보정 checkpoint 완료 목록이 손상되었습니다")

    rows: list[dict] = []
    for index, entry in enumerate(entries):
        if (
            not isinstance(entry, dict)
            or set(entry) != {"kind", "replicate", "row", "rng_state", "sha256"}
        ):
            raise ValueError("귀무 보정 checkpoint entry가 손상되었습니다")
        content = {key: value for key, value in entry.items() if key != "sha256"}
        expected_hash = hashlib.sha256(_canonical_json(content)).hexdigest()
        if entry.get("sha256") != expected_hash:
            raise ValueError("귀무 보정 checkpoint entry 무결성 검증에 실패했습니다")
        kind, replicate = expected_pairs[index]
        row = entry.get("row")
        if (
            entry.get("kind") != kind
            or entry.get("replicate") != replicate
            or not isinstance(row, dict)
            or set(row) != set(_OUTPUT_COLUMNS)
            or not isinstance(entry.get("rng_state"), dict)
            or row.get("kind") != kind
            or row.get("replicate") != replicate
        ):
            raise ValueError("귀무 보정 checkpoint 완료 순서가 현재 실행과 다릅니다")
        for field, expected in signature["row_scope"].items():
            if row.get(field) != expected:
                raise ValueError(
                    f"귀무 보정 checkpoint row 범위가 손상되었습니다: {field}"
                )
        rows.append(dict(row))
    state = entries[-1]["rng_state"] if entries else None
    return rows, state, entries


def _random_signal(base: pd.DataFrame, rng) -> pd.Series:
    return pd.Series(rng.standard_normal(len(base)), index=base.index)


def _persistent_signal(base: pd.DataFrame, rng, rho: float) -> pd.Series:
    assets = base["asset_id"].unique()
    state = pd.Series(rng.standard_normal(len(assets)), index=assets)
    output = pd.Series(np.nan, index=base.index, dtype=float)
    for ym in sorted(base["ym"].unique()):
        state = rho * state + np.sqrt(max(1 - rho ** 2, 1e-9)) * pd.Series(
            rng.standard_normal(len(assets)), index=assets
        )
        group = base[base["ym"] == ym]
        output.loc[group.index] = state.reindex(group["asset_id"]).to_numpy()
    return output


def _frozen_signal(base: pd.DataFrame, rng) -> pd.Series:
    assets = base["asset_id"].unique()
    state = pd.Series(rng.standard_normal(len(assets)), index=assets)
    return pd.Series(state.reindex(base["asset_id"]).to_numpy(), index=base.index)


def _scope_discovery_panel(
    panel: Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period,
) -> Panel:
    """Reconstruct the immutable discovery snapshot from a confirmation panel."""
    cutoff = pd.Timestamp(data_cutoff).normalize()
    if oos_start <= cutoff.to_period("M"):
        raise ValueError("campaign OOS는 research data cutoff 다음 달 이후여야 합니다")
    frame = panel.monthly
    scoped = frame[
        pd.to_datetime(frame["trade_date"]).dt.normalize().le(cutoff)
        & frame["ym"].lt(oos_start)
    ].copy()
    if scoped.empty or pd.Timestamp(scoped["trade_date"].max()).normalize() != cutoff:
        raise ValueError(
            "귀무 보정에서 campaign cutoff snapshot을 재현할 수 없습니다: "
            f"cutoff={cutoff.date()}"
        )

    last_day = pd.Timestamp(scoped["trade_date"].max())
    last_seen = scoped.groupby("asset_id")["trade_date"].max()
    dead = last_seen[
        last_seen < last_day - pd.Timedelta(days=panel_engine.INACTIVE_DAYS)
    ]
    meta = dict(panel.meta)
    meta.update({
        "campaign_data_cutoff": str(cutoff.date()),
        "campaign_oos_start": str(oos_start),
    })
    output = Panel(monthly=scoped, dead=dead, meta=meta)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = panel_engine.forward_returns(
            output, terminal=terminal,
        )
    return output


def _merge_discovery_and_oos(
    discovery: gate.Result,
    confirmation: gate.Result,
) -> gate.Result:
    """Attach only fixed-OOS evidence to the cutoff-bound discovery result."""
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
        failures = ", ".join(
            check.name for check in confirmation.failed
        ) or "OOS 계산 불가"
        oos_check = gate.Check(
            "T4.1", "고정 OOS IC", False, None,
            gate.oos_effect_threshold_label(),
            failures,
        )
    discovery.checks.append(oos_check)
    if "oos_ic" in confirmation.series:
        discovery.series["oos_ic"] = confirmation.series["oos_ic"]
    return discovery


def measure(
    panel: Panel,
    *,
    n: int = 25,
    seed: int = 20260731,
    trial_count: int = 1,
    prior_sharpes: tuple[float, ...] = (),
    oos_start: pd.Period | None = None,
    oos_end: pd.Period | None = None,
    research_data_cutoff: str | None = None,
    discovery_family_size: int = 1,
    oos_family_size: int = 1,
    discovery_family_digest: str = "standalone",
    oos_family_digest: str = "standalone",
    gold_family_digest: str = "none",
    confirmation_snapshot_digest: str | None = None,
    existing: dict[str, pd.Series] | None = None,
    qualification_policy: str = QUALIFICATION_POLICY,
    verbose: bool = True,
    checkpoint_path: str | Path | None = None,
    timing_callback: Callable[..., None] | None = None,
) -> pd.DataFrame:
    """Estimate family-wise false promotion with production-sized null campaigns.

    ``n`` is the number of null campaign families per generator, not the number
    of individual signals.  Each family contains the same number of discovery
    definitions as the bound research campaign. Every discovery non-reject is
    automatically confirmed, matching the production qualification policy.

    When ``checkpoint_path`` is set, each completed ``(kind, replicate)`` row
    and the post-family RNG state are durably appended. A later call with the
    exact same computational inputs resumes from that contiguous prefix. A
    directory path enables content-addressed reuse while campaign family
    evidence digests are rebound on output.
    """
    if n < 1:
        raise ValueError("null campaign 반복 수 n은 1 이상이어야 합니다")
    if discovery_family_size < 1 or oos_family_size < 1:
        raise ValueError("discovery/OOS family size는 1 이상이어야 합니다")
    if oos_family_size > discovery_family_size:
        raise ValueError("OOS family size는 discovery family size보다 클 수 없습니다")
    if oos_start is None or oos_end is None or research_data_cutoff is None:
        raise ValueError(
            "귀무 보정에는 research_data_cutoff, oos_start, oos_end가 모두 필요합니다"
        )
    oos_start = pd.Period(oos_start, freq="M")
    oos_end = pd.Period(oos_end, freq="M")
    window = CampaignWindow.create(
        discovery_data_cutoff=research_data_cutoff,
        oos_start=oos_start,
        oos_months=gate.TH["min_oos_months"],
    )
    window.validate_oos_end(oos_end)
    df = panel.monthly
    required_month = oos_end + 1
    if df.empty or df["ym"].max() != required_month:
        raise ValueError(
            "귀무 보정 confirmation snapshot 경계가 고정 OOS와 일치하지 않습니다: "
            f"expected_last_month={required_month}"
        )
    discovery_panel = _scope_discovery_panel(
        panel, data_cutoff=research_data_cutoff, oos_start=oos_start,
    )
    confirmation_snapshot_digest = (
        confirmation_snapshot_digest or panel_engine.snapshot_digest(panel)
    )
    discovery_df = discovery_panel.monthly
    discovery_context = gate.build_evaluation_context(
        discovery_panel,
        discovery_df,
        oos_start=oos_start,
        data_cutoff=research_data_cutoff,
        phase="discovery",
    )
    base = df.loc[panel.universe, ["ym", "asset_id"]]
    rng = np.random.default_rng(seed)
    generators = {
        "random": lambda: _random_signal(base, rng),
        "ar1_095": lambda: _persistent_signal(base, rng, .95),
        "ar1_0999": lambda: _persistent_signal(base, rng, .999),
        "frozen": lambda: _frozen_signal(base, rng),
    }
    row_scope = {
        "calibration_unit": "null_campaign_family",
        "generator_suite": _GENERATOR_SUITE,
        "qualification_policy": qualification_policy,
        "discovery_family_size": discovery_family_size,
        "oos_family_size": oos_family_size,
        "discovery_family_digest": discovery_family_digest,
        "oos_family_digest": oos_family_digest,
        "gold_family_digest": gold_family_digest,
        "confirmation_snapshot_digest": confirmation_snapshot_digest,
        "fdr_q": gate.TH["fdr_q"],
        "neutral_ic_retention_floor": gate.TH["neutral_ic_retention"],
        "oos_ic_floor": gate.TH["oos_ic"],
        "oos_ic_retention_floor": gate.TH["oos_ic_retention"],
        "max_gold_signal_corr_threshold": gate.TH["max_gold_corr"],
        "min_gold_signal_corr_months": gate.TH["min_gold_corr_months"],
        "seed": seed,
        "gold_signal_count": len(existing or {}),
        "ruleset_version": gate.RULESET_VERSION,
        "data_cutoff": str(df["trade_date"].max().date()),
        "oos_start": str(oos_start),
        "oos_end": str(oos_end),
        "research_data_cutoff": research_data_cutoff,
    }
    expected_pairs = [
        (kind, replicate)
        for kind in _GENERATOR_KINDS
        for replicate in range(n)
    ]
    checkpoint = Path(checkpoint_path) if checkpoint_path is not None else None
    if checkpoint is None:
        rows: list[dict] = []
        checkpoint_entries: list[dict] = []
        signature = None
    else:
        legacy_signature = {
            "checkpoint_schema": 1,
            "n": n,
            "seed": seed,
            "trial_count": trial_count,
            "prior_sharpes": _json_ready(prior_sharpes),
            "actual_panel_digest": panel_engine.snapshot_digest(panel),
            "existing_signal_digest": _existing_signal_digest(existing),
            "gate_thresholds": _json_ready(gate.TH),
            "row_scope": _json_ready(row_scope),
        }
        signature = {
            key: value for key, value in legacy_signature.items()
            if key not in {"checkpoint_schema", "trial_count", "prior_sharpes"}
        }
        signature["row_scope"] = _json_ready({
                key: value for key, value in row_scope.items()
                if key not in _REBOUND_EVIDENCE_FIELDS
        })
        if not checkpoint.suffix:
            calculation_digest = hashlib.sha256(
                _canonical_json(signature)
            ).hexdigest()
            checkpoint = checkpoint / f"{calculation_digest}.jsonl"
        rows, rng_state, checkpoint_entries = _load_checkpoint(
            checkpoint,
            signature=signature,
            expected_pairs=expected_pairs,
            legacy_signature=legacy_signature,
        )
        for row in rows:
            for field in _REBOUND_EVIDENCE_FIELDS:
                row[field] = row_scope[field]
        if rng_state is not None:
            try:
                rng.bit_generator.state = rng_state
            except (TypeError, ValueError) as exc:
                raise ValueError("귀무 보정 checkpoint RNG state가 손상되었습니다") from exc
    completed_count = len(rows)
    pair_index = 0
    for kind, generate in generators.items():
        for replicate in range(n):
            if pair_index < completed_count:
                pair_index += 1
                continue
            family_started = time.perf_counter()
            family_results: list[gate.Result] = []
            factors_by_hash: dict[str, Factor] = {}
            temporary_columns: list[tuple[str, str]] = []
            try:
                for candidate_index in range(discovery_family_size):
                    name = f"null_{kind}_{replicate}_{candidate_index}"
                    raw_col, factor_col = f"_raw_{name}", f"f_{name}"
                    temporary_columns.append((raw_col, factor_col))
                    df[raw_col] = np.nan
                    signal = generate()
                    df.loc[signal.index, raw_col] = signal
                    df[factor_col] = df[raw_col]
                    # Generate once on the confirmation panel, then replay the exact
                    # same historical values on the sealed discovery index.
                    discovery_df[raw_col] = signal.reindex(discovery_df.index)
                    discovery_df[factor_col] = discovery_df[raw_col]
                    factor = Factor(
                        name=name,
                        family=f"null_{kind}",
                        category="other",
                        hypothesis="합성 귀무: 미래수익에 대한 경제적 정보가 없어야 한다.",
                        predicted_sign=1,
                        params={
                            "kind": kind, "replicate": replicate,
                            "candidate": candidate_index, "seed": seed,
                        },
                        compute=lambda frame, source=raw_col: frame[source],
                    )
                    # The synthetic value was generated once on the immutable
                    # confirmation panel and copied to the discovery subset.
                    # Bind that exact column as the first determinism sample;
                    # the gate still performs an independent bounded compute
                    # and its causal anchor audit.
                    research_policy.bind_authoritative_factor_column(
                        factor, discovery_df, factor_col,
                    )
                    discovery_null_contract = gate.certify_internal_null_signal(
                        factor,
                        discovery_df,
                        generator_suite=_GENERATOR_SUITE,
                        kind=kind,
                        replicate=replicate,
                        candidate=candidate_index,
                        seed=seed,
                        raw_column=raw_col,
                        factor_column=factor_col,
                    )
                    discovery_result = gate.evaluate(
                        factor, discovery_panel, discovery_df, existing=existing,
                        trial_count=trial_count + discovery_family_size,
                        prior_sharpes=prior_sharpes,
                        oos_start=oos_start,
                        data_cutoff=research_data_cutoff,
                        phase="discovery",
                        context=discovery_context,
                        internal_null_contract=discovery_null_contract,
                        include_diagnostics=False,
                    )
                    family_results.append(discovery_result)
                    factors_by_hash[factor.definition_hash] = factor

                # Automatic qualification must use discovery only. Attaching T4.1
                # before this point would leak OOS into the qualification decision.
                gate.apply_multiple_testing(
                    family_results, total_trials=discovery_family_size,
                )
                eligible = [
                    result for result in family_results
                    if result.verdict != gate.Verdict.REJECT
                ]
                selected = sorted(
                    eligible,
                    key=lambda result: (
                        result.metrics.get("ic_p_investable")
                        if result.metrics.get("ic_p_investable") is not None
                        and np.isfinite(result.metrics["ic_p_investable"])
                        else float("inf"),
                        result.definition_hash,
                    ),
                )
                for index, discovery_result in enumerate(selected):
                    factor = factors_by_hash[discovery_result.definition_hash]
                    name = factor.name
                    confirmation_null_contract = gate.certify_internal_null_signal(
                        factor,
                        df,
                        generator_suite=_GENERATOR_SUITE,
                        kind=str(factor.params["kind"]),
                        replicate=int(factor.params["replicate"]),
                        candidate=int(factor.params["candidate"]),
                        seed=int(factor.params["seed"]),
                        raw_column=f"_raw_{name}",
                        factor_column=f"f_{name}",
                    )
                    confirmation_result = gate.evaluate_oos(
                        factor, panel, df,
                        oos_start=oos_start, oos_end=oos_end,
                        data_cutoff=research_data_cutoff,
                        discovery_ic=discovery_result.metrics.get("ic_investable"),
                        internal_null_contract=confirmation_null_contract,
                    )
                    selected[index] = _merge_discovery_and_oos(
                        discovery_result, confirmation_result,
                    )
                gate.apply_oos_multiple_testing(selected)
                promoted = [
                    result for result in selected
                    if result.verdict == gate.Verdict.PROMOTE
                ]
                definition_digest = hashlib.sha256(
                    "\n".join(
                        sorted(result.definition_hash for result in family_results)
                    ).encode()
                ).hexdigest()
                ic_values = [
                    float(result.metrics["ic_investable"])
                    for result in family_results
                    if result.metrics.get("ic_investable") is not None
                    and np.isfinite(result.metrics["ic_investable"])
                ]
            finally:
                for raw_col, factor_col in temporary_columns:
                    for frame, column in (
                        (df, raw_col), (df, factor_col),
                        (discovery_df, raw_col), (discovery_df, factor_col),
                    ):
                        if column in frame:
                            del frame[column]
            row = {
                "calibration_unit": row_scope["calibration_unit"],
                "generator_suite": row_scope["generator_suite"],
                "qualification_policy": row_scope["qualification_policy"],
                "kind": kind,
                "replicate": replicate,
                "pass": bool(promoted),
                "promoted_count": len(promoted),
                "revealed_count": len(selected),
                "discovery_family_size": row_scope["discovery_family_size"],
                "oos_family_size": row_scope["oos_family_size"],
                "discovery_family_digest": row_scope["discovery_family_digest"],
                "oos_family_digest": row_scope["oos_family_digest"],
                "gold_family_digest": row_scope["gold_family_digest"],
                "confirmation_snapshot_digest": row_scope[
                    "confirmation_snapshot_digest"
                ],
                "null_definition_digest": definition_digest,
                "max_ic_investable": max(ic_values) if ic_values else None,
                "fdr_q": row_scope["fdr_q"],
                "neutral_ic_retention_floor": row_scope[
                    "neutral_ic_retention_floor"
                ],
                "oos_ic_floor": row_scope["oos_ic_floor"],
                "oos_ic_retention_floor": row_scope["oos_ic_retention_floor"],
                "max_gold_signal_corr_threshold": row_scope[
                    "max_gold_signal_corr_threshold"
                ],
                "min_gold_signal_corr_months": row_scope[
                    "min_gold_signal_corr_months"
                ],
                "seed": row_scope["seed"],
                "gold_signal_count": row_scope["gold_signal_count"],
                "ruleset_version": row_scope["ruleset_version"],
                "data_cutoff": row_scope["data_cutoff"],
                "oos_start": row_scope["oos_start"],
                "oos_end": row_scope["oos_end"],
                "research_data_cutoff": row_scope["research_data_cutoff"],
            }
            rows.append(row)
            if checkpoint is not None:
                checkpoint_entries.append(
                    _checkpoint_entry(kind, replicate, row, rng)
                )
                _append_checkpoint(
                    checkpoint,
                    signature,
                    checkpoint_entries[-1],
                    checkpoint_entries[:-1],
                )
            pair_index += 1
            if timing_callback is not None:
                timing_callback(
                    "null.family",
                    family_started,
                    kind=kind,
                    replicate=replicate,
                    candidate_count=discovery_family_size,
                )
            if verbose:
                print(
                    f"  [null] {pair_index}/{len(expected_pairs)} "
                    f"{kind} replicate={replicate} pass={bool(promoted)}",
                    flush=True,
                )
    output = pd.DataFrame(rows, columns=_OUTPUT_COLUMNS)
    if verbose:
        for kind in generators:
            subset = output[output["kind"] == kind]
            rate = subset["pass"].mean() * 100 if len(subset) else 0.0
            print(f"  [null] {kind:12} families={len(subset):>3}  any PROMOTE {rate:5.1f}%")
        if len(output):
            print(f"  [null] campaign-family 오류율: {output['pass'].mean() * 100:.1f}%")
    return output
