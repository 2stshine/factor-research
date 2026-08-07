# cycle-0030-earnings_change_to_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260806-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `6c7d7d1bcd6a8f1e`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.5.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/earnings_change_to_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 전년동기 분기 순이익 변화액/총자산이 높은 종목은 낮은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

같은 회계분기와 비교한 순이익 개선은 계절성을 줄인 이익 변화다. 절대 변화액을 총자산으로 나누면 단순 기업 규모 효과를 줄일 수 있다. 투자자가 개선의 지속성을 점진적으로 반영하면 공시 이후에도 상대가격 조정이 이어질 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성·커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성을 통과하지 못하면 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다.

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
| T1.1 | 전체 커버리지 | Y | 0.9232203092927052 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8701713086507205 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.021892784906162435 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.022613815347682746 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5117945536655568 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.021892784906162435 |
| `ic_t_full` | 5.688606383336536 |
| `ic_p_full` | 6.51479010491238e-08 |
| `ic_investable` | 0.022613815347682746 |
| `ic_std_investable` | 0.04418533801448038 |
| `rank_icir_investable` | 0.5117945536655568 |
| `ic_t_investable` | 5.600181560864633 |
| `ic_p_investable` | 9.608719853231654e-08 |
| `ic_retention` | 1.032934614970677 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.021892784906162435 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.022613815347682746 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `sue` | earnings | 0.914 | 101 |
| `earnings_confirmed_small_value` | earnings | 0.443 | 101 |
| `operating_roa_change_12m` | earnings | 0.369 | 101 |
| `qual_roe` | quality | 0.219 | 101 |
| `net_roa` | quality | 0.206 | 101 |
| `sales_growth_12m` | other | -0.202 | 101 |
| `net_profit_margin` | quality | 0.190 | 101 |
| `value_ep` | value | 0.177 | 101 |
| `operating_roa` | quality | 0.161 | 101 |
| `working_capital_accruals_12m` | quality | -0.158 | 101 |
| `mom_12_1` | momentum | 0.156 | 101 |
| `high_12m_proximity` | momentum | 0.149 | 101 |
| `qual_opm` | quality | 0.146 | 101 |
| `asset_turnover_change_12m` | quality | 0.127 | 101 |
| `asset_growth_12m` | other | -0.113 | 101 |

## Expected relationship and data notes

- Expected relationship: 같은 원천 변화액을 과거 변동성으로 표준화하는 sue와 양의 관계가 예상되지만, 이 후보는 기업 규모 대비 변화 강도를 측정하므로 완전 중복은 아닐 것으로 예상한다. TTM 수익성 수준 및 operating_roa_change_12m과도 일부 관계가 있을 수 있다.
- Data notes: DART available_date 순으로 재생한 Silver PIT net_income_yoy_change와 total_assets를 사용한다. net_income_yoy_change는 최신 공개 분기 순이익에서 동일 회계분기의 전년 값을 뺀 금액이며 성장률이 아니다. 총자산이 양수인 관측에서만 정의하고 공시 사이에는 신호가 계단형으로 유지된다.
