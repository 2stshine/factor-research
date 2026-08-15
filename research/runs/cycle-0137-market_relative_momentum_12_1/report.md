# cycle-0137-market_relative_momentum_12_1

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-013` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `8377d93ea80f76dc`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/market_relative_momentum_12_1.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

동일 시장 평균을 뺀 12-1개월 분할조정 모멘텀이 높은 종목의 이후 순위가 높을 것이다.

## Mechanism

시장 전체 재평가가 아닌 기업고유 정보의 점진적 확산만 분리한다.

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
| `mom_12_1` | momentum | 0.995 | 63 |
| `price_trend_efficiency_12m` | momentum | 0.866 | 63 |
| `return_gain_loss_ratio_12m` | momentum | 0.862 | 63 |
| `intermediate_momentum_12_7` | momentum | 0.689 | 63 |
| `book_to_market_change_12m` | value | -0.663 | 63 |
| `amihud_change_12m` | other | 0.599 | 63 |
| `medium_term_momentum_6_2` | momentum | 0.577 | 63 |
| `positive_return_share_12m` | momentum | 0.569 | 63 |
| `price_recovery_12m` | momentum | 0.560 | 63 |
| `market_leverage_change_12m` | other | 0.536 | 63 |
| `high_12m_proximity` | momentum | 0.536 | 63 |
| `high_52w_price_proximity` | momentum | 0.515 | 63 |
| `adv20_change_12m` | other | -0.488 | 63 |
| `max_monthly_return_12m` | other | -0.363 | 63 |
| `downside_vol_12m` | other | 0.329 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: mom_12_1 — 차이: KOSPI·KOSDAQ별 공통 가격추세를 동월 횡단면에서 제거한다.
- Data notes: 분할조정 adj_close, 동시점 market, 정확한 1·12개월 달력 시차만 사용한다.
