# cycle-0184-market_beta_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `87688a5728969be7`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/market_beta_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 12개월 beta가 낮은 종목은 고위험 선호에 따른 과대가격을 피하여 이후 상대수익이 높다.

## Mechanism

전월 시가총액 가중 시장수익과의 공분산 구조를 사용해 총변동성과 다른 시장위험을 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9998164281507431 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9994962216624685 | >=30% |
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
| `market_beta_18m` | quality | 0.900 | 63 |
| `market_beta_9m` | quality | 0.899 | 63 |
| `market_beta_24m` | quality | 0.799 | 63 |
| `market_beta_6m` | quality | 0.728 | 63 |
| `market_beta_36m` | other | 0.667 | 63 |
| `market_return_correlation_12m` | quality | 0.655 | 63 |
| `market_return_correlation_9m` | quality | 0.575 | 63 |
| `market_return_correlation_18m` | quality | 0.538 | 63 |
| `market_return_correlation_24m` | quality | 0.483 | 63 |
| `market_return_correlation_6m` | quality | 0.477 | 63 |
| `low_vol_12m` | other | 0.450 | 63 |
| `downside_vol_12m` | other | 0.448 | 63 |
| `max_monthly_return_12m` | other | 0.359 | 63 |
| `price_range_12m` | other | 0.341 | 63 |
| `defensive_value` | value | 0.260 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 24개월 고유변동성과 관련되지만 시장 공통성분의 민감도 또는 상관을 직접 측정한다.
- Data notes: adj_close, 전월 market·market_cap으로 내부 PIT 시장 벤치마크를 구성하고 결측을 채우지 않는다.
