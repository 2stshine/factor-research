"""Build local diagnostic context from explicit monthly index JSON records.

python -m scripts.market_regimes --input index.json --as-of 2026-08-31 \
    --market-id KOSPI --source-id SOURCE_VERSION --output regimes.json
No DB access, campaign execution, OOS reads or Gold writes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from engine.regimes import RULES, RULESETS, classify_monthly_market


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--market-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--rules-version", choices=sorted(RULESETS), default=RULES["version"])
    args = parser.parse_args()
    result = classify_monthly_market(
        pd.DataFrame(json.loads(args.input.read_text())), as_of=args.as_of,
        market_id=args.market_id, source_id=args.source_id, rules_version=args.rules_version,
    )
    payload = {
        "as_of": args.as_of, "rules": RULESETS[args.rules_version],
        "certification": "INPUT_PROVENANCE_NOT_INDEPENDENTLY_VERIFIED",
        "rows": json.loads(result.to_json(orient="records", double_precision=15)),
    }
    # Do not overwrite previous evidence or the input file.
    with args.output.open("x") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
