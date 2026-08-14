"""전략 파라미터. 확정된 설계는 strategies/README.md 참조."""
from __future__ import annotations

from dataclasses import dataclass


# 팩터 목록은 gold.factor에서 조회한다(`strategies/gold.py`). 캐시가 없을 때만 아래 기본값을
# 쓴다 — 2026-08-11 시점의 APPROVED 4종. 엔진 compute_all이 f_<name> 컬럼을 만든다.
_FALLBACK_GOLD: tuple[str, ...] = (
    "max_daily_return_1m",
    "net_equity_issuance_price_adjusted_12m",
    "operating_income_to_liabilities",
    "realized_volatility_252d",
)


def _gold_factors() -> tuple[str, ...]:
    from strategies.gold import approved_factors

    return approved_factors(default=_FALLBACK_GOLD)


GOLD_FACTORS: tuple[str, ...] = _gold_factors()


@dataclass(frozen=True)
class StrategyConfig:
    # --- 입력 팩터 ---
    factors: tuple[str, ...] = GOLD_FACTORS

    # --- 1단계: 예측(ridge) ---
    # 학습 표본은 **매 거래일**이다. 각 (종목, 거래일)이 한 행이고 타깃은 fwd_days
    # 거래일 뒤까지의 누적 수익률. 예측·리밸런싱은 월 1회(월말) 그대로다.
    fwd_days: int = 21                 # 타깃 지평 (21거래일 ≈ 1개월)
    train_window_days: int = 1260      # 롤링 학습창 (1260거래일 ≈ 60개월)
    min_train_days: int = 500          # 최소 학습 거래일 수
    min_train_rows: int = 10_000       # 최소 학습 행 수
    # --- 정규화 강도 λ (표준형: 잔차제곱합 + λ‖β‖²) ---
    # "press"     LOOCV(PRESS)를 학습창 안에서 최소화 (기본)
    # "month_cv"  leave-one-month-out CV. 월내 횡단면 상관을 피하는 블록 CV
    # "fixed"     아래 ridge_lambda 값을 그대로 사용
    lambda_selection: str = "press"
    ridge_lambda: float = 1.0          # lambda_selection="fixed"일 때만 사용
    # 격자는 표본수에 비례시켜 정의한다: λ = κ·n. feature가 z-score라 XᵀX 대각 ≈ n 이므로
    # κ는 "패널티/신호" 비율로 해석된다 (κ=1이면 대각을 2배로 키움).
    # κ=0은 넣지 않는다 — 팩터가 전결측인 월은 해당 열이 상수 0이라 XᵀX가 특이해진다.
    # 최솟값 1e-5는 XᵀX 대각(≈n)의 0.001% 수준이라 사실상 OLS다.
    lambda_grid_kappa: tuple[float, ...] = (
        1e-5, 1e-4, 1e-3, 1e-2, 0.03, 0.1, 0.3, 1.0, 3.0,
        10.0, 30.0, 100.0, 300.0, 1000.0,
    )
    winsor_q: float = 0.01             # 횡단면 winsorize 하/상 분위

    # --- 유니버스/후보 선택 ---
    # 최적화 대상 후보 수(예측수익 상위). None이면 투자가능 전 종목을 넘긴다.
    # 원래는 Σ 추정 제약(N<T) 때문에 두었으나 일별 전환으로 T=500이 되어 근거가 사라졌다.
    # 상위 N개만 남기면 그 안에서 r̂ 분산이 거의 없어져(std 0.06%/월) μ가 무력해지는
    # 부작용이 있다. 전 종목을 넘겨도 롱온리+상한 제약이 해를 희소하게 만들어
    # 보유는 20~40종목으로 안착한다.
    top_n: int | None = None
    require_investable: bool = True     # adv20>0 (엔진 투자가능 유니버스)

    # --- 2단계: 배분(QP) ---
    # mean − c·var 의 c. 표준 mean-variance 효용에서 c = γ/2 (γ=상대위험회피계수)이고
    # 기관 통상 범위가 γ=2~10 이므로 c ∈ [1,5]. 그 중앙값을 택했다(γ=6).
    # 단, 전액투자(Σw=1)·상한 5% 제약 때문에 c의 영향은 제한적이다 — c를 0.1~200으로
    # 2000배 바꿔도 보유는 26~27종목으로 고정이고 예측 변동성만 13.6%→6.4%로 움직인다.
    risk_aversion_c: float = 3.0
    # 종목 상한. 단순한 분산 강제가 아니라 **추정오차 착취를 막는 핵심 방어선**이다.
    # 상한을 풀면 옵티마이저가 한 종목에 70%까지 넣고 "위험 2.7%"라 주장하지만
    # 실현 변동성은 56.6%였다(상한 5%일 때 31.0%). 제약이 곧 shrinkage(Jagannathan-Ma 2003).
    weight_cap_u: float = 0.05
    # Σ는 일별 수익률로 추정한다(월말만 쓰면 T=60 < N이라 표본공분산이 특이해진다).
    # 500거래일 ≈ 2년. 후보가 전 종목이라 N > T 이지만, 표본공분산은 PSD이고 제약이
    # 실행가능 영역을 컴팩트하게 만들므로 QP는 그대로 풀린다(역행렬을 쓰지 않는다).
    cov_window_days: int = 500
    cov_min_days: int = 250
    cov_min_obs_ratio: float = 0.8     # 창 내 관측 비율이 이보다 낮은 종목은 제외

    # --- 비용/턴오버 ---
    cost_bps_per_side: float = 30.0    # 편도 거래비용(수수료+세금 근사, bp)
    # γ(턴오버 페널티)는 편도 비용률과 정합 → 목적함수 안에서 cost-aware
    # γ = cost_bps_per_side / 1e4  (backtest에서 자동 설정; 아래 프로퍼티)

    # --- 타깃/수익 정의 ---
    target_col: str = "fwd_mid"        # 백테스트 실현수익 (엔진 월말 패널, terminal -0.50)
    # 일별 학습 타깃의 상폐 terminal. 엔진 fwd_mid와 같은 값을 써서 학습과 실현이
    # 상폐를 동일하게 취급하게 한다.
    terminal_return: float = -0.50
    return_level_col: str = "return_close"  # 총수익 레벨(=total_return_close) → 월수익·Σ

    @property
    def turnover_gamma(self) -> float:
        return self.cost_bps_per_side / 1e4
