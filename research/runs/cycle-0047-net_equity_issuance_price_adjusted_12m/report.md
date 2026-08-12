# cycle-0047-net_equity_issuance_price_adjusted_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260808-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `01ee73e28cd8f170`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_equity_issuance_price_adjusted_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

시가총액을 배당을 포함하지 않는 분할조정 가격으로 나눈 주식수 기반치의 정확한 12개월 증가율이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

경영자는 주가가 내재가치보다 높거나 외부자금 수요가 클 때 주식을 발행할 유인이 있다. 시장이 이 발행 결정을 늦게 해석하면 발행기업의 상대가격이 이후 조정될 수 있다.

## Pre-registered falsification

무결성·커버리지·IC·Rank ICIR·기간 강건성·중립화·다중검정 또는 정식 confirmation 기준을 통과하지 못하면 가설을 기각한다.

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
| T2.1 | 전체 IC 최소요건 | Y | 0.050313296074162565 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.052449891048064454 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.0068115459732727 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3259263264604425 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.02428669629368504 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.050313296074162565 |
| `ic_t_full` | 6.974497597422122 |
| `ic_p_full` | 1.2815857356956732e-09 |
| `ic_investable` | 0.052449891048064454 |
| `ic_std_investable` | 0.05209504326587929 |
| `rank_icir_investable` | 1.0068115459732727 |
| `ic_t_investable` | 7.813018915456071 |
| `ic_p_investable` | 4.614757343573604e-11 |
| `ic_retention` | 1.0424658120341095 |
| `months` | 50 |
| `turnover` | 144.56441233719679 |
| `gross` | 1.0401407994669494 |
| `cost` | 0.7073485512581505 |
| `net` | 0.3327922482087982 |
| `net_ir` | 0.07768305509036884 |
| `hac_t` | 0.17572933997380866 |
| `hac_pvalue` | 0.4306154013285269 |
| `missing_return_rate` | 0.0009813542688910696 |
| `neutral_ic` | 0.02428669629368504 |
| `neutral_ic_t` | 4.096489058211081 |
| `neutral_ic_p` | 6.282145857344465e-05 |
| `neutral_ic_retention` | 0.4630456957752115 |
| `n_trials` | 6 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_equity_issuance_12m` | other | 0.728 | 63 |
| `retained_earnings_to_assets` | quality | 0.400 | 63 |
| `dividend_yield_ttm` | value | 0.320 | 63 |
| `quality_stability` | quality | 0.319 | 63 |
| `defensive_value` | value | 0.316 | 63 |
| `realized_volatility_252d` | other | 0.298 | 63 |
| `value_bp` | value | 0.282 | 63 |
| `solvent_value` | value | 0.278 | 63 |
| `value_ep` | value | 0.273 | 63 |
| `paid_in_capital_ratio` | quality | 0.267 | 63 |
| `downside_vol_12m` | other | 0.262 | 63 |
| `profitable_small_value` | quality | 0.256 | 63 |
| `net_roa` | quality | 0.255 | 63 |
| `value_sp` | value | 0.250 | 63 |
| `qual_roe` | quality | 0.241 | 63 |

## Expected relationship and data notes

- Expected relationship: 기업 확장과 자금조달이 함께 나타날 수 있어 asset_growth_12m과 일부 관계를 예상하지만, 가격 모멘텀과 배당수익을 제거하므로 완전한 중복은 아닐 것으로 예상한다.
- Data notes: Silver PIT market_cap과 분할조정 가격 adj_close를 사용한다. 기존 net_equity_issuance_12m은 배당 포함 total-return을 분모로 사용해 배당을 발행 감소처럼 섞으므로 보존하되 재사용하지 않는다. 정확히 12개월 전 관측이 없으면 결측이다.
