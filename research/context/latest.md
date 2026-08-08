# Factor research context

> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.

## Frozen research state

- Silver source: `RDS public Silver`
- Visible Silver data period: `2015-01` ~ `2023-05`
- Discovery signal evaluation period: `2018-03` ~ `2023-04`
- Discovery return-support cutoff: `2023-05-31`
- Rows/months/assets: `228,067` / `101` / `2,912`
- Return field: `total_return_close`
- Return methodology: `krx_gross_dividend_reinvested_v1`
- Gate ruleset: `fr-3.10.0`
- Research protocol: `epoch-1.5`
- Recorded autonomous cycles: `42`
- Active sealed campaign: `-`
- Strategy context cutoff: `2023-05-31`

## Sealed-OOS campaigns

| campaign | status | discovery cutoff | OOS | OOS start | epochs | qualified | latest reflection |
|---|---|---|---|---|---:|---:|---|
| `campaign-20260806-001` | CLOSED_RETROSPECTIVE_ONLY | `2026-07-31` | NOT_USED | `-` | 2 | 2 | `research/campaigns/campaign-20260806-001/epochs/epoch-002/reflection.md` |
| `campaign-20260807-001` | CLOSED_NO_QUALIFIED | `2026-07-31` | NOT_USED | `-` | 0 | 0 | `-` |
| `campaign-20260807-002` | SUPERSEDED_BOUNDARY_POLICY | `2026-07-31` | NOT_USED | `-` | 3 | 3 | `research/campaigns/campaign-20260807-002/epochs/epoch-003/reflection.md` |

## Available strategy inputs

| column | overall coverage | latest-month coverage |
|---|---:|---:|
| `adj_close` | 100.0% | 100.0% |
| `adv20` | 100.0% | 100.0% |
| `amihud_illiquidity_1m` | 97.8% | 97.0% |
| `amihud_observations_1m` | 100.0% | 100.0% |
| `capital_stock` | 68.4% | 89.5% |
| `comprehensive_income` | 0.1% | 0.1% |
| `comprehensive_income_ttm` | 0.0% | 0.0% |
| `current_assets` | 77.2% | 89.7% |
| `current_liabilities` | 77.2% | 89.7% |
| `daily_return_observations_252d` | 100.0% | 100.0% |
| `daily_volatility_252d` | 99.9% | 99.9% |
| `dividend_cash_ttm` | 100.0% | 100.0% |
| `dividend_event_count_ttm` | 100.0% | 100.0% |
| `market` | 100.0% | 100.0% |
| `market_cap` | 100.0% | 100.0% |
| `max_daily_return_1m` | 100.0% | 100.0% |
| `max_daily_return_observations_1m` | 100.0% | 100.0% |
| `net_income` | 75.6% | 89.6% |
| `net_income_ttm` | 63.0% | 84.8% |
| `net_income_yoy_change` | 60.0% | 84.7% |
| `noncurrent_assets` | 77.1% | 89.7% |
| `noncurrent_liabilities` | 77.1% | 89.7% |
| `operating_income` | 75.6% | 89.6% |
| `operating_income_ttm` | 63.0% | 84.8% |
| `pretax_income` | 75.6% | 89.6% |
| `pretax_income_ttm` | 62.9% | 84.8% |
| `price_high_252d` | 100.0% | 100.0% |
| `price_high_observations_252d` | 100.0% | 100.0% |
| `retained_earnings` | 76.6% | 89.6% |
| `return_close` | 100.0% | 100.0% |
| `revenue` | 75.3% | 88.9% |
| `revenue_ttm` | 62.1% | 83.6% |
| `shares` | 100.0% | 100.0% |
| `sue_score` | 49.1% | 80.9% |
| `total_assets` | 77.3% | 89.7% |
| `total_equity` | 77.3% | 89.7% |
| `total_liabilities` | 77.3% | 89.7% |
| `trading_value` | 100.0% | 100.0% |

## Registered factors

