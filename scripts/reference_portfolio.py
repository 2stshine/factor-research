"""Explicit synthetic-only demo; never opens a database or loads real factors."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine.reference_portfolio import WalkForwardConfig, walk_forward_predict


def synthetic_fixture(*, months=36, assets=8):
    from engine.research_generation import make_factor_entry, make_generation
    entries = [make_factor_entry(generation_id="synthetic-reference-demo", factor_id=name,
        definition_sha256=hashlib.sha256((name + ":definition").encode()).hexdigest(),
        implementation_sha256=hashlib.sha256((name + ":implementation").encode()).hexdigest(),
        feature_sha256=hashlib.sha256((name + ":synthetic-artifact-placeholder").encode()).hexdigest(),
        approval_evidence_sha256=hashlib.sha256((name + ":synthetic-not-real-approval").encode()).hexdigest(),
        admitted_at="2017-12-01T00:00:00+09:00") for name in ("synthetic_quality", "synthetic_value", "synthetic_growth")]
    manifest = make_generation(generation_id="synthetic-reference-demo", purpose="SYNTHETIC", approved_factors=entries)
    rng = np.random.default_rng(73021)
    rows = []
    for m, month in enumerate(pd.period_range("2018-01", periods=months, freq="M")):
        decision = month.to_timestamp("M").tz_localize("Asia/Seoul") + pd.Timedelta(hours=18)
        label_end = (month + 1).to_timestamp("M").tz_localize("Asia/Seoul") + pd.Timedelta(hours=16)
        for asset in range(assets):
            first, second, third = rng.normal(size=3)
            rows.append({"asset_id": asset + 1, "signal_month": str(month), "decision_at": decision.isoformat(),
                "label_end_at": label_end.isoformat(), "label_available_at": (label_end + pd.Timedelta(hours=3)).isoformat(),
                "synthetic_quality": first, "synthetic_value": second,
                "synthetic_growth": 0.75 * first + 0.25 * third,
                "next_month_return": float(0.01 * first - 0.007 * second + rng.normal(scale=0.003)),
                **{f"{entry['factor_id']}__known_at": (decision - pd.Timedelta(hours=1)).isoformat() for entry in entries}})
    frame = pd.DataFrame(rows)
    frame.attrs["feature_entries"] = [{key: entry[key] for key in ("factor_id", "generation_id", "entry_sha256")} for entry in entries]
    config = WalkForwardConfig(first_test_month="2020-01", min_train_months=6, outer_train_months=24,
        inner_train_months=12, inner_validation_months=2, inner_splits=2)
    return frame, manifest, config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-demo", action="store_true", help="Required: synthetic numerical validation only")
    parser.add_argument("--output", type=Path, required=True, help="New local JSON file; existing files are never overwritten")
    args = parser.parse_args(argv)
    if not args.synthetic_demo:
        parser.error("Only --synthetic-demo is implemented; real data fitting is not connected")
    frame, manifest, config = synthetic_fixture()
    result = walk_forward_predict(frame, manifest, config)
    # No realized labels, profitability statistics, or trading recommendations.
    payload = {"schema_version": result["schema_version"], "status": "SYNTHETIC_DEVELOPMENT_DEMO_NOT_FINANCIAL_EVIDENCE",
        "purpose": "SYNTHETIC", "generation_id": result["generation_id"], "config_sha256": result["config_sha256"],
        "predictions": result["predictions"], "implementation": result["implementation"],
        "missing_production_hooks": result["missing_production_hooks"], "financial_claims": False,
        "real_data_fitted": False, "active_generation_modified": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": payload["status"], "output": str(args.output.resolve()), "predictions": len(payload["predictions"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
