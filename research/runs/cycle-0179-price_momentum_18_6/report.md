# cycle-0179-price_momentum_18_6

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `9b32d1620cdb42d7`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/price_momentum_18_6.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

분할조정 가격의 18개월 전 대비 6개월 전 수익률이 높은 종목은 정보의 지연반영 또는 장기 과잉반응 교정으로 이후 상대수익이 높다.

## Mechanism

서로 다른 시작·종료 시점의 가격 경로는 최근 한 달 잡음과 장기 추세를 분리하며, 사전 고정한 부호는 점진적 정보확산 또는 과잉반응 교정을 검증한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 18 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9780631640137984 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9717577132282306 | >=30% |
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
| `market_relative_momentum_18_3` | momentum | 0.861 | 63 |
| `price_momentum_24_6` | momentum | 0.746 | 63 |
| `market_relative_momentum_24_6` | momentum | 0.744 | 63 |
| `price_momentum_15_3` | momentum | 0.668 | 63 |
| `intermediate_momentum_12_7` | momentum | 0.631 | 63 |
| `price_trend_efficiency_24m` | momentum | 0.581 | 63 |
| `price_momentum_12_3` | momentum | 0.499 | 63 |
| `positive_return_share_18m` | momentum | 0.469 | 63 |
| `mom_12_1` | momentum | 0.446 | 63 |
| `market_relative_momentum_12_1` | momentum | 0.438 | 63 |
| `market_leverage_change_18m` | other | 0.436 | 63 |
| `high_24m_proximity` | momentum | 0.409 | 63 |
| `price_reversal_24_12` | momentum | -0.406 | 63 |
| `positive_return_share_24m` | momentum | 0.388 | 63 |
| `price_trend_efficiency_12m` | momentum | 0.385 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 모멘텀·반전과 관련될 수 있으나 정확한 구간이 달라 Gold 0.70 gate로 독립성을 확인한다.
- Data notes: PIT feature로 허용된 adj_close와 정확한 달력 시차만 사용하며 total_return_close는 사용하지 않는다.
