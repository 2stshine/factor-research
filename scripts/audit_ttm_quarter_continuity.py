"""Synthetic, read-only engine probe; does not validate any actual Silver rows.

Run with ``python -m scripts.audit_ttm_quarter_continuity``. A detected defect is
an audit finding, not a passing financial-data test. No DB or return labels used.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine import fundamentals
from engine.research_memory_transfer import write_artifact


def main():
    source = Path(fundamentals.__file__)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    fixtures = {
        "consecutive_control": [
            ("2021-06-30", "Q2", 20.0), ("2021-09-30", "Q3", 30.0),
            ("2021-12-31", "Q4", 40.0), ("2022-03-31", "Q1", 10.0),
        ],
        "missing_q3_probe": [
            ("2021-03-31", "Q1", 10.0), ("2021-06-30", "Q2", 20.0),
            ("2021-12-31", "Q4", 40.0), ("2022-03-31", "Q1", 10.0),
        ],
    }
    results = []
    for name, observations in fixtures.items():
        state = {(pd.Timestamp(date), quarter, "revenue"): {"value": value}
                 for date, quarter, value in observations}
        value = fundamentals._snapshot(state, 1, pd.Timestamp("2022-05-16"))["revenue_ttm"]
        results.append({
            "case": name, "synthetic": True, "observations": observations,
            "span_days": (pd.Timestamp(observations[-1][0]) - pd.Timestamp(observations[0][0])).days,
            "observed_revenue_ttm": None if pd.isna(value) else float(value),
            "expected_four_consecutive_quarter_contract": 100.0 if name == "consecutive_control" else "MISSING_OR_REJECT",
        })
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    stamp = datetime.now(timezone.utc)
    payload = {
        "schema_version": "synthetic-ttm-quarter-continuity-audit-v1",
        "observed_at": stamp.isoformat(), "source_sha256": before,
        "source_unchanged": True, "database_accessed": False,
        "actual_certified_data_occurrence": "NOT_EXAMINED",
        "normal_control_matches": results[0]["observed_revenue_ttm"] == 100.0,
        "missing_quarter_defect_reproduced": results[1]["observed_revenue_ttm"] is not None,
        "results": results,
    }
    path = Path(__file__).resolve().parents[1] / "research/v2/ttm-continuity-audits" / (stamp.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    write_artifact(path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("Saved:", path)


if __name__ == "__main__":
    main()
