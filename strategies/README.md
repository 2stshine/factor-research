# strategies

gold로 승격된 팩터들을 조합·배분해 포트폴리오를 구성하는 **전략 리서치 baseline**.

> 이 폴더는 factor-research 엔진의 "단일 팩터 계약"(여러 팩터 rank 가중합 금지, T0에서 거부)과
> 분리된 영역이다. 팩터의 발굴·검증·승격은 엔진(`engine/`, `research/`)의 몫이고, 이 레이어는
> 승격된 팩터를 입력으로 받아 수익 예측 → 비중 결정을 수행한다.

실험 기록은 [`experiments/`](experiments/)에 둔다. 이 문서에는 확정된 설계만 적는다.

---

## 파이프라인

```
gold.factor 조회 → 일별 팩터 → ridge 예측(일별 학습) → Σ 추정(일별) → QP 배분 → 월별 백테스트
```

### 1단계 — 수익률 예측 (Ridge)

$$
\hat{\beta} = \arg\min_{\beta} \sum_i \left( r_i - x_i^\top \beta \right)^2 + \lambda \lVert \beta \rVert_2^2
\qquad\Rightarrow\qquad \hat{r}_i = x_i^\top \hat{\beta}
$$

| 항목 | 내용 |
|---|---|
| 관측 단위 | **(종목, 거래일)** — 매 거래일이 표본 |
| `X` | gold 팩터 값, **날짜별 횡단면** winsorize(1/99) → z-score, 결측=0(중앙값) |
| `y` | **21거래일** forward 총수익률. 창 안에서 상폐되면 **terminal −50%** 부여 |
| 표준화 | `y`를 표준화해 적합한 뒤 `β × s_y`로 **수익률 단위 환원** |
| 절편 | 없음 (`X`가 날짜별 평균0이라 직교, 넣어도 `β` 불변) |
| 학습창 | 직전 **1260거래일** 롤링, 매월 재적합 |
| `λ` | **PRESS**(LOOCV)를 학습창 안에서 최소화, 격자 `λ = κ·n` |
| 예측 | **각 월 마지막 거래일**에 그 시점 횡단면으로 산출 |

`r̂`의 단위는 **21거래일 수익률**이며, `Σ`도 같은 지평(일별×21)이라 목적함수에서 단위가 정합한다.
절편이 없어 횡단면 평균이 0이므로 `r̂`는 "그 시점 평균 대비 초과분"이다.

**PIT** — 날짜 `d`의 타깃은 `d + 21`에 확정되므로, 신호일 `t`의 학습에는 `d ≤ t − 21`인 행만 쓴다.

**상폐 처리** — forward 창 안에서 종목이 사라지면 수익률이 NaN이 되어 학습에서 빠진다.
그대로 두면 모델이 상폐를 한 번도 못 보고 학습하는데 백테스트는 그 손실을 그대로 맞으므로,
엔진 `fwd_mid`와 **같은 terminal(−50%)** 을 부여해 양쪽이 상폐를 동일하게 취급하게 한다.

### 2단계 — 비중 최적화 (QP)

$$
\max_{w}\ w^\top \hat{r} - c\,w^\top \Sigma w - \gamma\lVert w - w_{\text{prev}}\rVert_1
\qquad\text{s.t.}\qquad \mathbf{1}^\top w = 1,\quad 0 \le w \le u
$$

- 후보: **투자가능 전 종목** (사전 필터 없음)
- cvxpy가 L1항을 보조변수로 풀어 표준 QP로 변환 → OSQP(실패 시 CLARABEL)
- 해 후처리: 음수 clip → 합 1로 재정규화
- `c = γ_RA/2` (표준 mean-variance 효용). 기관 통상 `γ_RA = 2~10` → `c ∈ [1,5]`

**턴오버는 목적함수 안에 둔다.** 사후 차감만 하면 옵티마이저가 비용을 못 보고 과도하게 회전한다.
백테스트 회계에도 같은 요율을 적용해 두 값이 일치한다.

### Σ 추정 (일별)

1. PIT-safe `adj_close` 일별 가격수익률 500거래일 창
   (창 내 관측 80% 이상인 종목만, 남은 결측은 0 대체)
2. 표본공분산 → 거래일 21일 기준 월 환산

`total_return_close`는 공분산에 쓰지 않고 향후 수익률 label에만 쓴다. 두 역할은
버전이 다른 로컬 캐시로 물리적으로 분리된다.

`N > T` 여도 표본공분산은 Gram 행렬이라 PSD이고, 제약이 실행가능 영역을 컴팩트하게
만들므로 QP는 그대로 풀린다(Σ의 역행렬은 쓰지 않는다).

---

## 팩터 값의 출처 — 월말 표본 경로

엔진 빌드 캐시(`.cache/panel.pkl`)는 **Silver/PIT 입력만 보관하고 팩터 값을 담지 않는다**.
승인 팩터의 월말 값은 엔진이 `.cache/gold-signals/<generation_digest>/signals.parquet`에
wide로 캐시하므로 전략은 `strategies/gold_signals.py`로 그것을 읽는다.

