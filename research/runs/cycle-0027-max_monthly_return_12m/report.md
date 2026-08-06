# cycle-0027-max_monthly_return_12m

- Verdict: **PROVISIONAL**
- Definition hash: `c0ea1874070bbd0b`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/max_monthly_return_12m.py`

## Hypothesis

Silver PIT 총수익지수로 계산한 최근 12개월 최대 월수익률이 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

일부 투자자가 작은 확률의 큰 이익을 과도하게 선호하면 최근 극단적 급등을 경험한 종목에 수요가 몰려 가격이 펀더멘털보다 높아질 수 있다. 이 복권형 수요가 되돌려질 때 높은 과거 최대수익률은 낮은 미래 횡단면 수익률로 이어질 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9999736393511766 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 1.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.07903944711756784 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0851754730265293 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.9429539570763563 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 7.19147517886925e-17 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.30968051537716557 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.03884733163039134 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.10032011747545135 | IC>=0.02 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 1.1944555132903251e-15 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6182442664579829 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.07903944711756784 |
| `ic_t_full` | 9.085654926263109 |
| `ic_p_full` | 2.0048895550109826e-13 |
| `ic_investable` | 0.0851754730265293 |
| `ic_std_investable` | 0.09032834783430699 |
| `rank_icir_investable` | 0.9429539570763563 |
| `ic_t_investable` | 11.106034819145432 |
| `ic_p_investable` | 7.19147517886925e-17 |
| `ic_retention` | 1.077632449779594 |
| `months` | 65 |
| `turnover` | 357.3824424388197 |
| `gross` | 1.273389014274341 |
| `cost` | 1.7031561873819374 |
| `net` | -0.42976717310759754 |
| `net_ir` | -0.0736265558672009 |
| `hac_t` | -0.20733517049781938 |
| `hac_pvalue` | 0.5817967941346593 |
| `missing_return_rate` | 0.0 |
| `neutral_ic` | 0.03884733163039134 |
| `neutral_ic_t` | 6.083265448954219 |
| `neutral_ic_p` | 3.64802982369228e-08 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.10032011747545135 |
| `oos_ic_t` | 7.7515197488383025 |
| `oos_ic_p` | 2.558435922984317e-09 |
| `n_trials` | 39 |
| `fdr_qvalue` | 1.1944555132903251e-15 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.918 | 102 |
| `defensive_value` | value | 0.744 | 102 |
| `defensive_small_value` | value | 0.600 | 102 |
| `return_skewness_24m` | other | 0.566 | 102 |
| `quality_stability` | quality | 0.480 | 102 |
| `downside_vol_12m` | other | 0.430 | 102 |
| `mom_12_1` | momentum | -0.424 | 102 |
| `value_bp` | value | 0.343 | 102 |
| `value_sp` | value | 0.266 | 102 |
| `profitable_small_value` | quality | 0.264 | 102 |
| `solvent_value` | value | 0.259 | 102 |
| `value_ep` | value | 0.231 | 102 |
| `net_equity_issuance_12m` | other | 0.204 | 102 |
| `retained_earnings_to_assets` | quality | 0.199 | 102 |
| `operating_roa_volatility_36m` | quality | 0.185 | 91 |

## Expected relationship and data notes

- Expected relationship: 극단 수익의 비대칭을 측정하는 return_skewness_24m와 양의 관계, 변동성 계열과 양의 관계가 예상된다. 다만 분포 전체가 아니라 단 하나의 최대 월수익만 사용하므로 완전한 중복은 아닐 것으로 예상한다.
- Data notes: Silver total_return_close에 매핑된 return_close로 월수익률을 계산한다. 최근 12개월 중 최소 9개월이 있을 때 최대값을 사용한다. 일중 최대수익률이 아니라 월 단위 근사이며, 극단값을 사후 절단하거나 윈도 길이를 바꾸지 않는다.
