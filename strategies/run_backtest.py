"""백테스트 엔트리 — 팩터 값으로 수익률을 적합하고 MVO로 비중을 정한다.

    uv run python -m strategies.run_backtest

월별 로그는 experiments/last_backtest.csv 에 저장한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategies.config import StrategyConfig
from strategies import data, daily, predict, backtest, metrics

OUT_DIR = Path(__file__).resolve().parent / "experiments"


def _fmt(m: dict) -> str:
    if not m:
        return "(no data)"
    return (f"CAGR={m['cagr']:+6.2%}  vol={m['ann_vol']:5.1%}  Sharpe={m['sharpe']:5.2f}  "
            f"MDD={m['mdd']:6.1%}  hit={m['hit_rate']:4.0%}")


def main() -> None:
    cfg = StrategyConfig()
    print("=== 설정 ===")
    print(f"factors={cfg.factors}")
    print(f"top_n={cfg.top_n}  cap={cfg.weight_cap_u}  c={cfg.risk_aversion_c}  "
          f"gamma={cfg.turnover_gamma:.4f}  cost/side={cfg.cost_bps_per_side}bp")
    print(f"fwd_days={cfg.fwd_days}  train_window={cfg.train_window_days}일  "
          f"cov_window={cfg.cov_window_days}일  target={cfg.target_col}")

    print("\n[1/4] 패널 로드...")
    panel = data.load_panel()
    frame = data.strategy_frame(panel, cfg)        # 월말 — 백테스트 실현수익용
    dframe = data.daily_frame(panel, cfg)          # 일별 — ridge 학습용
    dret = daily.load_daily()
    print(f"  {len(frame):,}행 / {frame['ym'].nunique()}개월 / "
          f"{frame['asset_id'].nunique():,}종목  ({frame['ym'].min()}~{frame['ym'].max()})")

    print("[2/4] ridge 예측...")
    preds = predict.predict_returns(dframe, cfg)
    print(f"  학습 일별 {len(dframe):,}행 → 예측 {len(preds):,}행 / "
          f"{preds['ym'].nunique()}개월")

    print("[3/4] QP 백테스트...")
    log = backtest.run_backtest(frame, preds, dret, cfg)["log"]

    print("[4/4] 성과\n")
    print(f"기간 {log.index.min()} ~ {log.index.max()}  ({len(log)}개 리밸런싱)")
    print(f"평균 보유 {log['n_holdings'].mean():.0f}종목  "
          f"평균 턴오버 {log['turnover'].mean():.2f}  "
          f"평균 월비용 {log['cost'].mean()*1e4:.1f}bp\n")
    print(f"전략 (net)   : {_fmt(metrics.summarize(log['net']))}")
    print(f"전략 (gross) : {_fmt(metrics.summarize(log['gross']))}")
    print(f"EW top_n     : {_fmt(metrics.summarize(log['ew_topn']))}   (참고, gross)")
    print(f"유니버스 EW  : {_fmt(metrics.summarize(log['univ_ew']))}   (참고, gross)")

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "last_backtest.csv"
    log.to_csv(out)
    print(f"\n월별 로그 저장: {out}")


if __name__ == "__main__":
    main()