| factor | category | family | definition hash | inputs |
|---|---|---|---|---|
| `value_bp` | value | `value_bp` | `fd04cd8318be381d` | total_equity |
| `value_ep` | value | `value_ep` | `0f96f2514e3c7a56` | net_income_ttm |
| `value_sp` | value | `value_sp` | `3d5060d0124f4605` | revenue_ttm |
| `qual_roe` | quality | `qual_roe` | `8428891b185a9db5` | net_income_ttm, total_equity |
| `qual_opm` | quality | `qual_opm` | `d452ffb71dae9ee7` | operating_income_ttm, revenue_ttm |
| `qual_lev` | quality | `qual_lev` | `551f0498e0cb6f6b` | total_liabilities, total_equity |
| `mom_12_1` | momentum | `mom_12_1` | `52aac900f2d206fe` | - |
| `rev_1m` | momentum | `rev_1m` | `5d85c305ea247c91` | - |
| `size` | size | `size` | `c261f8d2dedeb948` | - |
| `sue` | earnings | `sue` | `f7f1108e12dbb19a` | sue_score |
| `asset_turnover` | quality | `asset_turnover` | `413015db39ae3e23` | revenue_ttm, total_assets |
| `amihud_illiquidity_1m` | other | `liquidity` | `72bd57d66a5cb84d` | - |
| `annual_seasonality_5y` | momentum | `return_seasonality` | `e2712bceedbcdebd` | - |
| `asset_growth_12m` | other | `asset_growth` | `8036ceaacef6ac62` | total_assets |
| `asset_turnover_change_12m` | quality | `asset_turnover_change` | `8f8e7c42fdc9fce8` | revenue_ttm, total_assets |
| `current_liability_concentration` | quality | `liability_maturity_structure` | `38c06f992e387d49` | current_liabilities, total_liabilities |
| `current_ratio` | quality | `short_term_solvency` | `27ae11f304c7e10a` | current_assets, current_liabilities |
| `defensive_small_value` | value | `small_value` | `5ca0936652af719a` | total_equity |
| `defensive_value` | value | `defensive_value` | `89e8c8685bac02ac` | total_equity |
| `dividend_yield_ttm` | value | `dividend_yield` | `d9afc1c471d113ea` | dividend_cash_ttm |
| `downside_vol_12m` | other | `low_volatility` | `57a4463adb3b9ee7` | - |
| `earnings_change_to_assets` | earnings | `quarterly_earnings_change` | `6c7d7d1bcd6a8f1e` | net_income_yoy_change, total_assets |
| `earnings_confirmed_small_value` | earnings | `catalyst_small_value` | `89e7b296449ec6b2` | total_equity, sue_score |
| `equity_growth_12m` | other | `equity_growth` | `7c69893c5073ff70` | total_equity |
| `high_12m_proximity` | momentum | `price_anchoring` | `5bc5c56e28ba5b4f` | - |
| `high_52w_price_proximity` | momentum | `price_anchoring` | `559d74ab903459ce` | - |
| `liability_growth_12m` | other | `liability_growth` | `048bced1c445efe6` | total_liabilities |
| `long_term_reversal_36_12` | momentum | `long_term_reversal` | `b0a25a07020a622f` | - |
| `low_vol_12m` | other | `low_volatility` | `ae41d1ec7120cde0` | - |
| `market_beta_36m` | other | `market_beta` | `5d0c823050915663` | - |
| `max_daily_return_1m` | other | `lottery_demand` | `e29c3da27f06a3ba` | - |
| `max_monthly_return_12m` | other | `lottery_demand` | `c0ea1874070bbd0b` | - |
| `net_equity_issuance_12m` | other | `net_equity_issuance` | `19650b7013627426` | - |
| `net_equity_issuance_price_adjusted_12m` | other | `net_equity_issuance` | `01ee73e28cd8f170` | - |
| `net_profit_margin` | quality | `net_profit_margin` | `a1e679b213e5f339` | net_income_ttm, revenue_ttm |
| `net_roa` | quality | `net_roa` | `ad335843d7d17cec` | net_income_ttm, total_assets |
| `net_working_capital_to_assets` | quality | `working_capital_buffer` | `8dbeb79579b0e9eb` | current_assets, current_liabilities, total_assets |
| `noncurrent_asset_encumbrance` | quality | `long_term_asset_encumbrance` | `8c1ba3eef1fc9629` | noncurrent_liabilities, noncurrent_assets |
| `nonoperating_burden_to_assets` | quality | `nonoperating_burden` | `bafec4ce16293b98` | operating_income_ttm, net_income_ttm, total_assets |
| `operating_margin_change_12m` | earnings | `operating_margin_expansion` | `9700ff68f8b1878b` | operating_income_ttm, revenue_ttm |
| `operating_return_on_capital_employed` | quality | `capital_employment_efficiency` | `aa11ccad9cfd19c6` | operating_income_ttm, total_assets, current_liabilities |
| `operating_roa` | quality | `operating_roa` | `0c399c65bc5c8e11` | operating_income_ttm, total_assets |
| `operating_roa_change_12m` | earnings | `profitability_change` | `4c2f3e0638033747` | operating_income_ttm, total_assets |
| `operating_roa_volatility_36m` | quality | `profitability_stability` | `d4b9c4dfb4af6b5f` | operating_income_ttm, total_assets |
| `paid_in_capital_ratio` | quality | `equity_composition` | `8c82db0117290bcd` | capital_stock, total_equity |
| `positive_return_share_12m` | momentum | `return_consistency` | `25e1c2f6b6e54370` | - |
| `posttax_income_conversion` | quality | `tax_conversion_efficiency` | `3d16d45df92eff5a` | pretax_income_ttm, net_income_ttm |
| `profitable_small_value` | quality | `quality_small_value` | `ec639be0f12aad5a` | total_equity, operating_income_ttm, total_assets |
| `quality_stability` | quality | `quality_stability` | `c4315c8db6ef4e63` | operating_income_ttm, revenue_ttm, total_assets, total_equity |
| `realized_volatility_252d` | other | `low_volatility` | `e0668fb0e7c0eb69` | - |
| `retained_earnings_to_assets` | quality | `internal_financing` | `1489feceb711fd22` | retained_earnings, total_assets |
| `return_kurtosis_24m` | other | `return_tail_concentration` | `be70b24e1222fb72` | - |
| `return_skewness_24m` | other | `return_skewness` | `ae94a83fc4d5f034` | - |
| `sales_growth_12m` | other | `sales_growth` | `17b53e851b0e2994` | revenue_ttm |
| `small_value` | value | `small_value` | `764fa5bbc3b80dc4` | total_equity |
| `solvent_value` | value | `defensive_value` | `fb56009a013e76e1` | total_equity, total_liabilities |
| `trading_turnover_20d` | other | `trading_activity` | `c03efb8638407bd6` | - |
| `turnover_volatility_12m` | other | `trading_activity_instability` | `07f156b1d7953440` | - |
| `working_capital_accruals_12m` | quality | `working_capital_accruals` | `7d539b85a67522d6` | current_assets, current_liabilities, total_assets |

