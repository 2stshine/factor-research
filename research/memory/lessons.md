# 다음 회차 지침과 누적 시행

> 결정론 코드가 만든다. 새 후보를 세우기 전에 위에서부터 읽는다.
> **판정 결과는 담기지 않는다** — 봉인 OOS 를 지키기 위해 정체성과 구조적 교훈만 남긴다.

## 1. 이번 회차의 제약

최신 성찰의 지시는 봉인 경계 안에 있어 공개하지 않는다.

## 2. 후보 하나가 갖춰야 할 것

`factors/candidates/*.py` 의 `RESEARCH_SPEC` 스키마와 같다. 빈칸이 있으면 등록되지 않는다.

| 항목 | 내용 |
|---|---|
| 이름 | snake_case. 단일 경제 신호 하나 |
| `thesis` | 무엇을 주장하는가 |
| `mechanism` | 왜 초과수익이 나는가. 경제적 메커니즘이지 통계적 기대가 아니다 |
| `falsification` | 무엇을 보면 기각하는가 |
| **`expected_relationship`** | **아래 목록의 어느 팩터와 어떻게 다른가.** 같은 개념의 재구성이면 새 후보가 아니다 |
| `data_notes` | 쓰는 입력과 그 한계 |

> `expected_relationship` 을 빈칸으로 두지 않는다. 이름이 달라도 같은 개념이면 중복이다 —
> 아래 목록에서 **가장 가까운 것을 스스로 지목하고 무엇이 다른지 적는다.**

**요청자가 무엇을 물었든, 후보를 낼 때는 항상 다음 한 줄을 붙인다.**

```
가장 가까운 기존 팩터: <4절 목록에서 하나> — 차이: <한 줄>
```

붙일 대상이 떠오르지 않으면 4절을 다시 읽는다. 목록이 228건이라 "없다"는 답은 거의 틀린다.
같은 변수를 부호나 표현만 뒤집은 것(예: 고점 대비 근접도 ↔ 고점 대비 낙폭,
변동성 ↔ 안정성)은 **새 후보가 아니라 같은 후보**다.

## 3. 어느 쪽이 이미 채워졌나

- Accruals: 1건 등록
- Debt Issuance: 1건 등록
- Investment: 4건 등록
- Low Leverage: 6건 등록
- Low Risk: 9건 등록
- Momentum: 2건 등록
- Profit Growth: 4건 등록
- Profitability: 3건 등록
- Quality: 5건 등록
- Seasonality: 1건 등록
- Short-Term Reversal: 1건 등록
- Size: 1건 등록
- Value: 10건 등록
- (미매칭): 180건

### 구조적 교훈

**campaign-20260806-001 / epoch-001**

- `trading_turnover_20d` (trading_activity) — 시행함
- `working_capital_accruals_12m` (working_capital_accruals) — 시행함
- `earnings_change_to_assets` (quarterly_earnings_change) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260806-001 / epoch-002**

- `market_beta_36m` (market_beta) — 시행함
- `paid_in_capital_ratio` (equity_composition) — 시행함
- `current_liability_concentration` (liability_maturity_structure) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260807-002 / epoch-001**

- `net_working_capital_to_assets` (working_capital_buffer) — 시행함
- `operating_return_on_capital_employed` (capital_employment_efficiency) — 시행함
- `operating_margin_change_12m` (operating_margin_expansion) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260807-002 / epoch-002**

- `posttax_income_conversion` (tax_conversion_efficiency) — 시행함
- `noncurrent_asset_encumbrance` (long_term_asset_encumbrance) — 시행함
- `turnover_volatility_12m` (trading_activity_instability) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260807-002 / epoch-003**

- `equity_growth_12m` (equity_growth) — 시행함
- `positive_return_share_12m` (return_consistency) — 시행함
- `return_kurtosis_24m` (return_tail_concentration) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260808-001 / epoch-001**

- `amihud_illiquidity_1m` (liquidity) — 시행함
- `dividend_yield_ttm` (dividend_yield) — 시행함
- `high_52w_price_proximity` (price_anchoring) — 시행함
- `max_daily_return_1m` (lottery_demand) — 시행함
- `net_equity_issuance_price_adjusted_12m` (net_equity_issuance) — 시행함
- `realized_volatility_252d` (low_volatility) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260809-001 / epoch-001**

- `operating_income_to_liabilities` (operating_obligation_coverage) — 시행함
- `noncurrent_asset_share` (asset_rigidity) — 시행함
- `dividend_event_frequency_ttm` (payout_frequency) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260811-001 / epoch-001**

- `intermediate_momentum_12_7` (intermediate_momentum) — 시행함
- `market_leverage` (market_leverage) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260814-002 / epoch-001**

- `operating_earnings_yield` (operating_earnings_yield) — 시행함
- `retained_earnings_to_equity` (retained_earnings_equity_share) — 시행함
- `current_asset_turnover` (current_asset_turnover) — 시행함
- `idiosyncratic_volatility_24m` (idiosyncratic_volatility) — 시행함
- `operating_income_to_current_liabilities` (short_term_operating_coverage) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-001 / epoch-001**

- `pretax_profit_margin` (pretax_profitability_margin) — 시행함
- `operating_income_to_noncurrent_assets` (long_lived_asset_operating_productivity) — 시행함
- `retained_earnings_to_capital_stock` (earned_to_contributed_capital) — 시행함
- `current_assets_to_total_liabilities` (liquid_asset_debt_coverage) — 시행함
- `revenue_to_total_liabilities` (revenue_debt_turnover) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-002 / epoch-001**

- `capital_stock_growth_12m` (legal_capital_issuance_growth) — 시행함
- `current_assets_growth_12m` (working_capital_investment_growth) — 시행함
- `current_liabilities_growth_12m` (short_term_financing_growth) — 시행함
- `operating_income_growth_12m` (operating_income_growth) — 시행함
- `retained_earnings_growth_12m` (internal_capital_accumulation) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-003 / epoch-001**

- `noncurrent_assets_growth_12m` (long_lived_asset_investment_growth) — 시행함
- `noncurrent_liabilities_growth_12m` (long_term_debt_growth) — 시행함
- `net_income_growth_12m` (trailing_net_income_growth) — 시행함
- `pretax_income_growth_12m` (trailing_pretax_income_growth) — 시행함
- `noncurrent_asset_share_change_12m` (asset_rigidity_change) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-004 / epoch-001**

- `noncurrent_liabilities_to_assets` (long_term_liability_burden) — 시행함
- `current_liabilities_to_assets` (short_term_liability_burden) — 시행함
- `retained_earnings_to_liabilities` (earned_capital_debt_coverage) — 시행함
- `pretax_income_to_liabilities` (pretax_debt_coverage) — 시행함
- `net_income_to_liabilities` (posttax_debt_coverage) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-005 / epoch-001**

