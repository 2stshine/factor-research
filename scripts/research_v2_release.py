"""Closed real-pilot review and qualitative memory release; never author reviews."""
import argparse
import json
from pathlib import Path

from engine.research_memory_v2 import canonical, digest
from engine.research_v2_release import activate, load_bundle, prepare_review, stage, validate_draft


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-review")
    prepare.add_argument("--pilot-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    for name in ("validate-draft", "stage", "activate"):
        command = commands.add_parser(name)
        command.add_argument("--release-root", type=Path, required=True)
        if name != "activate":
            command.add_argument("--draft-file", type=Path, required=True)
        if name == "stage":
            command.add_argument("--critic-file", type=Path, required=True)
        if name == "activate":
            command.add_argument("--memory-database", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare-review":
        result = prepare_review(args.pilot_root, args.output)
    elif args.command == "activate":
        result = activate(args.release_root, args.memory_database)
    else:
        draft = json.loads(args.draft_file.read_text())
        if args.command == "validate-draft":
            result = {"draft_sha256": validate_draft(load_bundle(args.release_root), draft),
                      "evidence_bundle_sha256": draft["evidence_bundle_sha256"], "status": "AWAITING_INDEPENDENT_CRITIC"}
        else:
            result = stage(args.release_root, draft, json.loads(args.critic_file.read_text()))
    print(canonical(result))


if __name__ == "__main__":
    main()
