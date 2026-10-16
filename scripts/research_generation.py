"""Explicit local archive/generation tools; no automatic snapshot or Gold writes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine import research_generation as registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("capture-legacy")
    p.add_argument("--repo", action="append", required=True, help="NAME=/absolute/repository/path (repeat for both repos)")
    p.add_argument("--archive-root", type=Path, required=True)
    p.add_argument("--exclude", action="append", default=[])
    p = sub.add_parser("verify-archive")
    p.add_argument("--manifest", type=Path, required=True)
    p = sub.add_parser("initialize")
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--archive-manifest", type=Path, required=True)
    p.add_argument("--generation-id", default=registry.DEFAULT_GENERATION)
    p.add_argument("--activate", action="store_true")
    p = sub.add_parser("active")
    p.add_argument("--repo-root", type=Path, required=True)
    p = sub.add_parser("inventory-gold")
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture-legacy":
        pairs = [item.split("=", 1) for item in args.repo]
        if any(len(p) != 2 for p in pairs) or len({p[0] for p in pairs}) != len(pairs):
            parser.error("--repo must be unique NAME=/absolute/path entries")
        result = registry.capture_legacy_snapshot({name: Path(root) for name, root in pairs}, archive_root=args.archive_root, exclude_paths=args.exclude)
    elif args.command == "verify-archive":
        result = registry.verify_legacy_snapshot(args.manifest)
    elif args.command == "initialize":
        result = registry.initialize_generation(args.repo_root, archive_manifest=args.archive_manifest,
                                                generation_id=args.generation_id, activate=args.activate)
    elif args.command == "active":
        result = registry.load_active_generation(args.repo_root)
    else:
        from engine import silver
        with silver.connect(read_only=True) as conn:
            result = registry.legacy_gold_inventory(conn)
        registry._immutable(args.output, registry.canonical(result) + b"\n")
        result = {"output": str(args.output), "factor_count": len(result["rows"]),
                  "inventory_sha256": result["inventory_sha256"], "database_writes": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
