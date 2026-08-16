# cycle-0160-high_24m_proximity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `cd05cc73466c7e16`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/high_24m_proximity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

24개월 고점에 가까운 종목의 추세가 이후에도 지속된다.

## Mechanism

장기 고점 근접도는 지속적 수요와 정보 확산을 포착한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9594535677953786 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.954894044190027 | >=30% |
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
| `high_12m_proximity` | momentum | 0.809 | 63 |
| `high_52w_price_proximity` | momentum | 0.789 | 63 |
| `market_relative_momentum_12_1` | momentum | 0.656 | 63 |
| `price_trend_efficiency_12m` | momentum | 0.656 | 63 |
| `mom_12_1` | momentum | 0.655 | 63 |
| `return_gain_loss_ratio_12m` | momentum | 0.621 | 63 |
| `downside_vol_12m` | other | 0.606 | 63 |
| `capital_stock_yield_change_12m` | value | -0.577 | 63 |
| `price_trend_efficiency_6m` | momentum | 0.559 | 63 |
| `price_momentum_12_3` | momentum | 0.552 | 63 |
| `price_momentum_15_3` | momentum | 0.546 | 63 |
| `price_momentum_9_2` | momentum | 0.542 | 63 |
| `price_trend_efficiency_24m` | momentum | 0.536 | 63 |
| `medium_term_momentum_6_2` | momentum | 0.528 | 63 |
| `price_momentum_6_1` | momentum | 0.528 | 63 |

## Expected relationship and data notes

- Expected relationship: 12개월 고점 신호와 기간이 다르다.
- Data notes: adj_close 24개월 창만 사용한다.
