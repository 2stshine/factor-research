# cycle-0015-operating_roa_change_12m

- Verdict: **REJECT**
- Definition hash: `4c2f3e0638033747`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_roa_change_12m.py`

## Hypothesis

Silver PIT의 operating_income_ttm/total_assets가 12개월 전보다 많이 개선된 종목은 이후 수익률 순위도 높을 것이다.

## Mechanism

영업 자산수익성 개선은 같은 자산 기반에서 더 많은 핵심 이익을 만들거나 비효율 자산을 정리하고 있다는 신호다. 투자자가 수익성 수준에는 반응해도 변화의 지속성을 한 번에 반영하지 못하면 후속 공시와 함께 가격이 점진적으로 조정될 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.8876245540656907 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.838453500522466 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.014206648979375453 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.016338942786058862 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.30815001588700125 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 0.004227613025104721 | one-sided p<=0.1 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.014206648979375453 |
| `ic_t_full` | 2.6900558166097435 |
| `ic_p_full` | 0.0045505922518686405 |
| `ic_investable` | 0.016338942786058862 |
| `ic_std_investable` | 0.053022690065511344 |
| `rank_icir_investable` | 0.30815001588700125 |
| `ic_t_investable` | 2.717373454031295 |
| `ic_p_investable` | 0.004227613025104721 |
| `ic_retention` | 1.1500912572541895 |
| `months` | 58 |
| `turnover` | 204.2974705748209 |
| `gross` | 3.3405598075221974 |
| `cost` | 0.9810538860311385 |
| `net` | 2.3595059214910585 |
| `net_ir` | 0.5575290429596078 |
| `hac_t` | 1.3829107450271854 |
| `hac_pvalue` | 0.08604297409959102 |
| `missing_return_rate` | 0.0003260337988371461 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.014206648979375453 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.016338942786058862 (>=0.02)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `sales_growth_12m` | other | -0.464 | 102 |
| `sue` | earnings | 0.396 | 102 |
| `operating_roa` | quality | 0.335 | 102 |
| `qual_opm` | quality | 0.295 | 102 |
| `qual_roe` | quality | 0.280 | 102 |
| `value_ep` | value | 0.245 | 102 |
| `net_profit_margin` | quality | 0.225 | 102 |
| `mom_12_1` | momentum | 0.206 | 102 |
| `earnings_confirmed_small_value` | earnings | 0.203 | 102 |
| `quality_stability` | quality | 0.187 | 102 |
| `profitable_small_value` | quality | 0.177 | 102 |
| `asset_growth_12m` | other | -0.167 | 102 |
| `high_12m_proximity` | momentum | 0.123 | 102 |
| `asset_turnover` | quality | 0.118 | 102 |
| `downside_vol_12m` | other | 0.117 | 102 |

## Expected relationship and data notes

- Expected relationship: 수익성 수준을 쓰는 operating_roa와 약한 양의 관계, 이익 변화 정보를 담는 sue와 중간 정도의 양의 관계를 예상한다. 수준이 아닌 12개월 변화량이므로 qual_opm·qual_roe와의 중복은 제한적일 것으로 예상한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 total_assets를 사용한다. 현재와 12개월 전 총자산이 양수인 관측만 정의되며 최초 12개월은 결측이다. 공시 사이에는 신호가 계단형이고 인수합병·사업분할 효과는 별도로 조정하지 않는다.
