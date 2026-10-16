"""CLI broker for bounded research data search, acquisition and validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from engine import research_data_sources as data


def _read(path: str):
    file = Path(path)
    if file.stat().st_size > 2_000_000:
        raise data.DataSourceError("command input exceeds 2 MB")
    return json.loads(file.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Case parent for init; exact case directory otherwise")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "record-search", "source", "review"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--input", required=True, help="JSON contract/action file")
        if name == "review":
            cmd.add_argument("--source-id", required=True)
    sub.add_parser("packet")
    search = sub.add_parser("catalog-search")
    search.add_argument("--catalog", required=True)
    search.add_argument("--query", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--source-id", required=True)
    local = sub.add_parser("capture-local")
    local.add_argument("--source-id", required=True)
    local.add_argument("--path", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--artifact-id", required=True)
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--snapshot-id", required=True)
    snapshot.add_argument("--as-of")
    snapshot.add_argument("--include-rows", action="store_true", help="Explicitly emit data rows; default is metadata only")
    unmet = sub.add_parser("unmet")
    unmet.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = {"case_dir": str(data.create_requirement(args.root, _read(args.input)))}
        elif args.command == "packet":
            result = data.packet(args.root)
        elif args.command == "catalog-search":
            result = data.search_catalog(args.root, args.catalog, args.query)
        elif args.command == "record-search":
            action = _read(args.input)
            result = data.record_web_search(args.root, action["query"], action["results"], provider=action.get("provider", "host_agent_web_search"))
        elif args.command == "source":
            result = {"source_id": data.register_source(args.root, _read(args.input))}
        elif args.command == "review":
            data.review_source(args.root, args.source_id, _read(args.input))
            result = {"source_id": args.source_id, "review_recorded": True}
        elif args.command == "fetch":
            result = data.fetch_source(args.root, args.source_id)
        elif args.command == "capture-local":
            result = data.capture_local(args.root, args.source_id, args.path)
        elif args.command == "validate":
            result = data.validate_artifact(args.root, args.artifact_id)
        elif args.command == "snapshot":
            result = data.load_snapshot(args.root, args.snapshot_id, as_of=args.as_of)
            if not args.include_rows:
                result["available_row_count"] = len(result.pop("rows"))
        else:
            result = data.mark_unmet(args.root, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (data.DataSourceError, OSError, ValueError, KeyError, TypeError) as exc:
        # Raw OS/HTTP/JSON error strings could expose paths, credentials or input.
        message = str(exc) if isinstance(exc, data.DataSourceError) else "invalid or inaccessible command input"
        print(json.dumps({"error": message, "hypothesis_verdict": "NO_EVIDENCE"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
