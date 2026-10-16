"""Pure, fail-closed contract for a preregistered implementation comparison.

This module performs no I/O and does not grant access to any dataset. Call
``validate_manifest(plan, sealed_campaigns=metadata)`` before reading comparison
inputs, then check each realized label with ``assert_observation_bounds``.
The caller supplies all currently sealed campaigns; even an empty list must be
explicit. Campaign records contain ``campaign_id``, ``signal_start``,
``signal_end`` and ``return_end`` as YYYY-MM months. Every supplied record is
treated as sealed, without interpreting lifecycle statuses.

Plans require these fields (additional JSON fields are preserved and hashed)::

    {
        "schema_version": "strategy-comparison-plan-v1",
        "research_scope": "development_only",
        "independent_oos": False,
        "source_evidence_grade": "HISTORICAL_REUSED",
        "factor_bindings": [
            {"factor_id": "example_factor", "definition_hash": "a" * 16}
        ],
        "variants": fixed_variants(),
        "bounds": {
            "input_start": "2018-01-01T00:00:00+09:00",
            "input_end": "2022-12-31T23:59:59+09:00",
            "allowed_data_time": "2023-02-28T23:59:59+09:00",
            "decision_start": "2022-01", "decision_end": "2022-12",
            "signal_start": "2022-01-31T15:30:00+09:00",
            "signal_end": "2022-12-31T15:30:00+09:00",
            "trade_start": "2022-02-03T09:00:00+09:00",
            "trade_end": "2023-01-02T09:00:00+09:00",
            "return_start": "2022-02-03T09:00:00+09:00",
            "return_end": "2023-02-01T09:00:00+09:00",
            "return_support_end": "2023-02-28T23:59:59+09:00",
        },
    }

Validation order: pure JSON and identity/scope; fixed variants and factor
bindings; timestamp/month parsing, order and coverage; then sealed overlap.
Month boundaries always use Asia/Seoul; timestamps normalize to UTC. Timestamp
bounds are inclusive, whereas a sealed month interval ends exclusively at the
start of the following month. Exact exchange sessions and input availability
at each decision are the execution engine's responsibility.

``canonical_manifest_hash`` validates the local contract but cannot attest to
the supplied campaign inventory. Store its digest separately from the plan:
every plan field, including additional provenance or cost fields, is hashed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import re
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "strategy-comparison-plan-v1"
CALENDAR_TIMEZONE = "Asia/Seoul"
_MARKET_TZ = ZoneInfo(CALENDAR_TIMEZONE)
_MONTH = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])\Z")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)
_HASH = re.compile(r"(?:[0-9a-f]{16}|[0-9a-f]{64})\Z")
_FACTOR_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
_TIMESTAMP_FIELDS = (
    "input_start", "input_end", "allowed_data_time", "signal_start",
    "signal_end", "trade_start", "trade_end", "return_start", "return_end",
    "return_support_end",
)


def fixed_variants() -> list[dict]:
    """Return fresh JSON objects in their preregistered, non-performance order."""
    return [
        {"variant_id": "q20_equal", "fraction": 0.2,
         "weighting": "equal", "baseline": True},
        {"variant_id": "q10_equal", "fraction": 0.1,
         "weighting": "equal", "baseline": False},
        {"variant_id": "q20_sqrt_cap", "fraction": 0.2,
         "weighting": "sqrt_cap", "baseline": False},
        {"variant_id": "q10_sqrt_cap", "fraction": 0.1,
         "weighting": "sqrt_cap", "baseline": False},
    ]


def _json_copy(value, *, path: str = "manifest"):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_json_copy(item, path=f"{path}[{i}]") for i, item in enumerate(value)]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError(f"{path}: JSON object keys must be strings")
        return {key: _json_copy(item, path=f"{path}.{key}") for key, item in value.items()}
    raise ValueError(f"{path}: only finite, pure JSON values are permitted")


def _object(value, *, label: str) -> dict:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return value


def _month(value, *, label: str) -> datetime:
    if type(value) is not str or not _MONTH.fullmatch(value):
        raise ValueError(f"{label} must be a YYYY-MM month")
    try:
        return datetime(int(value[:4]), int(value[5:]), 1, tzinfo=_MARKET_TZ)
    except ValueError as exc:
        raise ValueError(f"{label} is not a valid calendar month") from exc


def _timestamp(value, *, label: str) -> datetime:
    if type(value) is not str or not _TIMESTAMP.fullmatch(value):
        raise ValueError(f"{label} requires an ISO timestamp with an explicit timezone")
    if not value.endswith("Z"):
        hours, minutes = int(value[-5:-3]), int(value[-2:])
        if hours > 14 or minutes > 59 or (hours == 14 and minutes):
            raise ValueError(f"{label} has an invalid timezone offset")
        if value.endswith("-00:00"):
            raise ValueError(f"{label} cannot use the unknown timezone offset -00:00")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{label} is not a valid timestamp") from exc


def _next_month(month: datetime) -> datetime:
    try:
        if month.month == 12:
            return month.replace(year=month.year + 1, month=1)
        return month.replace(month=month.month + 1)
    except ValueError as exc:
        raise ValueError("sealed return_end has no representable following month") from exc


def _validate_payload(manifest: dict) -> tuple[dict, dict[str, datetime]]:
    try:
        plan = _object(_json_copy(manifest), label="manifest")
    except RecursionError as exc:
        raise ValueError("manifest is not finite JSON") from exc
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    if plan.get("research_scope") != "development_only" or plan.get("independent_oos") is not False:
        raise ValueError("comparison must be development_only with independent_oos=false")
    if plan.get("source_evidence_grade") != "HISTORICAL_REUSED":
        raise ValueError("source_evidence_grade must be HISTORICAL_REUSED")
    if plan.get("calendar_timezone", CALENDAR_TIMEZONE) != CALENDAR_TIMEZONE:
        raise ValueError(f"calendar_timezone must be {CALENDAR_TIMEZONE}")

    variants = plan.get("variants")
    if type(variants) is not list or len(variants) != 4:
        raise ValueError("variants must contain the four preregistered variants")
    for row, expected in zip(variants, fixed_variants(), strict=True):
        row = _object(row, label="variant")
        for key, value in expected.items():
            if type(row.get(key)) is not type(value) or row[key] != value:
                raise ValueError(f"fixed variant order/definition mismatch: {key}")

    factors = plan.get("factor_bindings")
    if type(factors) is not list or not factors:
        raise ValueError("factor_bindings must be a nonempty frozen list")
    factor_ids, definition_hashes = set(), set()
    for row in factors:
        row = _object(row, label="factor binding")
        name, digest = row.get("factor_id"), row.get("definition_hash")
        if type(name) is not str or not _FACTOR_ID.fullmatch(name):
            raise ValueError("factor_id must be a lowercase factor identifier")
        if type(digest) is not str or not _HASH.fullmatch(digest):
            raise ValueError("definition_hash must be 16 or 64 lowercase hexadecimal digits")
        if name in factor_ids or digest in definition_hashes:
            raise ValueError("duplicate factor_id or definition_hash")
        factor_ids.add(name)
        definition_hashes.add(digest)

    bounds = _object(plan.get("bounds"), label="bounds")
    start = _month(bounds.get("decision_start"), label="decision_start")
    end = _month(bounds.get("decision_end"), label="decision_end")
    if start > end:
        raise ValueError("decision_start must not follow decision_end")
    times = {
        field: _timestamp(bounds.get(field), label=field)
        for field in _TIMESTAMP_FIELDS
    }
    for left, right in (
        ("input_start", "input_end"), ("input_end", "allowed_data_time"),
        ("signal_start", "signal_end"), ("trade_start", "trade_end"),
        ("return_start", "return_end"), ("return_end", "return_support_end"),
        ("return_support_end", "allowed_data_time"),
        ("input_start", "signal_start"), ("signal_end", "input_end"),
        ("trade_start", "return_start"), ("trade_end", "return_end"),
    ):
        if times[left] > times[right]:
            raise ValueError(f"{left} must not follow {right}")
    for left, right in (("signal_start", "trade_start"), ("signal_end", "trade_end")):
        if times[left] >= times[right]:
            raise ValueError(f"{left} must precede {right}")
    for field, declared in (("signal_start", "decision_start"), ("signal_end", "decision_end")):
        local_month = times[field].astimezone(_MARKET_TZ).strftime("%Y-%m")
        if local_month != bounds[declared]:
            raise ValueError(f"{field} must belong to {declared} in {CALENDAR_TIMEZONE}")
    for field, value in times.items():
        bounds[field] = value.isoformat().replace("+00:00", "Z")
    return plan, times


def validate_manifest(manifest: dict, *, sealed_campaigns: list[dict]) -> dict:
    """Return a normalized copy after checking every supplied sealed interval.

    Input coverage and the full signal-to-return-support evaluation interval
    must both be disjoint from sealed signal/return months. This deliberately
    includes warm-up inputs and return support beyond the final decision month.
    Missing campaign bounds, None inventories and None plan bounds fail closed.
    """
    plan, times = _validate_payload(manifest)
    if type(sealed_campaigns) is not list:
        raise ValueError("sealed_campaigns must be an explicitly supplied list")
    seen = set()
    for metadata in sealed_campaigns:
        metadata = _object(metadata, label="sealed campaign metadata")
        campaign_id = metadata.get("campaign_id")
        if type(campaign_id) is not str or not campaign_id.strip() or campaign_id in seen:
            raise ValueError("sealed campaign_id must be nonempty and unique")
        seen.add(campaign_id)
        first = _month(metadata.get("signal_start"), label="sealed signal_start")
        last = _month(metadata.get("signal_end"), label="sealed signal_end")
        return_end = _month(metadata.get("return_end"), label="sealed return_end")
        if not first <= last <= return_end:
            raise ValueError("sealed signal/return bounds are reversed")
        stop = _next_month(return_end)
        for label, desired_start, desired_end in (
            ("input", times["input_start"], times["input_end"]),
            ("evaluation/return support", times["signal_start"], times["return_support_end"]),
        ):
            if desired_start < stop and first <= desired_end:
                raise ValueError(f"{label} overlaps sealed campaign {campaign_id}")
    return plan


def canonical_manifest_hash(manifest: dict) -> str:
    """Hash all normalized JSON fields; this does not check external exposures."""
    plan, _ = _validate_payload(manifest)
    body = json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def assert_observation_bounds(
    manifest: dict,
    *,
    signal_time: str,
    trade_time: str,
    label_exit_time: str,
) -> None:
    """Reject observations whose actual timing exceeds the frozen contract.

    In particular, a decision inside the plan does not authorize a label that
    matures after the allowed data timestamp. This check does not substitute
    for exchange-session, transaction-price or point-in-time feature checks.
    """
    _, bounds = _validate_payload(manifest)
    signal = _timestamp(signal_time, label="signal_time")
    trade = _timestamp(trade_time, label="trade_time")
    exit_time = _timestamp(label_exit_time, label="label_exit_time")
    if not signal < trade < exit_time:
        raise ValueError("observation must satisfy signal_time < trade_time < label_exit_time")
    for label, value, first, last in (
        ("signal_time", signal, "signal_start", "signal_end"),
        ("trade_time", trade, "trade_start", "trade_end"),
        ("label_exit_time", exit_time, "return_start", "return_end"),
    ):
        if not bounds[first] <= value <= bounds[last]:
            raise ValueError(f"{label} lies outside frozen {first}/{last}")
    if exit_time > bounds["return_support_end"] or exit_time > bounds["allowed_data_time"]:
        raise ValueError("label_exit_time exceeds return support or allowed data time")
