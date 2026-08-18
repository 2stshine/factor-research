"""전략 파라미터. 확정된 설계는 strategies/README.md 참조."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FILE = REPO_ROOT / "research" / "context" / "latest.md"
_CUTOFF_RE = re.compile(r"^- Strategy context cutoff: `(\d{4})-(\d{2})-\d{2}`", re.M)


def context_cutoff_ym() -> str | None:
    """연구 컨텍스트가 고지한 전략 컨텍스트 컷오프(신호월).

    봉인된 캠페인이 있는 동안 전략은 컷오프 뒤 결과를 보면 안 된다. 값을 하드코딩하지
    않고 `research/context/latest.md`에서 읽으므로, 캠페인이 공개되면 컨텍스트를 다시
    만드는 것만으로 창이 넓어진다.
    """
    if not CONTEXT_FILE.exists():
        return None
    found = _CUTOFF_RE.search(CONTEXT_FILE.read_text(encoding="utf-8"))
    return f"{found.group(1)}-{found.group(2)}" if found else None


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

    # --- 표본 주기 ---
    # "daily"   README의 확정 설계. 일별 표본으로 학습하며 daily_* 캐시가 필요하다.
    # "monthly" 승인 팩터 월말 값만으로 학습. gold signal 캐시만 있으면 되고 RDS도
    #           daily 캐시도 필요 없다. 이때 아래 `fwd_days`·`train_window_days`·
    #           `min_train_days`의 단위는 거래일이 아니라 **월**이다.
    sample_frequency: str = "daily"
    # 봉인 캠페인이 있는 동안 전략이 볼 수 있는 마지막 신호월(`YYYY-MM`). None이면 무제한.
    context_cutoff_ym: str | None = None

    # --- 신호 결합 방식 ---
    # "ridge"        팩터별 가중치를 학습해 결합 (기본)
    # "ew_composite" 팩터 z-score를 동일가중 평균해 **단일 팩터**로 쓴다. 상대
    #                가중치는 학습하지 않고 스칼라 스케일만 같은 롤링 릿지로
    #                적합한다 — r̂를 수익률 단위로 되돌려야 QP 목적함수에서
    #                μ와 c·wᵀΣw의 단위가 정합하기 때문이다. z-score를 그대로
    #                넣으면 평균항이 위험·턴오버항을 압도해 비교가 성립하지 않는다.
    signal: str = "ridge"

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
    # 상장 펀드·투자회사 제외. Silver `instrument_type`이 이들을 common_stock으로
    # 분류해 엔진 `ok_common`을 통과시킨다. 근거는 data.LISTED_FUND_NAME_RE 참조.
    exclude_listed_funds: bool = True

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
    # 표본공분산은 N > T에서 랭크가 T로 막혀 N−T개 방향의 위험이 0이 된다. 옵티마이저가
    # 그 방향을 공짜로 쓰므로 축소가 필요하다. "ledoit_wolf"(상수상관 타깃, 축소강도는
    # 닫힌형으로 결정) / "none"(비교용 표본공분산). cov.py 참조.
    cov_shrinkage: str = "ledoit_wolf"

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


def monthly_config(**overrides) -> StrategyConfig:
    """월말 표본 프리셋.

    일별 설계를 그대로 두고 단위만 월로 바꾼 것이다 — `fwd_days=1`은 엔진 `fwd_mid`와
    같은 1개월 forward이고, 창 길이도 월 단위가 된다. 36개월 창을 쓰는 이유는 승인
    팩터 값이 2018-03부터라 컷오프 안에서 60개월 창을 잡으면 예측할 월이 남지 않기
    때문이다.

    컷오프는 연구 컨텍스트에서 읽는다. 봉인 구간을 일부러 포함하려면
    `monthly_config(context_cutoff_ym=None)`.
    """
    base = StrategyConfig(
        sample_frequency="monthly",
        context_cutoff_ym=context_cutoff_ym(),
        fwd_days=1,               # 1개월 forward
        train_window_days=36,     # 롤링 36개월
        min_train_days=24,        # 최소 24개월
        min_train_rows=10_000,
    )
    return replace(base, **overrides) if overrides else base
