# cycle-0066-current_liabilities_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `4d33cc2e60902b83`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_liabilities_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 12개월 current_liabilities 성장률이 낮은 기업은 높은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

유동부채의 급증은 공급자신용 의존, 단기차입 확대 또는 만기 단축을 뜻할 수 있다. 시장이 성장 재원을 먼저 평가하고 가까운 만기의 차환 위험을 늦게 반영하면 낮은 단기부채 성장 기업이 상대적으로 재평가될 수 있다.

## Pre-registered falsification

음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 12 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9444083249833638 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9351901743692338 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.0011925018429037309 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0020780671650135183 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.05914813643684401 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0011925018429037309 |
| `ic_t_full` | 0.26278976211820065 |
| `ic_p_full` | 0.3967990840855289 |
| `ic_investable` | 0.0020780671650135183 |
| `ic_std_investable` | 0.035133265225226404 |
| `rank_icir_investable` | 0.05914813643684401 |
| `ic_t_investable` | 0.4336148248658143 |
| `ic_p_investable` | 0.3330489101685843 |
| `ic_retention` | 1.742611281801833 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0011925018429037309 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0020780671650135183 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.05914813643684401 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `liability_growth_12m` | other | 0.769 | 63 |
| `asset_growth_12m` | other | 0.545 | 63 |
| `current_assets_growth_12m` | other | 0.430 | 63 |
| `working_capital_accruals_12m` | quality | -0.302 | 63 |
| `sales_growth_12m` | other | 0.293 | 63 |
| `revenue_to_total_liabilities` | quality | 0.181 | 63 |
| `solvent_value` | value | 0.179 | 63 |
| `operating_income_growth_12m` | earnings | -0.135 | 63 |
| `qual_lev` | quality | 0.134 | 63 |
| `current_ratio` | quality | 0.133 | 63 |
| `small_value` | value | 0.118 | 63 |
| `current_liability_concentration` | quality | 0.117 | 63 |
| `value_bp` | value | 0.112 | 63 |
| `defensive_small_value` | value | 0.105 | 63 |
| `asset_turnover_change_12m` | quality | 0.094 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: liability_growth_12m — 차이: 장기부채 변화를 제외하고 1년 안에 상환·차환해야 하는 유동부채의 증가만 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT current_liabilities를 사용한다. 정확히 12개월 전 유동부채가 양수인 관측에서 정의한다.
