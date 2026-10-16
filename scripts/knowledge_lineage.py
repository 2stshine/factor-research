"""Capture existing qualitative knowledge or audit a recorded lineage. No runs/DB."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.knowledge_registration import capture_knowledge, read_registered_lineage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("research"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capture", help="Archive exact existing knowledge with current lesson identities; does not refresh memory")
    audit = commands.add_parser("audit", help="Read retained registration identities; does not use current candidate definitions")
    audit.add_argument("--campaign", required=True)
    audit.add_argument("--epoch", required=True)
    audit.add_argument("--factor", required=True)
    args = parser.parse_args()
    if args.command == "capture":
        result = capture_knowledge(args.root)
    else:
        from engine.epochs import load_epoch
        result = read_registered_lineage(args.root, load_epoch(args.root, args.campaign, args.epoch), args.factor)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