- `current_ratio_change_12m` (short_term_solvency_change) — 시행함
- `net_profit_margin_change_12m` (net_margin_expansion) — 시행함
- `market_leverage_change_12m` (market_leverage_change) — 시행함
- `retained_earnings_to_assets_change_12m` (retained_earnings_accumulation) — 시행함
- `noncurrent_liability_share_change_12m` (liability_maturity_change) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-006 / epoch-001**

- `net_roa_volatility_36m` (net_profitability_stability) — 시행함
- `pretax_roa_volatility_36m` (pretax_profitability_stability) — 시행함
- `net_margin_volatility_36m` (net_margin_stability) — 시행함
- `pretax_margin_volatility_36m` (pretax_margin_stability) — 시행함
- `asset_turnover_volatility_36m` (asset_efficiency_stability) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-007 / epoch-001**

- `asset_growth_acceleration_12m` (investment_acceleration) — 시행함
- `capital_stock_to_liabilities` (nominal_capital_debt_coverage) — 시행함
- `current_assets_to_assets` (asset_liquidity_share) — 시행함
- `book_to_market_change_12m` (book_value_repricing) — 시행함
- `capital_stock_to_assets` (nominal_capital_intensity) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-008 / epoch-001**

- `current_assets_growth_acceleration_12m` (working_asset_acceleration) — 시행함
- `current_assets_to_equity` (equity_liquidity_capacity) — 시행함
- `net_working_capital_to_liabilities` (working_capital_debt_coverage) — 시행함
- `net_working_capital_yield` (liquid_asset_value) — 시행함
- `noncurrent_assets_to_equity` (equity_asset_rigidity) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-009 / epoch-001**

- `current_liabilities_growth_acceleration_12m` (short_term_debt_acceleration) — 시행함
- `operating_income_to_equity` (operating_book_equity_return) — 시행함
- `revenue_to_noncurrent_assets` (long_lived_asset_revenue_productivity) — 시행함
- `short_term_reversal_3m` (short_term_reversal_3m) — 시행함
- `noncurrent_liabilities_to_equity` (long_term_book_leverage) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-010 / epoch-001**

- `equity_growth_acceleration_12m` (equity_expansion_acceleration) — 시행함
- `liability_growth_acceleration_12m` (debt_growth_acceleration) — 시행함
- `operating_income_to_noncurrent_liabilities` (long_term_operating_coverage) — 시행함
- `revenue_to_equity` (equity_revenue_productivity) — 시행함
- `medium_term_momentum_6_2` (medium_term_momentum) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-011 / epoch-001**

- `net_income_to_noncurrent_assets` (long_asset_net_productivity) — 시행함
- `net_income_to_current_assets` (current_asset_net_productivity) — 시행함
- `revenue_to_noncurrent_liabilities` (long_term_revenue_coverage) — 시행함
- `adv20_to_book_equity` (book_scaled_trading_activity) — 시행함
- `price_trend_efficiency_12m` (directional_price_efficiency) — 시행함
- `working_capital_to_sales` (working_capital_sales_buffer) — 시행함
- `retained_earnings_yield` (accumulated_earnings_value) — 시행함
- `capital_stock_yield` (legal_capital_value) — 시행함
- `current_liabilities_to_sales` (short_term_funding_sales_burden) — 시행함
- `asset_to_market` (asset_backed_value) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-012 / epoch-001**

- `revenue_to_current_assets` (working_asset_revenue_productivity) — 시행함
- `pretax_income_to_equity` (pretax_book_equity_return) — 시행함
- `retained_earnings_growth_acceleration_12m` (internal_capital_acceleration) — 시행함
- `operating_income_to_current_assets` (current_asset_operating_productivity) — 시행함
- `revenue_to_capital_stock` (legal_capital_revenue_productivity) — 시행함
- `equity_to_noncurrent_liabilities` (long_term_equity_solvency) — 시행함
- `current_assets_to_noncurrent_assets` (flexible_asset_mix) — 시행함
- `amihud_change_12m` (liquidity_deterioration) — 시행함
- `price_range_12m` (price_range_risk) — 시행함
- `momentum_acceleration_6m` (price_momentum_acceleration) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-013 / epoch-001**

- `retained_earnings_to_noncurrent_assets` (internal_capital_long_asset_backing) — 시행함
- `retained_earnings_to_current_assets` (internal_capital_current_asset_backing) — 시행함
- `capital_stock_to_current_assets` (legal_capital_current_asset_intensity) — 시행함
- `equity_to_current_liabilities` (short_term_equity_solvency) — 시행함
- `operating_income_to_capital_stock` (legal_capital_operating_return) — 시행함
- `current_assets_yield` (liquid_asset_value) — 시행함
- `daily_volatility_change_12m` (risk_deterioration) — 시행함
- `max_daily_return_change_12m` (lottery_demand_acceleration) — 시행함
- `market_relative_momentum_12_1` (market_relative_momentum) — 시행함
- `turnover_change_6m` (trading_attention_change) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-014 / epoch-001**

- `operating_coverage_change_12m` (short_term_operating_coverage_improvement) — 시행함
- `revenue_to_current_liabilities` (short_term_revenue_coverage) — 시행함
- `retained_earnings_to_current_liabilities` (internal_capital_short_debt_coverage) — 시행함
- `capital_stock_to_current_liabilities` (legal_capital_short_debt_coverage) — 시행함
- `noncurrent_assets_yield` (long_lived_asset_value) — 시행함
- `current_liabilities_yield` (market_short_debt_burden) — 시행함
- `amihud_volatility_12m` (liquidity_instability) — 시행함
- `trading_value_volatility_12m` (trading_attention_instability) — 시행함
- `return_persistence_12m` (monthly_return_persistence) — 시행함
- `nonoperating_burden_margin` (nonoperating_sales_burden) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260815-015 / epoch-001**

- `net_income_to_capital_stock` (legal_capital_net_return) — 시행함
- `retained_earnings_to_noncurrent_liabilities` (internal_capital_long_debt_coverage) — 시행함
- `working_capital_growth_12m` (working_capital_investment) — 시행함
- `equity_debt_coverage_change_12m` (book_solvency_improvement) — 시행함
- `capital_stock_share_change_12m` (contributed_capital_share_change) — 시행함
- `noncurrent_assets_to_capital_stock` (legal_capital_long_asset_backing) — 시행함
- `noncurrent_liabilities_yield` (market_long_debt_burden) — 시행함
- `adv20_change_12m` (trading_liquidity_growth) — 시행함
- `price_recovery_12m` (price_recovery_from_low) — 시행함
- `return_gain_loss_ratio_12m` (return_magnitude_asymmetry) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-001 / epoch-001**

- `price_momentum_9_2` (price_momentum_9_2) — 시행함
- `high_24m_proximity` (high_24m_proximity) — 시행함
- `amihud_mean_6m` (amihud_mean_6m) — 시행함
- `amihud_volatility_6m` (amihud_volatility_6m) — 시행함
- `realized_daily_volatility_change_6m` (realized_daily_volatility_change_6m) — 시행함
- `market_beta_6m` (market_beta_6m) — 시행함
- `total_asset_growth_6m` (total_asset_growth_6m) — 시행함
- `capital_stock_growth_6m` (capital_stock_growth_6m) — 시행함
- `book_to_market_change_6m` (book_to_market_change_6m) — 시행함
- `operating_margin_change_6m` (operating_margin_change_6m) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-002 / epoch-001**

