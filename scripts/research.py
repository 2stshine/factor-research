#!/usr/bin/env python
"""Agent research artifacts; never publishes to Gold."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import research
from engine import factors as F
from factors.candidate_loader import RESEARCH_SPECS
from scripts import run


def cmd_context(_args) -> None:
    run.load_registry()
    panel = run._load()
    path = research.write_context(panel, F.REGISTRY)
    print(f"연구 컨텍스트 갱신: {path}")


def cmd_evaluate(args) -> None:
    run.load_registry()
    if args.factor not in F.REGISTRY:
        raise SystemExit(f"등록되지 않은 팩터: {args.factor}")
    if args.factor not in RESEARCH_SPECS:
        raise SystemExit(
            f"{args.factor}: 자율 연구 후보가 아닙니다. "
            "factors/candidates/*.py에 FACTOR와 RESEARCH_SPEC을 등록하세요."
        )
    try:
        research.assert_new_candidate(F.REGISTRY[args.factor], RESEARCH_SPECS[args.factor])
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    namespace = argparse.Namespace(factor=args.factor)
    panel, df, targets, results = run._evaluate(namespace)
    factor, result = targets[0], results[0]
    relationships = research.factor_relationships(panel, df, factor, F.REGISTRY)
    report, context = research.record_cycle(
        panel, F.REGISTRY, factor, result, RESEARCH_SPECS[factor.name], relationships
    )
    print(f"\n연구 사이클 기록: {report}")
    print(f"다음 루프 컨텍스트: {context}")
    print(f"최종 판정: {result.verdict.value}")
    print("Gold write: 없음")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("context", help="다음 루프가 읽을 현재 연구 상태 생성")
    evaluate = commands.add_parser("evaluate", help="후보 하나를 평가하고 영구 산출물 기록")
    evaluate.add_argument("--factor", required=True)
    args = parser.parse_args()
    {"context": cmd_context, "evaluate": cmd_evaluate}[args.command](args)


if __name__ == "__main__":
    main()
