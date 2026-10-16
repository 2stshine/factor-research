"""Reviewer-only identity check for optional future knowledge-lineage metadata.

No candidate registration, memory refresh, experiments, writes, or network.
Terminal evidence stays in memory and is never serialized to candidate output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from engine.knowledge_lineage import validate_lineage

ROOT = Path(__file__).resolve().parents[1]


def check(metadata, knowledge, cutoff, research_root=ROOT / "research"):
    if metadata is None:
        return validate_lineage(None, b"", [], cutoff=cutoff)
    # Import only for a new declaration. No legacy re-read or mass retrofit.
    from scripts.dashboard_exports.export_research_catalog import export
    catalog = export(research_root, datetime.now(timezone.utc).isoformat())
    return validate_lineage(metadata, knowledge, catalog["records"], cutoff=cutoff)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--knowledge-snapshot", type=Path)
    parser.add_argument("--cutoff", required=True, help="Proposed or externally verified registration cutoff; timezone required")
    args = parser.parse_args()
    if args.metadata is not None and args.knowledge_snapshot is None:
        parser.error("--knowledge-snapshot is required with --metadata")
    metadata = json.loads(args.metadata.read_text()) if args.metadata else None
    knowledge = args.knowledge_snapshot.read_bytes() if args.knowledge_snapshot else b""
    print(json.dumps(check(metadata, knowledge, args.cutoff), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
