# cycle-0068-retained_earnings_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `b3c24c1cb9c7a15a`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 12개월 retained_earnings 성장률이 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

이익잉여금 증가는 당기 이익에서 배당과 조정을 뺀 내부자본의 순축적이다. 지속적으로 내부자본을 늘리는 기업은 외부조달 의존과 재무곤경 위험이 낮고 시장이 그 복리 효과를 과소평가할 수 있다.

## Pre-registered falsification

양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.7323904879186777 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.710015521057696 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.023893506666357676 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.02398358222661633 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.32102977986519643 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.023893506666357676 |
| `ic_t_full` | 3.087490057246876 |
| `ic_p_full` | 0.0015178860367533378 |
| `ic_investable` | 0.02398358222661633 |
| `ic_std_investable` | 0.07470827857991016 |
| `rank_icir_investable` | 0.32102977986519643 |
| `ic_t_investable` | 3.025792267203383 |
| `ic_p_investable` | 0.0018138384790761975 |
| `ic_retention` | 1.0037698761222638 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.023893506666357676 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.02398358222661633 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_roe` | quality | 0.821 | 63 |
| `net_roa` | quality | 0.787 | 63 |
| `pretax_roa` | quality | 0.766 | 63 |
| `net_profit_margin` | quality | 0.736 | 63 |
| `pretax_profit_margin` | quality | 0.727 | 63 |
| `equity_growth_12m` | other | -0.689 | 63 |
| `operating_roa` | quality | 0.687 | 63 |
| `operating_return_on_capital_employed` | quality | 0.682 | 63 |
| `value_ep` | value | 0.661 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.661 | 63 |
| `qual_opm` | quality | 0.649 | 63 |
| `operating_income_to_liabilities` | quality | 0.625 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.616 | 63 |
| `operating_earnings_yield` | value | 0.495 | 63 |
| `operating_income_growth_12m` | earnings | 0.469 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: retained_earnings_to_equity — 차이: 자기자본 구성의 수준이 아니라 내부자본이 최근 12개월 동안 축적된 속도를 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT retained_earnings를 사용한다. 정확히 12개월 전 이익잉여금이 양수인 관측에서 정의하며 결손 기업의 기저 왜곡을 제외한다.
