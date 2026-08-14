"""Deterministic evidence for research/Python and Gold/SQL factor parity.

This module deliberately has no database, filesystem, or campaign-state access.
Callers provide already-computed frames and persist the returned evidence.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import json
import math
import re
from typing import Any

import numpy as np
import pandas as pd

from engine.factors import Factor
from engine.publish import VALUE_CONTRACT_ID


PARITY_SCHEMA_VERSION = "implementation-parity-v2"
DEFAULT_ATOL = 1e-12
DEFAULT_RTOL = 1e-10
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_QUERY_PARAMETERS = ("start_month", "end_month")
_LABEL_ONLY_SQL_FIELDS = frozenset({"total_return_close", "return_close"})
_MUTATING_SQL = re.compile(
    r"\b(?:insert|update|delete|merge|create|alter|drop|truncate|grant|revoke|"
    r"copy|call|do|vacuum|analyze|refresh|reindex|cluster|comment)\b",
    re.IGNORECASE,
)
_ALLOWED_SILVER_RELATIONS = frozenset({
    "public.asset",
    "public.asset_identifier",
    "public.corporate_action",
    "public.dividend_event_resolution",
    "public.dq_run",
    "public.fundamental",
    "public.factor_price_feature_daily",
    "public.price_daily",
    "public.price_return_contract",
})
_FEATURE_FORBIDDEN_RELATIONS = frozenset({
    "public.corporate_action",
    "public.dividend_event_resolution",
    "public.price_daily",
    "public.price_return_contract",
})
_CTE_NAME = re.compile(
    r"(?:\bwith|,)\s*([a-z_][a-z0-9_]*)\s+as\s+"
    r"(?:(?:not\s+)?materialized\s+)?\(",
    re.I,
)
_RELATION = re.compile(
    r"\b(?:from|join)\s+([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)?)",
    re.I,
)
_DYNAMIC_FIELD_SQL = re.compile(
    r"(?:\bto_jsonb?\s*\(|\brow_to_json\s*\(|\bjsonb?_[a-z0-9_]+\s*\(|"
    r"->>?|#>>?)",
    re.IGNORECASE,
)


def _canonical_json(payload: Any) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("payload는 유한한 JSON 값으로만 구성되어야 합니다") from exc


def _payload_digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def manifest_entry_digest(spec: Mapping[str, Any]) -> str:
    """Hash one canonical manifest entry, independent of other factors."""
    if not isinstance(spec, Mapping):
        raise TypeError("manifest spec은 mapping이어야 합니다")
    return _payload_digest(dict(spec))


def _sql_without_comments(sql: str) -> str:
    """Remove comments while retaining literals for field-name auditing."""
    without_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\r\n]*", " ", without_block_comments)


def _sql_code_only(sql: str) -> str:
    """Remove comments and quoted literals before structural SQL checks."""
    without_comments = _sql_without_comments(sql)
    without_strings = re.sub(r"'(?:''|[^'])*'", "''", without_comments)
    return re.sub(r'"(?:""|[^"])*"', '""', without_strings)


def validate_query_only_sql(sql: str) -> None:
    """Reject Gold SQL that is not one parameterized SELECT/CTE query.

    The production runner may wrap this query in its generic Gold upsert.  The
    implementation itself must remain executable on a read-only connection.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("Gold SQL query가 비어 있습니다")
    code = _sql_code_only(sql).strip()
    body = code[:-1].rstrip() if code.endswith(";") else code
    if ";" in body:
        raise ValueError("Gold query-only SQL에는 여러 statement를 넣을 수 없습니다")
    if not re.match(r"^(?:select|with)\b", body, flags=re.IGNORECASE):
        raise ValueError("Gold query-only SQL은 SELECT 또는 WITH로 시작해야 합니다")
    mutation = _MUTATING_SQL.search(body)
    if mutation:
        raise ValueError(
            f"Gold query-only SQL에 변경 명령이 포함되어 있습니다: {mutation.group(0).upper()}"
        )
    missing = [
        name
        for name in _REQUIRED_QUERY_PARAMETERS
        if re.search(rf"%\({re.escape(name)}\)s", body) is None
    ]
    if missing:
        raise ValueError(f"Gold query-only SQL 필수 parameter가 없습니다: {missing}")
    if '""' in body:
        raise ValueError("Gold SQL의 relation은 따옴표 없는 Silver allowlist 이름만 허용합니다")
    cte_names = {name.lower() for name in _CTE_NAME.findall(body)}
    relations = {name.lower() for name in _RELATION.findall(body)}
    invalid_relations = sorted(
        relation
        for relation in relations
        if relation != "lateral"
        and relation not in cte_names
        and relation not in _ALLOWED_SILVER_RELATIONS
    )
    if invalid_relations:
        raise ValueError(
            "Gold SQL은 인증 Silver relation만 읽을 수 있습니다: "
            f"{invalid_relations}"
        )


