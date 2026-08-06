#!/usr/bin/env python
"""Agent research artifacts; never publishes to Gold."""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import epochs, research
from engine import factors as F
from factors.candidate_loader import RESEARCH_SPECS
from scripts import run


def cmd_context(_args) -> None:
    run.load_registry()
    panel = run._load()
    path = research.write_context(panel, F.REGISTRY)
    print(f"연구 컨텍스트 갱신: {path}")


def _campaign_snapshot_boundary(
    panel,
    *,
    as_of_date: date | str | None = None,
) -> tuple[str, str]:
    """Return the last completed cutoff and first wholly unseen OOS month."""
    months = sorted(panel.monthly["ym"].dropna().unique())
    if not months:
        raise ValueError("Silver 월 데이터가 없습니다")
    today = as_of_date or datetime.now(ZoneInfo("Asia/Seoul")).date()
    current_month = pd.Timestamp(today).to_period("M")
    latest_month = pd.Period(months[-1], freq="M")
    if latest_month > current_month:
        raise ValueError(
            f"Silver 최신 월 {latest_month}이 현재 월 {current_month}보다 미래입니다"
        )
    if latest_month == current_month:
        completed = [
            pd.Period(month, freq="M") for month in months if month < current_month
        ]
        if not completed:
            raise ValueError("완료 여부를 확인할 과거 Silver 월이 부족합니다")
        completed_month = completed[-1]
    else:
        completed_month = latest_month
    cutoff_value = panel.monthly.loc[
        panel.monthly["ym"].eq(completed_month), "trade_date"
    ].max()
    if pd.isna(cutoff_value):
        raise ValueError(f"완료 월 {completed_month}의 cutoff를 찾을 수 없습니다")
    # A sealed confirmation must be prospective.  A lagged cache must never
    # turn already-realized historical months into a newly declared "OOS".
    # Everything through the current calendar month is therefore embargoed.
    first_unseen_month = current_month + 1
    return str(pd.Timestamp(cutoff_value).date()), str(first_unseen_month)


def cmd_campaign_start(args) -> None:
    run.load_registry()
    panel = run._load()
    try:
        cutoff, first_unseen_month = _campaign_snapshot_boundary(panel)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    oos_start = args.oos_start or first_unseen_month
    if pd.Period(oos_start, freq="M") < pd.Period(first_unseen_month, freq="M"):
        raise SystemExit(
            "OOS 시작은 campaign 생성 때 완전히 보지 않은 월이어야 합니다: "
            f"최소 {first_unseen_month}"
        )
    path = epochs.start_campaign(
        "research", args.campaign, data_cutoff=cutoff, oos_start=oos_start,
    )
    print(f"campaign 생성: {path}")
    print("최종 OOS: SEALED")


