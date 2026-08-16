# cycle-0183-realized_daily_volatility_change_24m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ac577decfdf6edbd`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/realized_daily_volatility_change_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 24개월 daily_volatility_252d 악화가 작은 종목은 위험수요의 과대가격을 피하여 이후 상대수익이 높다.

## Mechanism

위험 수준이 아니라 사전 고정 기간의 변화를 측정해 기존 Gold 저위험 수준 신호와 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 24 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9509939650754556 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9435311975548462 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.04383190617901758 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04682502636152427 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7869806378566275 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3112057700136459 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.014706526084475799 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.33577181773245957 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.04383190617901758 |
| `ic_t_full` | 6.9753808866800435 |
| `ic_p_full` | 1.2771166579046033e-09 |
| `ic_investable` | 0.04682502636152427 |
| `ic_std_investable` | 0.0594995913610455 |
| `rank_icir_investable` | 0.7869806378566275 |
| `ic_t_investable` | 8.178805412935743 |
| `ic_p_investable` | 1.0835926876049587e-11 |
| `ic_retention` | 1.0682863339386206 |
| `neutral_ic` | 0.014706526084475799 |
| `neutral_ic_t` | 3.391926178037046 |
| `neutral_ic_p` | 0.0006115806749304407 |
| `neutral_ic_retention` | 0.31407405883619594 |
| `n_trials` | 199 |
| `max_gold_signal_corr` | 0.33577181773245957 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'price_range_12m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `daily_volatility_change_12m` | other | 0.513 | 63 |
| `realized_volatility_252d` | other | 0.481 | 63 |
| `low_vol_12m` | other | 0.437 | 63 |
| `max_monthly_return_12m` | other | 0.432 | 63 |
| `max_daily_return_instability_18m` | quality | 0.400 | 63 |
| `max_daily_return_mean_6m` | quality | 0.397 | 63 |
| `price_trend_efficiency_24m` | momentum | -0.368 | 63 |
| `max_daily_return_instability_6m` | quality | 0.340 | 63 |
| `price_range_12m` | other | 0.336 | 63 |
| `price_recovery_24m` | momentum | -0.326 | 63 |
| `return_gain_loss_ratio_12m` | momentum | -0.307 | 63 |
| `realized_daily_volatility_change_6m` | quality | 0.296 | 63 |
| `idiosyncratic_volatility_24m` | other | 0.295 | 63 |
| `price_trend_efficiency_12m` | momentum | -0.294 | 63 |
| `trading_value_volatility_12m` | other | 0.294 | 63 |

## Expected relationship and data notes

- Expected relationship: 저위험 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.
- Data notes: Silver 월말 위험 요약과 정확한 달력 시차만 사용한다.
