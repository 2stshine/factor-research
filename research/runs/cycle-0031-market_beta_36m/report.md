# cycle-0031-market_beta_36m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260806-001` / `epoch-002`
- OOS: **SEALED**
- Definition hash: `5d0c823050915663`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.5.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/market_beta_36m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 36개월 시장 베타가 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

일부 투자자는 직접 레버리지를 쓰는 대신 고베타 주식으로 목표 수익을 추구한다. 이 수요가 고베타 종목 가격을 높이면 저베타 종목은 상대적으로 낮게 평가되어 이후 더 높은 수익을 제공할 수 있다.

## Pre-registered falsification

저베타 방향이 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성을 통과하지 못하거나 기존 저변동성 신호와 중복되면 독립적인 시장민감도 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다.

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
| T1.1 | 전체 커버리지 | Y | 0.9583088165938276 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9528637254109927 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.014452641284069092 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.014859493707535905 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.11859739176462576 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.014452641284069092 |
| `ic_t_full` | 1.3101424879474783 |
| `ic_p_full` | 0.09658968744840597 |
| `ic_investable` | 0.014859493707535905 |
| `ic_std_investable` | 0.12529359614439742 |
| `rank_icir_investable` | 0.11859739176462576 |
| `ic_t_investable` | 1.3982197180586915 |
| `ic_p_investable` | 0.08258583229994021 |
| `ic_retention` | 1.028150731445558 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.014452641284069092 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.014859493707535905 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.11859739176462576 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.327 | 101 |
| `downside_vol_12m` | other | 0.310 | 101 |
| `max_monthly_return_12m` | other | 0.265 | 101 |
| `defensive_value` | value | 0.233 | 101 |
| `defensive_small_value` | value | 0.221 | 101 |
| `quality_stability` | quality | 0.218 | 101 |
| `trading_turnover_20d` | other | 0.179 | 101 |
| `high_12m_proximity` | momentum | 0.153 | 101 |
| `profitable_small_value` | quality | 0.142 | 101 |
| `solvent_value` | value | 0.121 | 101 |
| `value_ep` | value | 0.118 | 101 |
| `retained_earnings_to_assets` | quality | 0.116 | 101 |
| `return_skewness_24m` | other | 0.113 | 101 |
| `operating_roa` | quality | 0.106 | 101 |
| `net_roa` | quality | 0.102 | 101 |

## Expected relationship and data notes

- Expected relationship: low_vol_12m과 downside_vol_12m의 저위험 방향과 양의 관계가 예상되지만, 총변동성이 아니라 시장 공분산만 측정하므로 완전 중복은 아닐 것으로 예상한다. 회계 가치·수익성과의 관계는 제한적일 것으로 예상한다.
- Data notes: Silver total_return_close로 연속 월 수익률을 만들고, 전월 PIT 시장구분과 전월 시가총액으로 각 월 KOSPI·KOSDAQ 수익률을 구성한다. 공식 지수수익률이 아니며 자기 종목 포함, 비동시거래와 시장 이전의 영향을 받는다. 36개월 달력창에서 최소 24개 동일월 쌍이 있을 때만 계산하고 결측을 채우거나 내부 표본선택·중립화를 하지 않는다.
