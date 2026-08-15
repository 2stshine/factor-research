# cycle-0123-revenue_to_capital_stock

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `b20541b3af6f7ff3`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/revenue_to_capital_stock.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

TTM 매출/자본금이 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

작은 납입자본 기반으로 큰 영업규모를 유지하면 자본 확장 없이 성장할 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 생산성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9210794024736306 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9022960059456216 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05078674372005632 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05208160307818479 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7277090855271748 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.35787218281206484 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.0392153487188175 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.869913624613728 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05078674372005632 |
| `ic_t_full` | 6.812480168623302 |
| `ic_p_full` | 2.4307937550098554e-09 |
| `ic_investable` | 0.05208160307818479 |
| `ic_std_investable` | 0.07156926320420375 |
| `rank_icir_investable` | 0.7277090855271748 |
| `ic_t_investable` | 7.34828915779312 |
| `ic_p_investable` | 2.915596318463006e-10 |
| `ic_retention` | 1.025496010637459 |
| `neutral_ic` | 0.0392153487188175 |
| `neutral_ic_t` | 5.389971989065934 |
| `neutral_ic_p` | 6.014595803399237e-07 |
| `neutral_ic_retention` | 0.7529597093996416 |
| `n_trials` | 139 |
| `max_gold_signal_corr` | 0.869913624613728 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.869913624613728 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `capital_stock_to_assets` | other | 0.870 | 63 |
| `capital_stock_to_current_assets` | other | 0.858 | 63 |
| `capital_stock_to_current_liabilities` | quality | -0.835 | 63 |
| `capital_stock_to_liabilities` | quality | -0.816 | 63 |
| `noncurrent_assets_to_capital_stock` | quality | 0.785 | 63 |
| `paid_in_capital_ratio` | quality | 0.780 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.723 | 63 |
| `operating_income_to_capital_stock` | quality | 0.663 | 63 |
| `value_sp` | value | 0.562 | 63 |
| `net_margin_volatility_36m` | quality | 0.562 | 52 |
| `pretax_margin_volatility_36m` | quality | 0.543 | 52 |
| `net_income_to_capital_stock` | quality | 0.542 | 63 |
| `operating_earnings_yield` | value | 0.539 | 63 |
| `retained_earnings_yield` | value | 0.535 | 63 |
| `asset_turnover` | quality | 0.523 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: asset_turnover — 차이: 전체 자산 대신 납입 법정자본의 매출 생산성을 측정한다.
- Data notes: DART available_date PIT 매출과 양의 자본금만 사용한다.
