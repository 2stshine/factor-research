# cycle-0090-capital_stock_to_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-007` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `177e5062f4f3b37c`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/capital_stock_to_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT capital_stock/total_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

채무 한 단위당 명목 납입자본이 많으면 외부 충격을 흡수하는 장부 완충력이 클 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 레버리지 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9564858228990585 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9490393818427995 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |

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
| `capital_stock_to_assets` | other | -0.864 | 63 |
| `paid_in_capital_ratio` | quality | -0.648 | 63 |
| `market_leverage` | other | -0.571 | 63 |
| `retained_earnings_to_capital_stock` | quality | -0.520 | 63 |
| `qual_lev` | quality | 0.517 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.473 | 63 |
| `noncurrent_liabilities_to_equity` | other | 0.465 | 63 |
| `value_sp` | value | -0.457 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.448 | 63 |
| `current_ratio` | quality | 0.432 | 63 |
| `noncurrent_assets_to_equity` | other | 0.417 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.408 | 63 |
| `revenue_to_equity` | quality | -0.397 | 63 |
| `net_working_capital_to_assets` | quality | 0.396 | 63 |
| `current_liabilities_to_assets` | quality | 0.394 | 63 |

## Expected relationship and data notes

- Expected relationship: solvency 신호와 관련되지만 누적이익을 제외한 자본금만 사용한다.
- Data notes: DART available_date PIT 자본금과 양의 총부채만 사용한다.