- `price_momentum_15_3` (price_momentum_15_3) — 시행함
- `price_recovery_24m` (price_recovery_24m) — 시행함
- `amihud_mean_18m` (amihud_mean_18m) — 시행함
- `amihud_volatility_18m` (amihud_volatility_18m) — 시행함
- `max_daily_return_change_6m` (max_daily_return_change_6m) — 시행함
- `market_beta_9m` (market_beta_9m) — 시행함
- `total_asset_growth_18m` (total_asset_growth_18m) — 시행함
- `capital_stock_growth_18m` (capital_stock_growth_18m) — 시행함
- `earnings_yield_change_12m` (earnings_yield_change_12m) — 시행함
- `net_margin_change_6m` (net_margin_change_6m) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-003 / epoch-001**

- `price_momentum_18_6` (price_momentum_18_6) — 시행함
- `positive_return_share_24m` (positive_return_share_24m) — 시행함
- `amihud_mean_24m` (amihud_mean_24m) — 시행함
- `amihud_volatility_24m` (amihud_volatility_24m) — 시행함
- `realized_daily_volatility_change_24m` (realized_daily_volatility_change_24m) — 시행함
- `market_beta_12m` (market_beta_12m) — 시행함
- `total_asset_growth_24m` (total_asset_growth_24m) — 시행함
- `equity_growth_6m` (equity_growth_6m) — 시행함
- `pretax_yield_change_6m` (pretax_yield_change_6m) — 시행함
- `retained_earnings_to_assets_change_6m` (retained_earnings_to_assets_change_6m) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-004 / epoch-0001**

- `price_momentum_24_6` (price_momentum_24_6) — 시행함
- `return_seasonality_12m` (return_seasonality_12m) — 시행함
- `amihud_mean_36m` (amihud_mean_36m) — 시행함
- `amihud_volatility_36m` (amihud_volatility_36m) — 시행함
- `realized_daily_volatility_instability_6m` (realized_daily_volatility_instability_6m) — 시행함
- `market_beta_18m` (market_beta_18m) — 시행함
- `total_asset_growth_30m` (total_asset_growth_30m) — 시행함
- `equity_growth_24m` (equity_growth_24m) — 시행함
- `enterprise_sales_yield_change_6m` (enterprise_sales_yield_change_6m) — 시행함
- `net_to_operating_income_conversion` (net_to_operating_income_conversion) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-005 / epoch-0001**

- `adv_turnover_mean_18m` (adv_turnover_mean_18m) — 시행함
- `price_momentum_6_1` (price_momentum_6_1) — 시행함
- `market_beta_24m` (market_beta_24m) — 시행함
- `max_daily_return_mean_6m` (max_daily_return_mean_6m) — 시행함
- `operating_yield_change_12m` (operating_yield_change_12m) — 시행함
- `market_leverage_change_6m` (market_leverage_change_6m) — 시행함
- `noncurrent_asset_growth_6m` (noncurrent_asset_growth_6m) — 시행함
- `price_trend_efficiency_24m` (price_trend_efficiency_24m) — 시행함
- `net_margin_volatility_12m` (net_margin_volatility_12m) — 시행함
- `working_capital_accruals_6m` (working_capital_accruals_6m) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-006 / epoch-0001**

- `adv_turnover_mean_24m` (adv_turnover_mean_24m) — 시행함
- `price_reversal_3_1` (price_reversal_3_1) — 시행함
- `market_return_correlation_6m` (market_return_correlation_6m) — 시행함
- `max_daily_return_change_18m` (max_daily_return_change_18m) — 시행함
- `pretax_yield_change_12m` (pretax_yield_change_12m) — 시행함
- `market_leverage_change_18m` (market_leverage_change_18m) — 시행함
- `noncurrent_asset_growth_18m` (noncurrent_asset_growth_18m) — 시행함
- `net_equity_issuance_price_adjusted_36m` (net_equity_issuance_price_adjusted_36m) — 시행함
- `pretax_to_operating_income_conversion` (pretax_to_operating_income_conversion) — 시행함
- `working_capital_accruals_24m` (working_capital_accruals_24m) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

**campaign-20260816-007 / epoch-0001**

- `adv_turnover_mean_36m` (adv_turnover_mean_36m) — 시행함
- `price_reversal_6_3` (price_reversal_6_3) — 시행함
- `market_return_correlation_9m` (market_return_correlation_9m) — 시행함
- `max_daily_return_instability_18m` (max_daily_return_instability_18m) — 시행함
- `enterprise_earnings_yield_change_12m` (enterprise_earnings_yield_change_12m) — 시행함
- `market_leverage_change_24m` (market_leverage_change_24m) — 시행함
- `noncurrent_asset_growth_24m` (noncurrent_asset_growth_24m) — 시행함
- `retained_earnings_to_assets_volatility_12m` (retained_earnings_to_assets_volatility_12m) — 시행함
- `trading_value_turnover_change_3m` (trading_value_turnover_change_3m) — 시행함
- `market_relative_momentum_6_1` (market_relative_momentum_6_1) — 시행함
- 결과는 봉인 경계 뒤라 싣지 않는다. 무엇을 시도했는지만 남는다.

## 4. 시행 전량

시행 228건 · 생략 없음

