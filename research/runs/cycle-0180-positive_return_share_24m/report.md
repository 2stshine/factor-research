# cycle-0180-positive_return_share_24m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `923fc8b46eed56ff`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/positive_return_share_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

24개월 상승월 비중이 높은 종목은 넓은 추세 참여로 이후 상대수익이 높다.

## Mechanism

소수 급등월이 아닌 추세의 폭을 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9557897796372926 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.951765957623093 | >=30% |
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
| `positive_return_share_18m` | momentum | 0.849 | 63 |
| `positive_return_share_12m` | momentum | 0.679 | 63 |
| `price_trend_efficiency_24m` | momentum | 0.597 | 63 |
| `price_momentum_24_6` | momentum | 0.499 | 63 |
| `market_relative_momentum_24_6` | momentum | 0.488 | 63 |
| `high_24m_proximity` | momentum | 0.450 | 63 |
| `market_relative_momentum_18_3` | momentum | 0.438 | 63 |
| `price_trend_efficiency_12m` | momentum | 0.420 | 63 |
| `price_recovery_24m` | momentum | 0.410 | 63 |
| `return_gain_loss_ratio_12m` | momentum | 0.403 | 63 |
| `price_momentum_15_3` | momentum | 0.396 | 63 |
| `price_reversal_24_12` | momentum | -0.395 | 63 |
| `price_momentum_18_6` | momentum | 0.388 | 63 |
| `mom_12_1` | momentum | 0.376 | 63 |
| `market_relative_momentum_12_1` | momentum | 0.375 | 63 |

## Expected relationship and data notes

- Expected relationship: 12개월 상승월 비중과 기간이 다르다.
- Data notes: 연속 월 adj_close 수익률만 사용한다.
