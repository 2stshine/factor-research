# cycle-0077-pretax_income_to_liabilities

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-004` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `47ef014a02b341ff`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_income_to_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT pretax_income_ttm/total_liabilities가 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

세금 전 이익이 부채 청구권에 비해 크면 금리·세율 변화 전의 기본 상환여력이 강하다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9341665455602384 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9173351089716262 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.051145192654251284 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.052870470229334186 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7157631999545833 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2569395931807388 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.04471962594683492 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6030981549419662 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.051145192654251284 |
| `ic_t_full` | 6.843102550141026 |
| `ic_p_full` | 2.1540161387849996e-09 |
| `ic_investable` | 0.052870470229334186 |
| `ic_std_investable` | 0.07386586825459723 |
| `rank_icir_investable` | 0.7157631999545833 |
| `ic_t_investable` | 6.743842601023562 |
| `ic_p_investable` | 3.1866566439872154e-09 |
| `ic_retention` | 1.033732937262472 |
| `neutral_ic` | 0.04471962594683492 |
| `neutral_ic_t` | 5.88996906124727 |
| `neutral_ic_p` | 8.93888666182792e-08 |
| `neutral_ic_retention` | 0.8458337093060897 |
| `n_trials` | 89 |
| `max_gold_signal_corr` | 0.6030981549419662 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_income_to_liabilities` | quality | 0.979 | 63 |
| `pretax_roa` | quality | 0.956 | 63 |
| `pretax_profit_margin` | quality | 0.939 | 63 |
| `net_roa` | quality | 0.934 | 63 |
| `net_profit_margin` | quality | 0.921 | 63 |
| `operating_income_to_liabilities` | quality | 0.880 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.868 | 63 |
| `qual_roe` | quality | 0.858 | 63 |
| `operating_roa` | quality | 0.815 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.801 | 63 |
| `qual_opm` | quality | 0.800 | 63 |
| `value_ep` | value | 0.772 | 63 |
| `operating_return_on_capital_employed` | quality | 0.750 | 63 |
| `quality_stability` | quality | 0.724 | 63 |
| `retained_earnings_growth_12m` | quality | 0.667 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: operating_income_to_liabilities — 차이: 영업이익이 아니라 금융·영업외손익까지 반영한 세전 커버리지다.
- Data notes: DART available_date PIT TTM 세전이익과 양의 총부채를 사용한다.
