# cycle-0012-operating_roa

- Verdict: **PROVISIONAL**
- Definition hash: `0c399c65bc5c8e11`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.1.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_roa.py`

## Hypothesis

Silver PIT의 최근 12개월 영업이익을 총자산으로 나눈 단일 operating ROA가 높은 종목은 이후 수익률 순위도 높을 것이다.

## Mechanism

높은 operating ROA는 기업이 보유 자산에서 핵심 영업이익을 효율적으로 창출한다는 뜻이다. 투자자가 이 수익성의 지속성을 충분히 반영하지 않으면 후속 실적 확인과 함께 점진적으로 재평가된다.

## Pre-registered falsification

전체 및 투자 가능 IC 최소요건, 기간·중립화 강건성, 고정 OOS IC, 다중검정 또는 Gold 신호 직교성 중 하나라도 hard fail이면 operating ROA 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9472743089116566 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9146694999978793 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.04640583216878974 | >=0.02 |
| T2.1 | 전체 IC HAC 유의성 | Y | 2.9690519238632046e-10 | one-sided p<=0.1 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06900144034216944 | >=0.01 |
| T2.1 | 투자가능 IC 유지율 | Y | 1.4869131123690178 | >=0.5 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 1.9272644813290744e-11 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2688293977261286 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.052906941558530506 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.10051274324789312 | IC>=0.01 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 2.8908967219936118e-11 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.1821841375830178 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.04640583216878974 |
| `ic_t_full` | 7.2821839604330565 |
| `ic_p_full` | 2.9690519238632046e-10 |
| `ic_investable` | 0.06900144034216944 |
| `ic_t_investable` | 7.955971986052476 |
| `ic_p_investable` | 1.9272644813290744e-11 |
| `ic_retention` | 1.4869131123690178 |
| `months` | 58 |
| `turnover` | 124.28075807414021 |
| `gross` | 5.3529261902684615 |
| `cost` | 0.6025825058092434 |
| `net` | 4.75034368445922 |
| `net_ir` | 0.6855421901762561 |
| `hac_t` | 1.6884972247677852 |
| `hac_pvalue` | 0.04839010562134854 |
| `missing_return_rate` | 0.0003757985719654265 |
| `neutral_ic` | 0.052906941558530506 |
| `neutral_ic_t` | 5.750385326879236 |
| `neutral_ic_p` | 1.3474161340760224e-07 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.10051274324789312 |
| `oos_ic_t` | 7.648876259069914 |
| `oos_ic_p` | 3.4277493693623304e-09 |
| `n_trials` | 24 |
| `fdr_qvalue` | 2.8908967219936118e-11 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_opm` | quality | 0.923 | 102 |
| `qual_roe` | quality | 0.854 | 102 |
| `quality_stability` | quality | 0.782 | 102 |
| `value_ep` | value | 0.721 | 102 |
| `profitable_small_value` | quality | 0.474 | 102 |
| `asset_turnover` | quality | 0.398 | 102 |
| `downside_vol_12m` | other | 0.342 | 102 |
| `size` | size | -0.303 | 102 |
| `asset_growth_12m` | other | -0.301 | 102 |
| `low_vol_12m` | other | 0.235 | 102 |
| `sue` | earnings | 0.223 | 102 |
| `high_12m_proximity` | momentum | 0.218 | 102 |
| `mom_12_1` | momentum | 0.199 | 102 |
| `value_sp` | value | 0.195 | 102 |
| `defensive_value` | value | 0.192 | 102 |

## Expected relationship and data notes

- Expected relationship: qual_opm·qual_roe와 양의 관계를 예상하고, 분모가 총자산이므로 asset_turnover와도 중간 정도의 관계를 예상한다. 가치·모멘텀 팩터와는 상대적으로 낮은 관계를 예상한다.
- Data notes: Silver revision을 available_date 기준으로 재생한 operating_income_ttm과 total_assets만 사용한다. 총자산이 0 이하인 관측은 비율이 정의되지 않아 결측으로 두며, 회계 데이터 가용성 때문에 가격 팩터보다 커버리지가 낮을 수 있다.
