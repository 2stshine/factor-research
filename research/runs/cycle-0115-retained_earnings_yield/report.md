# cycle-0115-retained_earnings_yield

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ed934394649254e9`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_yield.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

이익잉여금/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

과거 이익의 누적 내부자본이 가격에 비해 크면 외부조달 없이 투자할 선택권이 크다.

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
| T1.1 | 전체 커버리지 | Y | 0.9599277950726256 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.95575739893969 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.0817668094542934 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.08587536357793361 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.0017542620049968 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.35118846222688443 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.0554602463225617 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.8310442209639628 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0817668094542934 |
| `ic_t_full` | 6.659658436625032 |
| `ic_p_full` | 4.439971540597834e-09 |
| `ic_investable` | 0.08587536357793361 |
| `ic_std_investable` | 0.08572497950351146 |
| `rank_icir_investable` | 1.0017542620049968 |
| `ic_t_investable` | 7.570633512599073 |
| `ic_p_investable` | 1.206967003233557e-10 |
| `ic_retention` | 1.0502472109534473 |
| `neutral_ic` | 0.0554602463225617 |
| `neutral_ic_t` | 5.446868028346158 |
| `neutral_ic_p` | 4.85293981730567e-07 |
| `neutral_ic_retention` | 0.6458225504015528 |
| `n_trials` | 129 |
| `max_gold_signal_corr` | 0.8310442209639628 |
| `gold_signal_comparison_months` | {'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.8310442209639628 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `retained_earnings_to_equity` | quality | 0.831 | 63 |
| `retained_earnings_to_current_assets` | quality | 0.793 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.790 | 63 |
| `retained_earnings_to_assets` | quality | 0.772 | 63 |
| `value_bp` | value | 0.704 | 63 |
| `retained_earnings_to_current_liabilities` | quality | 0.698 | 63 |
| `retained_earnings_to_noncurrent_assets` | quality | 0.696 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.695 | 63 |
| `defensive_value` | value | 0.652 | 63 |
| `retained_earnings_to_noncurrent_liabilities` | quality | 0.632 | 63 |
| `solvent_value` | value | 0.616 | 63 |
| `paid_in_capital_ratio` | quality | 0.590 | 63 |
| `adv20_to_book_equity` | other | 0.573 | 63 |
| `profitable_small_value` | quality | 0.570 | 63 |
| `asset_to_market` | value | 0.550 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: value_bp — 차이: 전체 장부자본 중 누적 이익으로 조성된 부분만 가격과 비교한다.
- Data notes: DART available_date PIT 이익잉여금과 동시점 양의 시가총액을 사용한다.
