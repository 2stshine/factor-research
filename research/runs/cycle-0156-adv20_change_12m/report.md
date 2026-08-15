# cycle-0156-adv20_change_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-015` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `d9a4ee93f1d820c6`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/adv20_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

20일 평균 거래대금의 12개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.

## Mechanism

지속적인 거래 접근성 개선은 투자자의 요구 비유동성 보상을 낮춘다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 거래유동성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9778795921645416 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9658363967430516 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05906602885346034 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06033699841861902 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7348131681811984 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.30943452449797854 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | N | -0.0018556814023567897 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.4915929114947891 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05906602885346034 |
| `ic_t_full` | 7.120839925912714 |
| `ic_p_full` | 7.181501685122087e-10 |
| `ic_investable` | 0.06033699841861902 |
| `ic_std_investable` | 0.08211202660938223 |
| `rank_icir_investable` | 0.7348131681811984 |
| `ic_t_investable` | 7.329586855330769 |
| `ic_p_investable` | 3.1400438618961263e-10 |
| `ic_retention` | 1.0215177757812683 |
| `neutral_ic` | -0.0018556814023567897 |
| `neutral_ic_t` | -0.2175021651568926 |
| `neutral_ic_p` | 0.5857285410048494 |
| `neutral_ic_retention` | -0.03075528201588756 |
| `n_trials` | 169 |
| `max_gold_signal_corr` | 0.4915929114947891 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'price_range_12m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T3.2` 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: -0.0018556814023567897 (IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `amihud_change_12m` | other | -0.817 | 63 |
| `max_daily_return_change_12m` | other | 0.627 | 63 |
| `return_gain_loss_ratio_12m` | momentum | -0.555 | 63 |
| `price_trend_efficiency_12m` | momentum | -0.545 | 63 |
| `price_recovery_12m` | momentum | -0.519 | 63 |
| `mom_12_1` | momentum | -0.493 | 63 |
| `book_to_market_change_12m` | value | 0.491 | 63 |
| `market_relative_momentum_12_1` | momentum | -0.488 | 63 |
| `daily_volatility_change_12m` | other | 0.484 | 63 |
| `trading_turnover_20d` | other | 0.483 | 63 |
| `turnover_change_6m` | other | 0.461 | 63 |
| `max_daily_return_1m` | other | 0.435 | 63 |
| `adv20_to_book_equity` | other | 0.413 | 63 |
| `high_12m_proximity` | momentum | -0.375 | 63 |
| `market_leverage_change_12m` | other | -0.372 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: trading_turnover_20d — 차이: 현재 회전 수준이 아니라 절대 거래유동성의 12개월 성장률을 측정한다.
- Data notes: 동시점 adv20과 정확한 12개월 전 양의 값만 사용한다.
