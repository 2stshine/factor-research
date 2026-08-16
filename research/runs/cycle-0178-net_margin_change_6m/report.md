# cycle-0178-net_margin_change_6m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `71fc629dd84ab9d6`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_margin_change_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 6개월 net_income_ttm/revenue_ttm 개선이 큰 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.

## Mechanism

수익성 수준이 아니라 동일 PIT 비율의 개선을 측정해 기존 Gold 수준 신호와 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 6 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8910577562930725 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.842454690179748 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.023365268252716773 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.02417463824689417 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6576377103018658 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.023365268252716773 |
| `ic_t_full` | 5.42166483189631 |
| `ic_p_full` | 5.337349648052398e-07 |
| `ic_investable` | 0.02417463824689417 |
| `ic_std_investable` | 0.03675981147096574 |
| `rank_icir_investable` | 0.6576377103018658 |
| `ic_t_investable` | 5.263300680714599 |
| `ic_p_investable` | 9.674856305076313e-07 |
| `ic_retention` | 1.0346398759656135 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.023365268252716773 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.02417463824689417 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `pretax_yield_change_6m` | value | 0.676 | 63 |
| `net_profit_margin_change_12m` | earnings | 0.669 | 63 |
| `operating_margin_change_6m` | earnings | 0.637 | 63 |
| `net_income_growth_12m` | earnings | 0.625 | 63 |
| `earnings_change_to_assets` | earnings | 0.593 | 63 |
| `pretax_income_growth_12m` | earnings | 0.587 | 63 |
| `sue` | earnings | 0.571 | 63 |
| `enterprise_earnings_yield_change_12m` | value | 0.563 | 63 |
| `net_income_growth_acceleration_12m` | earnings | 0.538 | 51 |
| `earnings_yield_change_12m` | value | 0.523 | 63 |
| `pretax_income_growth_acceleration_12m` | earnings | 0.505 | 51 |
| `retained_earnings_growth_acceleration_12m` | quality | 0.505 | 63 |
| `pretax_yield_change_12m` | value | 0.491 | 63 |
| `operating_margin_change_12m` | earnings | 0.491 | 63 |
| `operating_roa_change_12m` | earnings | 0.458 | 63 |

## Expected relationship and data notes

- Expected relationship: 관련 수익성 수준 신호와 일부 관계가 예상되지만 변화율은 별도 메커니즘이다.
- Data notes: DART available_date PIT 값과 정확한 달력 시차, 0이 아닌 분모만 사용한다.
