"""Display changes must not recalculate or filter frozen diagnostic states."""
from copy import deepcopy

from scripts.dashboard_exports.export_research_catalog import compact_regimes


def test_coarse_default_is_only_presentation_and_keeps_all_states():
    section = {"status": "PARTIAL", "data": {
        "regimes": [{"regime": "UP_LOW", "n_months": 0}],
        "views": {"regime_detail": [{"regime_detail": "UNKNOWN", "n_months": 2}]},
        "monthly": [{"month": "2025-01", "regime": "UNKNOWN", "rank_ic": None}],
        "macro_views": {"MACRO": {"states": [{"state": "NEUTRAL", "n_months": 1}],
            "monthly": [{"month": "2025-01", "effective_month": "2025-02", "state": "NEUTRAL"}]}}}}
    original = deepcopy(section)
    result = compact_regimes(section)
    assert section == original
    assert result["presentation"]["primary_view"] == "regime"
    assert result["presentation"]["macro_cross_product"] is False
    assert result["regimes"] == original["data"]["regimes"]
    assert result["views"] == original["data"]["views"]
    assert result["monthly"] == original["data"]["monthly"]
    assert result["macro_views"]["MACRO"]["monthly_states"][0]["state"] == "NEUTRAL"
    assert "calendar-contiguous" in result["units"]["n_episodes"]
    assert "UNKNOWN does not create" in result["units"]["n_joint_usable_episodes"]


def test_no_diagnostics_are_manufactured_for_legacy_missing_sections():
    assert compact_regimes({"status": "NOT_COLLECTED"}) == {"status": "NOT_COLLECTED"}
