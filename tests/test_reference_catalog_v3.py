"""Definition-only catalog contract: no legacy factor imports, data/API or returns."""
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "research/v3/reference-catalog.json").read_text())
FACTORS = {item["id"]: item for item in CATALOG["factors"]}


def test_catalog_is_non_executable_and_has_no_approval_claims():
    assert CATALOG["schema_version"] == "research-v3-reference-catalog-v1"
    assert CATALOG["status"] == "DEFINITION_CATALOG_ONLY"
    assert not CATALOG["execution_enabled"]
    assert CATALOG["experiment_count"] == CATALOG["certification_writes"] == CATALOG["gold_writes"] == 0
    assert not CATALOG["global_readiness"]["v3_panel_certified"]
    assert len(FACTORS) == len(CATALOG["factors"]) == 10


def test_sources_are_dated_primary_references_and_resolve_by_id():
    references = {item["id"]: item for item in CATALOG["references"]}
    assert len(references) == len(CATALOG["references"])
    permitted = {"mba.tuck.dartmouth.edu", "www.aqr.com", "pages.stern.nyu.edu", "archive.nyu.edu", "doi.org"}
    for reference in references.values():
        parsed = urlparse(reference["url"])
        assert parsed.scheme == "https" and parsed.hostname in permitted
        assert reference["retrieved_date"] == "2026-10-02"
        assert reference["verified_scope"] and reference["source_type"]
    for item in FACTORS.values():
        assert item["reference_ids"] and set(item["reference_ids"]) <= references.keys()


@pytest.mark.parametrize("item", CATALOG["factors"], ids=FACTORS)
def test_each_definition_separates_reference_from_pending_korean_adaptation(item):
    assert item["approved"] is False and item["execution_enabled"] is False
    assert item["readiness"]["status"] in {"PENDING", "BLOCKED"}
    assert item["readiness"]["blockers"] and item["readiness"]["next_action"]
    assert item["canonical"]["formula"] and "lookback" in item["canonical"]
    assert item["korean_adaptation"]["equivalent_to_canonical"] is False
    assert item["korean_adaptation"]["differences"]
    assert item["input_requirements"] and item["measurement_requirements"]
    assert item["hypothesis_ko"] and item["orientation"]["raw_expected_sign"] in {-1, 1, None}
    assert item["role_after_standalone_alpha_failure"] == "RETAIN_AS_REFERENCE_CONTROL"


def test_market_return_is_not_a_cross_sectional_stock_score():
    market = FACTORS["ref_market_excess_kr_v1"]
    assert market["object_type"] == "MARKET_RETURN_CONTROL"
    assert market["korean_adaptation"]["stock_characteristic"] is None
    assert market["orientation"]["raw_expected_sign"] is None
    assert CATALOG["selection_policy"]["contemporaneous_factor_return_is_not_forward_feature"]


def test_momentum_skip_and_feature_label_boundary_are_explicit():
    momentum = FACTORS["ref_momentum_price_12_2_kr_v1"]
    assert momentum["canonical"]["lookback"]["months"] == 12
    assert momentum["canonical"]["lookback"]["skip_recent_months"] == 1
    assert momentum["korean_adaptation"]["formula"].endswith("adj_close_(t-1)/adj_close_(t-12)-1")
    boundary = CATALOG["global_readiness"]["feature_label_boundary"]
    assert "total_return_close" in boundary and "label-only" in boundary


def test_incomplete_composite_does_not_invent_an_executable_formula():
    quality = FACTORS["ref_quality_qmj_kr_v1"]
    assert quality["object_type"] == "REFERENCE_COMPOSITE_NOT_EXECUTABLE"
    assert quality["korean_adaptation"]["formula"] is None
    assert quality["readiness"]["status"] == "BLOCKED"


def test_low_beta_is_not_silently_shortened_or_confused_with_low_volatility():
    beta = FACTORS["ref_low_beta_bab_kr_v1"]
    volatility = FACTORS["ref_low_volatility_252d_kr_v1"]
    assert beta["canonical"]["lookback"]["months"] == 60
    assert "252" in beta["korean_adaptation"]["name"]
    assert "not canonical" in " ".join(beta["korean_adaptation"]["differences"])
    assert "not beta" in " ".join(volatility["korean_adaptation"]["differences"])


def test_reference_controls_and_joint_selection_do_not_reimpose_old_hard_novelty():
    policy = CATALOG["selection_policy"]
    assert policy["reference_controls_retained_after_standalone_alpha_failure"]
    assert policy["orthogonal_novelty_is_hard_requirement"] is False
    assert policy["final_holdout_may_select_factors"] is False
    assert policy["evaluate_incremental_joint_value"] and policy["explanation_is_not_prediction"]


def test_catalog_retains_legacy_issue_without_claiming_it_was_fixed():
    issues = CATALOG["legacy_findings_not_resolved_by_this_catalog"]
    assert issues[0]["status"] == "UNRESOLVED_LEGACY_ISSUE_AT_PIVOT"
    assert "old builder" in issues[0]["v3_action"]


def test_document_covers_all_catalog_members_in_readiness_table():
    document = (ROOT / "docs/research-v3-reference-library.md").read_text()
    assert "실행·승인 0건" in document and "종목 특성" in document
    assert "원장 동일성" in document and "최종 보류 구간" in document
    assert document.count("| PENDING:") == 4
    assert document.count("| BLOCKED:") == 6