def validate_feature_sql(sql: str) -> None:
    """Validate a Gold factor query and reject evaluator-only label fields."""
    validate_query_only_sql(sql)
    # Scan string literals too.  PostgreSQL can access a column dynamically,
    # for example ``to_jsonb(p)->>'total_return_close'``; stripping that
    # literal before this check would make the label-only contract bypassable.
    code = _sql_without_comments(sql)
    dynamic = _DYNAMIC_FIELD_SQL.search(code)
    if dynamic:
        raise ValueError(
            "Gold feature SQL은 row 직렬화·동적 필드 접근을 사용할 수 "
            f"없습니다: {dynamic.group(0)!r}"
        )
    exposed = sorted(
        field
        for field in _LABEL_ONLY_SQL_FIELDS
        if re.search(rf"\b{re.escape(field)}\b", code, flags=re.IGNORECASE)
    )
    if exposed:
        raise ValueError(
            "Gold feature SQL이 ex-post forward label 전용 필드를 읽습니다: "
            f"{exposed}"
        )
    cte_names = {name.lower() for name in _CTE_NAME.findall(code)}
    relations = {
        name.lower() for name in _RELATION.findall(code)
        if name.lower() not in cte_names
    }
    forbidden_relations = sorted(relations & _FEATURE_FORBIDDEN_RELATIONS)
    if forbidden_relations:
        raise ValueError(
            "Gold feature SQL은 label·latest-action 컬럼이 없는 인증 feature "
            "view만 사용해야 합니다: "
            f"{forbidden_relations}"
        )


