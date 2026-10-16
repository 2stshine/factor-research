"""Safety tests use only synthetic manifests; no market data are loaded."""
from copy import deepcopy

import pytest

from strategies.comparison_contract import (
    SCHEMA_VERSION,
    assert_observation_bounds,
    canonical_manifest_hash,
    fixed_variants,
    validate_manifest,
)


def plan():
    return {
        "schema_version": SCHEMA_VERSION,
        "research_scope": "development_only",
        "independent_oos": False,
        "source_evidence_grade": "HISTORICAL_REUSED",
        "factor_bindings": [{"factor_id": "example_factor", "definition_hash": "a" * 16}],
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


def sealed(start="2023-03", end="2023-05", return_end="2023-06"):
    return [{"campaign_id": "sealed-a", "signal_start": start,
             "signal_end": end, "return_end": return_end}]


def test_explicit_development_plan_is_copied_and_utc_normalized():
    raw = plan()
    original = deepcopy(raw)
    result = validate_manifest(raw, sealed_campaigns=sealed())
    assert raw == original
    assert result["bounds"]["signal_start"] == "2022-01-31T06:30:00Z"
    assert result["research_scope"] == "development_only"
    assert result["independent_oos"] is False
    assert [row["variant_id"] for row in result["variants"]] == [
        "q20_equal", "q10_equal", "q20_sqrt_cap", "q10_sqrt_cap",
    ]


def test_hash_includes_extra_provenance_and_preserves_frozen_factor_order():
    raw = plan()
    raw["provenance"] = {"dataset_sha256": "b" * 64, "cost_bps": 30}
    digest = canonical_manifest_hash(raw)
    assert digest == canonical_manifest_hash(dict(reversed(list(raw.items()))))
    assert digest == canonical_manifest_hash(validate_manifest(raw, sealed_campaigns=[]))
    raw["provenance"]["cost_bps"] = 31
    assert canonical_manifest_hash(raw) != digest
    raw["factor_bindings"].append({"factor_id": "another_factor", "definition_hash": "b" * 64})
    digest = canonical_manifest_hash(raw)
    raw["factor_bindings"].reverse()
    assert canonical_manifest_hash(raw) != digest


@pytest.mark.parametrize("field,value", [
    ("independent_oos", True), ("independent_oos", 0),
    ("research_scope", "confirmation"), ("source_evidence_grade", "PROSPECTIVE_PRISTINE"),
    ("calendar_timezone", "Mars/Olympus"), ("schema_version", "unknown"),
])
def test_scope_cannot_be_upgraded_to_independent_confirmation(field, value):
    raw = plan()
    raw[field] = value
    with pytest.raises(ValueError):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("field,value", [
    ("weighting", "market_cap"), ("fraction", 0.05),
    ("variant_id", "best_performance"), ("baseline", 1),
])
def test_variant_definitions_are_fixed_before_results(field, value):
    raw = plan()
    raw["variants"][0][field] = value
    with pytest.raises(ValueError, match="fixed variant"):
        validate_manifest(raw, sealed_campaigns=[])


def test_variant_order_and_membership_cannot_be_changed():
    raw = plan()
    raw["variants"].reverse()
    with pytest.raises(ValueError, match="fixed variant"):
        validate_manifest(raw, sealed_campaigns=[])
    raw = plan()
    raw["variants"].pop()
    with pytest.raises(ValueError, match="four preregistered"):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("binding", [
    {"factor_id": "example_factor", "definition_hash": "b" * 16},
    {"factor_id": "another_factor", "definition_hash": "a" * 16},
])
def test_duplicate_names_and_definition_aliases_are_rejected(binding):
    raw = plan()
    raw["factor_bindings"].append(binding)
    with pytest.raises(ValueError, match="duplicate"):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("digest", [None, "a" * 15, "a" * 32, "G" * 64])
def test_invalid_definition_hash_is_rejected(digest):
    raw = plan()
    raw["factor_bindings"][0]["definition_hash"] = digest
    with pytest.raises(ValueError, match="definition_hash"):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("field", list(plan()["bounds"]))
def test_every_bound_is_mandatory_and_none_never_means_unlimited(field):
    raw = plan()
    raw["bounds"].pop(field)
    with pytest.raises(ValueError):
        validate_manifest(raw, sealed_campaigns=[])
    raw["bounds"][field] = None
    with pytest.raises(ValueError):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("timestamp", [
    "2022-12-31", "2022-12-31T15:30:00", "2022-12-31T15:30:00+25:00",
    "2022-12-31T15:30:00+14:01", "2022-12-31T15:30:00+09:60",
    "2022-12-31T15:30:00-00:00", "2022-02-30T15:30:00+09:00",
])
def test_ambiguous_or_invalid_timestamps_are_rejected(timestamp):
    raw = plan()
    raw["bounds"]["signal_end"] = timestamp
    with pytest.raises(ValueError):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("field,value", [
    ("decision_start", "2023-01"), ("decision_end", "2022-11"),
    ("input_end", "2022-11-30T23:59:59+09:00"),
    ("trade_start", "2022-01-31T15:30:00+09:00"),
    ("return_end", "2022-12-01T09:00:00+09:00"),
    ("return_support_end", "2023-01-31T23:59:59+09:00"),
    ("allowed_data_time", "2023-02-15T23:59:59+09:00"),
])
def test_reversed_or_insufficient_support_is_rejected(field, value):
    raw = plan()
    raw["bounds"][field] = value
    with pytest.raises(ValueError):
        validate_manifest(raw, sealed_campaigns=[])


@pytest.mark.parametrize("record", [
    sealed("2018-06", "2018-07", "2018-08"),  # warm-up input only
    sealed("2022-06", "2022-07", "2022-08"),  # decisions
    sealed("2023-01", "2023-01", "2023-02"),  # final trade/return support
    sealed("2023-02", "2023-02", "2023-03"),  # support after last decision
    sealed("2017-11", "2017-12", "2018-01"),  # sealed return tail only
])
def test_input_and_return_support_overlaps_are_blocked(record):
    with pytest.raises(ValueError, match="overlaps sealed"):
        validate_manifest(plan(), sealed_campaigns=record)


def test_month_overlap_uses_korean_calendar_and_closed_requested_endpoint():
    raw = plan()
    raw["bounds"]["input_start"] = "2018-01-31T15:00:00Z"  # Feb 1 in Korea
    validate_manifest(raw, sealed_campaigns=sealed("2017-11", "2017-12", "2018-01"))
    raw["bounds"]["return_support_end"] = "2023-02-28T15:00:00Z"  # Mar 1 in Korea
    raw["bounds"]["allowed_data_time"] = "2023-02-28T15:00:00Z"
    with pytest.raises(ValueError, match="overlaps sealed"):
        validate_manifest(raw, sealed_campaigns=sealed())


def test_sealed_inventory_must_be_explicit_and_complete():
    with pytest.raises(TypeError):
        validate_manifest(plan())
    with pytest.raises(ValueError, match="explicitly supplied list"):
        validate_manifest(plan(), sealed_campaigns=None)
    for key in ("campaign_id", "signal_start", "signal_end", "return_end"):
        record = sealed()
        record[0].pop(key)
        with pytest.raises(ValueError):
            validate_manifest(plan(), sealed_campaigns=record)


def test_observation_checks_actual_exit_not_just_signal_month():
    args = dict(signal_time="2022-12-31T15:30:00+09:00",
                trade_time="2023-01-02T09:00:00+09:00",
                label_exit_time="2023-02-01T09:00:00+09:00")
    assert_observation_bounds(plan(), **args)
    args["label_exit_time"] = "2023-03-01T09:00:00+09:00"
    with pytest.raises(ValueError, match="label_exit_time"):
        assert_observation_bounds(plan(), **args)
    args["label_exit_time"] = args["trade_time"]
    with pytest.raises(ValueError, match="signal_time < trade_time < label_exit_time"):
        assert_observation_bounds(plan(), **args)


@pytest.mark.parametrize("extra", [float("nan"), float("inf"), (1, 2), {1: "invalid key"}])
def test_extra_metadata_must_also_be_canonical_finite_json(extra):
    raw = plan()
    raw["extra"] = extra
    with pytest.raises(ValueError, match="JSON"):
        canonical_manifest_hash(raw)
