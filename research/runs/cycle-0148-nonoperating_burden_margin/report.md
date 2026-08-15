# cycle-0148-nonoperating_burden_margin

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-014` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `3334a4ac95f88b68`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/nonoperating_burden_margin.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

(영업이익-순이익)/TTM 매출이 높은 종목의 이후 수익률 순위가 낮을 것이다.

## Mechanism

금융비용·영업외손실·세금이 매출의 큰 몫을 소모하면 본업 이익이 주주가치로 전환되지 않는다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 이익전환 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9180734134420486 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9016683328034891 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.03280366580904719 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.03407936155934626 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.8202553089743653 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3033028556322382 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.025112661863636854 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.3271458764073523 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.03280366580904719 |
| `ic_t_full` | 5.867120900279799 |
| `ic_p_full` | 9.761438709186311e-08 |
| `ic_investable` | 0.03407936155934626 |
| `ic_std_investable` | 0.04154726118378749 |
| `rank_icir_investable` | 0.8202553089743653 |
| `ic_t_investable` | 6.562661838590125 |
| `ic_p_investable` | 6.502486676212476e-09 |
| `ic_retention` | 1.038888816808615 |
| `neutral_ic` | 0.025112661863636854 |
| `neutral_ic_t` | 4.818139885015597 |
| `neutral_ic_p` | 4.98851050068008e-06 |
| `neutral_ic_retention` | 0.7368876855250157 |
| `n_trials` | 159 |
| `max_gold_signal_corr` | 0.3271458764073523 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'price_range_12m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `nonoperating_burden_to_assets` | quality | 0.939 | 63 |
| `posttax_income_conversion` | quality | 0.380 | 63 |
| `net_profit_margin` | quality | 0.329 | 63 |
| `net_income_to_liabilities` | quality | 0.326 | 63 |
| `value_ep` | value | 0.317 | 63 |
| `net_income_to_noncurrent_assets` | quality | 0.304 | 63 |
| `net_roa` | quality | 0.302 | 63 |
| `net_income_to_current_assets` | quality | 0.295 | 63 |
| `retained_earnings_yield` | value | 0.289 | 63 |
| `net_profit_margin_change_12m` | earnings | 0.286 | 63 |
| `solvent_value` | value | 0.284 | 63 |
| `retained_earnings_to_assets` | quality | 0.276 | 63 |
| `pretax_income_to_liabilities` | quality | 0.276 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.275 | 63 |
| `qual_roe` | quality | 0.274 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: nonoperating_burden_to_assets — 차이: 자산이 아니라 매출 단위당 영업외 부담을 측정한다.
- Data notes: DART available_date PIT 영업이익·순이익과 양의 TTM 매출만 사용한다.
