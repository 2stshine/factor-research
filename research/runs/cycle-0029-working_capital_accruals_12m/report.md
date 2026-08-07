# cycle-0029-working_capital_accruals_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260806-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `7d539b85a67522d6`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.5.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/working_capital_accruals_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT에서 12개월 순운전자본 증가액을 전기 총자산으로 나눈 값이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

유동자산 증가가 유동부채 증가보다 크면 기업의 운전자본에 현금이 묶인다. 이 증가가 매출채권·재고 축적이나 공격적인 수익 인식에서 왔다면 보고이익의 현금 전환과 지속성이 낮을 수 있고, 투자자가 이를 늦게 반영하면 이후 가격이 조정될 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성·커버리지, 전체·투자 가능 IC와 Rank ICIR, 네 기간 및 중립화 강건성을 통과하지 못하면 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다.

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
| T1.1 | 전체 커버리지 | Y | 0.9487551485152962 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9305083421154899 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |

### Failed checks

- `T1.2` 종착수익률 3점 방향: None (세 시나리오 IC > 0)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_roa` | quality | -0.353 | 101 |
| `qual_roe` | quality | -0.338 | 101 |
| `operating_roa` | quality | -0.333 | 101 |
| `net_profit_margin` | quality | -0.324 | 101 |
| `current_ratio` | quality | -0.294 | 101 |
| `qual_opm` | quality | -0.294 | 101 |
| `value_ep` | value | -0.289 | 101 |
| `quality_stability` | quality | -0.261 | 101 |
| `operating_roa_change_12m` | earnings | -0.234 | 101 |
| `asset_growth_12m` | other | 0.231 | 101 |
| `earnings_change_to_assets` | earnings | -0.158 | 101 |
| `qual_lev` | quality | -0.157 | 101 |
| `sue` | earnings | -0.152 | 101 |
| `retained_earnings_to_assets` | quality | -0.142 | 101 |
| `sales_growth_12m` | other | 0.140 | 101 |

## Expected relationship and data notes

- Expected relationship: 자산 확장 정보를 일부 포함하므로 asset_growth_12m의 저성장 방향과 관계가 있을 수 있다. current_ratio는 단기 지급능력의 수준이고 이 후보는 운전자본의 12개월 변화이므로 정의상 구별되며, 수익성·모멘텀과의 관계는 낮을 것으로 예상한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT current_assets, current_liabilities, total_assets를 사용한다. 정확히 12개월 전 관측과 양의 전기 총자산이 있을 때만 정의한다. 현금·단기차입금 분리가 없어 순수 영업 accrual이 아닌 넓은 근사치이며 M&A·분할·계정 재분류 효과가 섞일 수 있다.
