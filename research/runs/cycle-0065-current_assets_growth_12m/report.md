# cycle-0065-current_assets_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `3196d6dd2d501904`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_assets_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 12개월 current_assets 성장률이 낮은 기업은 높은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

유동자산 팽창은 영업 성장의 준비일 수도 있지만 재고 체화와 매출채권 회수 지연을 포함할 수 있다. 시장이 외형 증가를 먼저 반영하고 운전자본의 낮은 생산성을 늦게 반영하면 낮은 유동자산 성장 기업의 기대수익이 상대적으로 높다.

## Pre-registered falsification

음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9449284452229251 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9356581664963514 | >=30% |
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
| `asset_growth_12m` | other | 0.704 | 63 |
| `working_capital_accruals_12m` | quality | 0.538 | 63 |
| `liability_growth_12m` | other | 0.498 | 63 |
| `equity_growth_12m` | other | 0.448 | 63 |
| `current_liabilities_growth_12m` | other | 0.430 | 63 |
| `sales_growth_12m` | other | 0.357 | 63 |
| `retained_earnings_growth_12m` | quality | -0.322 | 63 |
| `operating_income_growth_12m` | earnings | -0.299 | 63 |
| `operating_income_to_noncurrent_assets` | quality | -0.247 | 63 |
| `qual_roe` | quality | -0.246 | 63 |
| `operating_return_on_capital_employed` | quality | -0.244 | 63 |
| `pretax_roa` | quality | -0.236 | 63 |
| `operating_roa` | quality | -0.234 | 63 |
| `net_roa` | quality | -0.226 | 63 |
| `qual_opm` | quality | -0.220 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: asset_growth_12m — 차이: 설비·투자자산을 제외하고 현금·재고·채권 등 단기 운전자본성 자산의 팽창만 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT current_assets를 사용한다. 정확히 12개월 전 유동자산이 양수인 관측에서 정의하며 M&A와 사업분할의 불연속은 별도 조정하지 않는다.