- 캐시는 **승인 exact set 일치**로 고른다(파일 시각이 아니라). 승인 목록이 바뀌었는데
  캐시가 없으면 조용히 옛 집합을 쓰는 대신 실패한다.
- `parquet_sha256`·`row_count`·컬럼 집합을 엔진이 쓴 매니페스트로 재검증한다.

이 경로는 `daily_*` 캐시도 RDS도 필요 없다. `StrategyConfig.sample_frequency="monthly"`
(`config.monthly_config()`)로 켜며, 이때 `fwd_days`·`train_window_days`·`min_train_days`의
단위는 거래일이 아니라 **월**이다. 승인 팩터 값이 2018-03부터라 컷오프 안에서 60개월 창을
잡으면 예측할 월이 남지 않아 기본값은 36개월 창이다.

**전략 컨텍스트 컷오프** — 봉인된 캠페인이 있는 동안 전략은 컷오프 뒤를 보면 안 된다.
`config.context_cutoff_ym()`이 `research/context/latest.md`의 `Strategy context cutoff`를
읽어 오므로 캠페인이 공개되면 컨텍스트를 다시 만드는 것만으로 창이 넓어진다. 일부러
봉인 구간을 포함하려면 `monthly_config(context_cutoff_ym=None)`.

## 부호 규약 (중요)

패널의 `f_<name>` 컬럼은 **이미 `predicted_sign`이 곱해져 있다** — `engine/factors.py`의
`compute_all`이 `f.compute(out) * f.predicted_sign`으로 저장한다. 따라서 어떤 팩터든
`f_` 컬럼은 **값이 클수록 예측 고수익**이다(`predicted_sign = −1`인 팩터는 부호가 뒤집혀
저장된다). 전략 레이어에서 `predicted_sign`을 다시 곱하면 이중 적용 버그가 된다.

**`gold.factor_value.value`도 같은 규약이다** — 즉 이미 방향이 적용돼 있다. `engine/publish.py`의
`value_contract`는 `value: "raw"` / `score: "value*predicted_sign"`이라 적고 있지만 적재된
값은 그 문구와 다르다. 계약 문구를 그대로 따르면 `predicted_sign = −1` 팩터가 전부
뒤집힌다. 확인 근거는 `strategies/gold_signals.py` docstring에 있다.

## 팩터의 일별 정의

학습 표본이 매 거래일이므로 팩터도 일별 값이 필요하다. 엔진 정의를 그대로 쓸 수 없는
경우가 있어 아래 규칙을 따른다.

| 엔진 정의 유형 | 일별 처리 |
|---|---|
| 일별 입력의 롤링 창 | 같은 창으로 일별 재계산 |
| 달력월 파티션 (`date_trunc('month')`) | **동등한 롤링 창으로 재정의** |
| 월 인덱스 `shift(N)` | **거래일 기준 롤링으로 재정의** |
| 일별 값이 없는 것 (재무 등) | **직전 월말 값을 asof로 부착** |

달력월 정의를 매일 쓰면 월초엔 며칠치, 월말엔 한 달치가 되어 "오늘이 월 며칠째인가"를
학습하게 되므로 재정의가 필요하다. 월말 시점에서는 두 정의가 사실상 일치한다.

### 새 팩터 추가

`daily_factors.DAILY_FACTOR_DEFS`가 **팩터명 → 일별 계산 함수** 레지스트리다. 한 줄 추가하면
된다. 함수는 `DailyInputs`(일별 수익률·주식수)를 받아 (거래일 × 종목) DataFrame을 반환하며,
**부호를 적용해** 값이 클수록 예측 고수익이 되게 한다.

```python
def _my_factor(ctx: DailyInputs) -> pd.DataFrame:
    return -ctx.returns.rolling(60).mean()

DAILY_FACTOR_DEFS["my_factor"] = _my_factor
```

**등록하지 않아도 파이프라인은 깨지지 않는다** — 해당 팩터는 자동으로 월말 asof 경로를 타고,
`build_cache()`와 `daily_frame()`이 어느 팩터가 어느 경로인지 출력한다.

이 재정의는 **전략 레이어에만 존재**한다. `gold.factor`·`engine/`·`factors/candidates/`는
건드리지 않으며, 연결은 `silver.connect(read_only=True)`라 쓰기가 불가능하다.

---

## 파라미터

`config.py`의 `StrategyConfig`.

| 항목 | 값 |
|---|---|
| 팩터 목록 | `gold.factor` APPROVED (동적 조회) |
| `fwd_days` | 21 |
| `train_window_days` | 1260 |
| `min_train_days` / `min_train_rows` | 500 / 10,000 |
| `winsor_q` | 0.01 |
| `lambda_selection` | `press` (격자 `κ` = 1e-5 ~ 1000) |
| 후보 (`top_n`) | `None` = 전 종목 |
| `risk_aversion_c` | **3.0** |
| `weight_cap_u` | **0.05** |
| `cov_window_days` / `cov_min_days` | 500 / 250 |
| `terminal_return` | −0.50 |
| `cost_bps_per_side` | 30 |
| 리밸런싱 | 월 1회(월말) |

## 구조

