# 누적 시행 컨텍스트

> 결정론 코드가 만든다. 다음 루프는 새 후보를 세우기 전에 이 파일을 읽는다.
> **판정 결과는 담기지 않는다** — 봉인 OOS 를 지키기 위해 정체성과 구조적 교훈만 남긴다.

시행 33건 · 생략 없음

## 시도한 것

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

## 등록 팩터 요약

- Accruals: 1건 등록
- Debt Issuance: 1건 등록
- Investment: 3건 등록
- Low Leverage: 3건 등록
- Low Risk: 6건 등록
- Momentum: 1건 등록
- Profit Growth: 2건 등록
- Profitability: 1건 등록
- Quality: 4건 등록
- Seasonality: 1건 등록
- Short-Term Reversal: 1건 등록
- Size: 0건 등록
- Value: 7건 등록
- (미매칭): 2건

## 구조적 교훈

### campaign-20260806-001 / epoch-001

- `trading_turnover_20d` (trading_activity) — DISCOVERY_FDR_PENDING · 신규성 INDEPENDENT
- `working_capital_accruals_12m` (working_capital_accruals) — DATA_OR_INTEGRITY · 신규성 INDEPENDENT
- `earnings_change_to_assets` (quarterly_earnings_change) — NO_PREDICTIVE_EVIDENCE · 신규성 DUPLICATE
- 중복: earnings_change_to_assets

### campaign-20260806-001 / epoch-002

- `market_beta_36m` (market_beta) — NO_PREDICTIVE_EVIDENCE · 신규성 INDEPENDENT
- `paid_in_capital_ratio` (equity_composition) — DISCOVERY_FDR_PENDING · 신규성 INDEPENDENT
- `current_liability_concentration` (liability_maturity_structure) — NO_PREDICTIVE_EVIDENCE · 신규성 INDEPENDENT

