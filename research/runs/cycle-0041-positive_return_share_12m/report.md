# cycle-0041-positive_return_share_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-003`
- OOS: **SEALED**
- Definition hash: `25e1c2f6b6e54370`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/positive_return_share_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver 총수익지수로 계산한 최근 12개월 양의 월수익 비중이 높은 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

한 번의 급등보다 반복적인 양의 월수익은 긍정적 정보의 점진적 가격 반영과 추세의 폭을 나타낼 수 있다. 투자자의 과소반응이 지속되면 상승의 일관성이 미래수익을 예측한다.

## Pre-registered falsification

사전등록한 양의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9999011844392441 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9995850622406639 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |

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
| `mom_12_1` | momentum | 0.605 | 101 |
| `high_12m_proximity` | momentum | 0.473 | 101 |
| `rev_1m` | momentum | -0.230 | 101 |
| `small_value` | value | -0.227 | 101 |
| `qual_roe` | quality | 0.221 | 101 |
| `operating_roa` | quality | 0.214 | 101 |
| `net_roa` | quality | 0.212 | 101 |
| `operating_return_on_capital_employed` | quality | 0.210 | 101 |
| `defensive_small_value` | value | -0.205 | 101 |
| `qual_opm` | quality | 0.199 | 101 |
| `net_profit_margin` | quality | 0.195 | 101 |
| `value_ep` | value | 0.191 | 101 |
| `downside_vol_12m` | other | 0.178 | 101 |
| `size` | size | -0.169 | 101 |
| `equity_growth_12m` | other | -0.163 | 101 |

## Expected relationship and data notes

- Expected relationship: mom_12_1 및 high_12m_proximity와 양의 관계가 가능하지만 시작·종점 수익률이나 고점 거리가 아니라 상승한 월의 비중만 측정하므로 정의상 다르다.
- Data notes: Silver total_return_close에 매핑된 return_close로 월수익률을 계산한다. 정확히 연속된 12개월 모두가 있을 때만 정의하며 최초 12개월은 결측이다.
