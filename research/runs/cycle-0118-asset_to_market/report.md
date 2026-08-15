# cycle-0118-asset_to_market

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `8b1db811b2216526`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/asset_to_market.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

총자산/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

장부자본뿐 아니라 부채로 조달한 운영자산까지 가격 대비 싸게 거래되는 기업은 재평가 여지가 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9617405670840377 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9579786459446815 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.07115490023763824 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.07303709435925565 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6414767973845339 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.40866067218043645 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.04197078082978192 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.42669310808995276 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.07115490023763824 |
| `ic_t_full` | 4.403175492356266 |
| `ic_p_full` | 2.1877063668294253e-05 |
| `ic_investable` | 0.07303709435925565 |
| `ic_std_investable` | 0.11385773368116617 |
| `rank_icir_investable` | 0.6414767973845339 |
| `ic_t_investable` | 4.443259166809252 |
| `ic_p_investable` | 1.9012001640518386e-05 |
| `ic_retention` | 1.0264520660605438 |
| `neutral_ic` | 0.04197078082978192 |
| `neutral_ic_t` | 3.190812940649811 |
| `neutral_ic_p` | 0.0011211162184213738 |
| `neutral_ic_retention` | 0.5746501992992162 |
| `n_trials` | 129 |
| `max_gold_signal_corr` | 0.42669310808995276 |
| `gold_signal_comparison_months` | {'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `noncurrent_assets_yield` | value | 0.923 | 63 |
| `value_bp` | value | 0.898 | 63 |
| `market_leverage` | other | 0.887 | 63 |
| `current_assets_yield` | value | 0.883 | 63 |
| `current_liabilities_yield` | value | -0.865 | 63 |
| `value_sp` | value | 0.846 | 63 |
| `noncurrent_liabilities_yield` | value | -0.748 | 63 |
| `defensive_value` | value | 0.722 | 63 |
| `defensive_small_value` | value | 0.692 | 63 |
| `small_value` | value | 0.692 | 63 |
| `adv20_to_book_equity` | other | 0.632 | 63 |
| `profitable_small_value` | quality | 0.613 | 63 |
| `earnings_confirmed_small_value` | earnings | 0.583 | 63 |
| `retained_earnings_yield` | value | 0.550 | 63 |
| `capital_stock_yield` | value | 0.471 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: value_bp — 차이: 순자산 대신 전체 운영자산의 시장가격 대비 크기를 측정한다.
- Data notes: DART available_date PIT 총자산과 동시점 양의 시가총액을 사용한다.
