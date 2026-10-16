from copy import deepcopy

import pandas as pd
import pytest

from engine import reference_admission as gate
from engine.reference_library import definition_hash
from engine.research_generation import digest


def fixture():
    definition = {"id": "risk", "name_ko": "위험 통제", "family": "risk", "formula": "x",
                  "sources": [{"url": "https://example.com/paper"}]}
    values = pd.DataFrame([{"reference_id": "risk", "definition_hash": definition_hash(definition),
                           "asset_id": a, "stock_code": f"{a:06d}", "date": date,
                           "known_at": date + "T15:30:00+09:00", "value": float(a)}
                          for date in ["2020-01-31", "2020-02-29"] for a in (1, 2)])
    return definition, values, gate.AdmissionPolicy(2, 2)


def test_measurement_can_pass_without_profitable_alpha_or_return_labels():
    d, f, p = fixture()
    r = gate.assess_measurement(f, d, policy=p)
    assert r["assessment"] == "PASS" and not r["profitability_tested"]
    assert not r["first_vintage_independently_verified"]
    f["next_return"] = 0.1
    with pytest.raises(ValueError, match="no returns"):
        gate.assess_measurement(f, d, policy=p)


@pytest.mark.parametrize("change,reason", [
    (lambda f: f.assign(value=float("inf")), "NONFINITE"),
    (lambda f: f.assign(known_at="2030-01-01T00:00:00Z"), "FUTURE"),
    (lambda f: f.assign(stock_code=5930), "SECURITY_CODE"),
    (lambda f: pd.concat([f, f.iloc[:1]]), "DUPLICATE"),
])
def test_bad_measurements_rejected(change, reason):
    d, f, p = fixture()
    r = gate.assess_measurement(change(f), d, policy=p)
    assert r["assessment"] == "REJECTED"
    assert any(reason in x for x in r["errors"])


def test_insufficient_coverage_is_needs_data_not_alpha_failure():
    d, f, p = fixture()
    assert gate.assess_measurement(f.iloc[:1], d, policy=p)["assessment"] == "NEEDS_DATA"


def test_snapshot_diagnostics_cannot_be_used_as_admission():
    d, f, p = fixture()
    r = gate.assess_measurement(f, d, policy=p)
    report = gate.finalize([r], {"risk": d}, program_sha256="a" * 64, policy=p,
                           live_database_verified=False, source_receipts=[])
    assert report["decisions"][0]["status"] == "UNVERIFIED_SNAPSHOT_ONLY"
    with pytest.raises(ValueError, match="Snapshot-only"):
        gate.admitted_features(report, program_sha256="a" * 64, origin="OBSERVED")


def test_origin_hash_and_definition_duplicates():
    d, f, p = fixture()
    other = {**d, "id": "risk_duplicate"}
    f2 = f.assign(reference_id=other["id"], definition_hash=definition_hash(other))
    report = gate.finalize([gate.assess_measurement(f, d, policy=p), gate.assess_measurement(f2, other, policy=p)],
                          {"risk": d, other["id"]: other}, program_sha256="a" * 64, policy=p,
                          live_database_verified=False, source_receipts=[], origin="SYNTHETIC")
    assert len(gate.admitted_features(report, program_sha256="a" * 64, origin="SYNTHETIC")) == 1
    with pytest.raises(ValueError, match="origin/program"):
        gate.admitted_features(report, program_sha256="a" * 64, origin="OBSERVED")
    altered = deepcopy(report)
    altered["decisions"][1]["status"] = "ADMITTED"
    with pytest.raises(ValueError, match="hash"):
        gate.admitted_features(altered, program_sha256="a" * 64, origin="SYNTHETIC")
