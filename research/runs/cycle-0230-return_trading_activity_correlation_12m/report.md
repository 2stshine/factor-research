# cycle-0230-return_trading_activity_correlation_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260921-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `e0e91e564995c7a2`
- Data cutoff / ruleset: `2023-06-30` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/return_trading_activity_correlation_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

직전 12개 월수익률과 각 월말 log(ADV20)의 Pearson 상관이 낮을수록 다음 달 총수익률 순위가 높다.

## Mechanism

가격 상승기에 상대적으로 큰 거래대금이 동반되는 특성에 비정보성 수요 압력이 섞이고 그 압력이 완화되면 이후 상대수익이 낮을 수 있다는 독립 월별 가설이다. campbell_grossman_wang_1993_volume의 거래량·가격압력 구별 논리를 참고했지만, 일별 거래량과 수익률 자기상관 연구의 재현도, 해당 논문이 검증한 월별 부호도 아니다.

## Pre-registered falsification

사전 고정한 음의 방향이 Discovery 및 campaign 검사를 통과하지 못하면 승격하지 않는다. 크기·유동성·변동성 노출 통제 뒤 관계가 사라지거나 높은 동행성의 이후 수익이 높으면 단순 가격압력 해석은 약해진다. 일시적 수요의 직접 관측이 없으므로 원인 확정은 불가능하다.

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
| T1.1 | 전체 커버리지 | Y | 0.9535422179456339 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9419719163551874 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.04867968323084295 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04867968323084295 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6959837163864159 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.34409292755397114 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.017337837659265675 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.45683574674812416 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.04867968323084295 |
| `ic_t_full` | 6.769057781069329 |
| `ic_p_full` | 2.694483713813144e-09 |
| `ic_investable` | 0.04867968323084295 |
| `ic_std_investable` | 0.06994371001032959 |
| `rank_icir_investable` | 0.6959837163864159 |
| `ic_t_investable` | 6.769057781069329 |
| `ic_p_investable` | 2.694483713813144e-09 |
| `ic_retention` | 1.0 |
| `neutral_ic` | 0.017337837659265675 |
| `neutral_ic_t` | 3.3549931956872263 |
| `neutral_ic_p` | 0.0006792622494203628 |
| `neutral_ic_retention` | 0.35616167790263265 |
| `n_trials` | 397 |
| `max_gold_signal_corr` | 0.45683574674812416 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 63, 'asset_to_market': 63, 'book_to_market_change_12m': 63, 'book_to_market_change_6m': 63, 'capital_stock_growth_18m': 63, 'capital_stock_to_assets': 63, 'close_position_mean_12m': 63, 'current_asset_turnover': 63, 'current_liabilities_to_sales': 63, 'enterprise_sales_yield_change_6m': 63, 'idiosyncratic_volatility_24m': 63, 'market_cap_instability_24m': 63, 'market_leverage': 63, 'max_daily_return_1m': 63, 'max_daily_return_instability_18m': 63, 'max_daily_return_mean_6m': 63, 'momentum_12_1': 63, 'net_equity_issuance_price_adjusted_12m': 63, 'net_equity_issuance_price_adjusted_36m': 63, 'net_income_to_liabilities': 63, 'net_margin_volatility_12m': 63, 'net_working_capital_yield': 63, 'nonoperating_burden_margin': 63, 'open_close_drift_12m': 63, 'operating_earnings_yield': 63, 'operating_income_to_current_liabilities': 63, 'operating_income_to_liabilities': 63, 'operating_return_on_capital_employed': 63, 'overnight_gap_mean_6m': 63, 'overnight_gap_volatility_12m': 63, 'paid_in_capital_ratio': 63, 'pretax_yield_change_6m': 63, 'price_high_gap_volatility_24m': 63, 'price_range_12m': 63, 'realized_daily_volatility_change_24m': 63, 'realized_daily_volatility_instability_6m': 63, 'realized_volatility_252d': 63, 'retained_earnings_to_assets_volatility_12m': 63, 'retained_earnings_to_equity': 63, 'return_kurtosis_24m': 63, 'return_skewness_12m': 63, 'return_skewness_36m': 63, 'revenue_scale': 63, 'revenue_to_noncurrent_assets': 63, 'share_turnover_change_12m': 63, 'share_turnover_change_6m': 63, 'shares_to_capital_stock': 63, 'trading_turnover_20d': 63, 'turnover_volatility_12m': 63} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `max_monthly_return_12m` | other | 0.481 | 64 |
| `low_vol_12m` | other | 0.404 | 64 |
| `return_gain_loss_ratio_12m` | momentum | -0.378 | 64 |
| `max_daily_return_instability_18m` | quality | 0.372 | 64 |
| `max_daily_return_instability_6m` | quality | 0.370 | 64 |
| `price_trend_efficiency_12m` | momentum | -0.367 | 64 |
| `max_daily_return_mean_6m` | quality | 0.362 | 64 |
| `realized_volatility_252d` | other | 0.354 | 64 |
| `adv_turnover_volatility_6m` | other | 0.349 | 64 |
| `defensive_value` | value | 0.337 | 64 |
| `idiosyncratic_volatility_24m` | other | 0.326 | 64 |
| `trading_turnover_20d` | other | 0.315 | 64 |
| `trading_value_volatility_12m` | other | 0.314 | 64 |
| `trading_value_turnover_volatility_6m` | other | 0.309 | 64 |
| `price_recovery_12m` | momentum | -0.309 | 64 |

## Expected relationship and data notes

- Expected relationship: 거래대금 수준·성장률, log(ADV20/시총)의 변동성과 달리 자기 수익률과 거래활동의 공동 변화를 측정한다. market_return_correlation_12m은 시장수익과의 동조성으로 상대 변수가 다르다. 결과 없는 정의 색인의 가격×거래활동 교차 검색으로 비교했으며 엔진 중복·Gold 상관 검사를 유지한다.
- Data notes: asset_id별 양의 adj_close 13개 연속 월말과 양의 ADV20 12개를 요구한다. ADV20은 최근 20거래일 평균 거래대금이지 주식 수 거래량·월 총량·매수주문 불균형이 아니다. 명목 거래대금에는 가격의 기계적 영향이 있다. 결측·달력 공백·0분산은 NaN이며 보간하지 않는다. 12개월은 검증 전 정한 설계이며 원논문 최적기간이 아니다. 현재 month 신호는 다음 달 수익과 연결한다. 레짐 38축은 동결 보조진단으로만 사용한다. PIT_ASSUMED를 팩터 입력 인증으로 전용하지 않는다. 공개 교훈 balance_sheet_growth_requires_construct_and_distribution_checks의 측정과 메커니즘 구별만 참고했으며 이 연구는 누적 탐색 뒤 과거 표본을 재사용한 연구이고 신규 독립 검증이 아니다.
