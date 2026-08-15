# cycle-0128-momentum_acceleration_6m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `98a613007a62aa32`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/momentum_acceleration_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 3개월 수익에서 직전 3개월 수익을 뺀 값이 큰 종목의 이후 순위가 높을 것이다.

## Mechanism

가격 추세의 가속은 정보 반영 속도가 아직 정점에 이르지 않았음을 나타낼 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 모멘텀 직교성이 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 6 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9999082140753716 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.999509393297173 | >=30% |
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
| `short_term_reversal_3m` | momentum | -0.708 | 63 |
| `rev_1m` | momentum | -0.338 | 63 |
| `price_recovery_12m` | momentum | 0.225 | 63 |
| `max_daily_return_1m` | other | -0.217 | 63 |
| `high_12m_proximity` | momentum | 0.205 | 63 |
| `high_52w_price_proximity` | momentum | 0.174 | 63 |
| `max_daily_return_change_12m` | other | -0.172 | 63 |
| `medium_term_momentum_6_2` | momentum | -0.171 | 63 |
| `trading_turnover_20d` | other | -0.150 | 63 |
| `adv20_change_12m` | other | -0.135 | 63 |
| `turnover_change_6m` | other | -0.120 | 63 |
| `adv20_to_book_equity` | other | -0.117 | 63 |
| `downside_vol_12m` | other | 0.080 | 63 |
| `amihud_change_12m` | other | 0.074 | 63 |
| `book_to_market_change_12m` | value | -0.061 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: medium_term_momentum_6_2 — 차이: 6개월 누적 수준이 아니라 인접 3개월 추세의 변화만 측정한다.
- Data notes: 분할조정 adj_close와 정확한 3·6개월 달력 시차만 사용한다.
