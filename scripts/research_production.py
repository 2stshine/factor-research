"""Host actions for general campaign v2 diagnostics; no factor reevaluation/OOS/Gold."""
import argparse
import json
from pathlib import Path

from engine.research_production import ProductionBroker, prepare_review, read, write


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("packet", "act", "status", "export", "prepare-review"):
        p = commands.add_parser(name)
        p.add_argument("--handoff", type=Path, required=True)
        p.add_argument("--output", type=Path)
        if name == "act":
            p.add_argument("--action", type=Path, required=True)
            p.add_argument("--request-id", required=True)
            p.add_argument("--expected-revision", type=int, required=True)
    args = parser.parse_args(argv)
    broker = ProductionBroker(args.handoff, read_only=args.command in {"status", "export", "prepare-review"})
    if args.command == "packet":
        result = broker.packet()
    elif args.command == "act":
        result = broker.act(read(args.action), request_id=args.request_id, expected_revision=args.expected_revision)
    elif args.command == "export":
        result = broker.export()
    elif args.command == "prepare-review":
        if args.output is None:
            parser.error("prepare-review requires a fresh --output directory")
        result = prepare_review(args.handoff, args.output)
    else:
        result = broker.status()
    if args.output and args.command != "prepare-review":
        result = {"output": str(args.output), "sha256": write(args.output, result)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
