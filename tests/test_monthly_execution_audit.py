import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.audit_monthly_execution_timing import audit
from scripts.build_assumed_fmp_regimes import save
from tests.test_assumed_regime_inputs import accept


def bundle(tmp_path, *, raw_open="100", next_day="2025-02-03", index_name="코스피", omit_daily=False):
    raw = tmp_path / "raw.parquet"
    pq.write_table(pa.Table.from_pylist([{"BAS_DD": next_day.replace("-", ""), "IDX_NM": index_name,
                                       "OPNPRC_IDX": raw_open}]), raw)
    raw_sha = hashlib.sha256(raw.read_bytes()).hexdigest()
    proof = {"local_calendar": {"dates": ["2025-01-31", next_day]}, "raw_daily_rows": [] if omit_daily else [
        {"trade_date": next_day, "source_file": str(raw), "source_sha256": raw_sha, "source_row_index": 0}]}
    sha = save(tmp_path / "provenance.json", proof)
    source = {"context_id": "KOSPI", "source_id": "synthetic-kospi", "kind": "market_index",
              "market_id": "KOSPI", "pit_status": "PIT_ASSUMED",
              "known_at_semantics": "ASSUMED_HISTORICAL_AVAILABILITY", "assumptions": ["Synthetic source"],
              "scope": {"start_month": "2025-01", "end_month": "2025-01"},
              "provenance_file": "provenance.json", "provenance_sha256": sha,
              "rows": [{"month": "2025-01", "known_at": "2025-01-31T23:59:59", "close": 99,
                        "source_trade_date": "2025-01-31"}]}
    approval_sha = save(tmp_path / "approval.json", accept(source))
    path = tmp_path / "context.json"
    save(path, {"schema_version": "diagnostic-regime-input-v1", "contexts": [
        {"source": source, "approval_file": "approval.json", "approval_sha256": approval_sha}]})
    return path, raw


def test_audit_only_dates_and_index_level_not_actual_execution(tmp_path):
    path, _ = bundle(tmp_path)
    result = audit(path, tmp_path / "report")
    assert result["date_aligned_months"] == 1
    assert result["rows"][0]["next_index_open_level"] == 100
    assert result["rows"][0]["exact_execution_at"] is None
    assert not result["execution_certified"] and not result["orders_submitted"]
    assert not result["factor_research_rerun"]
    with pytest.raises(FileExistsError):
        audit(path, tmp_path / "report")


@pytest.mark.parametrize("kwargs,reason", [({"raw_open": ""}, "MISSING_INDEX_OPEN"),
    ({"raw_open": "NaN"}, "INVALID_INDEX_OPEN"), ({"omit_daily": True}, "NEXT_CALENDAR_DATE_HAS_NO_INDEX_ROW"),
    ({"next_day": "2025-03-04"}, "NO_NEXT_MONTH_SESSION")])
def test_missing_not_forward_filled_or_approved(tmp_path, kwargs, reason):
    path, _ = bundle(tmp_path, **kwargs)
    result = audit(path, tmp_path / "report")
    assert result["rows"][0]["status"] == reason
    assert result["date_aligned_months"] == 0


def test_changed_raw_bytes_blocked(tmp_path):
    path, raw = bundle(tmp_path)
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw file hash"):
        audit(path, tmp_path / "report")


def test_exact_index_identity_required(tmp_path):
    path, _ = bundle(tmp_path, index_name="코스닥")
    with pytest.raises(ValueError, match="row identity"):
        audit(path, tmp_path / "report")
