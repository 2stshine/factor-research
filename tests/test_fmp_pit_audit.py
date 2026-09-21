from copy import deepcopy
import json

import pytest

from scripts.fmp_pit_audit import (
    compare_cboe, encoded, load_run, policy_comparison, series_stats, sha, write_new,
)


def observation(date="2020-01-02", value=12.3):
    return {"payload": {"date": date, "close": value}, "audit_received_at": "2026-09-20T00:00:00+00:00"}


def test_current_official_agreement_does_not_prove_first_vintage():
    report = compare_cboe([observation()], b"DATE,CLOSE\n01/02/2020,12.3\n")
    assert report["matched"] == 1
    assert report["first_vintage_proven"] is False


def test_mismatch_extra_and_missing_dates_are_separate():
    report = compare_cboe([observation(), observation("2020-01-06")],
                         b"DATE,CLOSE\n01/02/2020,12.4\n01/03/2020,12.3\n")
    assert report["mismatch_count"] == 1
    assert report["fmp_dates_absent_from_official"] == ["2020-01-06"]
    assert report["official_dates_missing_in_fmp"] == ["2020-01-03"]


def test_official_duplicate_fails_closed():
    with pytest.raises(ValueError, match="Duplicate official"):
        compare_cboe([observation()], b"DATE,CLOSE\n01/02/2020,12.3\n01/02/2020,12.4\n")


def test_announcement_date_is_not_effective_date():
    row = {"payload": {"date": "2020-03-16 07:48:00", "actual": .75},
           "source_row_index": 0, "audit_source_uri": "test"}
    result = policy_comparison([row], [("2019-10-16", 1.25), ("2020-03-17", .75)])
    assert result[0]["official_effective_rate"] == 1.25
    assert not result[0]["matches_effective_date_rate"]


def test_duplicate_payloads_and_nulls_are_preserved():
    row = observation()
    row["payload"] = {"date": "2020-01-02", "actual": None}
    second = deepcopy(row)
    second["payload"]["actual"] = 0
    result = series_stats("test", [row, second], "macro")
    assert result["null_value_rows"] == 1
    assert result["duplicate_excess"] == 1
    assert result["duplicates"][0]["distinct_payloads"] == 2
    assert result["pit_approved"] is False


def test_audit_output_cannot_overwrite_prior_review(tmp_path):
    path = tmp_path / "review.json"
    write_new(path, {"x": 1})
    with pytest.raises(FileExistsError):
        write_new(path, {"x": 2})
    assert json.loads(path.read_bytes()) == {"x": 1}


def test_load_run_validates_hash_and_raw_row_binding(tmp_path):
    raw = [{"date": "2015-01-02", "symbol": "X", "close": 1}]
    receipt = "2026-09-19T00:00:00+00:00"
    raw_path = tmp_path / "raw/response.json"
    obs_path = tmp_path / "observations.json"
    obs = [{"series_id": "X", "payload": raw[0], "source_row_index": 0,
            "payload_sha256": sha(encoded(raw[0])), "observed_at": receipt, "system_known_at": receipt}]
    write_new(raw_path, encoded(raw))
    write_new(obs_path, encoded(obs))
    write_new(raw_path.with_name("manifest.json"), {"complete": True, "status_code": 200,
        "received_at": receipt, "sha256": sha(encoded(raw)), "content_length": len(encoded(raw))})
    pm_path = tmp_path / "manifest.json"
    write_new(pm_path, {"complete": True, "source_object_uri": str(raw_path), "object_uri": str(obs_path),
        "source_sha256": sha(encoded(raw)), "sha256": sha(encoded(obs)), "content_length": len(encoded(obs)),
        "received_at": receipt, "row_count": 1})
    run_path = tmp_path / "run.json"
    write_new(run_path, {"complete": True, "partitions": [{"from": "2015-01-01", "row_count": 1,
        "manifest_uri": str(pm_path)}]})
    rows, _ = load_run(run_path)
    assert len(rows["X"]) == 1
    raw_path.write_bytes(b"[]")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_run(run_path)
