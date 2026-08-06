# cycle-0019-asset_turnover_change_12m

- Verdict: **REJECT**
- Definition hash: `8f8e7c42fdc9fce8`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/asset_turnover_change_12m.py`

## Hypothesis

Silver PIT의 revenue_ttm/total_assets가 12개월 전보다 많이 개선된 종목은 이후 수익률 순위도 높을 것이다.

## Mechanism

자산회전율 개선은 같은 자산 기반으로 더 많은 매출을 만들거나 비생산적 자산을 정리한 결과다. 투자자가 현재 효율 수준에는 반응해도 개선 추세의 지속성을 충분히 반영하지 못하면 후속 공시와 함께 가격이 점진적으로 조정될 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.8729109185807427 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.81652834056275 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.004825846473482485 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.003811783614928262 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.08746599261477021 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | N | 0.24971750101519744 | one-sided p<=0.1 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.004825846473482485 |
| `ic_t_full` | 1.0572248329173848 |
| `ic_p_full` | 0.14719166017548294 |
| `ic_investable` | 0.003811783614928262 |
| `ic_std_investable` | 0.04358017900416045 |
| `rank_icir_investable` | 0.08746599261477021 |
| `ic_t_investable` | 0.6792400360781764 |
| `ic_p_investable` | 0.24971750101519744 |
| `ic_retention` | 0.7898683963266567 |
| `months` | 50 |
| `turnover` | 252.59514125243285 |
| `gross` | 1.9002721812532546 |
| `cost` | 1.2128882255984925 |
| `net` | 0.6873839556547621 |
| `net_ir` | 0.18034892489390655 |
| `hac_t` | 0.4103096141115826 |
| `hac_pvalue` | 0.3416837209711651 |
| `missing_return_rate` | 0.0013041351953485844 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.004825846473482485 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.003811783614928262 (>=0.02)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.08746599261477021 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))
- `T2.1` 투자가능 IC HAC 유의성: 0.24971750101519744 (one-sided p<=0.1)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `sales_growth_12m` | other | -0.646 | 102 |
| `operating_roa_change_12m` | earnings | 0.401 | 102 |
| `asset_growth_12m` | other | 0.261 | 102 |
| `liability_growth_12m` | other | 0.200 | 102 |
| `asset_turnover` | quality | 0.169 | 102 |
| `sue` | earnings | 0.140 | 102 |
| `quality_stability` | quality | 0.117 | 102 |
| `operating_roa` | quality | 0.114 | 102 |
| `qual_opm` | quality | 0.082 | 102 |
| `value_sp` | value | 0.074 | 102 |
| `earnings_confirmed_small_value` | earnings | 0.065 | 102 |
| `mom_12_1` | momentum | 0.062 | 102 |
| `profitable_small_value` | quality | 0.059 | 102 |
| `qual_roe` | quality | 0.053 | 102 |
| `value_ep` | value | 0.052 | 102 |

## Expected relationship and data notes

- Expected relationship: 자산 효율 수준인 asset_turnover와 약한 양의 관계, 매출 변화가 분자에 있으므로 sales_growth_12m과 중간 정도의 양의 관계를 예상한다. 수준이 아닌 변화량이므로 기존 수익성 팩터와의 중복은 제한적일 것으로 예상한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT revenue_ttm과 total_assets를 사용한다. 현재와 12개월 전 총자산이 양수인 관측만 정의되며 최초 12개월은 결측이다. 인수합병·사업분할에 따른 구조적 매출·자산 변화는 별도로 조정하지 않는다.
