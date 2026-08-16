# cycle-0226-retained_earnings_to_assets_volatility_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-007` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `b7a8b39202f9a9eb`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_to_assets_volatility_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 12개월 retained_earnings/total_assets 변동성이 낮은 기업은 이익의 질이 높아 이후 상대수익이 높다.

## Mechanism

PIT 누적이익 비율의 안정성을 측정해 단일 시점 수익성 수준과 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 12 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9528373323950772 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9493449920050706 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.0422360201047888 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04388642176586769 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7328507790443679 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.32755493921670154 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03349697787885335 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.4773676992885685 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0422360201047888 |
| `ic_t_full` | 4.882935540747936 |
| `ic_p_full` | 3.941708980433312e-06 |
| `ic_investable` | 0.04388642176586769 |
| `ic_std_investable` | 0.059884526319389696 |
| `rank_icir_investable` | 0.7328507790443679 |
| `ic_t_investable` | 5.925134975863748 |
| `ic_p_investable` | 7.805079829545048e-08 |
| `ic_retention` | 1.0390756907725727 |
| `neutral_ic` | 0.03349697787885335 |
| `neutral_ic_t` | 5.131053633265282 |
| `neutral_ic_p` | 1.5830819613683772e-06 |
| `neutral_ic_retention` | 0.7632651861561736 |
| `n_trials` | 239 |
| `max_gold_signal_corr` | 0.4773676992885685 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'enterprise_sales_yield_change_6m': 62, 'idiosyncratic_volatility_24m': 62, 'max_daily_return_mean_6m': 62, 'net_equity_issuance_price_adjusted_36m': 62, 'net_income_to_liabilities': 62, 'net_margin_volatility_12m': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'pretax_yield_change_6m': 62, 'price_range_12m': 62, 'realized_daily_volatility_change_24m': 62, 'realized_daily_volatility_instability_6m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_roa_volatility_36m` | quality | 0.520 | 52 |
| `pretax_roa_volatility_36m` | quality | 0.513 | 52 |
| `net_margin_volatility_12m` | earnings | 0.477 | 63 |
| `net_margin_volatility_36m` | quality | 0.443 | 52 |
| `operating_roa_volatility_36m` | quality | 0.441 | 52 |
| `pretax_margin_volatility_36m` | quality | 0.437 | 52 |
| `operating_margin_volatility_12m` | earnings | 0.412 | 63 |
| `retained_earnings_yield` | value | 0.409 | 63 |
| `value_bp` | value | 0.353 | 63 |
| `defensive_value` | value | 0.336 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.329 | 63 |
| `asset_to_market` | value | 0.328 | 63 |
| `retained_earnings_to_current_assets` | quality | 0.321 | 63 |
| `operating_earnings_yield` | value | 0.320 | 63 |
| `noncurrent_assets_yield` | value | 0.318 | 63 |

## Expected relationship and data notes

- Expected relationship: 수익성·자본축적 수준과 관련될 수 있으나 시계열 안정성은 별도 메커니즘이다.
- Data notes: DART available_date PIT 비율의 고정 달력창만 사용한다.
