# cycle-0157-price_recovery_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-015` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `6c2f9df4e590ffad`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/price_recovery_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

현재 분할조정가격/12개월 최저가격 비율이 높은 종목의 이후 순위가 높을 것이다.

## Mechanism

저점 이후 지속적 회복은 재무곤경 완화와 정보확산을 나타내며 가격 조정이 이어질 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 가격앵커 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9998317258048478 | >=50% |
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
| `return_gain_loss_ratio_12m` | momentum | 0.758 | 63 |
| `price_trend_efficiency_12m` | momentum | 0.750 | 63 |
| `book_to_market_change_12m` | value | -0.605 | 63 |
| `short_term_reversal_3m` | momentum | -0.596 | 63 |
| `market_relative_momentum_12_1` | momentum | 0.560 | 63 |
| `mom_12_1` | momentum | 0.560 | 63 |
| `medium_term_momentum_6_2` | momentum | 0.548 | 63 |
| `max_monthly_return_12m` | other | -0.525 | 63 |
| `adv20_change_12m` | other | -0.519 | 63 |
| `amihud_change_12m` | other | 0.513 | 63 |
| `max_daily_return_1m` | other | -0.492 | 63 |
| `high_12m_proximity` | momentum | 0.482 | 63 |
| `market_leverage_change_12m` | other | 0.479 | 63 |
| `positive_return_share_12m` | momentum | 0.465 | 63 |
| `low_vol_12m` | other | -0.456 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: high_12m_proximity — 차이: 고점 근접도가 아니라 저점 이후 회복 배수를 측정한다.
- Data notes: 분할조정 adj_close의 정확한 12개 달력월만 사용한다.
