# cycle-0111-revenue_to_noncurrent_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `2994dfd7e6636119`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/revenue_to_noncurrent_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT revenue_ttm/noncurrent_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

장기부채 한 단위가 뒷받침하는 매출 기반이 크면 수요 충격과 차환 부담을 흡수할 여지가 크다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 revenue_to_total_liabilities 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9203833592118649 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8988148428625521 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.015526302639153724 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.01565757169166065 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.29350508374152895 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.015526302639153724 |
| `ic_t_full` | 2.551314734040723 |
| `ic_p_full` | 0.006627551624250505 |
| `ic_investable` | 0.01565757169166065 |
| `ic_std_investable` | 0.05334685005132404 |
| `rank_icir_investable` | 0.29350508374152895 |
| `ic_t_investable` | 2.473908218634313 |
| `ic_p_investable` | 0.00808140748222792 |
| `ic_retention` | 1.008454624101935 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.015526302639153724 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.01565757169166065 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `noncurrent_liabilities_to_assets` | quality | 0.856 | 63 |
| `current_liability_concentration` | quality | -0.806 | 63 |
| `noncurrent_liabilities_to_equity` | other | 0.800 | 63 |
| `equity_to_noncurrent_liabilities` | quality | 0.800 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.754 | 63 |
| `revenue_to_total_liabilities` | quality | 0.723 | 63 |
| `noncurrent_liabilities_yield` | value | 0.653 | 63 |
| `revenue_to_noncurrent_assets` | quality | 0.565 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.563 | 63 |
| `retained_earnings_to_noncurrent_liabilities` | quality | 0.550 | 63 |
| `noncurrent_assets_to_equity` | other | 0.548 | 63 |
| `quality_stability` | quality | 0.488 | 63 |
| `operating_income_to_noncurrent_liabilities` | quality | 0.472 | 63 |
| `current_assets_to_noncurrent_assets` | other | 0.467 | 63 |
| `current_assets_to_assets` | quality | 0.464 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: revenue_to_total_liabilities — 차이: 총부채가 아니라 장기부채 만기구조만 측정한다.
- Data notes: DART available_date PIT 매출과 양의 비유동부채만 사용한다.
