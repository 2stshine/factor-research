# cycle-0127-price_range_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `b564b360f33b0dca`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/price_range_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

12개월 최고/최저 분할조정가격 비율이 큰 종목의 이후 순위가 낮을 것이다.

## Mechanism

넓은 거래범위는 가치 불확실성과 상태의존적 투자자 수요를 반영한다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 저위험 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9998317258048478 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9994962216624685 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.07331140377766435 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.07818468683458767 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5791078064876594 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.38482985581086254 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.02883806149273056 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6430595200904468 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.07331140377766435 |
| `ic_t_full` | 5.763392980894235 |
| `ic_p_full` | 1.4542483776663537e-07 |
| `ic_investable` | 0.07818468683458767 |
| `ic_std_investable` | 0.1350088635633921 |
| `rank_icir_investable` | 0.5791078064876594 |
| `ic_t_investable` | 5.965894855176146 |
| `ic_p_investable` | 6.668136937496363e-08 |
| `ic_retention` | 1.0664737381336034 |
| `neutral_ic` | 0.02883806149273056 |
| `neutral_ic_t` | 2.7657305747176077 |
| `neutral_ic_p` | 0.003752197681563657 |
| `neutral_ic_retention` | 0.36884539236874014 |
| `n_trials` | 139 |
| `max_gold_signal_corr` | 0.6430595200904468 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.757 | 63 |
| `downside_vol_12m` | other | 0.708 | 63 |
| `realized_volatility_252d` | other | 0.679 | 63 |
| `idiosyncratic_volatility_24m` | other | 0.644 | 63 |
| `max_monthly_return_12m` | other | 0.633 | 63 |
| `defensive_value` | value | 0.608 | 63 |
| `high_52w_price_proximity` | momentum | 0.518 | 63 |
| `high_12m_proximity` | momentum | 0.502 | 63 |
| `quality_stability` | quality | 0.501 | 63 |
| `defensive_small_value` | value | 0.476 | 63 |
| `trading_value_volatility_12m` | other | 0.469 | 63 |
| `trading_turnover_20d` | other | 0.469 | 63 |
| `adv20_to_book_equity` | other | 0.466 | 63 |
| `max_daily_return_1m` | other | 0.418 | 63 |
| `price_recovery_12m` | momentum | -0.370 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: realized_volatility_252d — 차이: 일별 분산이 아니라 연간 극값 범위를 측정한다.
- Data notes: 분할조정 adj_close의 정확한 12개 달력월만 사용한다.
