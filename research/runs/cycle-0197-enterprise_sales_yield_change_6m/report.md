# cycle-0197-enterprise_sales_yield_change_6m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-004` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `7db27be88ae7fe84`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/enterprise_sales_yield_change_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

revenue_ttm 대비 기업가치의 6개월 개선이 큰 기업은 영업규모가 가격에 덜 반영되어 이후 상대수익이 높다.

## Mechanism

매출과 부채를 포함한 기업가치를 결합해 장부자산/시가총액 변화와 다른 가치 재평가를 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 6 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8947291932782108 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.850633062545985 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05753968948484366 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.057153081383966846 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6669377651685581 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3307762485282758 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.032739129567015614 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.5408386461080541 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05753968948484366 |
| `ic_t_full` | 4.842730874870213 |
| `ic_p_full` | 4.562593884844014e-06 |
| `ic_investable` | 0.057153081383966846 |
| `ic_std_investable` | 0.08569477448847465 |
| `rank_icir_investable` | 0.6669377651685581 |
| `ic_t_investable` | 4.827770550298808 |
| `ic_p_investable` | 4.817263260152889e-06 |
| `ic_retention` | 0.9932810186440326 |
| `neutral_ic` | 0.032739129567015614 |
| `neutral_ic_t` | 3.063155223770172 |
| `neutral_ic_p` | 0.0016287754501811955 |
| `neutral_ic_retention` | 0.5728322738553152 |
| `n_trials` | 209 |
| `max_gold_signal_corr` | 0.5408386461080541 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'book_to_market_change_6m': 62, 'capital_stock_growth_18m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'nonoperating_burden_margin': 62, 'operating_earnings_yield': 62, 'pretax_yield_change_6m': 62, 'price_range_12m': 62, 'realized_daily_volatility_change_24m': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `enterprise_sales_yield_change_12m` | value | 0.639 | 63 |
| `book_to_market_change_6m` | value | 0.540 | 63 |
| `medium_term_momentum_6_2` | momentum | -0.455 | 63 |
| `price_momentum_6_1` | momentum | -0.455 | 63 |
| `market_relative_momentum_6_1` | momentum | -0.451 | 63 |
| `asset_turnover_change_12m` | quality | 0.397 | 63 |
| `price_recovery_12m` | momentum | -0.381 | 63 |
| `book_to_market_change_12m` | value | 0.343 | 63 |
| `price_reversal_6_3` | momentum | 0.340 | 63 |
| `short_term_reversal_3m` | momentum | 0.338 | 63 |
| `sales_growth_12m` | other | -0.336 | 63 |
| `high_12m_proximity` | momentum | -0.330 | 63 |
| `asset_turnover_acceleration_12m` | quality | 0.305 | 51 |
| `market_leverage_change_6m` | other | -0.300 | 63 |
| `sales_growth_acceleration_12m` | earnings | 0.291 | 51 |

## Expected relationship and data notes

- Expected relationship: 기존 가치 수준과 관련될 수 있으나 매출/기업가치의 변화로 Gold 0.70 사전검사를 요구한다.
- Data notes: PIT revenue_ttm·total_liabilities와 동시점 market_cap, 정확한 달력 시차만 사용한다.
