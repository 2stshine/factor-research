# cycle-0038-noncurrent_asset_encumbrance

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-002`
- OOS: **SEALED**
- Definition hash: `8c1ba3eef1fc9629`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_asset_encumbrance.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 noncurrent_liabilities/noncurrent_assets가 낮은 기업은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

장기자산에 대한 높은 장기 채권자 청구는 자금조달 경직성과 하방 위험을 높인다. 시장이 이 장기 구조의 취약성을 늦게 반영하면 낮은 부담 기업이 상대적으로 우수할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.960684881668366 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9459762226829559 | >=30% |
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
| `current_liability_concentration` | quality | -0.748 | 101 |
| `qual_lev` | quality | 0.588 | 101 |
| `solvent_value` | value | 0.408 | 101 |
| `retained_earnings_to_assets` | quality | 0.282 | 101 |
| `quality_stability` | quality | 0.255 | 101 |
| `current_ratio` | quality | 0.238 | 101 |
| `value_sp` | value | -0.226 | 101 |
| `net_working_capital_to_assets` | quality | 0.201 | 101 |
| `liability_growth_12m` | other | 0.175 | 101 |
| `net_profit_margin` | quality | 0.150 | 101 |
| `net_roa` | quality | 0.143 | 101 |
| `nonoperating_burden_to_assets` | quality | 0.140 | 101 |
| `size` | size | 0.134 | 101 |
| `profitable_small_value` | quality | 0.113 | 101 |
| `posttax_income_conversion` | quality | 0.107 | 101 |

## Expected relationship and data notes

- Expected relationship: qual_lev의 총부채/자본 및 current_liability_concentration의 유동부채/총부채와 일부 관계는 가능하지만, 장기자산 대비 장기청구만 측정하므로 산식은 비동치다.
- Data notes: DART available_date 순으로 재생한 noncurrent_liabilities와 noncurrent_assets를 사용한다. 비유동자산이 양수일 때만 정의하며 담보권 자체를 직접 식별하는 지표는 아니다.