def _float_token(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "<NA>"
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "+Inf" if number > 0 else "-Inf"
    return number.hex()


def _normalize_frame(frame: pd.DataFrame, *, sql: bool) -> pd.DataFrame:
    required = {"asset_id", "as_of_date", "value"}
    if sql:
        required.add("rank")
    missing = required - set(frame.columns)
    if missing:
        side = "SQL" if sql else "Python"
        raise ValueError(f"{side} parity frame 필수 컬럼이 없습니다: {sorted(missing)}")

    output = frame[list(sorted(required))].copy()
    raw_asset = pd.to_numeric(output["asset_id"], errors="coerce")
    asset_values = raw_asset.to_numpy(dtype=float, na_value=np.nan)
    valid_asset = np.isfinite(asset_values) & (asset_values == np.floor(asset_values))
    output["_asset_id"] = pd.Series(
        np.where(valid_asset, asset_values, np.nan), index=output.index,
    ).astype("Int64")
    output["_valid_asset"] = valid_asset

    dates = pd.to_datetime(output["as_of_date"], errors="coerce", utc=True)
    output["_as_of_date"] = dates.dt.tz_convert(None).dt.normalize()
    output["_valid_date"] = output["_as_of_date"].notna()
    output["_month"] = output["_as_of_date"].dt.to_period("M")
    output["_value"] = pd.to_numeric(output["value"], errors="coerce").astype(float)
    if sql:
        output["_rank"] = pd.to_numeric(output["rank"], errors="coerce").astype(float)
    return output.reset_index(drop=True)


def _frame_digest(frame: pd.DataFrame, *, sql: bool) -> str:
    records: list[tuple[str, ...]] = []
    columns = ["_asset_id", "_as_of_date", "_value"]
    if sql:
        columns.append("_rank")
    for row in frame[columns].itertuples(index=False, name=None):
        asset, as_of_date, value, *remainder = row
        record = (
            "<NA>" if pd.isna(asset) else str(int(asset)),
            "<NA>" if pd.isna(as_of_date) else str(pd.Timestamp(as_of_date).date()),
            _float_token(value),
        )
        if sql:
            record += (_float_token(remainder[0]),)
        records.append(record)
    digest = hashlib.sha256()
    for record in sorted(records):
        digest.update("\x1f".join(record).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _key_rows(frame: pd.DataFrame) -> tuple[Counter, dict[tuple[int, pd.Timestamp], int]]:
    counts: Counter = Counter()
    indices: dict[tuple[int, pd.Timestamp], list[int]] = {}
    valid = frame["_valid_asset"] & frame["_valid_date"]
    for index in frame.index[valid]:
        key = (
            int(frame.at[index, "_asset_id"]),
            pd.Timestamp(frame.at[index, "_as_of_date"]),
        )
        counts[key] += 1
        indices.setdefault(key, []).append(int(index))
    unique = {key: rows[0] for key, rows in indices.items() if len(rows) == 1}
    return counts, unique


def _keyset_digest(keys: set[tuple[int, pd.Timestamp]]) -> str:
    digest = hashlib.sha256()
    for asset_id, as_of_date in sorted(keys, key=lambda key: (key[1], key[0])):
        digest.update(f"{asset_id}\x1f{as_of_date.date()}\n".encode("utf-8"))
    return digest.hexdigest()


def _validate_binding(
    factor: Factor,
    *,
    implementation_uri: str,
    implementation_sha256: str,
    manifest_spec: Mapping[str, Any],
    discovery_snapshot_digest: str,
) -> None:
    if not implementation_uri or not implementation_uri.strip():
        raise ValueError("implementation URI가 비어 있습니다")
    if not _SHA256_RE.fullmatch(implementation_sha256):
        raise ValueError("implementation SHA-256은 64자리 소문자 hex여야 합니다")
    if not _SHA256_RE.fullmatch(discovery_snapshot_digest):
        raise ValueError("discovery snapshot digest는 64자리 소문자 hex여야 합니다")
    required = {
        "sql", "predicted_sign", "research_definition_hash", "value_contract",
    }
    missing = required - set(manifest_spec)
    if missing:
        raise ValueError(f"Gold manifest binding 필드가 없습니다: {sorted(missing)}")
    if str(manifest_spec["research_definition_hash"]) != factor.definition_hash:
        raise ValueError("Gold manifest research_definition_hash가 Python 정의와 다릅니다")
    try:
        manifest_sign = int(manifest_spec["predicted_sign"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Gold manifest predicted_sign이 정수가 아닙니다") from exc
    if manifest_sign != factor.predicted_sign:
        raise ValueError("Gold manifest predicted_sign이 Python 정의와 다릅니다")
    if manifest_spec["value_contract"] != VALUE_CONTRACT_ID:
        raise ValueError("Gold manifest value contract가 연구 계약과 다릅니다")
    for field, default in (("parity_atol", DEFAULT_ATOL), ("parity_rtol", DEFAULT_RTOL)):
        try:
            tolerance = float(manifest_spec.get(field, default))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Gold manifest {field}이 숫자가 아닙니다") from exc
        if not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError(f"Gold manifest {field}은 유한한 0 이상이어야 합니다")
    rank_equivalence = manifest_spec.get("allow_tolerance_equivalent_ranks", False)
    if not isinstance(rank_equivalence, bool):
        raise ValueError("Gold manifest allow_tolerance_equivalent_ranks는 bool이어야 합니다")
    query_chunk_months = manifest_spec.get("query_chunk_months")
    if query_chunk_months is not None and (
        isinstance(query_chunk_months, bool)
        or not isinstance(query_chunk_months, int)
        or query_chunk_months < 1
    ):
        raise ValueError("Gold manifest query_chunk_months는 1 이상의 정수여야 합니다")
    planner_enable_nestloop = manifest_spec.get("planner_enable_nestloop", True)
    if not isinstance(planner_enable_nestloop, bool):
        raise ValueError("Gold manifest planner_enable_nestloop는 bool이어야 합니다")
    sql_path = str(manifest_spec["sql"]).strip()
    if not sql_path or not (
        implementation_uri == sql_path or implementation_uri.endswith(f"/{sql_path}")
    ):
        raise ValueError("implementation URI가 Gold manifest SQL 경로와 다릅니다")


def failure_evidence(
    factor: Factor,
    *,
    discovery_signal_start: str | pd.Period,
    discovery_signal_end: str | pd.Period,
    discovery_snapshot_digest: str,
    strategy_sha256: str,
    stage: str,
    error: Exception,
    binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create digest-bound FAIL evidence when SQL parity cannot be attempted."""
    if not _SHA256_RE.fullmatch(discovery_snapshot_digest):
        raise ValueError("discovery snapshot digest는 64자리 소문자 hex여야 합니다")
    if not _SHA256_RE.fullmatch(strategy_sha256):
        raise ValueError("전략 파일 SHA-256은 64자리 소문자 hex여야 합니다")
    start = pd.Period(discovery_signal_start, freq="M")
    end = pd.Period(discovery_signal_end, freq="M")
    if start > end:
        raise ValueError("discovery signal start는 end보다 늦을 수 없습니다")
    safe_stage = re.sub(r"[^a-z0-9_]+", "_", str(stage).lower()).strip("_")
    if not safe_stage:
        safe_stage = "unknown"
    values = dict(binding or {})
    evidence: dict[str, Any] = {
        "schema_version": PARITY_SCHEMA_VERSION,
        "factor": factor.name,
        "definition_hash": factor.definition_hash,
        "research_definition_hash": factor.definition_hash,
        "strategy_sha256": strategy_sha256,
        "predicted_sign": factor.predicted_sign,
        "value_contract": values.get("value_contract", VALUE_CONTRACT_ID),
        "implementation_uri": values.get("implementation_uri"),
        "implementation_sha256": values.get("implementation_sha256"),
        "manifest_entry_digest": values.get("manifest_entry_digest"),
        "discovery": {
            "signal_start": str(start),
            "signal_end": str(end),
            "snapshot_digest": discovery_snapshot_digest,
        },
        "stage": safe_stage,
        "error": {
            "type": type(error).__name__,
            "message": " ".join(str(error).split())[:1000],
        },
        "checks": {"implementation_attempt_completed": False},
        "counts": {},
        "passed": False,
        "status": "FAIL",
        "failure_reasons": [f"{safe_stage}_error"],
    }
    evidence["evidence_digest"] = _payload_digest(evidence)
    return evidence


def compare_parity(
    factor: Factor,
    python_frame: pd.DataFrame,
    sql_frame: pd.DataFrame,
    *,
    implementation_uri: str,
    implementation_sha256: str,
    manifest_spec: Mapping[str, Any],
    discovery_signal_start: str | pd.Period,
    discovery_signal_end: str | pd.Period,
    discovery_snapshot_digest: str,
    strategy_sha256: str,
    atol: float = DEFAULT_ATOL,
    rtol: float = DEFAULT_RTOL,
    allow_tolerance_equivalent_ranks: bool = False,
) -> dict[str, Any]:
    """Compare raw values and direction-adjusted ranks and return evidence.

    Invalid contracts raise ``ValueError``.  Ordinary implementation parity
    failures return a deterministic evidence row with ``status='FAIL'`` so the
    failed engineering attempt can be retained in an append-only audit trail.
    """
    if not isinstance(manifest_spec, Mapping):
        raise TypeError("manifest spec은 mapping이어야 합니다")
    if not _SHA256_RE.fullmatch(strategy_sha256):
        raise ValueError("전략 파일 SHA-256은 64자리 소문자 hex여야 합니다")
    _validate_binding(
        factor,
        implementation_uri=implementation_uri,
        implementation_sha256=implementation_sha256,
        manifest_spec=manifest_spec,
        discovery_snapshot_digest=discovery_snapshot_digest,
    )
    if not math.isfinite(atol) or not math.isfinite(rtol) or atol < 0 or rtol < 0:
        raise ValueError("parity tolerance는 유한한 0 이상 값이어야 합니다")
    if not isinstance(allow_tolerance_equivalent_ranks, bool):
        raise TypeError("rank tolerance-equivalence 계약은 bool이어야 합니다")
    start = pd.Period(discovery_signal_start, freq="M")
    end = pd.Period(discovery_signal_end, freq="M")
    if start > end:
        raise ValueError("discovery signal start는 end보다 늦을 수 없습니다")

    py = _normalize_frame(python_frame, sql=False)
    sql = _normalize_frame(sql_frame, sql=True)
    py_counts, py_unique = _key_rows(py)
    sql_counts, sql_unique = _key_rows(sql)
    py_keys = set(py_counts)
    sql_keys = set(sql_counts)
    missing_in_sql = py_keys - sql_keys
    extra_in_sql = sql_keys - py_keys
    shared_unique = set(py_unique) & set(sql_unique)
    ordered_shared = sorted(shared_unique, key=lambda key: (key[1], key[0]))

    py_values = np.array(
        [py.at[py_unique[key], "_value"] for key in ordered_shared], dtype=float,
    )
    sql_values = np.array(
        [sql.at[sql_unique[key], "_value"] for key in ordered_shared], dtype=float,
    )
    finite_pairs = np.isfinite(py_values) & np.isfinite(sql_values)
    close = np.zeros(len(ordered_shared), dtype=bool)
    if finite_pairs.any():
        close[finite_pairs] = np.isclose(
            sql_values[finite_pairs], py_values[finite_pairs], atol=atol, rtol=rtol,
        )
    raw_mismatch_count = int((~close).sum())
    raw_mismatch_samples = []
    for position in np.flatnonzero(~close)[:10]:
        key = ordered_shared[int(position)]
        raw_mismatch_samples.append({
            "asset_id": key[0],
            "as_of_date": str(key[1].date()),
            "python_value": float(py_values[position]),
            "sql_value": float(sql_values[position]),
        })
    if finite_pairs.any():
        absolute_errors = np.abs(sql_values[finite_pairs] - py_values[finite_pairs])
        relative_errors = absolute_errors / np.maximum(
            np.abs(py_values[finite_pairs]), atol if atol > 0 else np.finfo(float).tiny,
        )
        max_abs_error: float | None = float(absolute_errors.max())
        max_rel_error: float | None = float(relative_errors.max())
    else:
        max_abs_error = None
        max_rel_error = None

    py["_expected_rank"] = (
        (py["_value"] * factor.predicted_sign)
        .groupby(py["_month"])
        .rank(method="min", ascending=False)
    )
    allowed_rank_ranges: dict[int, tuple[int, int]] = {}
    if allow_tolerance_equivalent_ranks:
        for _month, group in py.groupby("_month", sort=False):
            adjusted = (group["_value"] * factor.predicted_sign).sort_values(
                ascending=False, kind="mergesort",
            )
            ordered_indices = list(adjusted.index)
            ordered_values = adjusted.to_numpy(dtype=float)
            cluster_start = 0
            for position in range(1, len(ordered_values) + 1):
                closes_cluster = position == len(ordered_values) or not np.isclose(
                    ordered_values[position], ordered_values[cluster_start],
                    atol=atol, rtol=rtol,
                )
                if closes_cluster:
                    allowed = (cluster_start + 1, position)
                    for index in ordered_indices[cluster_start:position]:
                        allowed_rank_ranges[int(index)] = allowed
                    cluster_start = position
    rank_mismatch_count = 0
    tolerance_equivalent_rank_mismatches = 0
    material_rank_mismatch_count = 0
    rank_mismatch_samples = []
    for key in ordered_shared:
        python_index = py_unique[key]
        expected = float(py.at[python_index, "_expected_rank"])
        observed = float(sql.at[sql_unique[key], "_rank"])
        exact = (
            math.isfinite(expected)
            and math.isfinite(observed)
            and observed > 0
            and observed.is_integer()
            and observed == expected
        )
        if not exact:
            rank_mismatch_count += 1
            allowed = allowed_rank_ranges.get(int(python_index))
            tolerance_equivalent = bool(
                allow_tolerance_equivalent_ranks
                and allowed is not None
                and math.isfinite(observed)
                and observed.is_integer()
                and allowed[0] <= observed <= allowed[1]
            )
            if tolerance_equivalent:
                tolerance_equivalent_rank_mismatches += 1
            else:
                material_rank_mismatch_count += 1
            if len(rank_mismatch_samples) < 10:
                rank_mismatch_samples.append({
                    "asset_id": key[0],
                    "as_of_date": str(key[1].date()),
                    "python_value": float(py.at[py_unique[key], "_value"]),
                    "sql_value": float(sql.at[sql_unique[key], "_value"]),
                    "python_rank": expected,
                    "sql_rank": observed,
                    "tolerance_equivalent": tolerance_equivalent,
                    "allowed_rank_range": list(allowed) if allowed is not None else None,
                })

    py_finite = np.isfinite(py["_value"].to_numpy(dtype=float))
    sql_finite = np.isfinite(sql["_value"].to_numpy(dtype=float))
    sql_rank_values = sql["_rank"].to_numpy(dtype=float)
    valid_sql_rank = (
        np.isfinite(sql_rank_values)
        & (sql_rank_values > 0)
        & (sql_rank_values == np.floor(sql_rank_values))
    )
    py_in_scope = py["_month"].ge(start) & py["_month"].le(end)
    sql_in_scope = sql["_month"].ge(start) & sql["_month"].le(end)
    expected_months = set(pd.period_range(start, end, freq="M"))
    python_months = set(py.loc[py_in_scope.fillna(False), "_month"].dropna())
    sql_months = set(sql.loc[sql_in_scope.fillna(False), "_month"].dropna())

    counts = {
        "python_rows": int(len(py)),
        "sql_rows": int(len(sql)),
        "compared_rows": int(len(ordered_shared)),
        "python_invalid_keys": int((~(py["_valid_asset"] & py["_valid_date"])).sum()),
        "sql_invalid_keys": int((~(sql["_valid_asset"] & sql["_valid_date"])).sum()),
        "python_duplicate_keys": int(sum(count > 1 for count in py_counts.values())),
        "sql_duplicate_keys": int(sum(count > 1 for count in sql_counts.values())),
        "python_duplicate_rows": int(sum(max(0, count - 1) for count in py_counts.values())),
        "sql_duplicate_rows": int(sum(max(0, count - 1) for count in sql_counts.values())),
        "missing_in_sql": int(len(missing_in_sql)),
        "extra_in_sql": int(len(extra_in_sql)),
        "python_nonfinite_values": int((~py_finite).sum()),
        "sql_nonfinite_values": int((~sql_finite).sum()),
        "sql_invalid_ranks": int((~valid_sql_rank).sum()),
        "python_out_of_scope_rows": int((~py_in_scope.fillna(False)).sum()),
        "sql_out_of_scope_rows": int((~sql_in_scope.fillna(False)).sum()),
        "expected_signal_months": int(len(expected_months)),
        "python_signal_months": int(len(python_months)),
        "sql_signal_months": int(len(sql_months)),
        "python_missing_signal_months": int(len(expected_months - python_months)),
        "sql_missing_signal_months": int(len(expected_months - sql_months)),
        "raw_mismatches": raw_mismatch_count,
        "rank_mismatches": int(rank_mismatch_count),
        "tolerance_equivalent_rank_mismatches": int(
            tolerance_equivalent_rank_mismatches
        ),
        "material_rank_mismatches": int(material_rank_mismatch_count),
    }
    checks = {
        "nonempty": counts["python_rows"] > 0 and counts["sql_rows"] > 0,
        "scope_exact": (
            counts["python_out_of_scope_rows"] == 0
            and counts["sql_out_of_scope_rows"] == 0
        ),
        "month_coverage_exact": (
            counts["python_missing_signal_months"] == 0
            and counts["sql_missing_signal_months"] == 0
        ),
        "keys_exact": all(
            counts[name] == 0
            for name in (
                "python_invalid_keys", "sql_invalid_keys", "python_duplicate_keys",
                "sql_duplicate_keys", "missing_in_sql", "extra_in_sql",
            )
        ),
        "values_finite": (
            counts["python_nonfinite_values"] == 0
            and counts["sql_nonfinite_values"] == 0
        ),
        "raw_values_close": counts["raw_mismatches"] == 0,
        "direction_adjusted_ranks_consistent": (
            counts["sql_invalid_ranks"] == 0
            and counts["material_rank_mismatches"] == 0
        ),
    }
    failure_reasons = [name for name, passed in checks.items() if not passed]
    evidence: dict[str, Any] = {
        "schema_version": PARITY_SCHEMA_VERSION,
        "factor": factor.name,
        "definition_hash": factor.definition_hash,
        "research_definition_hash": factor.definition_hash,
        "strategy_sha256": strategy_sha256,
        "predicted_sign": factor.predicted_sign,
        "value_contract": VALUE_CONTRACT_ID,
        "implementation_uri": implementation_uri,
        "implementation_sha256": implementation_sha256,
        "manifest_entry_digest": manifest_entry_digest(manifest_spec),
        "discovery": {
            "signal_start": str(start),
            "signal_end": str(end),
            "snapshot_digest": discovery_snapshot_digest,
        },
        "tolerances": {"atol": float(atol), "rtol": float(rtol)},
        "rank_contract": {
            "allow_tolerance_equivalent_ranks": allow_tolerance_equivalent_ranks,
            "exact_rank_mismatches": counts["rank_mismatches"],
            "tolerance_equivalent_rank_mismatches": counts[
                "tolerance_equivalent_rank_mismatches"
            ],
            "material_rank_mismatches": counts["material_rank_mismatches"],
        },
        "digests": {
            "python_frame": _frame_digest(py, sql=False),
            "sql_frame": _frame_digest(sql, sql=True),
            "python_keyset": _keyset_digest(py_keys),
            "sql_keyset": _keyset_digest(sql_keys),
        },
        "counts": counts,
        "mismatches": {
            "missing_in_sql": counts["missing_in_sql"],
            "extra_in_sql": counts["extra_in_sql"],
            "raw_values": counts["raw_mismatches"],
            "ranks": counts["rank_mismatches"],
        },
        "mismatch_samples": {
            "raw_values": raw_mismatch_samples,
            "ranks": rank_mismatch_samples,
        },
        "max_abs_error": max_abs_error,
        "max_rel_error": max_rel_error,
        "checks": checks,
        "passed": not failure_reasons,
        "status": "PASS" if not failure_reasons else "FAIL",
        "failure_reasons": failure_reasons,
    }
    evidence["evidence_digest"] = _payload_digest(evidence)
    return evidence
