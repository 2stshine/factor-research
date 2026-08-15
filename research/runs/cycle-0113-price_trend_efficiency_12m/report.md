# cycle-0113-price_trend_efficiency_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ef0a1d0f9ef6aaff`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/price_trend_efficiency_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

12개월 누적 분할조정수익/월별 절대수익 경로가 큰 종목의 이후 순위가 높을 것이다.

## Mechanism

정보가 일관되게 반영된 추세는 단기 반전 잡음보다 지속 가능성이 높다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 모멘텀 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.985505472735756 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9746647881940997 | >=30% |
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
| `return_gain_loss_ratio_12m` | momentum | 0.993 | 63 |
| `mom_12_1` | momentum | 0.876 | 63 |
| `market_relative_momentum_12_1` | momentum | 0.866 | 63 |
| `price_recovery_12m` | momentum | 0.750 | 63 |
| `book_to_market_change_12m` | value | -0.745 | 63 |
| `positive_return_share_12m` | momentum | 0.640 | 63 |
| `amihud_change_12m` | other | 0.609 | 63 |
| `intermediate_momentum_12_7` | momentum | 0.591 | 63 |
| `market_leverage_change_12m` | other | 0.583 | 63 |
| `high_12m_proximity` | momentum | 0.553 | 63 |
| `adv20_change_12m` | other | -0.545 | 63 |
| `medium_term_momentum_6_2` | momentum | 0.518 | 63 |
| `high_52w_price_proximity` | momentum | 0.517 | 63 |
| `max_monthly_return_12m` | other | -0.513 | 63 |
| `short_term_reversal_3m` | momentum | -0.418 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: mom_12_1 — 차이: 누적수익 수준이 아니라 이동 경로 대비 방향 효율을 측정한다.
- Data notes: 분할조정 adj_close와 정확한 12개월 달력 경로만 사용한다.
