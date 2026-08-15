# cycle-0142-capital_stock_to_current_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-014` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `41a5be7768c1c7c1`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/capital_stock_to_current_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

자본금/유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

회수 요구가 없는 납입자본이 단기부채보다 크면 지급위기 시 손실흡수 여력이 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자본구성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.955529719517512 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9475105632980835 | >=30% |
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
| `capital_stock_to_liabilities` | quality | 0.962 | 63 |
| `capital_stock_to_assets` | other | -0.841 | 63 |
| `revenue_to_capital_stock` | quality | -0.835 | 63 |
| `noncurrent_assets_to_capital_stock` | quality | -0.798 | 63 |
| `capital_stock_to_current_assets` | other | -0.778 | 63 |
| `paid_in_capital_ratio` | quality | -0.633 | 63 |
| `current_liabilities_yield` | value | 0.568 | 63 |
| `market_leverage` | other | -0.544 | 63 |
| `retained_earnings_to_capital_stock` | quality | -0.525 | 63 |
| `equity_to_current_liabilities` | quality | 0.514 | 63 |
| `operating_income_to_capital_stock` | quality | -0.494 | 63 |
| `current_liabilities_to_assets` | quality | 0.492 | 63 |
| `qual_lev` | quality | 0.485 | 63 |
| `value_sp` | value | -0.477 | 63 |
| `current_ratio` | quality | 0.462 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: capital_stock_to_liabilities — 차이: 전체부채가 아니라 단기부채에 대한 법정자본 완충력만 측정한다.
- Data notes: DART available_date PIT 자본금과 양의 유동부채만 사용한다.
