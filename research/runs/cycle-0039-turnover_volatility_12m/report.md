# cycle-0039-turnover_volatility_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-002`
- OOS: **SEALED**
- Definition hash: `07f156b1d7953440`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/turnover_volatility_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 log(ADV20/market_cap) 12개월 변동성이 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

거래활동의 급격한 증감은 일시적 관심, 투기 수요와 의견 불일치를 반영할 수 있다. 이런 수요 충격이 가격을 펀더멘털보다 높인 뒤 정상화되면 활동이 안정적인 종목의 기대수익이 상대적으로 높을 수 있다.

## Pre-registered falsification

사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9681364732726366 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9600642340228344 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.06487158481686311 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06560528353626979 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6138686431023062 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.43180897466923474 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.02667298939981132 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.06487158481686311 |
| `ic_t_full` | 6.142417814572635 |
| `ic_p_full` | 8.50626309600777e-09 |
| `ic_investable` | 0.06560528353626979 |
| `ic_std_investable` | 0.1068718597593136 |
| `rank_icir_investable` | 0.6138686431023062 |
| `ic_t_investable` | 6.0983022064718915 |
| `ic_p_investable` | 1.0397663560959113e-08 |
| `ic_retention` | 1.0113100168814737 |
| `months` | 86 |
| `turnover` | 130.42104635402123 |
| `gross` | 1.543379129662322 |
| `cost` | 0.5945121686756575 |
| `net` | 0.9488669609866645 |
| `net_ir` | 0.15027627793080506 |
| `hac_t` | 0.4053396813699657 |
| `hac_pvalue` | 0.3431231325881973 |
| `missing_return_rate` | 0.00034848872058174384 |
| `neutral_ic` | 0.02667298939981132 |
| `neutral_ic_t` | 4.574296908490673 |
| `neutral_ic_p` | 6.930512828997766e-06 |
| `neutral_ic_retention` | 0.4065677025092833 |
| `n_trials` | 51 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `size` | size | -0.484 | 101 |
| `low_vol_12m` | other | 0.372 | 101 |
| `trading_turnover_20d` | other | 0.358 | 101 |
| `max_monthly_return_12m` | other | 0.357 | 101 |
| `paid_in_capital_ratio` | quality | 0.321 | 101 |
| `quality_stability` | quality | 0.281 | 101 |
| `return_skewness_24m` | other | 0.276 | 101 |
| `small_value` | value | -0.265 | 101 |
| `downside_vol_12m` | other | 0.257 | 101 |
| `operating_roa` | quality | 0.256 | 101 |
| `qual_opm` | quality | 0.255 | 101 |
| `operating_return_on_capital_employed` | quality | 0.251 | 101 |
| `qual_roe` | quality | 0.239 | 101 |
| `value_ep` | value | 0.230 | 101 |
| `earnings_confirmed_small_value` | earnings | -0.230 | 101 |

## Expected relationship and data notes

- Expected relationship: trading_turnover_20d의 거래활동 수준 및 변동성 계열과 일부 관계는 가능하지만, 이 후보는 수준이 아니라 12개월 동안의 log turnover 불안정성만 측정한다.
- Data notes: Silver의 양의 ADV20과 market_cap만 사용한다. 12개월 창에서 최소 9개 관측과 정확한 달력 연속성을 요구한다. 체결가격 충격이나 Amihud 비율을 사용하지 않으며 최초 11개월은 결측이다.
