# cycle-0051-dividend_event_frequency_ttm

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260809-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `51a69f3cd5826f8b`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/dividend_event_frequency_ttm.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

신호시점에 알려진 최근 12개월 canonical 현금배당 사건 수가 많은 종목은 적은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

반복적인 현금배당은 배당액의 크기와 별개로 경영진의 현금흐름 규율과 주주환원 지속성을 보여준다. 이 질적 차이가 가격에 천천히 반영되면 배당 실시 빈도가 미래수익을 예측할 수 있다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성, 커버리지, 전체·투자가능 IC와 Rank ICIR, 기간·중립화 강건성, 다중검정, Gold SQL parity 또는 일회성 OOS 기준을 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 1.0 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 1.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | Y | 0.05247288351029927 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.053738722117767 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7554634924301166 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2908928786655836 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.027009391385103963 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05247288351029927 |
| `ic_t_full` | 8.738174170539734 |
| `ic_p_full` | 1.1935950169555585e-12 |
| `ic_investable` | 0.053738722117767 |
| `ic_std_investable` | 0.07113344675982215 |
| `rank_icir_investable` | 0.7554634924301166 |
| `ic_t_investable` | 8.625129910775309 |
| `ic_p_investable` | 1.8616627652261893e-12 |
| `ic_retention` | 1.0241236715573154 |
| `months` | 53 |
| `turnover` | 119.48309857910775 |
| `gross` | -0.12965468280264186 |
| `cost` | 0.580011227579252 |
| `net` | -0.7096659103818941 |
| `net_ir` | -0.1421215208844162 |
| `hac_t` | -0.31385069524451203 |
| `hac_pvalue` | 0.6225549683394848 |
| `missing_return_rate` | 0.0006673209028459274 |
| `neutral_ic` | 0.027009391385103963 |
| `neutral_ic_t` | 3.7972479393215854 |
| `neutral_ic_p` | 0.00016967993835537864 |
| `neutral_ic_retention` | 0.5026057621153251 |
| `n_trials` | 10 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `dividend_yield_ttm` | value | 0.917 | 63 |
| `net_equity_issuance_12m` | other | 0.705 | 63 |
| `retained_earnings_to_assets` | quality | 0.574 | 63 |
| `paid_in_capital_ratio` | quality | 0.501 | 63 |
| `value_ep` | value | 0.498 | 63 |
| `operating_roa` | quality | 0.474 | 63 |
| `operating_income_to_liabilities` | quality | 0.467 | 63 |
| `quality_stability` | quality | 0.464 | 63 |
| `net_roa` | quality | 0.457 | 63 |
| `operating_return_on_capital_employed` | quality | 0.457 | 63 |
| `qual_roe` | quality | 0.448 | 63 |
| `qual_opm` | quality | 0.440 | 63 |
| `net_profit_margin` | quality | 0.425 | 63 |
| `realized_volatility_252d` | other | 0.382 | 63 |
| `defensive_value` | value | 0.368 | 63 |

## Expected relationship and data notes

- Expected relationship: dividend_yield_ttm과 양의 관계를 예상하지만 현금배당의 금액이나 가격을 사용하지 않고 실시 횟수만 측정한다. 관계가 너무 높아 사실상 같은 신호라면 새 정보로 인정하지 않는다.
- Data notes: 현재 CERTIFIED total-return run에 결합된 canonical DART ISSUER 현금배당 사건만 센다. announcement_date 다음 날과 applied_trade_date 중 늦은 날부터 보이게 한 PIT 사건을 신호월 말 기준 최근 12개월로 집계하며, 사건이 없는 인증기간 월은 0이다.
