# cycle-0069-noncurrent_assets_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `f671f2fe6d3fbfb6`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_assets_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT 비유동자산의 정확한 12개월 성장률이 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

장기 설비·투자자산의 급증은 경영자의 과잉확장과 낮은 한계 투자수익을 뒤늦게 드러낼 수 있다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9422360581004903 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9328468471081272 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.006242308685585234 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.007538311550138794 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.13766096215037177 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.006242308685585234 |
| `ic_t_full` | 0.9903228450155108 |
| `ic_p_full` | 0.1629642339015881 |
| `ic_investable` | 0.007538311550138794 |
| `ic_std_investable` | 0.054759980116254305 |
| `rank_icir_investable` | 0.13766096215037177 |
| `ic_t_investable` | 1.1269718083125513 |
| `ic_p_investable` | 0.13208408147222897 |
| `ic_retention` | 1.207615952659678 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.006242308685585234 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.007538311550138794 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.13766096215037177 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `asset_growth_12m` | other | 0.575 | 63 |
| `noncurrent_asset_share_change_12m` | other | 0.569 | 63 |
| `liability_growth_12m` | other | 0.435 | 63 |
| `equity_growth_12m` | other | 0.364 | 63 |
| `noncurrent_liabilities_growth_12m` | other | 0.329 | 63 |
| `current_liabilities_growth_12m` | other | 0.297 | 63 |
| `working_capital_accruals_12m` | quality | -0.235 | 63 |
| `retained_earnings_growth_12m` | quality | -0.234 | 63 |
| `asset_turnover_change_12m` | quality | 0.232 | 63 |
| `qual_roe` | quality | -0.202 | 63 |
| `small_value` | value | 0.201 | 63 |
| `net_roa` | quality | -0.197 | 63 |
| `net_profit_margin` | quality | -0.194 | 63 |
| `pretax_profit_margin` | quality | -0.194 | 63 |
| `sales_growth_12m` | other | 0.192 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: asset_growth_12m — 차이: 유동자산을 제외하고 장기 자산 투자만 측정한다.
- Data notes: DART available_date PIT noncurrent_assets를 쓰며 정확히 12개월 전 양수 관측이 있을 때만 정의한다.
