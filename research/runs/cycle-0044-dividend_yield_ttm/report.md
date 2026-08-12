# cycle-0044-dividend_yield_ttm

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260808-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `d9afc1c471d113ea`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/dividend_yield_ttm.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

신호시점에 알려져 있고 실제 가격에 적용된 최근 12개월 주당 현금배당 합계를 월말 분할조정 가격으로 나눈 값이 높은 종목은 낮은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

지속적인 현금배당은 주주환원과 현금창출의 관측 가능한 신호이며, 배당 대비 가격이 낮은 기업에는 가치·환원 프리미엄이 남을 수 있다.

## Pre-registered falsification

배당 피드 커버리지·무결성, 전체·투자가능 IC, Rank ICIR, 기간 강건성, 기존 가치 신호와의 중복 및 정식 confirmation 기준을 통과하지 못하면 가설을 기각한다.

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
| T2.1 | 전체 IC 최소요건 | Y | 0.06521537611489664 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06696557008836772 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7926094761897065 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3059583518156893 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03225873761941463 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.06521537611489664 |
| `ic_t_full` | 9.155026119324738 |
| `ic_p_full` | 2.334099993812317e-13 |
| `ic_investable` | 0.06696557008836772 |
| `ic_std_investable` | 0.08448747094255014 |
| `rank_icir_investable` | 0.7926094761897065 |
| `ic_t_investable` | 8.7880672684171 |
| `ic_p_investable` | 9.812089123326397e-13 |
| `ic_retention` | 1.0268371368492544 |
| `months` | 51 |
| `turnover` | 199.22097627735766 |
| `gross` | 2.2727243753606405 |
| `cost` | 0.957762974716524 |
| `net` | 1.3149614006441164 |
| `net_ir` | 0.23156722947235855 |
| `hac_t` | 0.5879002505851616 |
| `hac_pvalue` | 0.27962265739245534 |
| `missing_return_rate` | 0.000745829244357213 |
| `neutral_ic` | 0.03225873761941463 |
| `neutral_ic_t` | 4.063117020262228 |
| `neutral_ic_p` | 7.031108448248439e-05 |
| `neutral_ic_retention` | 0.48172124237643354 |
| `n_trials` | 3 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_equity_issuance_12m` | other | 0.778 | 63 |
| `retained_earnings_to_assets` | quality | 0.552 | 63 |
| `value_ep` | value | 0.524 | 63 |
| `quality_stability` | quality | 0.485 | 63 |
| `defensive_value` | value | 0.471 | 63 |
| `realized_volatility_252d` | other | 0.458 | 63 |
| `paid_in_capital_ratio` | quality | 0.458 | 63 |
| `operating_roa` | quality | 0.438 | 63 |
| `net_roa` | quality | 0.430 | 63 |
| `operating_return_on_capital_employed` | quality | 0.419 | 63 |
| `qual_roe` | quality | 0.415 | 63 |
| `qual_opm` | quality | 0.401 | 63 |
| `value_bp` | value | 0.396 | 63 |
| `net_profit_margin` | quality | 0.392 | 63 |
| `profitable_small_value` | quality | 0.375 | 63 |

## Expected relationship and data notes

- Expected relationship: value_bp·value_ep와 양의 관계를 예상하지만 공시 장부가나 이익이 아니라 실제 현금 주주환원을 사용하므로 완전한 중복은 아닐 것으로 예상한다.
- Data notes: 현재 CERTIFIED total-return run에 결합된 canonical DART ISSUER 현금배당만 사용한다. announcement_date 다음 날과 applied_trade_date 중 늦은 날부터 보이게 해 PIT를 지키며, adjusted_cash_amount와 adj_close를 같은 분할조정 기준으로 나눈다. 세전 gross 배당이고 적용 가능한 사건이 없는 인증기간 월은 0이다.
