#!/usr/bin/env python
"""Agent research artifacts; never publishes to Gold."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import epochs, panel as P, research, silver
from engine.boundaries import (
    HISTORICAL_HOLDOUT_MODE,
    PROSPECTIVE_HOLDOUT_MODE,
    CampaignWindow,
)
from engine import factors as F
from factors.candidate_loader import RESEARCH_SPECS
from scripts import run


REPO_ROOT = Path(__file__).resolve().parents[1]


def cmd_context(_args) -> None:
    run.load_registry()
    panel = run._load()
    try:
        next_window = _campaign_snapshot_boundary(panel)
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    path = research.write_context(
        panel, F.REGISTRY,
        context_cutoff=next_window.discovery_data_cutoff,
    )
    print(f"연구 컨텍스트 갱신: {path}")


def cmd_identity_audit(_args) -> None:
    """Compare the active cache identity with current RDS without evaluating factors."""
    panel = run._load()
    expected = P.verify_asset_identity(panel)
    try:
        with silver.connect(read_only=True) as conn:
            actual = P.verify_live_asset_identity(conn, panel)
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({
        "status": "MATCH",
        "cache": expected,
        "rds": actual,
        "gold_write": False,
    }, ensure_ascii=False, indent=2))


def cmd_campaign_invalidate_input(args) -> None:
    """Apply one reviewed, append-only input-identity migration artifact."""
    migration_path = (
        REPO_ROOT / "research" / "data-migrations" / args.migration
        / "manifest.json"
    )
    if not migration_path.is_file():
        raise SystemExit(f"입력 identity migration manifest가 없습니다: {migration_path}")
    migration = json.loads(migration_path.read_text(encoding="utf-8"))
    if migration.get("migration_id") != args.migration:
        raise SystemExit("migration id와 manifest 내용이 다릅니다")
    if args.campaign not in migration.get("affected_campaigns", []):
        raise SystemExit(f"migration 대상 campaign이 아닙니다: {args.campaign}")
    try:
        path = epochs.invalidate_input_identity(
            "research", args.campaign,
            migration_id=args.migration,
            before_identity_digest=migration["before"]["asset_identity_digest"],
            after_identity_digest=migration["after"]["asset_identity_digest"],
            reason=migration["reason"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"campaign 입력 identity 무효화 기록: {path}")
    print("campaign 상태: CLOSED_INVALIDATED_INPUT_IDENTITY / OOS NOT_USED")
    print("기존 discovery·epoch·parity 시도 산출물: 보존")
    print("Gold write: 없음")


def _campaign_snapshot_boundary(
    panel,
    *,
    as_of_date: date | str | None = None,
) -> CampaignWindow:
    """Derive the latest trailing holdout that can be judged today.

    The newest completed return month is not necessarily reveal-ready: its
    preceding signal month still needs the fixed inactive-security observation
    lag.  Walk backwards until both the return-support month and that lag are
    already observable at ``as_of_date``.
    """
    current_month, completed_month, _snapshot_cutoff = _latest_completed_snapshot(
        panel, as_of_date=as_of_date,
    )
    observed_as_of = pd.Timestamp(
        as_of_date or datetime.now(ZoneInfo("Asia/Seoul")).date()
    ).normalize()
    while True:
        signal_end = completed_month - 1
        inactive_ready_after = (
            signal_end.to_timestamp(how="end").normalize()
            + pd.Timedelta(days=P.INACTIVE_DAYS)
        )
        # The month after the final return month supplies terminal-membership
        # evidence. Never freeze that closure month while it is still partial.
        closure_ready = current_month >= completed_month + 2
        if observed_as_of > inactive_ready_after and closure_ready:
            break
        completed_month -= 1
        if completed_month < pd.Period(epochs.RESEARCH_START, freq="M"):
            raise ValueError("현재 판단 가능한 36개월 OOS 경계를 만들 수 없습니다")

    snapshot_cutoff = panel.monthly.loc[
        panel.monthly["ym"].eq(completed_month), "trade_date"
    ].max()
    if pd.isna(snapshot_cutoff):
        raise ValueError(f"OOS 마지막 수익률월 {completed_month}이 Silver에 없습니다")
    calendar_month_end = completed_month.to_timestamp(how="end").normalize()
    if pd.Timestamp(snapshot_cutoff).normalize() < calendar_month_end - pd.Timedelta(days=7):
        raise ValueError(
            f"Silver OOS 수익률월 {completed_month}은 월말까지 적재됐다고 볼 수 없습니다: "
            f"마지막 관측 {pd.Timestamp(snapshot_cutoff).date()}"
        )
    oos_signal_end = completed_month - 1
    oos_start = oos_signal_end - (epochs.TH["min_oos_months"] - 1)
    discovery_return_end = oos_start - 1
    discovery_cutoff = panel.monthly.loc[
        panel.monthly["ym"].eq(discovery_return_end), "trade_date"
    ].max()
    if pd.isna(discovery_cutoff):
        raise ValueError(
            "36개월 OOS와 최소 discovery를 분리할 Silver 이력이 부족합니다: "
            f"필요 discovery return 월 {discovery_return_end}"
        )
    window = CampaignWindow.from_completed_snapshot(
        discovery_data_cutoff=str(pd.Timestamp(discovery_cutoff).date()),
        snapshot_cutoff=str(pd.Timestamp(snapshot_cutoff).date()),
        oos_months=epochs.TH["min_oos_months"],
    )
    _assert_minimum_discovery(window)
    return window


def _latest_completed_snapshot(
    panel,
    *,
    as_of_date: date | str | None = None,
) -> tuple[pd.Period, pd.Period, pd.Timestamp]:
    """Return current month, latest completed month, and its final observation."""
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
    completed_history = {
        pd.Period(month, freq="M")
        for month in months
        if pd.Period(month, freq="M") <= completed_month
    }
    expected_history = set(pd.period_range(min(completed_history), completed_month, freq="M"))
    missing_months = sorted(expected_history - completed_history)
    if missing_months:
        raise ValueError(
            "Silver 월 이력이 연속적이지 않습니다: "
            f"누락 {', '.join(map(str, missing_months[:6]))}"
        )
    snapshot_cutoff = panel.monthly.loc[
        panel.monthly["ym"].eq(completed_month), "trade_date"
    ].max()
    if pd.isna(snapshot_cutoff):
        raise ValueError(f"완료 월 {completed_month}의 cutoff를 찾을 수 없습니다")
    calendar_month_end = completed_month.to_timestamp(how="end").normalize()
    if pd.Timestamp(snapshot_cutoff).normalize() < calendar_month_end - pd.Timedelta(days=7):
        raise ValueError(
            f"Silver 최신 월 {completed_month}은 월말까지 적재됐다고 볼 수 없습니다: "
            f"마지막 관측 {pd.Timestamp(snapshot_cutoff).date()}"
        )
    return current_month, completed_month, pd.Timestamp(snapshot_cutoff).normalize()


def _assert_minimum_discovery(window: CampaignWindow) -> None:
    discovery_months = len(pd.period_range(
        epochs.RESEARCH_START, window.discovery_signal_end, freq="M",
    ))
    if discovery_months < epochs.TH["min_months"]:
        raise ValueError(
            "36개월 OOS를 봉인한 뒤 최소 discovery 기간이 부족합니다: "
            f"현재 {discovery_months}, 최소 {epochs.TH['min_months']} signal개월"
        )


def _prospective_campaign_boundary(
    panel,
    *,
    as_of_date: date | str | None = None,
) -> CampaignWindow:
    """Reserve 36 future signal months after the current partial month."""
    current_month, completed_month, snapshot_cutoff = _latest_completed_snapshot(
        panel, as_of_date=as_of_date,
    )
    oos_start = max(current_month + 1, completed_month + 2)
    window = CampaignWindow.from_prospective_snapshot(
        discovery_data_cutoff=str(snapshot_cutoff.date()),
        snapshot_cutoff=str(snapshot_cutoff.date()),
        oos_start=oos_start,
        oos_months=epochs.TH["min_oos_months"],
    )
    _assert_minimum_discovery(window)
    return window


def cmd_campaign_start(args) -> None:
    run.load_registry()
    panel = run._load()
    try:
        window = (
            _prospective_campaign_boundary(panel)
            if args.mode == PROSPECTIVE_HOLDOUT_MODE
            else _campaign_snapshot_boundary(panel)
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    snapshot_panel = run._scope_snapshot_panel(
        panel, snapshot_cutoff=window.snapshot_cutoff,
    )
    discovery_panel = run._scope_discovery_panel(
        panel,
        data_cutoff=window.discovery_data_cutoff,
        oos_start=window.oos_signal_start,
    )
    snapshot_identity = P.verify_asset_identity(snapshot_panel)
    discovery_identity = P.verify_asset_identity(discovery_panel)
    closure_identity = (
        run._closure_observation_identity(
            panel, closure_month=window.closure_month,
        )
        if args.mode == HISTORICAL_HOLDOUT_MODE
        else None
    )
    try:
        with silver.connect(read_only=True) as conn:
            P.verify_live_asset_identity(
                conn, snapshot_panel, cutoff=window.snapshot_cutoff,
            )
            P.verify_live_asset_identity(
                conn, discovery_panel, cutoff=window.discovery_data_cutoff,
            )
            if closure_identity is not None:
                silver.verify_live_asset_identity(
                    conn, closure_identity,
                    cutoff=closure_identity["asset_identity_cutoff"],
                )
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    path = epochs.start_campaign(
        "research", args.campaign,
        discovery_data_cutoff=window.discovery_data_cutoff,
        snapshot_cutoff=window.snapshot_cutoff,
        snapshot_digest=P.snapshot_digest(snapshot_panel),
        discovery_snapshot_digest=P.snapshot_digest(discovery_panel),
        snapshot_asset_identity_digest=(
            snapshot_identity["asset_identity_digest"]
        ),
        discovery_asset_identity_digest=(
            discovery_identity["asset_identity_digest"]
        ),
        closure_asset_identity_digest=(
            closure_identity["asset_identity_digest"]
            if closure_identity is not None else None
        ),
        closure_asset_identity_cutoff=(
            closure_identity["asset_identity_cutoff"]
            if closure_identity is not None else None
        ),
        mode=args.mode,
        oos_start=window.oos_signal_start,
        planned_epoch_count=args.epochs,
    )
    context = research.write_context(panel, F.REGISTRY)
    print(f"campaign 생성: {path}")
    print(f"OOS mode: {window.mode}")
    print(f"사전 고정 epoch 수: {args.epochs}")
    print(
        f"Discovery signal 종료 {window.discovery_signal_end}; "
        f"OOS signal {window.oos_signal_start}~{window.oos_signal_end} (SEALED)"
    )
    print(f"마지막 OOS 수익률 월: {window.oos_return_end}")
    print(f"campaign 전용 컨텍스트: {context}")


def cmd_epoch_start(args) -> None:
    run.load_registry()
    missing = [name for name in args.factors if name not in F.REGISTRY]
    if missing:
        raise SystemExit(f"등록되지 않은 팩터: {missing}")
    factors = [F.REGISTRY[name] for name in args.factors]
    attempted = run.trials.TrialLedger(run.TRIAL_DB).definition_hashes()
    for factor in factors:
        if factor.name not in RESEARCH_SPECS:
            raise SystemExit(f"자율 연구 후보가 아닙니다: {factor.name}")
        try:
            research.assert_new_candidate(
                factor,
                RESEARCH_SPECS[factor.name],
                attempted_definition_hashes=attempted,
            )
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
        research.assert_new_candidate(
            F.REGISTRY[args.factor],
            RESEARCH_SPECS[args.factor],
            attempted_definition_hashes=(
                run.trials.TrialLedger(run.TRIAL_DB).definition_hashes()
            ),
        )
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
            data_cutoff=campaign["discovery"]["data_cutoff"],
            oos_start=campaign["oos"]["start"],
            defer_multiple_testing=True,
            discovery_snapshot_digest=(
                campaign["snapshot"]["discovery_input_digest"]
            ),
            discovery_asset_identity_digest=(
                campaign["snapshot"].get("discovery_asset_identity_digest")
            ),
        )
    except (ValueError, RuntimeError) as exc:
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
    print("Discovery FDR: PENDING (campaign finalize에서 전체 후보 일괄 판정)")
    print("최종 OOS: SEALED")


def cmd_campaign_finalize(args) -> None:
    run.load_registry()
    panel = run._load()
    try:
        path = epochs.finalize_campaign("research", args.campaign)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    campaign = epochs.load_campaign("research", args.campaign)
    context = research.write_context(panel, F.REGISTRY)
    if campaign["status"] == "CLOSED_NO_QUALIFIED":
        print(f"campaign 종료(기준 통과 후보 없음): {path}")
    else:
        print(f"campaign discovery 확정: {path}")
        print(f"기준 통과 후보 {len(campaign['qualified_factors'])}개 자동 구현 대상")
    print(f"Discovery BY 확정: {campaign['discovery_multiple_testing']}")
    print(f"다음 루프 컨텍스트 갱신: {context}")
    if campaign["status"] == "AWAITING_IMPLEMENTATION":
        print("다음 단계: qualified 전체의 Gold SQL 작성 및 discovery-only parity 검증")
        print("OOS는 구현 검증이 끝날 때까지 SEALED")


def cmd_campaign_verify_implementations(args) -> None:
    run.load_registry()
    campaign = epochs.load_campaign("research", args.campaign)
    if campaign.get("status") != "AWAITING_IMPLEMENTATION":
        raise SystemExit(
            "AWAITING_IMPLEMENTATION campaign만 구현 검증할 수 있습니다: "
            f"{campaign.get('status')}"
        )
    factors = []
    for row in campaign["qualified_factors"]:
        factor = F.REGISTRY[row["name"]] if row["name"] in F.REGISTRY else None
        if factor is None or factor.definition_hash != row["definition_hash"]:
            raise SystemExit(f"동결 후보 소스/hash를 재현할 수 없습니다: {row['name']}")
        factors.append(factor)
    try:
        evidence = run.verify_implementations(campaign, factors)
    except (ValueError, RuntimeError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    try:
        attempt = epochs.record_implementation_attempt(
            "research", args.campaign, evidence,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    failed = [row for row in evidence if not row["passed"]]
    if failed:
        summary = "; ".join(
            f"{row['factor']}={','.join(row['failure_reasons'])}" for row in failed
        )
        raise SystemExit(
            f"Gold 구현 parity 실패; campaign은 AWAITING_IMPLEMENTATION 유지: {summary}. "
            f"시도 증거: {attempt}"
        )
    try:
        path = epochs.record_implementation_verification(
            "research", args.campaign, evidence,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    panel = run._load()
    context = research.write_context(panel, F.REGISTRY)
    print(f"Gold 구현 검증 확정: {path}")
    print(f"Python/SQL key·raw value·direction rank parity: {len(evidence)}개 PASS")
    print("campaign 상태: READY_FOR_CONFIRMATION")
    print("Gold write: 없음")
    print(f"다음 루프 컨텍스트: {context}")


def cmd_campaign_reveal(args) -> None:
    run.load_registry()
    panel = run._load()
    panel_as_of = panel.monthly["trade_date"].max()
    campaign = epochs.load_campaign("research", args.campaign)
    names = [row["name"] for row in campaign["qualified_factors"]]
    discovery_artifact = epochs.load_discovery_multiple_testing(
        "research", args.campaign,
    )
    frozen_discovery = {
        row["definition_hash"]: row
        for row in discovery_artifact["results"]
    }
    for row in campaign["qualified_factors"]:
        if row["name"] not in F.REGISTRY:
            raise SystemExit(f"동결 후보 소스가 없습니다: {row['name']}")
        if F.REGISTRY[row["name"]].definition_hash != row["definition_hash"]:
            raise SystemExit(f"동결 후 정의가 바뀌었습니다: {row['name']}")
    factors = [F.REGISTRY[name] for name in names]
    try:
        bindings = run._implementation_bindings(factors)
        snapshot = run._scope_snapshot_panel(
            panel, snapshot_cutoff=campaign["snapshot"]["data_cutoff"],
        )
        snapshot_digest = P.snapshot_digest(snapshot)
        snapshot_identity = P.verify_asset_identity(snapshot)[
            "asset_identity_digest"
        ]
        if snapshot_identity != campaign["snapshot"].get(
            "asset_identity_digest"
        ):
            raise ValueError(
                "campaign 생성 당시 snapshot asset identity를 재현하지 못했습니다"
            )
        campaign = epochs.assert_reveal_ready(
            "research", args.campaign, panel_as_of,
            snapshot_digest=snapshot_digest,
            current_bindings=bindings,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    namespace = argparse.Namespace(factor=None)
    _, _, factors, results = run._evaluate(
        namespace,
        phase="full",
        oos_start=campaign["oos"]["start"],
        oos_end=campaign["oos"]["signal_end"],
        data_cutoff=campaign["discovery"]["data_cutoff"],
        factor_names=names,
        calibration_scope={
            "discovery_family_size": campaign["discovery_family_size"],
            "oos_family_size": len(campaign["qualified_factors"]),
            "discovery_family_digest": campaign["discovery_family_digest"],
            "oos_family_digest": campaign["oos_family_digest"],
            "research_data_cutoff": campaign["discovery"]["data_cutoff"],
            "qualification_policy": campaign["qualification_policy"],
        },
        frozen_discovery=frozen_discovery,
        discovery_snapshot_digest=(
            campaign["snapshot"]["discovery_input_digest"]
        ),
        discovery_asset_identity_digest=(
            campaign["snapshot"].get("discovery_asset_identity_digest")
        ),
        snapshot_asset_identity_digest=(
            campaign["snapshot"].get("asset_identity_digest")
        ),
        closure_asset_identity_digest=(
            campaign["snapshot"].get("closure_asset_identity_digest")
        ),
        confirmation_mode=campaign["oos"]["mode"],
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
        report, result = epochs.record_reveal(
            "research", args.campaign, confirmations,
            panel_as_of=panel_as_of,
            snapshot_digest=snapshot_digest,
            current_bindings=bindings,
        )
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
    commands.add_parser(
        "identity-audit",
        help="현재 패널 asset identity와 live RDS를 읽기 전용 대조",
    )
    campaign_invalidate = commands.add_parser(
        "campaign-invalidate-input",
        help="검증된 asset identity migration으로 기존 campaign을 종료",
    )
    campaign_invalidate.add_argument("--campaign", required=True)
    campaign_invalidate.add_argument("--migration", required=True)
    campaign_start = commands.add_parser("campaign-start", help="봉인 OOS campaign 시작")
    campaign_start.add_argument("--campaign", required=True)
    campaign_start.add_argument(
        "--mode",
        choices=[HISTORICAL_HOLDOUT_MODE, PROSPECTIVE_HOLDOUT_MODE],
        default=HISTORICAL_HOLDOUT_MODE,
        help=(
            "기본값은 현재 데이터 안의 최신 reveal-ready 36개월을 처음부터 "
            "숨기는 trailing_historical_holdout; 미래 추적은 명시적으로 선택"
        ),
    )
    campaign_start.add_argument(
        "--epochs", type=int, default=1,
        help="campaign에서 결과 전에 고정할 전체 epoch 수",
    )
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
    campaign_finalize = commands.add_parser(
        "campaign-finalize",
        help="campaign 전체 BY 후 모든 기준 통과 후보를 자동 확정",
    )
    campaign_finalize.add_argument("--campaign", required=True)
    campaign_verify = commands.add_parser(
        "campaign-verify-implementations",
        help="qualified 전체 Gold SQL을 discovery 구간에서 Python과 대조",
    )
    campaign_verify.add_argument("--campaign", required=True)
    campaign_reveal = commands.add_parser("campaign-reveal", help="충분히 쌓인 봉인 OOS를 한 번 공개")
    campaign_reveal.add_argument("--campaign", required=True)
    args = parser.parse_args()
    {
        "context": cmd_context,
        "identity-audit": cmd_identity_audit,
        "campaign-invalidate-input": cmd_campaign_invalidate_input,
        "campaign-start": cmd_campaign_start,
        "epoch-start": cmd_epoch_start,
        "evaluate": cmd_evaluate,
        "epoch-close": cmd_epoch_close,
        "campaign-finalize": cmd_campaign_finalize,
        "campaign-verify-implementations": cmd_campaign_verify_implementations,
        "campaign-reveal": cmd_campaign_reveal,
    }[args.command](args)


if __name__ == "__main__":
    main()
