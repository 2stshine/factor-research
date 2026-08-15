# cycle-0112-adv20_to_book_equity

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `8df24f36d7bb6745`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/adv20_to_book_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

20일 평균 거래대금/장부 자기자본이 높은 종목의 이후 수익률 순위가 낮을 것이다.

## Mechanism

기업의 누적 위험자본에 비해 거래가 과도하면 관심과 의견불일치가 현재 가격에 먼저 반영될 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 거래활동 계열 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9593694306978024 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9555804974068882 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.12016050277928284 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.12703014125040693 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.1138266031046644 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.36541781492049086 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.041460659556766734 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6051224773263237 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.12016050277928284 |
| `ic_t_full` | 9.434285508773185 |
| `ic_p_full` | 7.879036906957956e-14 |
| `ic_investable` | 0.12703014125040693 |
| `ic_std_investable` | 0.11404839936155675 |
| `rank_icir_investable` | 1.1138266031046644 |
| `ic_t_investable` | 9.582339863969606 |
| `ic_p_investable` | 4.441950697611678e-14 |
| `ic_retention` | 1.0571705203642716 |
| `neutral_ic` | 0.041460659556766734 |
| `neutral_ic_t` | 3.411925741159959 |
| `neutral_ic_p` | 0.000575156761066024 |
| `neutral_ic_retention` | 0.3263844245834365 |
| `n_trials` | 129 |
| `max_gold_signal_corr` | 0.6051224773263237 |
| `gold_signal_comparison_months` | {'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `trading_turnover_20d` | other | 0.878 | 63 |
| `defensive_value` | value | 0.792 | 63 |
| `value_bp` | value | 0.724 | 63 |
| `realized_volatility_252d` | other | 0.673 | 63 |
| `defensive_small_value` | value | 0.655 | 63 |
| `asset_to_market` | value | 0.632 | 63 |
| `max_daily_return_1m` | other | 0.628 | 63 |
| `idiosyncratic_volatility_24m` | other | 0.604 | 63 |
| `trading_value_volatility_12m` | other | 0.599 | 63 |
| `noncurrent_assets_yield` | value | 0.586 | 63 |
| `low_vol_12m` | other | 0.574 | 63 |
| `retained_earnings_yield` | value | 0.573 | 63 |
| `current_assets_yield` | value | 0.553 | 63 |
| `solvent_value` | value | 0.543 | 63 |
| `max_monthly_return_12m` | other | 0.531 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: trading_turnover_20d — 차이: 시가총액 대신 PIT 장부 자기자본으로 거래활동을 정규화한다.
- Data notes: 동시점 Silver adv20과 DART available_date PIT 양의 자기자본만 사용한다.
