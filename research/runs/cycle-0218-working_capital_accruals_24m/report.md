# cycle-0218-working_capital_accruals_24m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-006` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `8676e7864fe77761`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/working_capital_accruals_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

working_capital_accrual 신호가 낮은 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.

## Mechanism

PIT 이익·운전자본의 수준 변화 또는 변동성을 이용해 단순 수익성 수준과 다른 이익의 질을 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 24 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8912948699316959 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8847209029553714 | >=30% |
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
| `working_capital_accruals_12m` | quality | 0.658 | 63 |
| `working_capital_growth_12m` | other | 0.620 | 63 |
| `operating_asset_growth_24m` | quality | 0.528 | 63 |
| `equity_growth_24m` | other | 0.473 | 63 |
| `working_capital_accruals_6m` | earnings | 0.455 | 63 |
| `current_ratio_change_12m` | quality | -0.414 | 63 |
| `net_working_capital_to_assets` | quality | -0.403 | 63 |
| `operating_asset_growth_12m` | quality | 0.393 | 63 |
| `equity_growth_12m` | other | 0.377 | 63 |
| `current_ratio` | quality | -0.368 | 63 |
| `current_assets_growth_12m` | other | 0.366 | 63 |
| `retained_earnings_growth_12m` | quality | -0.362 | 63 |
| `working_capital_to_sales` | quality | -0.361 | 63 |
| `net_working_capital_to_liabilities` | quality | -0.355 | 63 |
| `net_income_to_noncurrent_assets` | quality | -0.353 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 수익성 또는 자산성장과 일부 관계가 예상되지만 측정 대상이 발생액·안정성이다.
- Data notes: DART available_date PIT 재무값과 고정 36개월 이하 달력창만 사용한다.
