# cycle-0040-equity_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-003`
- OOS: **SEALED**
- Definition hash: `7c69893c5073ff70`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/equity_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 12개월 total_equity 성장률이 낮은 기업은 높은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

자기자본의 빠른 팽창은 증자·주식보상·인수 또는 기대가 높은 확장을 포함할 수 있다. 투자자가 조달과 확장의 희석·평균회귀 위험을 늦게 반영하면 낮은 성장 기업의 기대수익이 상대적으로 높을 수 있다.

## Pre-registered falsification

사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9523574248664867 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9312058579144163 | >=30% |
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
| `asset_growth_12m` | other | 0.605 | 101 |
| `qual_roe` | quality | -0.592 | 101 |
| `net_roa` | quality | -0.566 | 101 |
| `net_profit_margin` | quality | -0.527 | 101 |
| `value_ep` | value | -0.507 | 101 |
| `operating_roa` | quality | -0.504 | 101 |
| `operating_return_on_capital_employed` | quality | -0.498 | 101 |
| `working_capital_accruals_12m` | quality | 0.484 | 101 |
| `qual_opm` | quality | -0.471 | 101 |
| `sales_growth_12m` | other | 0.289 | 101 |
| `operating_roa_change_12m` | earnings | -0.281 | 101 |
| `quality_stability` | quality | -0.272 | 101 |
| `operating_margin_change_12m` | earnings | -0.237 | 101 |
| `size` | size | 0.216 | 101 |
| `long_term_reversal_36_12` | momentum | 0.215 | 101 |

## Expected relationship and data notes

- Expected relationship: shares 변화 기반 net_equity_issuance_12m 및 total-assets 기반 asset_growth_12m과 일부 관계가 가능하지만, 이 후보는 PIT 장부 자기자본 전체의 12개월 변화만 측정한다.
- Data notes: DART available_date 순으로 재생한 total_equity를 사용한다. 정확히 12개월 전 양의 자기자본이 있을 때만 정의하며 적자 누적에 따른 음의 자본 출발점은 비율에서 제외한다.
