"""Trusted host CLI for a frozen diagnostic pilot; no registration, DB write or OOS reveal."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

from engine.research_v2_pilot import (
    PilotBroker, SELECTED, _read_json, _sha_file, _write_json, exposure_bindings, prepare_pilot,
)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Freeze authenticated Discovery input before any diagnostics")
    prepare.add_argument("--plan", type=Path, required=True)
    prepare.add_argument("--regime-contract", type=Path, required=True)
    prepare.add_argument("--audit-receipt", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True, help="New immutable directory; never overwritten")
    prepare.add_argument("--source-label", required=True)
    prepare.add_argument("--as-of", required=True, help="Exact YYYY-MM-DD for metadata-only boundary derivation")
    prepare.add_argument("--exposure-file", type=Path, action="append", required=True,
                         help="Existing global trial ledger, definition index or campaign manifest; hash only, repeat as needed")
    for name, help_text in (
        ("init", "Create an isolated case/arm session"),
        ("packet", "Persist and return the exact public investigator prompt"),
        ("act", "Submit an explicit investigator action to the trusted adapter"),
        ("fixed", "Collect the six fixed diagnostics; leave ACTIVE for an independent LLM interpretation"),
        ("export", "Export the auditable session; this does not certify interpretation truth"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--pilot", type=Path, required=True)
        command.add_argument("--case", choices=SELECTED, required=True)
        if name != "fixed":
            command.add_argument("--arm", choices=("FIXED_REFERENCE", "HOST_LLM"), required=True)
        if name == "act":
            command.add_argument("--action", type=Path, required=True)
            command.add_argument("--request-id", required=True)
            command.add_argument("--expected-revision", type=int, required=True)
        command.add_argument("--output", type=Path, help="Optional new JSON file; never overwritten")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "prepare":
        # CACHE_DIR selects the existing authenticated cache. No database lookup
        # or automatic authentication occurs here; the live receipt is explicit.
        from scripts import run
        from scripts.research import _campaign_snapshot_boundary
        import pandas as pd

        stamp = pd.Timestamp(args.as_of)
        if stamp.strftime("%Y-%m-%d") != args.as_of:
            raise ValueError("--as-of must be an exact YYYY-MM-DD date")
        with redirect_stdout(sys.stderr):
            panel = run._load()
            boundary = _campaign_snapshot_boundary(panel, as_of_date=args.as_of)
            result = prepare_pilot(panel, boundary,
                plan=_read_json(args.plan), regime_contract=_read_json(args.regime_contract),
                audit_receipt=_read_json(args.audit_receipt), output=args.output,
                source_panel_file_sha256=_sha_file(run.PANEL_CACHE), source_label=args.source_label,
                exposure_metadata=exposure_bindings(args.exposure_file))
        result = {"status": result["status"], "output": str(args.output),
                  "manifest_sha256": result["manifest_sha256"],
                  "cases": [{key: case[key] for key in ("case_id", "status", "row_count", "signal_finite_rows", "missing_inputs")}
                            for case in result["cases"]],
                  "diagnostics_run": False, "oos_reads": 0, "gold_writes": 0}
    else:
        broker = PilotBroker(args.pilot)
        if args.command == "init":
            result = broker.init_session(args.case, args.arm)
        elif args.command == "packet":
            result = broker.packet(args.case, args.arm)
        elif args.command == "act":
            result = broker.act(args.case, args.arm, _read_json(args.action),
                request_id=args.request_id, expected_revision=args.expected_revision)
        elif args.command == "fixed":
            result = broker.collect_fixed(args.case)
        else:
            result = broker.export(args.case, args.arm)
        if args.output:
            output_sha = _write_json(args.output, result)
            result = {"output": str(args.output), "file_sha256": output_sha,
                      "state": result.get("state", {}).get("state"),
                      "receipt_status": result.get("status")}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
