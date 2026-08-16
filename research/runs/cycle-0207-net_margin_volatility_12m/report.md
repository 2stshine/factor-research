# cycle-0207-net_margin_volatility_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-005` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `229f9382dbbdee96`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_margin_volatility_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

net_margin_volatility 신호가 낮은 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.

## Mechanism

PIT 이익·운전자본의 수준 변화 또는 변동성을 이용해 단순 수익성 수준과 다른 이익의 질을 측정한다.

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
| T1.1 | 전체 커버리지 | Y | 0.8839978889237335 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8320115395529212 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05518742872902117 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05691895850345122 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.9481451769976467 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.30153331273521566 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.048331997259941174 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.47712489226246146 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05518742872902117 |
| `ic_t_full` | 6.57359704920931 |
| `ic_p_full` | 6.228941889317095e-09 |
| `ic_investable` | 0.05691895850345122 |
| `ic_std_investable` | 0.06003190216469613 |
| `rank_icir_investable` | 0.9481451769976467 |
| `ic_t_investable` | 7.724804681792384 |
| `ic_p_investable` | 6.547667632272898e-11 |
| `ic_retention` | 1.0313754384704554 |
| `neutral_ic` | 0.048331997259941174 |
| `neutral_ic_t` | 7.36872543228543 |
| `neutral_ic_p` | 2.688625414862942e-10 |
| `neutral_ic_retention` | 0.849137063128283 |
| `n_trials` | 219 |
| `max_gold_signal_corr` | 0.47712489226246146 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'enterprise_sales_yield_change_6m': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'pretax_yield_change_6m': 62, 'price_range_12m': 62, 'realized_daily_volatility_change_24m': 62, 'realized_daily_volatility_instability_6m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_margin_volatility_36m` | quality | 0.824 | 52 |
| `pretax_margin_volatility_36m` | quality | 0.806 | 52 |
| `operating_margin_volatility_12m` | earnings | 0.769 | 63 |
| `net_roa_volatility_36m` | quality | 0.684 | 52 |
| `pretax_roa_volatility_36m` | quality | 0.652 | 52 |
| `revenue_to_capital_stock` | quality | 0.528 | 63 |
| `asset_turnover` | quality | 0.518 | 63 |
| `operating_earnings_yield` | value | 0.477 | 63 |
| `retained_earnings_to_assets_volatility_12m` | earnings | 0.477 | 63 |
| `quality_stability` | quality | 0.475 | 63 |
| `value_sp` | value | 0.475 | 63 |
| `operating_roa_volatility_36m` | quality | 0.463 | 52 |
| `current_asset_turnover` | quality | 0.458 | 63 |
| `revenue_to_current_assets` | quality | 0.458 | 63 |
| `operating_income_to_capital_stock` | quality | 0.458 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 수익성 또는 자산성장과 일부 관계가 예상되지만 측정 대상이 발생액·안정성이다.
- Data notes: DART available_date PIT 재무값과 고정 36개월 이하 달력창만 사용한다.
