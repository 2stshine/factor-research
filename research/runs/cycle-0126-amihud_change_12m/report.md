# cycle-0126-amihud_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ae4560c85988cb8d`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/amihud_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Amihud 비유동성의 12개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.

## Mechanism

유동성의 급격한 악화는 투자자 이탈과 정보비대칭 확대를 나타낼 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 유동성 수준 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9609909820329052 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9502490422218067 | >=30% |
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
| `adv20_change_12m` | other | -0.817 | 63 |
| `return_gain_loss_ratio_12m` | momentum | 0.619 | 63 |
| `price_trend_efficiency_12m` | momentum | 0.609 | 63 |
| `mom_12_1` | momentum | 0.603 | 63 |
| `market_relative_momentum_12_1` | momentum | 0.599 | 63 |
| `book_to_market_change_12m` | value | -0.521 | 63 |
| `price_recovery_12m` | momentum | 0.513 | 63 |
| `daily_volatility_change_12m` | other | -0.466 | 63 |
| `market_leverage_change_12m` | other | 0.422 | 63 |
| `medium_term_momentum_6_2` | momentum | 0.406 | 63 |
| `intermediate_momentum_12_7` | momentum | 0.406 | 63 |
| `trading_turnover_20d` | other | -0.403 | 63 |
| `positive_return_share_12m` | momentum | 0.401 | 63 |
| `high_12m_proximity` | momentum | 0.385 | 63 |
| `amihud_illiquidity_1m` | other | -0.383 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: amihud_illiquidity_1m — 차이: 현재 수준이 아니라 12개월 악화 속도를 측정한다.
- Data notes: 인증된 월별 Amihud 값과 정확한 12개월 전 양의 값만 사용한다.