| cycle | factor | family | ruleset | 테마 | 데이터 |
|---|---|---|---|---|---|
| `cycle-0001-low_vol_12m` | `low_vol_12m` | `low_volatility` | `fr-2.0.0` | Low Risk | Price |
| `cycle-0002-asset_growth_12m` | `asset_growth_12m` | `asset_growth` | `fr-2.0.0` | Investment | Accounting |
| `cycle-0003-downside_vol_12m` | `downside_vol_12m` | `low_volatility` | `fr-2.0.0` | Low Risk | Price |
| `cycle-0004-defensive_value` | `defensive_value` | `defensive_value` | `fr-2.0.0` | Value | Accounting |
| `cycle-0005-solvent_value` | `solvent_value` | `defensive_value` | `fr-2.0.0` | Value | Accounting |
| `cycle-0006-small_value` | `small_value` | `small_value` | `fr-2.0.0` | Value | Accounting |
| `cycle-0007-defensive_small_value` | `defensive_small_value` | `small_value` | `fr-2.0.0` | Value | Accounting |
| `cycle-0008-high_12m_proximity` | `high_12m_proximity` | `price_anchoring` | `fr-2.0.0` | Momentum | Price |
| `cycle-0009-earnings_confirmed_small_value` | `earnings_confirmed_small_value` | `catalyst_small_value` | `fr-2.0.0` | Value | Accounting |
| `cycle-0010-quality_stability` | `quality_stability` | `quality_stability` | `fr-2.0.0` | Quality | Accounting |
| `cycle-0011-profitable_small_value` | `profitable_small_value` | `quality_small_value` | `fr-2.0.0` | Value | Accounting |
| `cycle-0012-operating_roa` | `operating_roa` | `operating_roa` | `fr-3.1.0` | Quality | Accounting |
| `cycle-0013-net_profit_margin` | `net_profit_margin` | `net_profit_margin` | `fr-3.2.0` | Profitability | Accounting |
| `cycle-0014-sales_growth_12m` | `sales_growth_12m` | `sales_growth` | `fr-3.2.0` | Investment | Accounting |
| `cycle-0015-operating_roa_change_12m` | `operating_roa_change_12m` | `profitability_change` | `fr-3.2.0` | Profit Growth | Accounting |
| `cycle-0016-long_term_reversal_36_12` | `long_term_reversal_36_12` | `long_term_reversal` | `fr-3.2.0` | Investment | Price |
| `cycle-0017-net_roa` | `net_roa` | `net_roa` | `fr-3.2.0` | Quality | Accounting |
| `cycle-0018-liability_growth_12m` | `liability_growth_12m` | `liability_growth` | `fr-3.2.0` | Debt Issuance | Accounting |
| `cycle-0019-asset_turnover_change_12m` | `asset_turnover_change_12m` | `asset_turnover_change` | `fr-3.2.0` | Quality | Accounting |
| `cycle-0020-return_skewness_24m` | `return_skewness_24m` | `return_skewness` | `fr-3.2.0` | Short-Term Reversal | Price |
| `cycle-0021-net_equity_issuance_12m` | `net_equity_issuance_12m` | `net_equity_issuance` | `fr-3.2.0` | Value | Accounting |
| `cycle-0022-operating_roa_volatility_36m` | `operating_roa_volatility_36m` | `profitability_stability` | `fr-3.2.0` | Low Risk | Accounting |
| `cycle-0023-annual_seasonality_5y` | `annual_seasonality_5y` | `return_seasonality` | `fr-3.2.0` | Seasonality | Price |
| `cycle-0024-retained_earnings_to_assets` | `retained_earnings_to_assets` | `internal_financing` | `fr-3.2.0` | Low Leverage | Accounting |
| `cycle-0025-current_ratio` | `current_ratio` | `short_term_solvency` | `fr-3.2.0` | Low Leverage | Accounting |
| `cycle-0026-nonoperating_burden_to_assets` | `nonoperating_burden_to_assets` | `nonoperating_burden` | `fr-3.2.0` | - | Accounting |
| `cycle-0027-max_monthly_return_12m` | `max_monthly_return_12m` | `lottery_demand` | `fr-3.2.0` | Low Risk | Price |
| `cycle-0028-trading_turnover_20d` | `trading_turnover_20d` | `trading_activity` | `fr-3.5.0` | Low Risk | Trading |
| `cycle-0029-working_capital_accruals_12m` | `working_capital_accruals_12m` | `working_capital_accruals` | `fr-3.5.0` | Accruals | Accounting |
| `cycle-0030-earnings_change_to_assets` | `earnings_change_to_assets` | `quarterly_earnings_change` | `fr-3.5.0` | Profit Growth | Accounting |
| `cycle-0031-market_beta_36m` | `market_beta_36m` | `market_beta` | `fr-3.5.0` | Low Risk | Price |
| `cycle-0032-paid_in_capital_ratio` | `paid_in_capital_ratio` | `equity_composition` | `fr-3.5.0` | - | Accounting |
| `cycle-0033-current_liability_concentration` | `current_liability_concentration` | `liability_maturity_structure` | `fr-3.5.0` | Low Leverage | Accounting |
| `cycle-0034-net_working_capital_to_assets` | `net_working_capital_to_assets` | `working_capital_buffer` | `fr-3.9.0` | Low Leverage | Accounting |
| `cycle-0035-operating_return_on_capital_employed` | `operating_return_on_capital_employed` | `capital_employment_efficiency` | `fr-3.9.0` | Profitability | Accounting |
| `cycle-0036-operating_margin_change_12m` | `operating_margin_change_12m` | `operating_margin_expansion` | `fr-3.9.0` | Profit Growth | Accounting |
| `cycle-0037-posttax_income_conversion` | `posttax_income_conversion` | `tax_conversion_efficiency` | `fr-3.9.0` | - | Accounting |
| `cycle-0038-noncurrent_asset_encumbrance` | `noncurrent_asset_encumbrance` | `long_term_asset_encumbrance` | `fr-3.9.0` | Low Leverage | Accounting |
| `cycle-0039-turnover_volatility_12m` | `turnover_volatility_12m` | `trading_activity_instability` | `fr-3.9.0` | Profitability | Trading |
| `cycle-0040-equity_growth_12m` | `equity_growth_12m` | `equity_growth` | `fr-3.9.0` | Investment | Accounting |
| `cycle-0041-positive_return_share_12m` | `positive_return_share_12m` | `return_consistency` | `fr-3.9.0` | - | Price |
| `cycle-0042-return_kurtosis_24m` | `return_kurtosis_24m` | `return_tail_concentration` | `fr-3.9.0` | Low Risk | Price |
| `cycle-0043-amihud_illiquidity_1m` | `amihud_illiquidity_1m` | `liquidity` | `fr-3.10.1` | Size | Trading |
| `cycle-0044-dividend_yield_ttm` | `dividend_yield_ttm` | `dividend_yield` | `fr-3.10.1` | Value | Accounting |
| `cycle-0045-high_52w_price_proximity` | `high_52w_price_proximity` | `price_anchoring` | `fr-3.10.1` | Momentum | Price |
| `cycle-0046-max_daily_return_1m` | `max_daily_return_1m` | `lottery_demand` | `fr-3.10.1` | Low Risk | Price |
| `cycle-0047-net_equity_issuance_price_adjusted_12m` | `net_equity_issuance_price_adjusted_12m` | `net_equity_issuance` | `fr-3.10.1` | Value | Accounting |
| `cycle-0048-realized_volatility_252d` | `realized_volatility_252d` | `low_volatility` | `fr-3.10.1` | Low Risk | Price |
| `cycle-0049-operating_income_to_liabilities` | `operating_income_to_liabilities` | `operating_obligation_coverage` | `fr-3.10.1` | Quality | Accounting |
| `cycle-0050-noncurrent_asset_share` | `noncurrent_asset_share` | `asset_rigidity` | `fr-3.10.1` | Low Leverage | Accounting |
| `cycle-0051-dividend_event_frequency_ttm` | `dividend_event_frequency_ttm` | `payout_frequency` | `fr-3.10.1` | - | Event |
| `cycle-0052-intermediate_momentum_12_7` | `intermediate_momentum_12_7` | `intermediate_momentum` | `fr-3.10.1` | Profit Growth | Price |
| `cycle-0053-market_leverage` | `market_leverage` | `market_leverage` | `fr-3.10.1` | Value | Accounting |
| `cycle-0054-operating_earnings_yield` | `operating_earnings_yield` | `operating_earnings_yield` | `fr-3.13.0` | - | - |
| `cycle-0055-retained_earnings_to_equity` | `retained_earnings_to_equity` | `retained_earnings_equity_share` | `fr-3.13.0` | - | - |
| `cycle-0056-current_asset_turnover` | `current_asset_turnover` | `current_asset_turnover` | `fr-3.13.0` | - | - |
| `cycle-0057-idiosyncratic_volatility_24m` | `idiosyncratic_volatility_24m` | `idiosyncratic_volatility` | `fr-3.13.0` | - | - |
| `cycle-0058-operating_income_to_current_liabilities` | `operating_income_to_current_liabilities` | `short_term_operating_coverage` | `fr-3.13.0` | - | - |
| `cycle-0059-pretax_profit_margin` | `pretax_profit_margin` | `pretax_profitability_margin` | `fr-3.13.0` | - | - |
| `cycle-0060-operating_income_to_noncurrent_assets` | `operating_income_to_noncurrent_assets` | `long_lived_asset_operating_productivity` | `fr-3.13.0` | - | - |
| `cycle-0061-retained_earnings_to_capital_stock` | `retained_earnings_to_capital_stock` | `earned_to_contributed_capital` | `fr-3.13.0` | - | - |
| `cycle-0062-current_assets_to_total_liabilities` | `current_assets_to_total_liabilities` | `liquid_asset_debt_coverage` | `fr-3.13.0` | - | - |
| `cycle-0063-revenue_to_total_liabilities` | `revenue_to_total_liabilities` | `revenue_debt_turnover` | `fr-3.13.0` | - | - |
| `cycle-0064-capital_stock_growth_12m` | `capital_stock_growth_12m` | `legal_capital_issuance_growth` | `fr-3.13.0` | - | - |
| `cycle-0065-current_assets_growth_12m` | `current_assets_growth_12m` | `working_capital_investment_growth` | `fr-3.13.0` | - | - |
| `cycle-0066-current_liabilities_growth_12m` | `current_liabilities_growth_12m` | `short_term_financing_growth` | `fr-3.13.0` | - | - |
| `cycle-0067-operating_income_growth_12m` | `operating_income_growth_12m` | `operating_income_growth` | `fr-3.13.0` | - | - |
| `cycle-0068-retained_earnings_growth_12m` | `retained_earnings_growth_12m` | `internal_capital_accumulation` | `fr-3.13.0` | - | - |
| `cycle-0069-noncurrent_assets_growth_12m` | `noncurrent_assets_growth_12m` | `long_lived_asset_investment_growth` | `fr-3.13.0` | - | - |
| `cycle-0070-noncurrent_liabilities_growth_12m` | `noncurrent_liabilities_growth_12m` | `long_term_debt_growth` | `fr-3.13.0` | - | - |
| `cycle-0071-net_income_growth_12m` | `net_income_growth_12m` | `trailing_net_income_growth` | `fr-3.13.0` | - | - |
| `cycle-0072-pretax_income_growth_12m` | `pretax_income_growth_12m` | `trailing_pretax_income_growth` | `fr-3.13.0` | - | - |
| `cycle-0073-noncurrent_asset_share_change_12m` | `noncurrent_asset_share_change_12m` | `asset_rigidity_change` | `fr-3.13.0` | - | - |
| `cycle-0074-noncurrent_liabilities_to_assets` | `noncurrent_liabilities_to_assets` | `long_term_liability_burden` | `fr-3.13.0` | - | - |
| `cycle-0075-current_liabilities_to_assets` | `current_liabilities_to_assets` | `short_term_liability_burden` | `fr-3.13.0` | - | - |
| `cycle-0076-retained_earnings_to_liabilities` | `retained_earnings_to_liabilities` | `earned_capital_debt_coverage` | `fr-3.13.0` | - | - |
| `cycle-0077-pretax_income_to_liabilities` | `pretax_income_to_liabilities` | `pretax_debt_coverage` | `fr-3.13.0` | - | - |
| `cycle-0078-net_income_to_liabilities` | `net_income_to_liabilities` | `posttax_debt_coverage` | `fr-3.13.0` | - | - |
| `cycle-0079-current_ratio_change_12m` | `current_ratio_change_12m` | `short_term_solvency_change` | `fr-3.13.0` | - | - |
| `cycle-0080-net_profit_margin_change_12m` | `net_profit_margin_change_12m` | `net_margin_expansion` | `fr-3.13.0` | - | - |
| `cycle-0081-market_leverage_change_12m` | `market_leverage_change_12m` | `market_leverage_change` | `fr-3.13.0` | - | - |
| `cycle-0082-retained_earnings_to_assets_change_12m` | `retained_earnings_to_assets_change_12m` | `retained_earnings_accumulation` | `fr-3.13.0` | - | - |
| `cycle-0083-noncurrent_liability_share_change_12m` | `noncurrent_liability_share_change_12m` | `liability_maturity_change` | `fr-3.13.0` | - | - |
| `cycle-0084-net_roa_volatility_36m` | `net_roa_volatility_36m` | `net_profitability_stability` | `fr-3.13.0` | - | - |
| `cycle-0085-pretax_roa_volatility_36m` | `pretax_roa_volatility_36m` | `pretax_profitability_stability` | `fr-3.13.0` | - | - |
| `cycle-0086-net_margin_volatility_36m` | `net_margin_volatility_36m` | `net_margin_stability` | `fr-3.13.0` | - | - |
| `cycle-0087-pretax_margin_volatility_36m` | `pretax_margin_volatility_36m` | `pretax_margin_stability` | `fr-3.13.0` | - | - |
| `cycle-0088-asset_turnover_volatility_36m` | `asset_turnover_volatility_36m` | `asset_efficiency_stability` | `fr-3.13.0` | - | - |
| `cycle-0089-asset_growth_acceleration_12m` | `asset_growth_acceleration_12m` | `investment_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0090-capital_stock_to_liabilities` | `capital_stock_to_liabilities` | `nominal_capital_debt_coverage` | `fr-3.14.0` | - | - |
| `cycle-0091-current_assets_to_assets` | `current_assets_to_assets` | `asset_liquidity_share` | `fr-3.14.0` | - | - |
| `cycle-0092-book_to_market_change_12m` | `book_to_market_change_12m` | `book_value_repricing` | `fr-3.14.0` | - | - |
| `cycle-0093-capital_stock_to_assets` | `capital_stock_to_assets` | `nominal_capital_intensity` | `fr-3.14.0` | - | - |
| `cycle-0094-current_assets_growth_acceleration_12m` | `current_assets_growth_acceleration_12m` | `working_asset_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0095-current_assets_to_equity` | `current_assets_to_equity` | `equity_liquidity_capacity` | `fr-3.14.0` | - | - |
| `cycle-0096-net_working_capital_to_liabilities` | `net_working_capital_to_liabilities` | `working_capital_debt_coverage` | `fr-3.14.0` | - | - |
| `cycle-0097-net_working_capital_yield` | `net_working_capital_yield` | `liquid_asset_value` | `fr-3.14.0` | - | - |
| `cycle-0098-noncurrent_assets_to_equity` | `noncurrent_assets_to_equity` | `equity_asset_rigidity` | `fr-3.14.0` | - | - |
| `cycle-0099-current_liabilities_growth_acceleration_12m` | `current_liabilities_growth_acceleration_12m` | `short_term_debt_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0100-operating_income_to_equity` | `operating_income_to_equity` | `operating_book_equity_return` | `fr-3.14.0` | - | - |
| `cycle-0101-revenue_to_noncurrent_assets` | `revenue_to_noncurrent_assets` | `long_lived_asset_revenue_productivity` | `fr-3.14.0` | - | - |
| `cycle-0102-short_term_reversal_3m` | `short_term_reversal_3m` | `short_term_reversal_3m` | `fr-3.14.0` | - | - |
| `cycle-0103-noncurrent_liabilities_to_equity` | `noncurrent_liabilities_to_equity` | `long_term_book_leverage` | `fr-3.14.0` | - | - |
| `cycle-0104-equity_growth_acceleration_12m` | `equity_growth_acceleration_12m` | `equity_expansion_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0105-liability_growth_acceleration_12m` | `liability_growth_acceleration_12m` | `debt_growth_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0106-operating_income_to_noncurrent_liabilities` | `operating_income_to_noncurrent_liabilities` | `long_term_operating_coverage` | `fr-3.14.0` | - | - |
| `cycle-0107-revenue_to_equity` | `revenue_to_equity` | `equity_revenue_productivity` | `fr-3.14.0` | - | - |
| `cycle-0108-medium_term_momentum_6_2` | `medium_term_momentum_6_2` | `medium_term_momentum` | `fr-3.14.0` | - | - |
| `cycle-0109-net_income_to_noncurrent_assets` | `net_income_to_noncurrent_assets` | `long_asset_net_productivity` | `fr-3.14.0` | - | - |
| `cycle-0110-net_income_to_current_assets` | `net_income_to_current_assets` | `current_asset_net_productivity` | `fr-3.14.0` | - | - |
| `cycle-0111-revenue_to_noncurrent_liabilities` | `revenue_to_noncurrent_liabilities` | `long_term_revenue_coverage` | `fr-3.14.0` | - | - |
| `cycle-0112-adv20_to_book_equity` | `adv20_to_book_equity` | `book_scaled_trading_activity` | `fr-3.14.0` | - | - |
| `cycle-0113-price_trend_efficiency_12m` | `price_trend_efficiency_12m` | `directional_price_efficiency` | `fr-3.14.0` | - | - |
| `cycle-0114-working_capital_to_sales` | `working_capital_to_sales` | `working_capital_sales_buffer` | `fr-3.14.0` | - | - |
| `cycle-0115-retained_earnings_yield` | `retained_earnings_yield` | `accumulated_earnings_value` | `fr-3.14.0` | - | - |
| `cycle-0116-capital_stock_yield` | `capital_stock_yield` | `legal_capital_value` | `fr-3.14.0` | - | - |
| `cycle-0117-current_liabilities_to_sales` | `current_liabilities_to_sales` | `short_term_funding_sales_burden` | `fr-3.14.0` | - | - |
| `cycle-0118-asset_to_market` | `asset_to_market` | `asset_backed_value` | `fr-3.14.0` | - | - |
| `cycle-0119-revenue_to_current_assets` | `revenue_to_current_assets` | `working_asset_revenue_productivity` | `fr-3.14.0` | - | - |
| `cycle-0120-pretax_income_to_equity` | `pretax_income_to_equity` | `pretax_book_equity_return` | `fr-3.14.0` | - | - |
| `cycle-0121-retained_earnings_growth_acceleration_12m` | `retained_earnings_growth_acceleration_12m` | `internal_capital_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0122-operating_income_to_current_assets` | `operating_income_to_current_assets` | `current_asset_operating_productivity` | `fr-3.14.0` | - | - |
| `cycle-0123-revenue_to_capital_stock` | `revenue_to_capital_stock` | `legal_capital_revenue_productivity` | `fr-3.14.0` | - | - |
| `cycle-0124-equity_to_noncurrent_liabilities` | `equity_to_noncurrent_liabilities` | `long_term_equity_solvency` | `fr-3.14.0` | - | - |
| `cycle-0125-current_assets_to_noncurrent_assets` | `current_assets_to_noncurrent_assets` | `flexible_asset_mix` | `fr-3.14.0` | - | - |
| `cycle-0126-amihud_change_12m` | `amihud_change_12m` | `liquidity_deterioration` | `fr-3.14.0` | - | - |
| `cycle-0127-price_range_12m` | `price_range_12m` | `price_range_risk` | `fr-3.14.0` | - | - |
| `cycle-0128-momentum_acceleration_6m` | `momentum_acceleration_6m` | `price_momentum_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0129-retained_earnings_to_noncurrent_assets` | `retained_earnings_to_noncurrent_assets` | `internal_capital_long_asset_backing` | `fr-3.14.0` | - | - |
| `cycle-0130-retained_earnings_to_current_assets` | `retained_earnings_to_current_assets` | `internal_capital_current_asset_backing` | `fr-3.14.0` | - | - |
| `cycle-0131-capital_stock_to_current_assets` | `capital_stock_to_current_assets` | `legal_capital_current_asset_intensity` | `fr-3.14.0` | - | - |
| `cycle-0132-equity_to_current_liabilities` | `equity_to_current_liabilities` | `short_term_equity_solvency` | `fr-3.14.0` | - | - |
| `cycle-0133-operating_income_to_capital_stock` | `operating_income_to_capital_stock` | `legal_capital_operating_return` | `fr-3.14.0` | - | - |
| `cycle-0134-current_assets_yield` | `current_assets_yield` | `liquid_asset_value` | `fr-3.14.0` | - | - |
| `cycle-0135-daily_volatility_change_12m` | `daily_volatility_change_12m` | `risk_deterioration` | `fr-3.14.0` | - | - |
| `cycle-0136-max_daily_return_change_12m` | `max_daily_return_change_12m` | `lottery_demand_acceleration` | `fr-3.14.0` | - | - |
| `cycle-0137-market_relative_momentum_12_1` | `market_relative_momentum_12_1` | `market_relative_momentum` | `fr-3.14.0` | - | - |
| `cycle-0138-turnover_change_6m` | `turnover_change_6m` | `trading_attention_change` | `fr-3.14.0` | - | - |
| `cycle-0139-operating_coverage_change_12m` | `operating_coverage_change_12m` | `short_term_operating_coverage_improvement` | `fr-3.14.0` | - | - |
| `cycle-0140-revenue_to_current_liabilities` | `revenue_to_current_liabilities` | `short_term_revenue_coverage` | `fr-3.14.0` | - | - |
| `cycle-0141-retained_earnings_to_current_liabilities` | `retained_earnings_to_current_liabilities` | `internal_capital_short_debt_coverage` | `fr-3.14.0` | - | - |
| `cycle-0142-capital_stock_to_current_liabilities` | `capital_stock_to_current_liabilities` | `legal_capital_short_debt_coverage` | `fr-3.14.0` | - | - |
| `cycle-0143-noncurrent_assets_yield` | `noncurrent_assets_yield` | `long_lived_asset_value` | `fr-3.14.0` | - | - |
| `cycle-0144-current_liabilities_yield` | `current_liabilities_yield` | `market_short_debt_burden` | `fr-3.14.0` | - | - |
| `cycle-0145-amihud_volatility_12m` | `amihud_volatility_12m` | `liquidity_instability` | `fr-3.14.0` | - | - |
| `cycle-0146-trading_value_volatility_12m` | `trading_value_volatility_12m` | `trading_attention_instability` | `fr-3.14.0` | - | - |
| `cycle-0147-return_persistence_12m` | `return_persistence_12m` | `monthly_return_persistence` | `fr-3.14.0` | - | - |
| `cycle-0148-nonoperating_burden_margin` | `nonoperating_burden_margin` | `nonoperating_sales_burden` | `fr-3.14.0` | - | - |
| `cycle-0149-net_income_to_capital_stock` | `net_income_to_capital_stock` | `legal_capital_net_return` | `fr-3.14.0` | - | - |
| `cycle-0150-retained_earnings_to_noncurrent_liabilities` | `retained_earnings_to_noncurrent_liabilities` | `internal_capital_long_debt_coverage` | `fr-3.14.0` | - | - |
| `cycle-0151-working_capital_growth_12m` | `working_capital_growth_12m` | `working_capital_investment` | `fr-3.14.0` | - | - |
| `cycle-0152-equity_debt_coverage_change_12m` | `equity_debt_coverage_change_12m` | `book_solvency_improvement` | `fr-3.14.0` | - | - |
| `cycle-0153-capital_stock_share_change_12m` | `capital_stock_share_change_12m` | `contributed_capital_share_change` | `fr-3.14.0` | - | - |
| `cycle-0154-noncurrent_assets_to_capital_stock` | `noncurrent_assets_to_capital_stock` | `legal_capital_long_asset_backing` | `fr-3.14.0` | - | - |
| `cycle-0155-noncurrent_liabilities_yield` | `noncurrent_liabilities_yield` | `market_long_debt_burden` | `fr-3.14.0` | - | - |
| `cycle-0156-adv20_change_12m` | `adv20_change_12m` | `trading_liquidity_growth` | `fr-3.14.0` | - | - |
| `cycle-0157-price_recovery_12m` | `price_recovery_12m` | `price_recovery_from_low` | `fr-3.14.0` | - | - |
| `cycle-0158-return_gain_loss_ratio_12m` | `return_gain_loss_ratio_12m` | `return_magnitude_asymmetry` | `fr-3.14.0` | - | - |
| `cycle-0159-price_momentum_9_2` | `price_momentum_9_2` | `price_momentum_9_2` | `fr-3.16.0` | - | - |
| `cycle-0160-high_24m_proximity` | `high_24m_proximity` | `high_24m_proximity` | `fr-3.16.0` | - | - |
| `cycle-0161-amihud_mean_6m` | `amihud_mean_6m` | `amihud_mean_6m` | `fr-3.16.0` | - | - |
| `cycle-0162-amihud_volatility_6m` | `amihud_volatility_6m` | `amihud_volatility_6m` | `fr-3.16.0` | - | - |
| `cycle-0163-realized_daily_volatility_change_6m` | `realized_daily_volatility_change_6m` | `realized_daily_volatility_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0164-market_beta_6m` | `market_beta_6m` | `market_beta_6m` | `fr-3.16.0` | - | - |
| `cycle-0165-total_asset_growth_6m` | `total_asset_growth_6m` | `total_asset_growth_6m` | `fr-3.16.0` | - | - |
| `cycle-0166-capital_stock_growth_6m` | `capital_stock_growth_6m` | `capital_stock_growth_6m` | `fr-3.16.0` | - | - |
| `cycle-0167-book_to_market_change_6m` | `book_to_market_change_6m` | `book_to_market_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0168-operating_margin_change_6m` | `operating_margin_change_6m` | `operating_margin_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0169-price_momentum_15_3` | `price_momentum_15_3` | `price_momentum_15_3` | `fr-3.16.0` | - | - |
| `cycle-0170-price_recovery_24m` | `price_recovery_24m` | `price_recovery_24m` | `fr-3.16.0` | - | - |
| `cycle-0171-amihud_mean_18m` | `amihud_mean_18m` | `amihud_mean_18m` | `fr-3.16.0` | - | - |
| `cycle-0172-amihud_volatility_18m` | `amihud_volatility_18m` | `amihud_volatility_18m` | `fr-3.16.0` | - | - |
| `cycle-0173-max_daily_return_change_6m` | `max_daily_return_change_6m` | `max_daily_return_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0174-market_beta_9m` | `market_beta_9m` | `market_beta_9m` | `fr-3.16.0` | - | - |
| `cycle-0175-total_asset_growth_18m` | `total_asset_growth_18m` | `total_asset_growth_18m` | `fr-3.16.0` | - | - |
| `cycle-0176-capital_stock_growth_18m` | `capital_stock_growth_18m` | `capital_stock_growth_18m` | `fr-3.16.0` | - | - |
| `cycle-0177-earnings_yield_change_12m` | `earnings_yield_change_12m` | `earnings_yield_change_12m` | `fr-3.16.0` | - | - |
| `cycle-0178-net_margin_change_6m` | `net_margin_change_6m` | `net_margin_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0179-price_momentum_18_6` | `price_momentum_18_6` | `price_momentum_18_6` | `fr-3.16.0` | - | - |
| `cycle-0180-positive_return_share_24m` | `positive_return_share_24m` | `positive_return_share_24m` | `fr-3.16.0` | - | - |
| `cycle-0181-amihud_mean_24m` | `amihud_mean_24m` | `amihud_mean_24m` | `fr-3.16.0` | - | - |
| `cycle-0182-amihud_volatility_24m` | `amihud_volatility_24m` | `amihud_volatility_24m` | `fr-3.16.0` | - | - |
| `cycle-0183-realized_daily_volatility_change_24m` | `realized_daily_volatility_change_24m` | `realized_daily_volatility_change_24m` | `fr-3.16.0` | - | - |
| `cycle-0184-market_beta_12m` | `market_beta_12m` | `market_beta_12m` | `fr-3.16.0` | - | - |
| `cycle-0185-total_asset_growth_24m` | `total_asset_growth_24m` | `total_asset_growth_24m` | `fr-3.16.0` | - | - |
| `cycle-0186-equity_growth_6m` | `equity_growth_6m` | `equity_growth_6m` | `fr-3.16.0` | - | - |
| `cycle-0187-pretax_yield_change_6m` | `pretax_yield_change_6m` | `pretax_yield_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0188-retained_earnings_to_assets_change_6m` | `retained_earnings_to_assets_change_6m` | `retained_earnings_to_assets_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0189-price_momentum_24_6` | `price_momentum_24_6` | `price_momentum_24_6` | `fr-3.16.0` | - | - |
| `cycle-0190-return_seasonality_12m` | `return_seasonality_12m` | `return_seasonality_12m` | `fr-3.16.0` | - | - |
| `cycle-0191-amihud_mean_36m` | `amihud_mean_36m` | `amihud_mean_36m` | `fr-3.16.0` | - | - |
| `cycle-0192-amihud_volatility_36m` | `amihud_volatility_36m` | `amihud_volatility_36m` | `fr-3.16.0` | - | - |
| `cycle-0193-realized_daily_volatility_instability_6m` | `realized_daily_volatility_instability_6m` | `realized_daily_volatility_instability_6m` | `fr-3.16.0` | - | - |
| `cycle-0194-market_beta_18m` | `market_beta_18m` | `market_beta_18m` | `fr-3.16.0` | - | - |
| `cycle-0195-total_asset_growth_30m` | `total_asset_growth_30m` | `total_asset_growth_30m` | `fr-3.16.0` | - | - |
| `cycle-0196-equity_growth_24m` | `equity_growth_24m` | `equity_growth_24m` | `fr-3.16.0` | - | - |
| `cycle-0197-enterprise_sales_yield_change_6m` | `enterprise_sales_yield_change_6m` | `enterprise_sales_yield_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0198-net_to_operating_income_conversion` | `net_to_operating_income_conversion` | `net_to_operating_income_conversion` | `fr-3.16.0` | - | - |
| `cycle-0199-adv_turnover_mean_18m` | `adv_turnover_mean_18m` | `adv_turnover_mean_18m` | `fr-3.16.0` | - | - |
| `cycle-0200-price_momentum_6_1` | `price_momentum_6_1` | `price_momentum_6_1` | `fr-3.16.0` | - | - |
| `cycle-0201-market_beta_24m` | `market_beta_24m` | `market_beta_24m` | `fr-3.16.0` | - | - |
| `cycle-0202-max_daily_return_mean_6m` | `max_daily_return_mean_6m` | `max_daily_return_mean_6m` | `fr-3.16.0` | - | - |
| `cycle-0203-operating_yield_change_12m` | `operating_yield_change_12m` | `operating_yield_change_12m` | `fr-3.16.0` | - | - |
| `cycle-0204-market_leverage_change_6m` | `market_leverage_change_6m` | `market_leverage_change_6m` | `fr-3.16.0` | - | - |
| `cycle-0205-noncurrent_asset_growth_6m` | `noncurrent_asset_growth_6m` | `noncurrent_asset_growth_6m` | `fr-3.16.0` | - | - |
| `cycle-0206-price_trend_efficiency_24m` | `price_trend_efficiency_24m` | `price_trend_efficiency_24m` | `fr-3.16.0` | - | - |
| `cycle-0207-net_margin_volatility_12m` | `net_margin_volatility_12m` | `net_margin_volatility_12m` | `fr-3.16.0` | - | - |
| `cycle-0208-working_capital_accruals_6m` | `working_capital_accruals_6m` | `working_capital_accruals_6m` | `fr-3.16.0` | - | - |
| `cycle-0209-adv_turnover_mean_24m` | `adv_turnover_mean_24m` | `adv_turnover_mean_24m` | `fr-3.16.0` | - | - |
| `cycle-0210-price_reversal_3_1` | `price_reversal_3_1` | `price_reversal_3_1` | `fr-3.16.0` | - | - |
| `cycle-0211-market_return_correlation_6m` | `market_return_correlation_6m` | `market_return_correlation_6m` | `fr-3.16.0` | - | - |
| `cycle-0212-max_daily_return_change_18m` | `max_daily_return_change_18m` | `max_daily_return_change_18m` | `fr-3.16.0` | - | - |
| `cycle-0213-pretax_yield_change_12m` | `pretax_yield_change_12m` | `pretax_yield_change_12m` | `fr-3.16.0` | - | - |
| `cycle-0214-market_leverage_change_18m` | `market_leverage_change_18m` | `market_leverage_change_18m` | `fr-3.16.0` | - | - |
| `cycle-0215-noncurrent_asset_growth_18m` | `noncurrent_asset_growth_18m` | `noncurrent_asset_growth_18m` | `fr-3.16.0` | - | - |
| `cycle-0216-net_equity_issuance_price_adjusted_36m` | `net_equity_issuance_price_adjusted_36m` | `net_equity_issuance_price_adjusted_36m` | `fr-3.16.0` | - | - |
| `cycle-0217-pretax_to_operating_income_conversion` | `pretax_to_operating_income_conversion` | `pretax_to_operating_income_conversion` | `fr-3.16.0` | - | - |
| `cycle-0218-working_capital_accruals_24m` | `working_capital_accruals_24m` | `working_capital_accruals_24m` | `fr-3.16.0` | - | - |
| `cycle-0219-adv_turnover_mean_36m` | `adv_turnover_mean_36m` | `adv_turnover_mean_36m` | `fr-3.16.0` | - | - |
| `cycle-0220-price_reversal_6_3` | `price_reversal_6_3` | `price_reversal_6_3` | `fr-3.16.0` | - | - |
| `cycle-0221-market_return_correlation_9m` | `market_return_correlation_9m` | `market_return_correlation_9m` | `fr-3.16.0` | - | - |
| `cycle-0222-max_daily_return_instability_18m` | `max_daily_return_instability_18m` | `max_daily_return_instability_18m` | `fr-3.16.0` | - | - |
| `cycle-0223-enterprise_earnings_yield_change_12m` | `enterprise_earnings_yield_change_12m` | `enterprise_earnings_yield_change_12m` | `fr-3.16.0` | - | - |
| `cycle-0224-market_leverage_change_24m` | `market_leverage_change_24m` | `market_leverage_change_24m` | `fr-3.16.0` | - | - |
| `cycle-0225-noncurrent_asset_growth_24m` | `noncurrent_asset_growth_24m` | `noncurrent_asset_growth_24m` | `fr-3.16.0` | - | - |
| `cycle-0226-retained_earnings_to_assets_volatility_12m` | `retained_earnings_to_assets_volatility_12m` | `retained_earnings_to_assets_volatility_12m` | `fr-3.16.0` | - | - |
| `cycle-0227-trading_value_turnover_change_3m` | `trading_value_turnover_change_3m` | `trading_value_turnover_change_3m` | `fr-3.16.0` | - | - |
| `cycle-0228-market_relative_momentum_6_1` | `market_relative_momentum_6_1` | `market_relative_momentum_6_1` | `fr-3.16.0` | - | - |
