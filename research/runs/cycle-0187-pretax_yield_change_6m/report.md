# cycle-0187-pretax_yield_change_6m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ffea4912dd9bcb98`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_yield_change_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

pretax_income_ttm 대비 시장가치의 6개월 개선이 큰 기업은 펀더멘털 대비 가격이 덜 반영되어 이후 상대수익이 높다.

## Mechanism

가치비율의 현재 수준 대신 사전 고정 기간의 개선을 측정해 기존 Gold 가치 수준 신호와 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 6 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9051392468964884 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8716262084003676 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.033457954845472024 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.03403238580301296 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7011333389734321 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3495028435180181 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.033161815796788195 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.29614259962392186 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.033457954845472024 |
| `ic_t_full` | 4.775173549101239 |
| `ic_p_full` | 5.8279016186237986e-06 |
| `ic_investable` | 0.03403238580301296 |
| `ic_std_investable` | 0.04853910648842009 |
| `rank_icir_investable` | 0.7011333389734321 |
| `ic_t_investable` | 4.794049068367729 |
| `ic_p_investable` | 5.443385640464701e-06 |
| `ic_retention` | 1.0171687408926813 |
| `neutral_ic` | 0.033161815796788195 |
| `neutral_ic_t` | 5.27833827294804 |
| `neutral_ic_p` | 9.145698477853206e-07 |
| `neutral_ic_retention` | 0.9744193659749917 |
| `n_trials` | 199 |
| `max_gold_signal_corr` | 0.29614259962392186 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'price_range_12m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `pretax_yield_change_12m` | value | 0.687 | 63 |
| `net_margin_change_6m` | earnings | 0.676 | 63 |
| `earnings_yield_change_12m` | value | 0.643 | 63 |
| `enterprise_earnings_yield_change_12m` | value | 0.611 | 63 |
| `pretax_income_growth_12m` | earnings | 0.605 | 63 |
| `net_income_growth_12m` | earnings | 0.572 | 63 |
| `operating_yield_change_12m` | value | 0.520 | 63 |
| `net_profit_margin_change_12m` | earnings | 0.506 | 63 |
| `sue` | earnings | 0.496 | 63 |
| `earnings_change_to_assets` | earnings | 0.486 | 63 |
| `operating_margin_change_6m` | earnings | 0.485 | 63 |
| `pretax_income_growth_acceleration_12m` | earnings | 0.471 | 51 |
| `operating_income_growth_12m` | earnings | 0.451 | 63 |
| `net_income_growth_acceleration_12m` | earnings | 0.448 | 51 |
| `retained_earnings_growth_acceleration_12m` | quality | 0.448 | 63 |

## Expected relationship and data notes

- Expected relationship: 가치 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.
- Data notes: PIT 재무 분자와 동시점 양의 market_cap 또는 enterprise value, 정확한 달력 시차만 사용한다.
