# cycle-0020-return_skewness_24m

- Verdict: **PROVISIONAL**
- Definition hash: `ae94a83fc4d5f034`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/return_skewness_24m.py`

## Hypothesis

Silver PIT 총수익지수로 계산한 최근 24개월 월수익률 왜도가 낮은 종목은 양의 왜도가 큰 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

일부 투자자는 낮은 확률의 큰 상승을 제공하는 복권형 주식에 높은 가격을 지불할 수 있다. 과거 수익률 분포의 큰 양의 꼬리는 이러한 선호의 관측 가능한 대리변수이며, 과대수요가 미래 기대수익률을 낮출 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, 고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 T0~T5 게이트를 순차 적용했다. 앞 단계 hard fail 이후의 검사는 실행하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9795704971618369 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9738396983765996 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.05593960936973922 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06486846807842303 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.1410118273902925 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 8.149923166285155e-18 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.29336440234988 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.039190104308002044 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.08429165514545568 | IC>=0.02 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 9.304495614842218e-17 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.2632689418626263 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.05593960936973922 |
| `ic_t_full` | 11.030840261403872 |
| `ic_p_full` | 9.589973547190766e-17 |
| `ic_investable` | 0.06486846807842303 |
| `ic_std_investable` | 0.05685170523323089 |
| `rank_icir_investable` | 1.1410118273902925 |
| `ic_t_investable` | 11.680578506445238 |
| `ic_p_investable` | 8.149923166285155e-18 |
| `ic_retention` | 1.1596160361018524 |
| `months` | 43 |
| `turnover` | 281.03923835981755 |
| `gross` | 2.9302507607255466 |
| `cost` | 1.3518150220767429 |
| `net` | 1.578435738648804 |
| `net_ir` | 0.4085423466520082 |
| `hac_t` | 0.779680201160313 |
| `hac_pvalue` | 0.21997539577318237 |
| `missing_return_rate` | 0.0023621624523541096 |
| `neutral_ic` | 0.039190104308002044 |
| `neutral_ic_t` | 8.331750247831668 |
| `neutral_ic_p` | 4.197700448601657e-12 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.08429165514545568 |
| `oos_ic_t` | 8.334099433131934 |
| `oos_ic_p` | 4.977143824075616e-10 |
| `n_trials` | 32 |
| `fdr_qvalue` | 9.304495614842218e-17 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.485 | 102 |
| `defensive_value` | value | 0.377 | 102 |
| `quality_stability` | quality | 0.277 | 102 |
| `defensive_small_value` | value | 0.272 | 102 |
| `value_bp` | value | 0.173 | 102 |
| `downside_vol_12m` | other | 0.155 | 102 |
| `value_ep` | value | 0.151 | 102 |
| `value_sp` | value | 0.147 | 102 |
| `profitable_small_value` | quality | 0.140 | 102 |
| `qual_opm` | quality | 0.136 | 102 |
| `mom_12_1` | momentum | -0.135 | 102 |
| `operating_roa` | quality | 0.133 | 102 |
| `qual_roe` | quality | 0.130 | 102 |
| `solvent_value` | value | 0.129 | 102 |
| `size` | size | -0.125 | 102 |

## Expected relationship and data notes

- Expected relationship: 양의 왜도 종목이 고변동인 경우가 많아 low_vol_12m 및 downside_vol_12m과 양의 관계를 예상한다. 그러나 분산이 아니라 분포의 비대칭을 측정하므로 완전한 중복은 아니며, 회계 품질·가치 팩터와의 관계는 낮을 것으로 예상한다.
- Data notes: Silver total_return_close에 매핑된 return_close로 월수익률을 계산한다. 24개월 창에서 최소 18개 관측을 사전 고정하며, 이력이 부족하거나 수익률 분산이 없어 왜도가 정의되지 않는 관측은 결측으로 둔다. 일별 왜도가 아닌 월별 왜도라는 한계가 있다.
