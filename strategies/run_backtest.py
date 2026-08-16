"""백테스트 엔트리 — 팩터 값으로 수익률을 적합하고 MVO로 비중을 정한다.

    uv run python -m strategies.run_backtest            # 일별 표본 (daily_* 캐시 필요)
    uv run python -m strategies.run_backtest monthly    # 승인 팩터 월말 표본

월별 로그는 experiments/last_backtest.csv 에 저장한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategies.config import StrategyConfig, monthly_config
from strategies import data, daily, predict, backtest, metrics

OUT_DIR = Path(__file__).resolve().parent / "experiments"


def _fmt(m: dict) -> str:
    if not m:
        return "(no data)"
    return (f"CAGR={m['cagr']:+6.2%}  vol={m['ann_vol']:5.1%}  Sharpe={m['sharpe']:5.2f}  "
            f"MDD={m['mdd']:6.1%}  hit={m['hit_rate']:4.0%}")


def main(cfg: StrategyConfig | None = None) -> None:
    cfg = cfg or StrategyConfig()
    unit = "월" if cfg.sample_frequency == "monthly" else "일"
    print("=== 설정 ===")
    print(f"factors={len(cfg.factors)}개 (gold.factor APPROVED)")
    print(f"top_n={cfg.top_n}  cap={cfg.weight_cap_u}  c={cfg.risk_aversion_c}  "
          f"gamma={cfg.turnover_gamma:.4f}  cost/side={cfg.cost_bps_per_side}bp")
    print(f"표본={cfg.sample_frequency}  fwd={cfg.fwd_days}{unit}  "
          f"train_window={cfg.train_window_days}{unit}  "
          f"cov_window={cfg.cov_window_days}일  target={cfg.target_col}")
    if cfg.context_cutoff_ym:
        print(f"전략 컨텍스트 컷오프={cfg.context_cutoff_ym}")

    print("\n[1/4] 패널 로드...")
    panel = data.load_panel()
    if cfg.sample_frequency == "monthly":
        # 월말 표본에서는 학습 프레임과 실현수익 프레임이 같다.
        frame = dframe = data.build_frame(panel, cfg)
    else:
        frame = data.strategy_frame(panel, cfg)    # 월말 — 백테스트 실현수익용
        dframe = data.daily_frame(panel, cfg)      # 일별 — ridge 학습용
    dret = daily.load_daily()
    print(f"  {len(frame):,}행 / {frame['ym'].nunique()}개월 / "
          f"{frame['asset_id'].nunique():,}종목  ({frame['ym'].min()}~{frame['ym'].max()})")

    print("[2/4] ridge 예측...")
    preds = predict.predict_returns(dframe, cfg)
    print(f"  학습 {len(dframe):,}행 → 예측 {len(preds):,}행 / "
          f"{preds['ym'].nunique()}개월")

    print("[3/4] QP 백테스트...")
    log = backtest.run_backtest(frame, preds, dret, cfg)["log"]

    print("[4/4] 성과\n")
    print(f"기간 {log.index.min()} ~ {log.index.max()}  ({len(log)}개 리밸런싱)")
    print(f"평균 보유 {log['n_holdings'].mean():.0f}종목  "
          f"평균 턴오버 {log['turnover'].mean():.2f}  "
          f"평균 월비용 {log['cost'].mean()*1e4:.1f}bp")
    realized = metrics.summarize(log["net"]).get("ann_vol", float("nan"))
    predicted = log["pred_vol_ann"].mean()
    print(f"후보 {log['n_candidates'].mean():.0f}종목 (Σ 창 {cfg.cov_window_days}일)  "
          f"예측 변동성 {predicted:.1%} vs 실현 {realized:.1%}  "
          f"→ 과소평가 {realized / predicted:.1f}배\n")
    print(f"전략 (net)   : {_fmt(metrics.summarize(log['net']))}")
    print(f"전략 (gross) : {_fmt(metrics.summarize(log['gross']))}")
    print(f"EW top_n     : {_fmt(metrics.summarize(log['ew_topn']))}   (참고, gross)")
    print(f"유니버스 EW  : {_fmt(metrics.summarize(log['univ_ew']))}   (참고, gross)")

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "last_backtest.csv"
    log.to_csv(out)
    print(f"\n월별 로그 저장: {out}")


if __name__ == "__main__":
    main(monthly_config() if sys.argv[1:2] == ["monthly"] else StrategyConfig())
