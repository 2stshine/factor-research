# cycle-0119-revenue_to_current_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `afb920b0e657b7c9`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/revenue_to_current_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

PIT 매출/유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

같은 재고·매출채권·현금 기반에서 더 많은 매출을 내는 기업은 운전자본 회전이 효율적이다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전 계열 직교성이 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 0 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9240547961970031 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9068077368534231 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.03197677986699694 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0327352820060551 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5281725367327502 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.33351985729933403 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.02813203036197428 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 1.0 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.03197677986699694 |
| `ic_t_full` | 4.198543721660586 |
| `ic_p_full` | 4.439657579825153e-05 |
| `ic_investable` | 0.0327352820060551 |
| `ic_std_investable` | 0.061978387230343275 |
| `rank_icir_investable` | 0.5281725367327502 |
| `ic_t_investable` | 4.229719696957081 |
| `ic_p_investable` | 3.989803993567289e-05 |
| `ic_retention` | 1.0237204040623553 |
| `neutral_ic` | 0.02813203036197428 |
| `neutral_ic_t` | 4.177023397259717 |
| `neutral_ic_p` | 4.77842160527466e-05 |
| `neutral_ic_retention` | 0.8593795024209858 |
| `n_trials` | 139 |
| `max_gold_signal_corr` | 1.0 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 1.0 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_asset_turnover` | quality | 1.000 | 63 |
| `asset_turnover` | quality | 0.723 | 63 |
| `revenue_to_equity` | quality | 0.720 | 63 |
| `working_capital_to_sales` | quality | -0.683 | 63 |
| `value_sp` | value | 0.636 | 63 |
| `net_working_capital_to_assets` | quality | -0.492 | 63 |
| `current_ratio` | quality | -0.482 | 63 |
| `current_assets_to_total_liabilities` | quality | -0.481 | 63 |
| `pretax_margin_volatility_36m` | quality | 0.474 | 52 |
| `net_working_capital_to_liabilities` | quality | -0.474 | 63 |
| `revenue_to_capital_stock` | quality | 0.474 | 63 |
| `net_margin_volatility_36m` | quality | 0.469 | 52 |
| `noncurrent_assets_to_equity` | other | -0.466 | 63 |
| `market_leverage` | other | 0.439 | 63 |
| `noncurrent_assets_yield` | value | 0.432 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: asset_turnover — 차이: 총자산이 아니라 단기 영업자산의 매출 생산성만 측정한다.
- Data notes: DART available_date PIT revenue_ttm과 양의 current_assets만 사용한다.
