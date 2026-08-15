# cycle-0105-liability_growth_acceleration_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-010` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `f14b34ecb54a5d5b`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/liability_growth_acceleration_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 총부채 성장의 가속도가 높은 종목은 이후 수익률 순위가 낮을 것이다.

## Mechanism

채무 증가의 가속은 차환 의존도나 공격적 투자 확대를 나타내며 하방 위험이 늦게 반영될 수 있다.

## Pre-registered falsification

음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 liability_growth_12m 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.892365705719028 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.887014050226795 | >=30% |
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
| `asset_growth_acceleration_12m` | other | 0.730 | 63 |
| `current_liabilities_growth_acceleration_12m` | other | 0.725 | 63 |
| `liability_growth_12m` | other | 0.647 | 63 |
| `current_assets_growth_acceleration_12m` | other | 0.519 | 63 |
| `current_liabilities_growth_12m` | other | 0.482 | 63 |
| `asset_growth_12m` | other | 0.429 | 63 |
| `current_assets_growth_12m` | other | 0.348 | 63 |
| `noncurrent_liabilities_growth_12m` | other | 0.307 | 63 |
| `current_ratio_change_12m` | quality | 0.294 | 63 |
| `market_leverage_change_12m` | other | 0.284 | 63 |
| `asset_turnover_change_12m` | quality | 0.242 | 63 |
| `noncurrent_assets_growth_12m` | other | 0.202 | 63 |
| `sales_growth_acceleration_12m` | earnings | -0.185 | 51 |
| `retained_earnings_to_assets_change_12m` | quality | 0.182 | 63 |
| `noncurrent_asset_share_change_12m` | other | -0.127 | 63 |

## Expected relationship and data notes

- Expected relationship: liability_growth_12m과 관련되지만 부채 성장의 2차 차분이다.
- Data notes: DART available_date PIT 총부채와 정확한 12·24개월 전 양의 총부채를 요구한다.
