# cycle-0046-max_daily_return_1m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260808-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `e29c3da27f06a3ba`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/max_daily_return_1m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

직전 월의 최대 일별 총수익률이 낮은 종목은 최대 일수익률이 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

일부 투자자는 낮은 확률의 큰 보상을 선호해 최근 극단적 상승을 보인 주식에 과도한 가격을 지불할 수 있고, 이 고평가는 이후 평균수익을 낮춘다.

## Pre-registered falsification

무결성·IC·Rank ICIR·기간 강건성·다중검정·confirmation을 통과하지 못하거나 다른 저위험 신호와 중복되면 독립적인 복권수요 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9995288968588059 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9987042240996805 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | Y | 0.09485458066536168 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.10036212328718574 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.1552844541093328 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3269237828740936 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.030495421463869705 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.09485458066536168 |
| `ic_t_full` | 9.629460236288592 |
| `ic_p_full` | 3.702838299382695e-14 |
| `ic_investable` | 0.10036212328718574 |
| `ic_std_investable` | 0.08687221829238581 |
| `rank_icir_investable` | 1.1552844541093328 |
| `ic_t_investable` | 11.517481675414196 |
| `ic_p_investable` | 3.046956479647866e-17 |
| `ic_retention` | 1.0580630116457335 |
| `months` | 62 |
| `turnover` | 709.121780939851 |
| `gross` | 1.4426111903925187 |
| `cost` | 3.383566658593711 |
| `net` | -1.9409554682011931 |
| `net_ir` | -0.3647005503009014 |
| `hac_t` | -1.0284504230473441 |
| `hac_pvalue` | 0.8461005667392466 |
| `missing_return_rate` | 0.0 |
| `neutral_ic` | 0.030495421463869705 |
| `neutral_ic_t` | 5.477089242951239 |
| `neutral_ic_p` | 4.328967612796475e-07 |
| `neutral_ic_retention` | 0.3038538889477976 |
| `n_trials` | 5 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `trading_turnover_20d` | other | 0.669 | 63 |
| `realized_volatility_252d` | other | 0.518 | 63 |
| `low_vol_12m` | other | 0.456 | 63 |
| `defensive_value` | value | 0.446 | 63 |
| `max_monthly_return_12m` | other | 0.417 | 63 |
| `rev_1m` | momentum | 0.391 | 63 |
| `defensive_small_value` | value | 0.371 | 63 |
| `quality_stability` | quality | 0.304 | 63 |
| `value_bp` | value | 0.300 | 63 |
| `downside_vol_12m` | other | 0.278 | 63 |
| `dividend_yield_ttm` | value | 0.262 | 63 |
| `solvent_value` | value | 0.258 | 63 |
| `profitable_small_value` | quality | 0.252 | 63 |
| `net_equity_issuance_12m` | other | 0.252 | 63 |
| `amihud_illiquidity_1m` | other | 0.239 | 63 |

## Expected relationship and data notes

- Expected relationship: return_skewness_24m, return_kurtosis_24m 및 저변동성 신호와 관계가 예상되지만 최근 한 달의 단일 최대 일수익에만 반응한다.
- Data notes: 인증된 Silver total_return_close의 월중 일별 수익률 최대값이다. 기존 max_monthly_return_12m은 12개월 최대 월수익률 proxy이므로 보존하고 이 정의와 구분한다. 월중 최소 10개 유효 관측이 필요하다.