def cmd_epoch_start(args) -> None:
    run.load_registry()
    missing = [name for name in args.factors if name not in F.REGISTRY]
    if missing:
        raise SystemExit(f"등록되지 않은 팩터: {missing}")
    factors = [F.REGISTRY[name] for name in args.factors]
    for factor in factors:
        if factor.name not in RESEARCH_SPECS:
            raise SystemExit(f"자율 연구 후보가 아닙니다: {factor.name}")
        try:
            research.assert_new_candidate(factor, RESEARCH_SPECS[factor.name])
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    try:
        path = epochs.start_epoch("research", args.campaign, args.epoch, factors)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"epoch 사전등록: {path}")
    print(f"후보 {len(factors)}개 정의·방향·해시 동결")
    print("최종 OOS: SEALED")


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
        epochs.assert_candidate_ready(
            "research", args.campaign, args.epoch, F.REGISTRY[args.factor]
        )
        campaign = epochs.load_campaign("research", args.campaign)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    namespace = argparse.Namespace(factor=args.factor)
    try:
        panel, df, targets, results = run._evaluate(
            namespace,
            phase="discovery",
            data_cutoff=campaign["data_cutoff"],
            oos_start=campaign["oos"]["start"],
            defer_multiple_testing=True,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    factor, result = targets[0], results[0]
    relationships = research.factor_relationships(panel, df, factor, F.REGISTRY)
    report, context = research.record_cycle(
        panel, F.REGISTRY, factor, result, RESEARCH_SPECS[factor.name], relationships,
        campaign_id=args.campaign, epoch_id=args.epoch, phase="discovery",
    )
    epochs.mark_evaluated(
        "research", args.campaign, args.epoch, factor, result,
        report=str(report),
        strongest_relationship=relationships[0] if relationships else None,
    )
    print(f"\n연구 사이클 기록: {report}")
    print(f"다음 루프 컨텍스트: {context}")
    print(f"Discovery 사전 판정(FDR 대기): {result.verdict.value}")
    print("최종 OOS: SEALED (계산·기록 없음)")
    print("Gold write: 없음")


def cmd_epoch_close(args) -> None:
    try:
        report, result = epochs.close_epoch(
            "research", args.campaign, args.epoch,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"epoch 종료: {report}")
    print(f"구조화 성찰: {result}")
    print("Discovery FDR: PENDING (campaign freeze에서 전체 후보 일괄 판정)")
    print("최종 OOS: SEALED")


def cmd_campaign_freeze(args) -> None:
    run.load_registry()
    panel = run._load()
    try:
        path = epochs.freeze_campaign("research", args.campaign, args.factors)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    campaign = epochs.load_campaign("research", args.campaign)
    context = research.write_context(panel, F.REGISTRY)
    if campaign["status"] == "CLOSED_NO_SURVIVOR":
        print(f"campaign 종료(통과 survivor 없음): {path}")
    else:
        print(f"campaign 동결: {path}")
        print(f"survivor {len(campaign['survivors'])}개 정의 해시 고정")
    print(f"Discovery BY 확정: {campaign['discovery_multiple_testing']}")
    print(f"다음 루프 컨텍스트 갱신: {context}")
    if campaign["status"] == "FROZEN":
        print(
            f"OOS {campaign['oos']['start']}부터 최소 {campaign['oos']['min_months']}개월; "
            f"가장 이른 공개 가능 데이터 월 {campaign['oos']['earliest_data_month']}"
        )


def cmd_campaign_reveal(args) -> None:
    run.load_registry()
    panel = run._load()
    panel_month = panel.monthly["ym"].max()
    try:
        campaign = epochs.assert_reveal_ready("research", args.campaign, panel_month)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    names = [row["name"] for row in campaign["survivors"]]
    discovery_artifact = epochs.load_discovery_multiple_testing(
        "research", args.campaign,
    )
    frozen_discovery = {
        row["definition_hash"]: row
        for row in discovery_artifact["results"]
    }
    for row in campaign["survivors"]:
        if row["name"] not in F.REGISTRY:
            raise SystemExit(f"동결 후보 소스가 없습니다: {row['name']}")
        if F.REGISTRY[row["name"]].definition_hash != row["definition_hash"]:
            raise SystemExit(f"동결 후 정의가 바뀌었습니다: {row['name']}")
    namespace = argparse.Namespace(factor=None)
    _, _, factors, results = run._evaluate(
        namespace,
        phase="full",
        oos_start=campaign["oos"]["start"],
        oos_end=campaign["oos"]["signal_end"],
        data_cutoff=campaign["data_cutoff"],
        factor_names=names,
        calibration_scope={
            "discovery_family_size": campaign["discovery_family_size"],
            "oos_family_size": len(campaign["survivors"]),
            "discovery_family_digest": campaign["discovery_family_digest"],
            "oos_family_digest": campaign["oos_family_digest"],
            "research_data_cutoff": campaign["data_cutoff"],
        },
        frozen_discovery=frozen_discovery,
    )
    confirmations = []
    for factor, result in zip(factors, results, strict=True):
        serialized = research.serialize_result(result)
        confirmations.append({
            "factor": factor.name,
            "definition_hash": factor.definition_hash,
            "verdict": result.verdict.value,
            "evaluation": serialized,
        })
    try:
        report, result = epochs.record_reveal("research", args.campaign, confirmations)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    context = research.write_context(panel, F.REGISTRY)
    print(f"봉인 OOS 공개 및 campaign 종료: {report}")
    print(f"전체 확인 결과: {result}")
    print("이 OOS 결과는 종료된 campaign 후보 수정에 사용할 수 없습니다")
    print(f"다음 루프 컨텍스트 갱신: {context}")
    print("Gold write: 없음")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("context", help="다음 루프가 읽을 현재 연구 상태 생성")
    campaign_start = commands.add_parser("campaign-start", help="봉인 OOS campaign 시작")
    campaign_start.add_argument("--campaign", required=True)
    campaign_start.add_argument("--oos-start")
    epoch_start = commands.add_parser("epoch-start", help="후보 배치 사전등록")
    epoch_start.add_argument("--campaign", required=True)
    epoch_start.add_argument("--epoch", required=True)
    epoch_start.add_argument("--factors", nargs="+", required=True)
    evaluate = commands.add_parser("evaluate", help="후보 하나를 평가하고 영구 산출물 기록")
    evaluate.add_argument("--factor", required=True)
    evaluate.add_argument("--campaign", required=True)
    evaluate.add_argument("--epoch", required=True)
    epoch_close = commands.add_parser("epoch-close", help="epoch 종료 및 구조화 성찰")
    epoch_close.add_argument("--campaign", required=True)
    epoch_close.add_argument("--epoch", required=True)
    campaign_freeze = commands.add_parser("campaign-freeze", help="survivor 정의 동결")
    campaign_freeze.add_argument("--campaign", required=True)
    campaign_freeze.add_argument(
        "--factors", nargs="*", default=[],
        help="OOS survivor. 모두 탈락이면 생략해 campaign을 종료",
    )
    campaign_reveal = commands.add_parser("campaign-reveal", help="충분히 쌓인 봉인 OOS를 한 번 공개")
    campaign_reveal.add_argument("--campaign", required=True)
    args = parser.parse_args()
    {
        "context": cmd_context,
        "campaign-start": cmd_campaign_start,
        "epoch-start": cmd_epoch_start,
        "evaluate": cmd_evaluate,
        "epoch-close": cmd_epoch_close,
        "campaign-freeze": cmd_campaign_freeze,
        "campaign-reveal": cmd_campaign_reveal,
    }[args.command](args)


if __name__ == "__main__":
    main()
