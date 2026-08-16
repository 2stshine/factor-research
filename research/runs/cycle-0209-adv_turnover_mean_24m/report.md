# cycle-0209-adv_turnover_mean_24m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-006` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `53d4a37b3c495356`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/adv_turnover_mean_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 24개월 ADV20/시가총액 거래회전의 mean가 낮은 종목은 유동성 보상 또는 과도한 관심 교정으로 이후 상대수익이 높다.

## Mechanism

거래 규모를 기업가치로 정규화하거나 가격충격을 직접 측정해 단순 대형주 노출과 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9818875775399842 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9756222755881315 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.07586667139737037 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.07937069586120735 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5436892950263406 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.42258026258578313 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | N | 0.013816857630789275 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.6886558690004123 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.07586667139737037 |
| `ic_t_full` | 6.068047498799278 |
| `ic_p_full` | 4.489668290766237e-08 |
| `ic_investable` | 0.07937069586120735 |
| `ic_std_investable` | 0.14598539384035877 |
| `rank_icir_investable` | 0.5436892950263406 |
| `ic_t_investable` | 6.215639990520942 |
| `ic_p_investable` | 2.5292732732885312e-08 |
| `ic_retention` | 1.0461866113182137 |
| `neutral_ic` | 0.013816857630789275 |
| `neutral_ic_t` | 1.2252067785921708 |
| `neutral_ic_p` | 0.11260359458876282 |
| `neutral_ic_retention` | 0.17408008687425788 |
| `n_trials` | 229 |
| `max_gold_signal_corr` | 0.6886558690004123 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'enterprise_sales_yield_change_6m': 62, 'idiosyncratic_volatility_24m': 62, 'max_daily_return_mean_6m': 62, 'net_income_to_liabilities': 62, 'net_margin_volatility_12m': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'pretax_yield_change_6m': 62, 'price_range_12m': 62, 'realized_daily_volatility_change_24m': 62, 'realized_daily_volatility_instability_6m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T3.2` 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: 0.013816857630789275 (IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `adv_turnover_mean_18m` | other | 0.974 | 63 |
| `adv_turnover_mean_36m` | other | 0.964 | 63 |
| `adv_turnover_volatility_24m` | other | 0.948 | 63 |
| `adv_turnover_volatility_18m` | other | 0.914 | 63 |
| `adv_turnover_volatility_36m` | other | 0.912 | 63 |
| `trading_value_turnover_volatility_24m` | other | 0.851 | 63 |
| `trading_value_volatility_12m` | other | 0.786 | 63 |
| `adv_turnover_volatility_6m` | other | 0.783 | 63 |
| `realized_volatility_252d` | other | 0.719 | 63 |
| `trading_turnover_20d` | other | 0.710 | 63 |
| `trading_value_turnover_volatility_6m` | other | 0.697 | 63 |
| `idiosyncratic_volatility_24m` | other | 0.688 | 63 |
| `adv20_to_book_equity` | other | 0.683 | 63 |
| `max_daily_return_instability_18m` | quality | 0.677 | 63 |
| `max_daily_return_mean_6m` | quality | 0.579 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 유동성 수준·변화 신호와 관련될 수 있어 Gold 상관 gate로 독립성을 확인한다.
- Data notes: 인증된 월말 거래·시가총액·Amihud 입력만 사용하며 결측을 채우지 않는다.
