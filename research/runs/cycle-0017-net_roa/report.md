# cycle-0017-net_roa

- Verdict: **PROVISIONAL**
- Definition hash: `ad335843d7d17cec`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_roa.py`

## Hypothesis

Silver PIT의 최근 12개월 순이익을 총자산으로 나눈 단일 net ROA가 높은 종목은 이후 수익률 순위도 높을 것이다.

## Mechanism

net ROA는 보유 자산이 최종 주주이익으로 전환되는 정도를 측정한다. 높은 값은 영업 효율뿐 아니라 부채비용·세금·비영업손익까지 관리한다는 뜻이며, 이 효율이 지속되면 후속 공시를 통해 점진적으로 가격에 반영될 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, 고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9464659156810713 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9156681020448338 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.04708374007359344 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06599928431881447 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.769094937937817 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 2.6320056039533727e-10 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2897220480303121 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.05094809226015548 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.09221544821881612 | IC>=0.02 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 1.447603082174355e-09 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.19741969489543823 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.04708374007359344 |
| `ic_t_full` | 7.050969451280834 |
| `ic_p_full` | 7.570589016977115e-10 |
| `ic_investable` | 0.06599928431881447 |
| `ic_std_investable` | 0.08581422274833728 |
| `rank_icir_investable` | 0.769094937937817 |
| `ic_t_investable` | 7.311911652549017 |
| `ic_p_investable` | 2.6320056039533727e-10 |
| `ic_retention` | 1.4017426019185264 |
| `months` | 55 |
| `turnover` | 151.76242947295816 |
| `gross` | 3.142580446029783 |
| `cost` | 0.7328323967889037 |
| `net` | 2.40974804924088 |
| `net_ir` | 0.39406448796594074 |
| `hac_t` | 0.8934487343006872 |
| `hac_pvalue` | 0.18779078522148177 |
| `missing_return_rate` | 0.0005368551028077521 |
| `neutral_ic` | 0.05094809226015548 |
| `neutral_ic_t` | 5.655412793285395 |
| `neutral_ic_p` | 1.9493095695256326e-07 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.09221544821881612 |
| `oos_ic_t` | 7.722131653423658 |
| `oos_ic_p` | 2.7815954687045217e-09 |
| `n_trials` | 29 |
| `fdr_qvalue` | 1.447603082174355e-09 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_roe` | quality | 0.967 | 102 |
| `net_profit_margin` | quality | 0.945 | 102 |
| `operating_roa` | quality | 0.863 | 102 |
| `value_ep` | value | 0.832 | 102 |
| `qual_opm` | quality | 0.816 | 102 |
| `quality_stability` | quality | 0.721 | 102 |
| `profitable_small_value` | quality | 0.416 | 102 |
| `asset_growth_12m` | other | -0.326 | 102 |
| `downside_vol_12m` | other | 0.321 | 102 |
| `qual_lev` | quality | 0.288 | 102 |
| `asset_turnover` | quality | 0.282 | 102 |
| `sue` | earnings | 0.269 | 102 |
| `operating_roa_change_12m` | earnings | 0.263 | 102 |
| `sales_growth_12m` | other | -0.260 | 102 |
| `size` | size | -0.259 | 102 |

## Expected relationship and data notes

- Expected relationship: 분자가 순이익인 qual_roe, 분모가 총자산인 operating_roa와 강한 양의 관계를 예상한다. net_profit_margin과도 관련되지만 매출 대신 자산을 분모로 사용하므로 자산회전율 차이가 남을 것으로 예상한다.
- Data notes: DART available_date 순으로 정정공시를 재생한 Silver PIT net_income_ttm과 total_assets만 사용한다. 총자산이 0 이하인 관측은 결측으로 두며, 순이익에는 일회성 비영업손익과 세금 효과가 포함될 수 있다.
