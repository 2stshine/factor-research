"""Host-only CLI for a frozen procedural memory comparison; no model calls."""
import argparse
import json
from pathlib import Path

from engine.research_memory_benchmark import MemoryBenchmark, initialize
from engine.research_memory_v2 import canonical


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--model", required=True)
    init.add_argument("--context-mode", choices=["FRESH_CASE", "ARM_BUNDLED"], default="FRESH_CASE")
    for name in ("packet", "act", "status", "score"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--root", type=Path, required=True)
        if name in {"packet", "act"}:
            cmd.add_argument("--arm", choices=["B0", "B1", "B2"], required=True)
            cmd.add_argument("--case", required=True)
        if name == "act":
            cmd.add_argument("--action-file", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "init":
        result = initialize(args.root, model=args.model, context_mode=args.context_mode)
    else:
        benchmark = MemoryBenchmark(args.root)
        if args.command == "packet":
            result = benchmark.packet(args.arm, args.case)
        elif args.command == "act":
            result = benchmark.act(args.arm, args.case, json.loads(args.action_file.read_text()))
        else:
            result = getattr(benchmark, args.command)()
    print(canonical(result))


if __name__ == "__main__":
    main()
