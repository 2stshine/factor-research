# cycle-0216-net_equity_issuance_price_adjusted_36m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-006` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `e7a5c1273e578254`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_equity_issuance_price_adjusted_36m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 36개월 price_adjusted_issuance 확대가 큰 기업은 외부자금 수요나 고평가 활용 가능성이 높아 이후 상대수익이 낮다.

## Mechanism

발행·부채조달·자본금 변화 중 하나를 PIT 시점에서 분리하여 경영자의 자금조달 결정을 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 36 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9117631311238421 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9052759924824242 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05601575902405743 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.057991870799164034 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.909363858610605 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3293984629403082 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03475083465824582 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6506726946998955 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05601575902405743 |
| `ic_t_full` | 6.808918053879889 |
| `ic_p_full` | 2.4652078439907754e-09 |
| `ic_investable` | 0.057991870799164034 |
| `ic_std_investable` | 0.06377191071544058 |
| `rank_icir_investable` | 0.909363858610605 |
| `ic_t_investable` | 7.71616289840938 |
| `ic_p_investable` | 6.775995002429688e-11 |
| `ic_retention` | 1.035277782708575 |
| `neutral_ic` | 0.03475083465824582 |
| `neutral_ic_t` | 5.358973245723573 |
| `neutral_ic_p` | 6.758704836675974e-07 |
| `neutral_ic_retention` | 0.5992363098371843 |
| `n_trials` | 229 |
| `max_gold_signal_corr` | 0.6506726946998955 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'enterprise_sales_yield_change_6m': 62, 'idiosyncratic_volatility_24m': 62, 'max_daily_return_mean_6m': 62, 'net_income_to_liabilities': 62, 'net_margin_volatility_12m': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'pretax_yield_change_6m': 62, 'price_range_12m': 62, 'realized_daily_volatility_change_24m': 62, 'realized_daily_volatility_instability_6m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_equity_issuance_price_adjusted_24m` | other | 0.846 | 63 |
| `net_equity_issuance_12m` | other | 0.657 | 63 |
| `net_equity_issuance_price_adjusted_12m` | other | 0.657 | 63 |
| `capital_stock_growth_18m` | other | 0.650 | 63 |
| `capital_stock_growth_12m` | other | 0.595 | 63 |
| `retained_earnings_yield` | value | 0.546 | 63 |
| `retained_earnings_to_equity` | quality | 0.545 | 63 |
| `retained_earnings_to_assets` | quality | 0.530 | 63 |
| `retained_earnings_to_current_assets` | quality | 0.525 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.508 | 63 |
| `capital_stock_growth_6m` | other | 0.507 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.495 | 63 |
| `retained_earnings_to_current_liabilities` | quality | 0.495 | 63 |
| `retained_earnings_to_noncurrent_assets` | quality | 0.487 | 63 |
| `retained_earnings_to_noncurrent_liabilities` | quality | 0.454 | 63 |

## Expected relationship and data notes

- Expected relationship: 자산성장과 일부 관계가 예상되지만 조달 측면만 측정한다.
- Data notes: 정확한 달력 시차와 양의 분모만 사용하며 기업행사 후행 라벨은 사용하지 않는다.
