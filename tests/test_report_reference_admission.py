from copy import deepcopy

import pytest

from engine import reference_admission as gate
from scripts.report_reference_admission import render
from tests.test_reference_admission import fixture


def report():
    d, f, p = fixture()
    return gate.finalize([gate.assess_measurement(f, d, policy=p)], {d["id"]: d},
                         program_sha256="a" * 64, policy=p,
                         live_database_verified=False, source_receipts=[])


def test_snapshot_report_never_claims_actual_admission_or_strategy_performance():
    body = render(report())
    assert "실제 입고 확정이 아니다" in body
    assert "실제 수익률 기반 전략 선택 결과는 포함하지 않는다" in body
    assert "동결 원본 진단만 완료" in body


def test_tampered_admission_or_unrelated_readiness_rejected():
    r = report()
    changed = deepcopy(r)
    changed["live_database_verified"] = True
    with pytest.raises(ValueError, match="digest"):
        render(changed)
    with pytest.raises(ValueError, match="another program"):
        render(r, {"program_sha256": "b" * 64})