```
strategies/
  config.py         StrategyConfig
  gold.py           gold.factor 목록 조회·캐시
  data.py           월말 패널 로드 / 일별 학습 프레임 조립
  daily.py          일별 총수익률 적재·캐시
  daily_factors.py  일별 팩터값 계산·캐시 (시총·주가 적재 포함)
  predict.py        일별 표본 롤링 ridge
  cov.py            일별 Σ (표본공분산)
  optimize.py       cvxpy QP
  backtest.py       월별 루프 (경로 의존 w_prev)
  metrics.py        CAGR·연변동성·Sharpe·MDD·hit rate
  run_backtest.py   백테스트 엔트리
  evaluate.py       예측 진단 (IC, 10분위, R²)
  experiments/      실험 기록·산출물
```

## 캐시

| 파일 | 생성 |
|---|---|
| `.cache/panel.pkl` | `scripts/run.py build` (엔진) |
| `.cache/gold-signals/<generation>/` | 엔진 (승인 팩터 월말 값) |
| `.cache/gold_factors.json` | `strategies.gold` |
| `.cache/daily_price_returns_krx_split_adjusted_v1.parquet` | `strategies.daily` — 팩터·공분산 전용 |
| `.cache/daily_label_returns_krx_gross_dividend_v3.parquet` | `strategies.daily` — 향후 label 전용 |
| `.cache/daily_price.parquet` | `strategies.daily_factors price` |
| `.cache/daily_factors.parquet` | `strategies.daily_factors build` (로컬) |

## 실행

RDS가 SSM 터널 뒤에 있으면 `SILVER_DB_HOST_OVERRIDE`/`PORT_OVERRIDE`로 로컬 포트를 지정한다.

```bash
# 1) 엔진 월말 패널 (RDS)
SILVER_DB_SECRET_ID= SILVER_DB_HOST_OVERRIDE=localhost SILVER_DB_PORT_OVERRIDE=55432 \
  uv run python scripts/run.py build
```
```bash
# 2) gold 목록 · 일별 수익률 · 일별 시총/주가 (RDS)
SILVER_DB_SECRET_ID= SILVER_DB_HOST_OVERRIDE=localhost SILVER_DB_PORT_OVERRIDE=55432 \
  uv run python -m strategies.gold
SILVER_DB_SECRET_ID= SILVER_DB_HOST_OVERRIDE=localhost SILVER_DB_PORT_OVERRIDE=55432 \
  uv run python -m strategies.daily
SILVER_DB_SECRET_ID= SILVER_DB_HOST_OVERRIDE=localhost SILVER_DB_PORT_OVERRIDE=55432 \
  uv run python -m strategies.daily_factors price
```
```bash
# 3) 일별 팩터 계산 (로컬)
uv run python -m strategies.daily_factors build
```
```bash
# 4) 백테스트 / 예측 진단 (캐시만 있으면 RDS 불필요)
uv run python -m strategies.run_backtest
uv run python -m strategies.evaluate
```

월말 표본 경로는 `gold-signals` 캐시와 `panel.pkl`만 있으면 되므로 1)·3)을 건너뛴다.

```bash
uv run python -m strategies.evaluate monthly
```

**추가 의존성**: `cvxpy`(+osqp/clarabel), `scikit-learn`. 엔진 core deps와 분리하려고
`uv pip install`로 venv에만 설치했고 `pyproject.toml`은 건드리지 않았다.

---

## 알려진 한계

- **비용 모델에 시장충격이 없다.** 편도 30bp 고정이라 소형주 비중이 커지면 과소평가된다.
- **2000-05 패널 이상.** 그 달 투자가능 종목 전부가 terminal `−50%`를 받는다(직후 월과
  asset_id 집합이 완전히 분리 — 재배정 추정). 이 달을 포함한 백테스트는 절대 CAGR·MDD가
  왜곡되므로, 필요하면 시작을 2000-06 이후로 옮긴다.
- **일별 정의가 없는 팩터는 월 단위 계단식**이다(월말 asof). 재무 기반 팩터가 여기 해당하며,
  Silver 재무 원장의 가용범위에 따라 초기 구간 커버리지가 비어 있을 수 있다.
- **Σ는 최적화 입력으로 쓰면 위험을 과소평가한다.** 주어진 포트폴리오(동일가중)의 위험
  예측은 실현 대비 1.14배 수준이지만, 같은 Σ로 최적화한 포트폴리오는 3.5배가량 과소예측된다
  (근거: [`experiments/2026-08-12-공분산-추정.md`](experiments/2026-08-12-공분산-추정.md)).
- **학습 타깃과 실현 수익의 지평이 다르다** — 학습은 21거래일, 백테스트 실현은 엔진
  `fwd_mid`(월말→월말)다. 상폐 취급은 양쪽 모두 terminal −50%로 일치시켰다.
  `fwd_opt`/`fwd_pess`로 3점 스트레스 가능.

## 참고

- 팩터 판정 기준: [`docs/factor-promotion-criteria.md`](../docs/factor-promotion-criteria.md)
- 유니버스·수익률·안전장치 계약: 루트 [`README.md`](../README.md)
