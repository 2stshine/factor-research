# cycle-0227-trading_value_turnover_change_3m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-007` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `1de516aad267f8a3`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/trading_value_turnover_change_3m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 3개월 trading_value_turnover 급증이 작은 종목은 과도한 관심과 투기수요를 피하여 이후 상대수익이 높다.

## Mechanism

거래활동 수준 대신 기업가치 정규화 회전의 변화를 측정해 기존 Gold 유동성 수준과 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 3 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9675766221249972 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9571803102736388 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.03399266978521635 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.03415898696769665 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5407278361717158 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.4118844769474899 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | N | 0.009181578726690467 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.18046517900313802 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.03399266978521635 |
| `ic_t_full` | 4.59058881688282 |
| `ic_p_full` | 1.1296812538154356e-05 |
| `ic_investable` | 0.03415898696769665 |
| `ic_std_investable` | 0.06317223690486867 |
| `rank_icir_investable` | 0.5407278361717158 |
| `ic_t_investable` | 4.694386690623674 |
| `ic_p_investable` | 7.7959723429673e-06 |
| `ic_retention` | 1.0048927366850315 |
| `neutral_ic` | 0.009181578726690467 |
| `neutral_ic_t` | 1.3943581242408054 |
| `neutral_ic_p` | 0.08413370392006368 |
| `neutral_ic_retention` | 0.26878954974201286 |
| `n_trials` | 239 |
| `max_gold_signal_corr` | 0.18046517900313802 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'enterprise_sales_yield_change_6m': 62, 'idiosyncratic_volatility_24m': 62, 'max_daily_return_mean_6m': 62, 'net_equity_issuance_price_adjusted_36m': 62, 'net_income_to_liabilities': 62, 'net_margin_volatility_12m': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'pretax_yield_change_6m': 62, 'price_range_12m': 62, 'realized_daily_volatility_change_24m': 62, 'realized_daily_volatility_instability_6m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T3.2` 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: 0.009181578726690467 (IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `trading_value_turnover_change_6m` | other | 0.501 | 63 |
| `momentum_acceleration_6m` | momentum | -0.425 | 63 |
| `trading_value_turnover_change_12m` | other | 0.424 | 63 |
| `short_term_reversal_3m` | momentum | 0.400 | 63 |
| `turnover_change_6m` | other | 0.332 | 63 |
| `rev_1m` | momentum | 0.283 | 63 |
| `max_daily_return_1m` | other | 0.279 | 63 |
| `max_daily_return_change_6m` | quality | 0.271 | 63 |
| `price_reversal_3_1` | momentum | 0.265 | 63 |
| `adv20_change_12m` | other | 0.246 | 63 |
| `max_daily_return_change_12m` | other | 0.233 | 63 |
| `trading_turnover_20d` | other | 0.232 | 63 |
| `max_daily_return_change_18m` | quality | 0.220 | 63 |
| `high_12m_proximity` | momentum | -0.206 | 63 |
| `price_reversal_6_3` | momentum | -0.195 | 63 |

## Expected relationship and data notes

- Expected relationship: 거래활동 수준과 일부 관계가 예상되지만 변화율이므로 0.70 Gold gate를 요구한다.
- Data notes: 월말 거래대금·ADV20·시가총액과 정확한 달력 시차만 사용한다.
