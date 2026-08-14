"""gold 팩터 조합 → 포트폴리오 전략 레이어 (factor-research 엔진과 분리).

파이프라인: data → predict(ridge) → cov(Ledoit-Wolf) → optimize(QP) → backtest.
설계 근거와 결정 사항은 strategies/README.md 참조.
"""
