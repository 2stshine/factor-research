# cycle-0083-noncurrent_liability_share_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-005` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `959597640823529f`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_liability_share_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT noncurrent_liabilities/total_liabilities의 12개월 변화가 큰 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

부채 만기가 장기로 이동하면 가까운 시점의 차환·유동성 충격 노출이 줄어 재무 유연성이 개선될 수 있다.

## Pre-registered falsification

양의 방향, 강건성, BY, 봉인 OOS, 귀무 또는 단기 지급능력·레버리지 신호와의 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9438499606085407 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9349030566317287 | >=30% |
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
| `noncurrent_liabilities_growth_12m` | other | -0.767 | 63 |
| `current_liabilities_growth_12m` | other | 0.497 | 63 |
| `current_ratio_change_12m` | quality | 0.453 | 63 |
| `current_liability_concentration` | quality | 0.343 | 63 |
| `working_capital_accruals_12m` | quality | -0.331 | 63 |
| `noncurrent_liabilities_to_assets` | quality | -0.259 | 63 |
| `noncurrent_asset_encumbrance` | quality | -0.255 | 63 |
| `current_liabilities_to_assets` | quality | 0.202 | 63 |
| `noncurrent_asset_share_change_12m` | other | -0.166 | 63 |
| `current_ratio` | quality | 0.149 | 63 |
| `noncurrent_assets_growth_12m` | other | -0.134 | 63 |
| `asset_turnover_change_12m` | quality | -0.111 | 63 |
| `net_working_capital_to_assets` | quality | 0.103 | 63 |
| `operating_income_growth_12m` | earnings | -0.080 | 63 |
| `operating_roa_change_12m` | earnings | -0.078 | 63 |

## Expected relationship and data notes

- Expected relationship: noncurrent_liabilities_to_assets와 관련되지만 총부채 내 만기구성의 12개월 변화만 측정한다.
- Data notes: DART available_date PIT 비유동부채와 양의 총부채를 사용하며 정확히 12개월 전 비율이 있을 때만 정의한다.
