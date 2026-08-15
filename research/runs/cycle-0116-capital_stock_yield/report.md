# cycle-0116-capital_stock_yield

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `1de2eb2066948601`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/capital_stock_yield.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

자본금/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

가격에 비해 납입된 법정자본이 크면 시장이 기초 자본기반을 낮게 평가했을 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 가치 신호 직교성이 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 0 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9565852576507392 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9490393818427995 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.023380245506276324 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.024142592801958667 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.22520956509287038 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.023380245506276324 |
| `ic_t_full` | 1.886325736224139 |
| `ic_p_full` | 0.03200683360364047 |
| `ic_investable` | 0.024142592801958667 |
| `ic_std_investable` | 0.10720056580191392 |
| `rank_icir_investable` | 0.22520956509287038 |
| `ic_t_investable` | 1.7704848081146718 |
| `ic_p_investable` | 0.040821510879114085 |
| `ic_retention` | 1.032606470940508 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.023380245506276324 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.024142592801958667 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `paid_in_capital_ratio` | quality | -0.688 | 63 |
| `capital_stock_to_current_assets` | other | -0.642 | 63 |
| `capital_stock_to_assets` | other | -0.619 | 63 |
| `small_value` | value | 0.582 | 63 |
| `noncurrent_assets_to_capital_stock` | quality | -0.515 | 63 |
| `size` | size | 0.508 | 63 |
| `retained_earnings_to_capital_stock` | quality | -0.499 | 63 |
| `earnings_confirmed_small_value` | earnings | 0.481 | 63 |
| `revenue_to_capital_stock` | quality | -0.480 | 63 |
| `asset_to_market` | value | 0.471 | 63 |
| `current_liabilities_yield` | value | -0.460 | 63 |
| `operating_income_to_capital_stock` | quality | -0.457 | 63 |
| `defensive_small_value` | value | 0.452 | 63 |
| `net_income_to_capital_stock` | quality | -0.450 | 63 |
| `market_leverage` | other | 0.448 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: capital_stock_to_assets — 차이: 자산구성이 아니라 시장가격 대비 법정자본 가치만 측정한다.
- Data notes: DART available_date PIT 자본금과 동시점 양의 시가총액을 사용한다.
