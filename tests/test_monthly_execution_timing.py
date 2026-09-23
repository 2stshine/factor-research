from copy import deepcopy

import pytest

from engine.monthly_execution_timing import check_timing


def setup():
    # Weekend month-end and delayed/special session open are supplied explicitly.
    return dict(month="2025-08", decision_at="2025-08-31T23:59:59+09:00",
                input_available_at=["2025-08-31T23:59:00+09:00"],
                session_opens=["2025-08-29T09:00:00+09:00", "2025-09-01T10:00:00+09:00"],
                execution_at="2025-09-01T10:00:00+09:00", price=100.)


def test_ordered_timing_does_not_certify_trading():
    result = check_timing(**setup())
    assert result["timing_passed"] and not result["provided_contract_passed"]
    assert len(result["missing_attestations"]) == 4
    assert not result["actual_fill_verified"] and not result["orders_submitted"]


def test_explicit_attestations_not_inferred_from_temporal_success():
    args = setup()
    args["attestations"] = {k: True for k in check_timing(**args)["missing_attestations"]}
    result = check_timing(**args)
    assert result["provided_contract_passed"]
    assert result["status"] == "PROVIDED_CONTRACT_CHECK_ONLY"
    assert not result["actual_fill_verified"]


@pytest.mark.parametrize("field,value,reason", [
    ("execution_at", "2025-08-29T15:30:00+09:00", "EXECUTION_NOT_AFTER_DECISION"),
    ("execution_at", "2025-09-01T09:00:00+09:00", "NOT_FIRST_SUPPLIED_NEXT_SESSION_OPEN"),
    ("input_available_at", ["2025-09-01T00:00:00+09:00"], "INPUT_AVAILABLE_AFTER_DECISION"),
    ("decision_at", "2025-08-29T15:30:00+09:00", "DECISION_NOT_DECLARED_MONTH_END_CUTOFF"),
    ("input_available_at", [], "NO_INPUT_AVAILABILITY_EVIDENCE"),
    ("session_opens", [], "NOT_FIRST_SUPPLIED_NEXT_SESSION_OPEN"),
    ("price", 0, "INVALID_EXECUTION_PRICE"), ("price", True, "INVALID_EXECUTION_PRICE"),
    ("price", float("nan"), "INVALID_EXECUTION_PRICE"),
])
def test_invalid_contract_blocked(field, value, reason):
    args = setup()
    args[field] = value
    result = check_timing(**args)
    assert not result["timing_passed"] and reason in result["violations"]


def test_missing_next_month_cannot_be_silently_skipped():
    args = setup()
    args.update(session_opens=["2025-10-01T09:00:00+09:00"], execution_at="2025-10-01T09:00:00+09:00")
    assert "EXECUTION_NOT_NEXT_MONTH" in check_timing(**args)["violations"]


def test_timezone_required_and_duplicate_calendar_rejected():
    args = setup()
    args["decision_at"] = "2025-08-31T23:59:59"
    with pytest.raises(ValueError, match="Timezone"):
        check_timing(**args)
    args = setup()
    args["session_opens"] *= 2
    with pytest.raises(ValueError, match="Duplicate"):
        check_timing(**args)


def test_equal_instants_cross_timezone_are_supported():
    args = setup()
    args["decision_at"] = "2025-08-31T14:59:59Z"
    assert check_timing(**args)["timing_passed"]
