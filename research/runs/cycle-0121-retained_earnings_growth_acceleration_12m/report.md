# cycle-0121-retained_earnings_growth_acceleration_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `34a28f0d2076a197`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_growth_acceleration_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 이익잉여금 성장의 가속도가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

내부자본 축적의 가속은 외부조달 의존도 감소와 누적 수익력 개선을 나타낼 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 retained_earnings_growth_12m 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.6715976105064289 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.6580279111233557 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.026293525216477074 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.026283068417751666 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5208013551031668 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.026293525216477074 |
| `ic_t_full` | 5.662428568225855 |
| `ic_p_full` | 2.140052338022221e-07 |
| `ic_investable` | 0.026283068417751666 |
| `ic_std_investable` | 0.05046658991996131 |
| `rank_icir_investable` | 0.5208013551031668 |
| `ic_t_investable` | 5.475606544784425 |
| `ic_p_investable` | 4.35332034334995e-07 |
| `ic_retention` | 0.9996023051820052 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.026293525216477074 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.026283068417751666 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_profit_margin_change_12m` | earnings | 0.698 | 63 |
| `net_income_growth_12m` | earnings | 0.697 | 63 |
| `pretax_income_growth_12m` | earnings | 0.664 | 63 |
| `net_income_growth_acceleration_12m` | earnings | 0.651 | 51 |
| `pretax_income_growth_acceleration_12m` | earnings | 0.620 | 51 |
| `equity_growth_acceleration_12m` | other | -0.587 | 63 |
| `operating_roa_change_12m` | earnings | 0.519 | 63 |
| `retained_earnings_growth_12m` | quality | 0.505 | 63 |
| `operating_margin_change_12m` | earnings | 0.490 | 63 |
| `operating_income_growth_12m` | earnings | 0.486 | 63 |
| `operating_income_growth_acceleration_12m` | earnings | 0.439 | 51 |
| `operating_coverage_change_12m` | earnings | 0.418 | 63 |
| `operating_margin_acceleration_12m` | earnings | 0.407 | 51 |
| `sue` | earnings | 0.389 | 63 |
| `earnings_change_to_assets` | earnings | 0.386 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: retained_earnings_growth_12m — 차이: 성장률 수준이 아니라 성장의 가속만 측정한다.
- Data notes: DART available_date PIT 이익잉여금과 정확한 12·24개월 전 양의 값을 요구한다.
