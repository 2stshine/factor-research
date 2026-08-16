# cycle-0190-return_seasonality_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-004` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `4225bbe32cc2bf60`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/return_seasonality_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

같은 달의 12개월 전 월수익이 높은 종목은 반복되는 계절적 수요와 정보주기로 이후 상대수익이 높다.

## Mechanism

연속 추세가 아니라 직전 연도의 동일 달력월 수익만 사용해 기업고유 계절성을 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 13 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9967415996756898 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9938504422982798 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.010630046380648774 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.009643320924455157 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.16781758001852848 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.010630046380648774 |
| `ic_t_full` | 1.8588538408610706 |
| `ic_p_full` | 0.03393679736290136 |
| `ic_investable` | 0.009643320924455157 |
| `ic_std_investable` | 0.05746311514795085 |
| `rank_icir_investable` | 0.16781758001852848 |
| `ic_t_investable` | 1.763819427148542 |
| `ic_p_investable` | 0.04138487521554372 |
| `ic_retention` | 0.9071758089419178 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.010630046380648774 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.009643320924455157 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `max_daily_return_change_12m` | other | 0.329 | 63 |
| `price_momentum_15_3` | momentum | 0.242 | 63 |
| `price_reversal_24_12` | momentum | -0.239 | 63 |
| `price_momentum_18_6` | momentum | 0.225 | 63 |
| `market_relative_momentum_18_3` | momentum | 0.202 | 63 |
| `trading_value_turnover_change_12m` | other | 0.196 | 63 |
| `market_relative_momentum_24_6` | momentum | 0.182 | 63 |
| `price_momentum_24_6` | momentum | 0.181 | 63 |
| `positive_return_share_18m` | momentum | 0.165 | 63 |
| `positive_return_share_24m` | momentum | 0.154 | 63 |
| `price_trend_efficiency_24m` | momentum | 0.149 | 63 |
| `long_term_reversal_36_12` | momentum | -0.144 | 63 |
| `adv20_change_12m` | other | 0.141 | 63 |
| `high_24m_proximity` | momentum | 0.133 | 63 |
| `market_leverage_change_18m` | other | 0.107 | 63 |

## Expected relationship and data notes

- Expected relationship: 일반 모멘텀과 입력은 공유하지만 불연속적인 12개월 시차의 한 달 수익만 사용해 구분한다.
- Data notes: adj_close로 계산한 과거 동일월 수익만 사용하며 미래 수익률과 OOS 결과를 사용하지 않는다.
