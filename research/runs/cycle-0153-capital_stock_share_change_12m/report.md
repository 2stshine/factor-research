# cycle-0153-capital_stock_share_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-015` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `7f5557c0c07307a4`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/capital_stock_share_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

자본금/자기자본 비중의 12개월 증가가 큰 종목의 이후 순위가 낮을 것이다.

## Mechanism

누적이익보다 납입자본 비중이 빠르게 커지면 외부조달과 주식희석 가능성을 나타낸다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자본조달 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.8772516234635419 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.4510104971558855 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.017267132276782893 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.016754829826261013 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.29706431854620596 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.017267132276782893 |
| `ic_t_full` | 2.8264007438768872 |
| `ic_p_full` | 0.0031781521391699573 |
| `ic_investable` | 0.016754829826261013 |
| `ic_std_investable` | 0.05640135411838408 |
| `rank_icir_investable` | 0.29706431854620596 |
| `ic_t_investable` | 2.599774651667255 |
| `ic_p_investable` | 0.005842425478376692 |
| `ic_retention` | 0.970330773963508 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.017267132276782893 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.016754829826261013 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `equity_growth_12m` | other | -0.726 | 63 |
| `retained_earnings_growth_12m` | quality | 0.634 | 63 |
| `qual_roe` | quality | 0.552 | 63 |
| `pretax_income_to_equity` | quality | 0.531 | 63 |
| `net_roa` | quality | 0.523 | 63 |
| `net_income_to_noncurrent_assets` | quality | 0.515 | 63 |
| `pretax_roa` | quality | 0.508 | 63 |
| `net_income_to_current_assets` | quality | 0.505 | 63 |
| `net_income_growth_12m` | earnings | 0.499 | 63 |
| `pretax_income_to_current_assets` | quality | 0.485 | 63 |
| `net_profit_margin` | quality | 0.484 | 63 |
| `pretax_income_growth_12m` | earnings | 0.483 | 63 |
| `net_income_to_liabilities` | quality | 0.473 | 63 |
| `value_ep` | value | 0.472 | 63 |
| `pretax_profit_margin` | quality | 0.471 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: paid_in_capital_ratio — 차이: 자본구성 수준이 아니라 12개월 외부자본 비중 변화를 측정한다.
- Data notes: DART available_date PIT 자본금·양의 자기자본과 정확한 12개월 시차를 사용한다.
