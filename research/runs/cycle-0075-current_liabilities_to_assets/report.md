# cycle-0075-current_liabilities_to_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-004` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `f66afd1139d97ee9`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_liabilities_to_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT current_liabilities/total_assets가 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

단기 만기 부채가 적으면 불리한 시점의 차환·자산매각 위험이 줄어 하방 위험이 낮아진다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 0 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9610139285140624 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9569640847388851 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.011610356781916853 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.011617101480430141 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.19563235319001718 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.011610356781916853 |
| `ic_t_full` | 1.7234809080433569 |
| `ic_p_full` | 0.04493362806135902 |
| `ic_investable` | 0.011617101480430141 |
| `ic_std_investable` | 0.05938231223516737 |
| `rank_icir_investable` | 0.19563235319001718 |
| `ic_t_investable` | 1.5722193092163441 |
| `ic_p_investable` | 0.06053632442837644 |
| `ic_retention` | 1.0005809208657388 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.011610356781916853 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.011617101480430141 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_lev` | quality | 0.844 | 63 |
| `current_ratio` | quality | 0.794 | 63 |
| `net_working_capital_to_assets` | quality | 0.653 | 63 |
| `market_leverage` | other | -0.620 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.607 | 63 |
| `solvent_value` | value | 0.599 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.519 | 63 |
| `retained_earnings_to_assets` | quality | 0.419 | 63 |
| `value_sp` | value | -0.414 | 63 |
| `revenue_to_total_liabilities` | quality | 0.402 | 63 |
| `asset_turnover` | quality | -0.365 | 63 |
| `net_income_to_liabilities` | quality | 0.358 | 63 |
| `pretax_income_to_liabilities` | quality | 0.355 | 63 |
| `current_liability_concentration` | quality | 0.330 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.323 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: current_liability_concentration — 차이: 부채 내 만기구조가 아니라 총자산 대비 단기청구권 규모다.
- Data notes: DART available_date PIT 유동부채와 양의 총자산을 사용한다.
