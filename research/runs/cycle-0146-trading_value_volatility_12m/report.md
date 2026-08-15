# cycle-0146-trading_value_volatility_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-014` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `74ce4f67d200762d`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/trading_value_volatility_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

12개월 거래대금/시가총액 표준편차가 높은 종목의 이후 순위가 낮을 것이다.

## Mechanism

간헐적 거래 급증은 안정적 유동성보다 투기적 관심과 가격충격 위험을 나타낸다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 거래활동 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9998317258048478 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9994962216624685 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.08214769704483418 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.08687851029054598 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6961189704730427 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.362493383123336 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | N | 0.025109016304253436 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6121847288255928 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.08214769704483418 |
| `ic_t_full` | 8.164613985860607 |
| `ic_p_full` | 1.146170761564148e-11 |
| `ic_investable` | 0.08687851029054598 |
| `ic_std_investable` | 0.12480411248023926 |
| `rank_icir_investable` | 0.6961189704730427 |
| `ic_t_investable` | 8.525814533177856 |
| `ic_p_investable` | 2.7527019581583512e-12 |
| `ic_retention` | 1.0575891158960895 |
| `neutral_ic` | 0.025109016304253436 |
| `neutral_ic_t` | 3.362602527939296 |
| `neutral_ic_p` | 0.0006689525201521134 |
| `neutral_ic_retention` | 0.2890129701842479 |
| `n_trials` | 159 |
| `max_gold_signal_corr` | 0.6121847288255928 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'price_range_12m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T3.2` 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: 0.025109016304253436 (IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `realized_volatility_252d` | other | 0.734 | 63 |
| `trading_turnover_20d` | other | 0.670 | 63 |
| `low_vol_12m` | other | 0.633 | 63 |
| `idiosyncratic_volatility_24m` | other | 0.612 | 63 |
| `adv20_to_book_equity` | other | 0.599 | 63 |
| `turnover_volatility_12m` | other | 0.585 | 63 |
| `max_monthly_return_12m` | other | 0.567 | 63 |
| `defensive_value` | value | 0.550 | 63 |
| `price_range_12m` | other | 0.469 | 63 |
| `downside_vol_12m` | other | 0.466 | 63 |
| `quality_stability` | quality | 0.379 | 63 |
| `max_daily_return_1m` | other | 0.370 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.363 | 63 |
| `retained_earnings_yield` | value | 0.344 | 63 |
| `paid_in_capital_ratio` | quality | 0.341 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: turnover_volatility_12m — 차이: 주식회전율 대신 기업가치 대비 거래대금 변동성을 측정한다.
- Data notes: 동시점 trading_value·양의 market_cap의 정확한 12개월 달력창을 사용한다.
