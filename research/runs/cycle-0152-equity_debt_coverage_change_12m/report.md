# cycle-0152-equity_debt_coverage_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-015` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `cd46d2f611150038`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/equity_debt_coverage_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

자기자본/총부채의 12개월 변화가 큰 종목의 이후 순위가 높을 것이다.

## Mechanism

부채 대비 손실흡수자본의 증가는 파산·차환위험을 낮추지만 신용평가와 가격은 후행할 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 레버리지 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9455174049059577 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9365941507505865 | >=30% |
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
| `liability_growth_12m` | other | 0.800 | 63 |
| `current_liabilities_growth_12m` | other | 0.628 | 63 |
| `current_ratio_change_12m` | quality | 0.608 | 63 |
| `liability_growth_acceleration_12m` | other | 0.557 | 63 |
| `current_liabilities_growth_acceleration_12m` | other | 0.462 | 63 |
| `retained_earnings_to_assets_change_12m` | quality | 0.419 | 63 |
| `market_leverage_change_12m` | other | 0.402 | 63 |
| `noncurrent_liabilities_growth_12m` | other | 0.332 | 63 |
| `equity_growth_12m` | other | -0.329 | 63 |
| `asset_growth_12m` | other | 0.275 | 63 |
| `working_capital_accruals_12m` | quality | -0.271 | 63 |
| `capital_stock_share_change_12m` | other | 0.255 | 63 |
| `asset_growth_acceleration_12m` | other | 0.254 | 63 |
| `working_capital_growth_12m` | other | -0.224 | 63 |
| `equity_growth_acceleration_12m` | other | -0.222 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: qual_lev — 차이: 레버리지 수준이 아니라 장부 지급능력의 12개월 개선폭을 측정한다.
- Data notes: DART available_date PIT 자기자본·양의 총부채와 정확한 12개월 시차를 사용한다.