## Prior autonomous cycles

| cycle | factor | family | ruleset | verdict | failed checks | strongest relation | report |
|---|---|---|---|---|---|---|---|
| `cycle-0013-net_profit_margin` | `net_profit_margin` | `net_profit_margin` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0014-sales_growth_12m` | `sales_growth_12m` | `sales_growth` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0015-operating_roa_change_12m` | `operating_roa_change_12m` | `profitability_change` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0016-long_term_reversal_36_12` | `long_term_reversal_36_12` | `long_term_reversal` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0017-net_roa` | `net_roa` | `net_roa` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0018-liability_growth_12m` | `liability_growth_12m` | `liability_growth` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0019-asset_turnover_change_12m` | `asset_turnover_change_12m` | `asset_turnover_change` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0020-return_skewness_24m` | `return_skewness_24m` | `return_skewness` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0021-net_equity_issuance_12m` | `net_equity_issuance_12m` | `net_equity_issuance` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0022-operating_roa_volatility_36m` | `operating_roa_volatility_36m` | `profitability_stability` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0023-annual_seasonality_5y` | `annual_seasonality_5y` | `return_seasonality` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0024-retained_earnings_to_assets` | `retained_earnings_to_assets` | `internal_financing` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0025-current_ratio` | `current_ratio` | `short_term_solvency` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0026-nonoperating_burden_to_assets` | `nonoperating_burden_to_assets` | `nonoperating_burden` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0027-max_monthly_return_12m` | `max_monthly_return_12m` | `lottery_demand` | `fr-3.2.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0028-trading_turnover_20d` | `trading_turnover_20d` | `trading_activity` | `fr-3.5.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0029-working_capital_accruals_12m` | `working_capital_accruals_12m` | `working_capital_accruals` | `fr-3.5.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0030-earnings_change_to_assets` | `earnings_change_to_assets` | `quarterly_earnings_change` | `fr-3.5.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0031-market_beta_36m` | `market_beta_36m` | `market_beta` | `fr-3.5.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0032-paid_in_capital_ratio` | `paid_in_capital_ratio` | `equity_composition` | `fr-3.5.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0033-current_liability_concentration` | `current_liability_concentration` | `liability_maturity_structure` | `fr-3.5.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0034-net_working_capital_to_assets` | `net_working_capital_to_assets` | `working_capital_buffer` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0035-operating_return_on_capital_employed` | `operating_return_on_capital_employed` | `capital_employment_efficiency` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0036-operating_margin_change_12m` | `operating_margin_change_12m` | `operating_margin_expansion` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0037-posttax_income_conversion` | `posttax_income_conversion` | `tax_conversion_efficiency` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0038-noncurrent_asset_encumbrance` | `noncurrent_asset_encumbrance` | `long_term_asset_encumbrance` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0039-turnover_volatility_12m` | `turnover_volatility_12m` | `trading_activity_instability` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0040-equity_growth_12m` | `equity_growth_12m` | `equity_growth` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0041-positive_return_share_12m` | `positive_return_share_12m` | `return_consistency` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
| `cycle-0042-return_kurtosis_24m` | `return_kurtosis_24m` | `return_tail_concentration` | `fr-3.9.0` | WITHHELD_POST_CUTOFF | 봉인 경계 뒤 결과이므로 숨김 | - | - |
