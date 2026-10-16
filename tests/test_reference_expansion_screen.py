import pandas as pd
import pytest

from engine.reference_expansion_screen import completion, field_coverage, screen


def test_candidate_dry_run_is_not_loaded():
    with pytest.raises(ValueError, match="not a Gold-loaded"):
        completion(["old"], [{"id": "candidate", "quota_bucket": "aqr"}])


def test_source_quotas_do_not_add_up_to_total_target():
    result = completion([str(i) for i in range(45)], [])
    assert result["total_shortfall"] == 55
    assert result["source_shortfalls"] == {"academic": 20, "aqr": 10, "other_quant_firm": 10}
    assert not result["complete"]


def test_receipt_cannot_be_reused_for_an_invented_reference():
    ref = {"id": "invented", "quota_bucket": "aqr", "receipt": {
        "outer_transaction_committed": True, "status": "PUBLISHED", "readback_rows": 10,
        "dataset_id": "a" * 64, "readback_sha256": "b" * 64, "reference_count": 1}}
    with pytest.raises(ValueError, match="exact committed"):
        completion([], [ref])


def test_fail_closed_even_with_coverage_and_nonduplicate_name():
    result = screen({"id": "new", "formula": " a / b ", "assets": 1000,
                     "observed_months": 100}, existing_formulas=["a/b"])
    assert "EXACT_FORMULA_DUPLICATE" in result["failures"]
    assert "AVAILABILITY_REVIEW_REQUIRED" in result["failures"]
    assert not result["eligible"]


def test_cells_are_not_imputed_and_markets_remain_separate():
    frame = pd.DataFrame({"asset_id": [1, 2], "date": ["2020-01-31"] * 2,
                          "market": ["KOSPI", "KOSDAQ"], "fy_goodwill": [None, 10.]})
    rows = field_coverage(frame)
    assert next(r for r in rows if r["market"] == "TOTAL")["fraction"] == .5
    assert next(r for r in rows if r["market"] == "KOSPI")["nonnull"] == 0
    with pytest.raises(ValueError, match="Duplicate"):
        field_coverage(pd.concat([frame, frame]))
