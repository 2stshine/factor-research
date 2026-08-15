# Factor research context

> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.

## Frozen research state

- Silver source: `RDS public Silver`
- Raw Silver period inside context boundary: `1995-05` ~ `2026-08`
- Visible Silver data period: `2015-01` ~ `2026-08`
- Research input floor: `2015-01`
- Maximum factor lookback: `36` months
- Discovery signal evaluation period: `2018-03` ~ `2026-08`
- Discovery return-support cutoff: `-`
- Rows/months/assets: `317,530` / `140` / `3,146`
- Historical feature return: `adj_close` / `krx_split_adjusted_price_return_v1`
- Forward-label return: `total_return_close` / `krx_gross_dividend_reinvested_v3` / `forward_return_labels_only` / revision=`latest_revision_ex_post_realized` / candidate_access=`False`
- Gate ruleset: `fr-3.14.0`
- Research protocol: `epoch-1.7`
- Recorded autonomous cycles: `158`
- Active sealed campaign: `-`
- Strategy context cutoff: `-`

## Sealed-OOS campaigns

| campaign | status | discovery cutoff | OOS | OOS start | epochs | qualified | latest reflection |
|---|---|---|---|---|---:|---:|---|
| `campaign-20260806-001` | CLOSED_RETROSPECTIVE_ONLY | `2026-07-31` | NOT_USED | `-` | 2 | 2 | `research/campaigns/campaign-20260806-001/epochs/epoch-002/reflection.md` |
| `campaign-20260807-001` | CLOSED_NO_QUALIFIED | `2026-07-31` | NOT_USED | `-` | 0 | 0 | `-` |
| `campaign-20260807-002` | SUPERSEDED_BOUNDARY_POLICY | `2026-07-31` | NOT_USED | `-` | 3 | 3 | `research/campaigns/campaign-20260807-002/epochs/epoch-003/reflection.md` |
| `campaign-20260808-001` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 5 | `research/campaigns/campaign-20260808-001/epochs/epoch-001/reflection.md` |
| `campaign-20260809-001` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260809-001/epochs/epoch-001/reflection.md` |
| `campaign-20260811-001` | CLOSED_INVALIDATED_INPUT_IDENTITY | `2023-05-31` | NOT_USED | `-` | 1 | 1 | `research/campaigns/campaign-20260811-001/epochs/epoch-001/reflection.md` |
| `campaign-20260814-001` | CLOSED_ABORTED | `2023-05-31` | NOT_USED | `-` | 1 | 0 | `-` |
| `campaign-20260814-002` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 5 | `research/campaigns/campaign-20260814-002/epochs/epoch-001/reflection.md` |
| `campaign-20260815-001` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260815-001/epochs/epoch-001/reflection.md` |
| `campaign-20260815-002` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260815-002/epochs/epoch-001/reflection.md` |
| `campaign-20260815-003` | CLOSED_NO_QUALIFIED | `2023-05-31` | NOT_USED | `-` | 1 | 0 | `research/campaigns/campaign-20260815-003/epochs/epoch-001/reflection.md` |
| `campaign-20260815-004` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260815-004/epochs/epoch-001/reflection.md` |
| `campaign-20260815-005` | CLOSED_NO_QUALIFIED | `2023-05-31` | NOT_USED | `-` | 1 | 0 | `research/campaigns/campaign-20260815-005/epochs/epoch-001/reflection.md` |
| `campaign-20260815-006` | CLOSED_NO_QUALIFIED | `2023-05-31` | NOT_USED | `-` | 1 | 0 | `research/campaigns/campaign-20260815-006/epochs/epoch-001/reflection.md` |
| `campaign-20260815-007` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260815-007/epochs/epoch-001/reflection.md` |
| `campaign-20260815-008` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260815-008/epochs/epoch-001/reflection.md` |
| `campaign-20260815-009` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260815-009/epochs/epoch-001/reflection.md` |
| `campaign-20260815-010` | CLOSED_NO_QUALIFIED | `2023-05-31` | NOT_USED | `-` | 1 | 0 | `research/campaigns/campaign-20260815-010/epochs/epoch-001/reflection.md` |
| `campaign-20260815-011` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 3 | `research/campaigns/campaign-20260815-011/epochs/epoch-001/reflection.md` |
| `campaign-20260815-012` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260815-012/epochs/epoch-001/reflection.md` |
| `campaign-20260815-013` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 3 | `research/campaigns/campaign-20260815-013/epochs/epoch-001/reflection.md` |
| `campaign-20260815-014` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260815-014/epochs/epoch-001/reflection.md` |
| `campaign-20260815-015` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260815-015/epochs/epoch-001/reflection.md` |

## Available strategy inputs

| column | overall coverage | latest-month coverage |
|---|---:|---:|
| `adj_close` | 100.0% | 100.0% |
| `adv20` | 100.0% | 100.0% |
| `amihud_illiquidity_1m` | 97.3% | 95.8% |
| `amihud_observations_1m` | 100.0% | 100.0% |
| `capital_stock` | 80.5% | 99.4% |
| `comprehensive_income` | 27.4% | 98.8% |
| `comprehensive_income_ttm` | 17.1% | 93.6% |
| `current_assets` | 86.1% | 97.2% |
| `current_liabilities` | 86.1% | 97.1% |
| `daily_return_observations_252d` | 100.0% | 100.0% |
| `daily_volatility_252d` | 99.9% | 100.0% |
| `market` | 100.0% | 100.0% |
| `market_cap` | 100.0% | 100.0% |
| `max_daily_return_1m` | 100.0% | 100.0% |
| `max_daily_return_observations_1m` | 100.0% | 100.0% |
| `net_income` | 85.6% | 99.3% |
| `net_income_ttm` | 74.3% | 94.5% |
| `net_income_yoy_change` | 71.6% | 94.6% |
| `noncurrent_assets` | 85.9% | 96.8% |
| `noncurrent_liabilities` | 86.0% | 97.1% |
| `operating_income` | 85.6% | 99.3% |
| `operating_income_ttm` | 74.4% | 94.6% |
| `pretax_income` | 85.6% | 99.3% |
| `pretax_income_ttm` | 74.4% | 94.6% |
| `price_high_252d` | 100.0% | 100.0% |
| `price_high_observations_252d` | 100.0% | 100.0% |
| `retained_earnings` | 86.4% | 99.5% |
| `revenue` | 84.6% | 97.2% |
| `revenue_ttm` | 72.9% | 91.6% |
| `shares` | 100.0% | 100.0% |
| `sue_score` | 62.3% | 89.6% |
| `total_assets` | 86.9% | 99.5% |
| `total_equity` | 86.9% | 99.5% |
| `total_liabilities` | 86.9% | 99.5% |
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
| `mom_12_1` | momentum | `mom_12_1` | `14fe2a50aa311864` | - |
| `rev_1m` | momentum | `rev_1m` | `d323749c9e833267` | - |
| `size` | size | `size` | `c261f8d2dedeb948` | - |
| `sue` | earnings | `sue` | `f7f1108e12dbb19a` | sue_score |
| `asset_turnover` | quality | `asset_turnover` | `413015db39ae3e23` | revenue_ttm, total_assets |
| `adv20_change_12m` | other | `trading_liquidity_growth` | `d9a4ee93f1d820c6` | - |
| `adv20_to_book_equity` | other | `book_scaled_trading_activity` | `8df24f36d7bb6745` | total_equity |
| `amihud_change_12m` | other | `liquidity_deterioration` | `ae4560c85988cb8d` | - |
| `amihud_illiquidity_1m` | other | `liquidity` | `72bd57d66a5cb84d` | - |
| `amihud_volatility_12m` | other | `liquidity_instability` | `bfd49a2484fe9153` | - |
| `asset_growth_12m` | other | `asset_growth` | `8036ceaacef6ac62` | total_assets |
| `asset_growth_acceleration_12m` | other | `investment_acceleration` | `c9ffb35aab06e21f` | total_assets |
| `asset_to_market` | value | `asset_backed_value` | `8b1db811b2216526` | total_assets |
| `asset_turnover_acceleration_12m` | quality | `asset_efficiency_acceleration` | `990062b564c6ae51` | revenue_ttm, total_assets |
| `asset_turnover_change_12m` | quality | `asset_turnover_change` | `8f8e7c42fdc9fce8` | revenue_ttm, total_assets |
| `asset_turnover_volatility_36m` | quality | `asset_efficiency_stability` | `7790b109be96a0c3` | revenue_ttm, total_assets |
| `book_to_market_change_12m` | value | `book_value_repricing` | `e73b53f0ffaaf3c5` | total_equity |
| `capital_stock_growth_12m` | other | `legal_capital_issuance_growth` | `e09f61de6fa86d70` | capital_stock |
| `capital_stock_share_change_12m` | other | `contributed_capital_share_change` | `7f5557c0c07307a4` | capital_stock, total_equity |
| `capital_stock_to_assets` | other | `nominal_capital_intensity` | `dd1d0d32a2a49a3c` | capital_stock, total_assets |
| `capital_stock_to_current_assets` | other | `legal_capital_current_asset_intensity` | `479a770e1c7ab82a` | capital_stock, current_assets |
| `capital_stock_to_current_liabilities` | quality | `legal_capital_short_debt_coverage` | `41a5be7768c1c7c1` | capital_stock, current_liabilities |
| `capital_stock_to_liabilities` | quality | `nominal_capital_debt_coverage` | `177e5062f4f3b37c` | capital_stock, total_liabilities |
| `capital_stock_yield` | value | `legal_capital_value` | `1de2eb2066948601` | capital_stock |
| `current_asset_turnover` | quality | `current_asset_turnover` | `05c6633ec72d4e6a` | revenue_ttm, current_assets |
| `current_assets_growth_12m` | other | `working_capital_investment_growth` | `3196d6dd2d501904` | current_assets |
| `current_assets_growth_acceleration_12m` | other | `working_asset_acceleration` | `b3f7dad7f70bc0c3` | current_assets |
| `current_assets_to_assets` | quality | `asset_liquidity_share` | `7986938fba4179c9` | current_assets, total_assets |
| `current_assets_to_equity` | quality | `equity_liquidity_capacity` | `cd296082edb97588` | current_assets, total_equity |
| `current_assets_to_noncurrent_assets` | other | `flexible_asset_mix` | `ce9ed307736e8971` | current_assets, noncurrent_assets |
| `current_assets_to_total_liabilities` | quality | `liquid_asset_debt_coverage` | `35b5c72f04c6c4fa` | current_assets, total_liabilities |
| `current_assets_yield` | value | `liquid_asset_value` | `dcaa49f977629384` | current_assets |
| `current_liabilities_growth_12m` | other | `short_term_financing_growth` | `4d33cc2e60902b83` | current_liabilities |
| `current_liabilities_growth_acceleration_12m` | other | `short_term_debt_acceleration` | `b0c7969f66daa172` | current_liabilities |
| `current_liabilities_to_assets` | quality | `short_term_liability_burden` | `f66afd1139d97ee9` | current_liabilities, total_assets |
| `current_liabilities_to_sales` | quality | `short_term_funding_sales_burden` | `8ee67f572f89d053` | current_liabilities, revenue_ttm |
| `current_liabilities_yield` | value | `market_short_debt_burden` | `d078fb7ccd166434` | current_liabilities |
| `current_liability_concentration` | quality | `liability_maturity_structure` | `38c06f992e387d49` | current_liabilities, total_liabilities |
| `current_ratio` | quality | `short_term_solvency` | `27ae11f304c7e10a` | current_assets, current_liabilities |
| `current_ratio_change_12m` | quality | `short_term_solvency_change` | `6b612f0530a1e066` | current_assets, current_liabilities |
| `daily_volatility_change_12m` | other | `risk_deterioration` | `29e6a2dd45feac4d` | - |
| `defensive_small_value` | value | `small_value` | `20ae444177ae7843` | total_equity |
| `defensive_value` | value | `defensive_value` | `4047e0758bf9b78c` | total_equity |
| `downside_vol_12m` | other | `low_volatility` | `9cb7741d758b8fd2` | - |
| `earnings_change_to_assets` | earnings | `quarterly_earnings_change` | `6c7d7d1bcd6a8f1e` | net_income_yoy_change, total_assets |
| `earnings_confirmed_small_value` | earnings | `catalyst_small_value` | `89e7b296449ec6b2` | total_equity, sue_score |
| `equity_debt_coverage_change_12m` | quality | `book_solvency_improvement` | `cd46d2f611150038` | total_equity, total_liabilities |
| `equity_growth_12m` | other | `equity_growth` | `7c69893c5073ff70` | total_equity |
| `equity_growth_acceleration_12m` | other | `equity_expansion_acceleration` | `aef96b739387ffd1` | total_equity |
| `equity_to_current_liabilities` | quality | `short_term_equity_solvency` | `cb5d900cd356de54` | total_equity, current_liabilities |
| `equity_to_noncurrent_liabilities` | quality | `long_term_equity_solvency` | `dbfa1a3f3bc862d3` | total_equity, noncurrent_liabilities |
| `high_12m_proximity` | momentum | `price_anchoring` | `fce1984269262fba` | - |
| `high_52w_price_proximity` | momentum | `price_anchoring` | `559d74ab903459ce` | - |
| `idiosyncratic_volatility_24m` | other | `idiosyncratic_volatility` | `af24645c3a81a842` | - |
| `intermediate_momentum_12_7` | momentum | `intermediate_momentum` | `df9d7a028fded1f2` | - |
| `liability_growth_12m` | other | `liability_growth` | `048bced1c445efe6` | total_liabilities |
| `liability_growth_acceleration_12m` | other | `debt_growth_acceleration` | `f14b34ecb54a5d5b` | total_liabilities |
| `long_term_reversal_36_12` | momentum | `long_term_reversal` | `27b93af8ce3d6c07` | - |
| `low_vol_12m` | other | `low_volatility` | `2dcb671efc74db88` | - |
| `market_beta_36m` | other | `market_beta` | `2651806103f53620` | - |
| `market_leverage` | other | `market_leverage` | `34e619cb846843cc` | total_liabilities |
| `market_leverage_change_12m` | other | `market_leverage_change` | `8dd3424bb7bcc564` | total_liabilities |
| `market_relative_momentum_12_1` | momentum | `market_relative_momentum` | `8377d93ea80f76dc` | - |
| `max_daily_return_1m` | other | `lottery_demand` | `e29c3da27f06a3ba` | - |
| `max_daily_return_change_12m` | other | `lottery_demand_acceleration` | `ce0680b52ff03580` | - |
| `max_monthly_return_12m` | other | `lottery_demand` | `54e7c79ca04fdc7e` | - |
| `medium_term_momentum_6_2` | momentum | `medium_term_momentum` | `fe7484d4b16ecc1c` | - |
| `momentum_acceleration_6m` | momentum | `price_momentum_acceleration` | `98a613007a62aa32` | - |
| `net_equity_issuance_12m` | other | `net_equity_issuance` | `45bcea59dbd07918` | - |
| `net_equity_issuance_price_adjusted_12m` | other | `net_equity_issuance` | `01ee73e28cd8f170` | - |
| `net_income_growth_12m` | earnings | `trailing_net_income_growth` | `6bec9560dceccc6d` | net_income_ttm |
| `net_income_growth_acceleration_12m` | earnings | `net_earnings_acceleration` | `9cf84e9a3afcffa9` | net_income_ttm |
| `net_income_to_capital_stock` | quality | `legal_capital_net_return` | `86f96d4808be68f4` | net_income_ttm, capital_stock |
| `net_income_to_current_assets` | quality | `current_asset_net_productivity` | `6cdf007f39f23b91` | net_income_ttm, current_assets |
| `net_income_to_liabilities` | quality | `posttax_debt_coverage` | `0cb38fb5ad3db869` | net_income_ttm, total_liabilities |
| `net_income_to_noncurrent_assets` | quality | `long_asset_net_productivity` | `976770c25d2e7a5e` | net_income_ttm, noncurrent_assets |
| `net_margin_volatility_36m` | quality | `net_margin_stability` | `c111dc48be850952` | net_income_ttm, revenue_ttm |
| `net_profit_margin` | quality | `net_profit_margin` | `a1e679b213e5f339` | net_income_ttm, revenue_ttm |
| `net_profit_margin_change_12m` | earnings | `net_margin_expansion` | `7c03a263baafbc66` | net_income_ttm, revenue_ttm |
| `net_roa` | quality | `net_roa` | `ad335843d7d17cec` | net_income_ttm, total_assets |
| `net_roa_volatility_36m` | quality | `net_profitability_stability` | `fc4107bfda24d6d7` | net_income_ttm, total_assets |
| `net_working_capital_to_assets` | quality | `working_capital_buffer` | `8dbeb79579b0e9eb` | current_assets, current_liabilities, total_assets |
| `net_working_capital_to_liabilities` | quality | `working_capital_debt_coverage` | `2314b9f8f2ead59a` | current_assets, current_liabilities, total_liabilities |
| `net_working_capital_yield` | value | `liquid_asset_value` | `0c14cdb6457bdf0a` | current_assets, current_liabilities |
| `noncurrent_asset_encumbrance` | quality | `long_term_asset_encumbrance` | `8c1ba3eef1fc9629` | noncurrent_liabilities, noncurrent_assets |
| `noncurrent_asset_share` | other | `asset_rigidity` | `1ce4e1a937a3b221` | noncurrent_assets, total_assets |
| `noncurrent_asset_share_change_12m` | other | `asset_rigidity_change` | `ea299e63f30cf0b9` | noncurrent_assets, total_assets |
| `noncurrent_assets_growth_12m` | other | `long_lived_asset_investment_growth` | `f671f2fe6d3fbfb6` | noncurrent_assets |
| `noncurrent_assets_to_capital_stock` | quality | `legal_capital_long_asset_backing` | `fd965ea3cd408aeb` | noncurrent_assets, capital_stock |
| `noncurrent_assets_to_equity` | other | `equity_asset_rigidity` | `2e53940365dac6af` | noncurrent_assets, total_equity |
| `noncurrent_assets_yield` | value | `long_lived_asset_value` | `f4738ee115ea9c1e` | noncurrent_assets |
| `noncurrent_liabilities_growth_12m` | other | `long_term_debt_growth` | `3328787c0692acd8` | noncurrent_liabilities |
| `noncurrent_liabilities_to_assets` | quality | `long_term_liability_burden` | `3b7176e14e22e8dd` | noncurrent_liabilities, total_assets |
| `noncurrent_liabilities_to_equity` | other | `long_term_book_leverage` | `c58df5bf5f733ad0` | noncurrent_liabilities, total_equity |
| `noncurrent_liabilities_yield` | value | `market_long_debt_burden` | `3563f184ff3b6f7a` | noncurrent_liabilities |
| `noncurrent_liability_share_change_12m` | other | `liability_maturity_change` | `959597640823529f` | noncurrent_liabilities, total_liabilities |
| `nonoperating_burden_margin` | quality | `nonoperating_sales_burden` | `3334a4ac95f88b68` | operating_income_ttm, net_income_ttm, revenue_ttm |
| `nonoperating_burden_to_assets` | quality | `nonoperating_burden` | `bafec4ce16293b98` | operating_income_ttm, net_income_ttm, total_assets |
| `operating_coverage_change_12m` | earnings | `short_term_operating_coverage_improvement` | `299bdf764c5cdf8e` | operating_income_ttm, current_liabilities |
| `operating_earnings_yield` | value | `operating_earnings_yield` | `692110a461d94df5` | operating_income_ttm |
| `operating_income_growth_12m` | earnings | `operating_income_growth` | `82aab27246acdca1` | operating_income_ttm |
| `operating_income_growth_acceleration_12m` | earnings | `operating_earnings_acceleration` | `f685aaa5ceabb430` | operating_income_ttm |
| `operating_income_to_capital_stock` | quality | `legal_capital_operating_return` | `001adf63fa5695a7` | operating_income_ttm, capital_stock |
| `operating_income_to_current_assets` | quality | `current_asset_operating_productivity` | `e02d45bea9f2c933` | operating_income_ttm, current_assets |
| `operating_income_to_current_liabilities` | quality | `short_term_operating_coverage` | `eaf7784cd83b4082` | operating_income_ttm, current_liabilities |
| `operating_income_to_equity` | quality | `operating_book_equity_return` | `428627112a91cdf9` | operating_income_ttm, total_equity |
| `operating_income_to_liabilities` | quality | `operating_obligation_coverage` | `5ff8c69343b28a3f` | operating_income_ttm, total_liabilities |
| `operating_income_to_noncurrent_assets` | quality | `long_lived_asset_operating_productivity` | `78eae3fe699e6c63` | operating_income_ttm, noncurrent_assets |
| `operating_income_to_noncurrent_liabilities` | quality | `long_term_operating_coverage` | `4c2a4df32ec5ee5c` | operating_income_ttm, noncurrent_liabilities |
| `operating_margin_acceleration_12m` | earnings | `operating_margin_acceleration` | `382aabc51af8687f` | operating_income_ttm, revenue_ttm |
| `operating_margin_change_12m` | earnings | `operating_margin_expansion` | `9700ff68f8b1878b` | operating_income_ttm, revenue_ttm |
| `operating_return_on_capital_employed` | quality | `capital_employment_efficiency` | `aa11ccad9cfd19c6` | operating_income_ttm, total_assets, current_liabilities |
| `operating_roa` | quality | `operating_roa` | `0c399c65bc5c8e11` | operating_income_ttm, total_assets |
| `operating_roa_change_12m` | earnings | `profitability_change` | `4c2f3e0638033747` | operating_income_ttm, total_assets |
| `operating_roa_volatility_36m` | quality | `profitability_stability` | `d4b9c4dfb4af6b5f` | operating_income_ttm, total_assets |
| `paid_in_capital_ratio` | quality | `equity_composition` | `8c82db0117290bcd` | capital_stock, total_equity |
| `positive_return_share_12m` | momentum | `return_consistency` | `acae6c61863c2804` | - |
| `posttax_income_conversion` | quality | `tax_conversion_efficiency` | `3d16d45df92eff5a` | pretax_income_ttm, net_income_ttm |
| `pretax_income_growth_12m` | earnings | `trailing_pretax_income_growth` | `2bf41bc52822d174` | pretax_income_ttm |
| `pretax_income_growth_acceleration_12m` | earnings | `pretax_earnings_acceleration` | `39d456f6eb483d79` | pretax_income_ttm |
| `pretax_income_to_current_assets` | quality | `current_asset_pretax_productivity` | `48e04986317f20ad` | pretax_income_ttm, current_assets |
| `pretax_income_to_equity` | quality | `pretax_book_equity_return` | `48f4938d8e5af99d` | pretax_income_ttm, total_equity |
| `pretax_income_to_liabilities` | quality | `pretax_debt_coverage` | `47ef014a02b341ff` | pretax_income_ttm, total_liabilities |
| `pretax_margin_volatility_36m` | quality | `pretax_margin_stability` | `d15d6923d7e4e417` | pretax_income_ttm, revenue_ttm |
| `pretax_profit_margin` | quality | `pretax_profitability_margin` | `76ccaa1e135def8b` | pretax_income_ttm, revenue_ttm |
| `pretax_roa` | quality | `pretax_roa` | `9ad1b0b40a9f57d9` | pretax_income_ttm, total_assets |
| `pretax_roa_volatility_36m` | quality | `pretax_profitability_stability` | `d4dec956cc9a8c0b` | pretax_income_ttm, total_assets |
| `price_range_12m` | other | `price_range_risk` | `b564b360f33b0dca` | - |
| `price_recovery_12m` | momentum | `price_recovery_from_low` | `6c2f9df4e590ffad` | - |
| `price_trend_efficiency_12m` | momentum | `directional_price_efficiency` | `ef0a1d0f9ef6aaff` | - |
| `profitable_small_value` | quality | `quality_small_value` | `ec639be0f12aad5a` | total_equity, operating_income_ttm, total_assets |
| `quality_stability` | quality | `quality_stability` | `6ee5f5fd4f04ffe0` | operating_income_ttm, revenue_ttm, total_assets, total_equity |
| `realized_volatility_252d` | other | `low_volatility` | `e0668fb0e7c0eb69` | - |
| `retained_earnings_growth_12m` | quality | `internal_capital_accumulation` | `b3c24c1cb9c7a15a` | retained_earnings |
| `retained_earnings_growth_acceleration_12m` | quality | `internal_capital_acceleration` | `34a28f0d2076a197` | retained_earnings |
| `retained_earnings_to_assets` | quality | `internal_financing` | `1489feceb711fd22` | retained_earnings, total_assets |
| `retained_earnings_to_assets_change_12m` | quality | `retained_earnings_accumulation` | `c98308cb4bcfc12b` | retained_earnings, total_assets |
| `retained_earnings_to_capital_stock` | quality | `earned_to_contributed_capital` | `ac476a86c1174da7` | retained_earnings, capital_stock |
| `retained_earnings_to_current_assets` | quality | `internal_capital_current_asset_backing` | `a00c5c91229e2e08` | retained_earnings, current_assets |
| `retained_earnings_to_current_liabilities` | quality | `internal_capital_short_debt_coverage` | `bfc0cf2c33de0169` | retained_earnings, current_liabilities |
| `retained_earnings_to_equity` | quality | `retained_earnings_equity_share` | `ede7286f5e5ca082` | retained_earnings, total_equity |
| `retained_earnings_to_liabilities` | quality | `earned_capital_debt_coverage` | `50d2f8c1276ed5cf` | retained_earnings, total_liabilities |
| `retained_earnings_to_noncurrent_assets` | quality | `internal_capital_long_asset_backing` | `e2cec8a4d63286cb` | retained_earnings, noncurrent_assets |
| `retained_earnings_to_noncurrent_liabilities` | quality | `internal_capital_long_debt_coverage` | `e485b63dd64938fd` | retained_earnings, noncurrent_liabilities |
| `retained_earnings_yield` | value | `accumulated_earnings_value` | `ed934394649254e9` | retained_earnings |
| `return_gain_loss_ratio_12m` | momentum | `return_magnitude_asymmetry` | `b1d121f4359b9bd3` | - |
| `return_kurtosis_24m` | other | `return_tail_concentration` | `28373510626d93b0` | - |
| `return_persistence_12m` | momentum | `monthly_return_persistence` | `82f9ce9d7b871458` | - |
| `return_skewness_24m` | other | `return_skewness` | `5aa1c6a0520281df` | - |
| `revenue_to_capital_stock` | quality | `legal_capital_revenue_productivity` | `b20541b3af6f7ff3` | revenue_ttm, capital_stock |
| `revenue_to_current_assets` | quality | `working_asset_revenue_productivity` | `afb920b0e657b7c9` | revenue_ttm, current_assets |
| `revenue_to_current_liabilities` | quality | `short_term_revenue_coverage` | `b8f3cc903a169ec7` | revenue_ttm, current_liabilities |
| `revenue_to_equity` | quality | `equity_revenue_productivity` | `69502c479c0d9ebd` | revenue_ttm, total_equity |
| `revenue_to_noncurrent_assets` | quality | `long_lived_asset_revenue_productivity` | `29eedb3de737a6f9` | revenue_ttm, noncurrent_assets |
| `revenue_to_noncurrent_liabilities` | quality | `long_term_revenue_coverage` | `2994dfd7e6636119` | revenue_ttm, noncurrent_liabilities |
| `revenue_to_total_liabilities` | quality | `revenue_debt_turnover` | `50c3bd228268077e` | revenue_ttm, total_liabilities |
| `sales_growth_12m` | other | `sales_growth` | `17b53e851b0e2994` | revenue_ttm |
| `sales_growth_acceleration_12m` | earnings | `sales_growth_acceleration` | `cb546e7aa9325118` | revenue_ttm |
| `short_term_reversal_3m` | momentum | `short_term_reversal_3m` | `bb5c9a621d0bd540` | - |
| `small_value` | value | `small_value` | `764fa5bbc3b80dc4` | total_equity |
| `solvent_value` | value | `defensive_value` | `fb56009a013e76e1` | total_equity, total_liabilities |
| `trading_turnover_20d` | other | `trading_activity` | `c03efb8638407bd6` | - |
| `trading_value_volatility_12m` | other | `trading_attention_instability` | `74ce4f67d200762d` | - |
| `turnover_change_6m` | other | `trading_attention_change` | `f21fb281d5313d01` | - |
| `turnover_volatility_12m` | other | `trading_activity_instability` | `07f156b1d7953440` | - |
| `working_capital_accruals_12m` | quality | `working_capital_accruals` | `7d539b85a67522d6` | current_assets, current_liabilities, total_assets |
| `working_capital_growth_12m` | other | `working_capital_investment` | `3b7ad689dbdebc0a` | current_assets, current_liabilities |
| `working_capital_to_sales` | quality | `working_capital_sales_buffer` | `85cadc517d7da429` | current_assets, current_liabilities, revenue_ttm |

## Prior autonomous cycles

| cycle | factor | family | ruleset | verdict | failed checks | strongest relation | report |
|---|---|---|---|---|---|---|---|
| `cycle-0129-retained_earnings_to_noncurrent_assets` | `retained_earnings_to_noncurrent_assets` | `internal_capital_long_asset_backing` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | retained_earnings_to_assets (0.94) | `research/runs/cycle-0129-retained_earnings_to_noncurrent_assets/report.md` |
| `cycle-0130-retained_earnings_to_current_assets` | `retained_earnings_to_current_assets` | `internal_capital_current_asset_backing` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | retained_earnings_to_assets (0.92) | `research/runs/cycle-0130-retained_earnings_to_current_assets/report.md` |
| `cycle-0131-capital_stock_to_current_assets` | `capital_stock_to_current_assets` | `legal_capital_current_asset_intensity` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | capital_stock_to_assets (0.92) | `research/runs/cycle-0131-capital_stock_to_current_assets/report.md` |
| `cycle-0132-equity_to_current_liabilities` | `equity_to_current_liabilities` | `short_term_equity_solvency` | `fr-3.14.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건, 다중검정 FDR | current_liabilities_to_assets (0.97) | `research/runs/cycle-0132-equity_to_current_liabilities/report.md` |
| `cycle-0133-operating_income_to_capital_stock` | `operating_income_to_capital_stock` | `legal_capital_operating_return` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | operating_roa (0.87) | `research/runs/cycle-0133-operating_income_to_capital_stock/report.md` |
| `cycle-0134-current_assets_yield` | `current_assets_yield` | `liquid_asset_value` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | asset_to_market (0.88) | `research/runs/cycle-0134-current_assets_yield/report.md` |
| `cycle-0135-daily_volatility_change_12m` | `daily_volatility_change_12m` | `risk_deterioration` | `fr-3.14.0` | PROVISIONAL | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | adv20_change_12m (0.48) | `research/runs/cycle-0135-daily_volatility_change_12m/report.md` |
| `cycle-0136-max_daily_return_change_12m` | `max_daily_return_change_12m` | `lottery_demand_acceleration` | `fr-3.14.0` | PROVISIONAL | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | adv20_change_12m (0.63) | `research/runs/cycle-0136-max_daily_return_change_12m/report.md` |
| `cycle-0137-market_relative_momentum_12_1` | `market_relative_momentum_12_1` | `market_relative_momentum` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | mom_12_1 (1.00) | `research/runs/cycle-0137-market_relative_momentum_12_1/report.md` |
| `cycle-0138-turnover_change_6m` | `turnover_change_6m` | `trading_attention_change` | `fr-3.14.0` | PROVISIONAL | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | adv20_change_12m (0.46) | `research/runs/cycle-0138-turnover_change_6m/report.md` |
| `cycle-0139-operating_coverage_change_12m` | `operating_coverage_change_12m` | `short_term_operating_coverage_improvement` | `fr-3.14.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건, 투자가능 Rank ICIR 최소요건, 다중검정 FDR | operating_roa_change_12m (0.83) | `research/runs/cycle-0139-operating_coverage_change_12m/report.md` |
| `cycle-0140-revenue_to_current_liabilities` | `revenue_to_current_liabilities` | `short_term_revenue_coverage` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | current_liabilities_to_sales (1.00) | `research/runs/cycle-0140-revenue_to_current_liabilities/report.md` |
| `cycle-0141-retained_earnings_to_current_liabilities` | `retained_earnings_to_current_liabilities` | `internal_capital_short_debt_coverage` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | retained_earnings_to_liabilities (0.98) | `research/runs/cycle-0141-retained_earnings_to_current_liabilities/report.md` |
| `cycle-0142-capital_stock_to_current_liabilities` | `capital_stock_to_current_liabilities` | `legal_capital_short_debt_coverage` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | capital_stock_to_liabilities (0.96) | `research/runs/cycle-0142-capital_stock_to_current_liabilities/report.md` |
| `cycle-0143-noncurrent_assets_yield` | `noncurrent_assets_yield` | `long_lived_asset_value` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | asset_to_market (0.92) | `research/runs/cycle-0143-noncurrent_assets_yield/report.md` |
| `cycle-0144-current_liabilities_yield` | `current_liabilities_yield` | `market_short_debt_burden` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | market_leverage (-0.97) | `research/runs/cycle-0144-current_liabilities_yield/report.md` |
| `cycle-0145-amihud_volatility_12m` | `amihud_volatility_12m` | `liquidity_instability` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | amihud_illiquidity_1m (-0.82) | `research/runs/cycle-0145-amihud_volatility_12m/report.md` |
| `cycle-0146-trading_value_volatility_12m` | `trading_value_volatility_12m` | `trading_attention_instability` | `fr-3.14.0` | PROVISIONAL | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | realized_volatility_252d (0.73) | `research/runs/cycle-0146-trading_value_volatility_12m/report.md` |
| `cycle-0147-return_persistence_12m` | `return_persistence_12m` | `monthly_return_persistence` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | downside_vol_12m (0.25) | `research/runs/cycle-0147-return_persistence_12m/report.md` |
| `cycle-0148-nonoperating_burden_margin` | `nonoperating_burden_margin` | `nonoperating_sales_burden` | `fr-3.14.0` | PROVISIONAL | - | nonoperating_burden_to_assets (0.94) | `research/runs/cycle-0148-nonoperating_burden_margin/report.md` |
| `cycle-0149-net_income_to_capital_stock` | `net_income_to_capital_stock` | `legal_capital_net_return` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | net_roa (0.89) | `research/runs/cycle-0149-net_income_to_capital_stock/report.md` |
| `cycle-0150-retained_earnings_to_noncurrent_liabilities` | `retained_earnings_to_noncurrent_liabilities` | `internal_capital_long_debt_coverage` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | retained_earnings_to_liabilities (0.92) | `research/runs/cycle-0150-retained_earnings_to_noncurrent_liabilities/report.md` |
| `cycle-0151-working_capital_growth_12m` | `working_capital_growth_12m` | `working_capital_investment` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | working_capital_accruals_12m (0.94) | `research/runs/cycle-0151-working_capital_growth_12m/report.md` |
| `cycle-0152-equity_debt_coverage_change_12m` | `equity_debt_coverage_change_12m` | `book_solvency_improvement` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | liability_growth_12m (0.80) | `research/runs/cycle-0152-equity_debt_coverage_change_12m/report.md` |
| `cycle-0153-capital_stock_share_change_12m` | `capital_stock_share_change_12m` | `contributed_capital_share_change` | `fr-3.14.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건 | equity_growth_12m (-0.73) | `research/runs/cycle-0153-capital_stock_share_change_12m/report.md` |
| `cycle-0154-noncurrent_assets_to_capital_stock` | `noncurrent_assets_to_capital_stock` | `legal_capital_long_asset_backing` | `fr-3.14.0` | REJECT | Gold 신호 직교성 | capital_stock_to_assets (0.93) | `research/runs/cycle-0154-noncurrent_assets_to_capital_stock/report.md` |
| `cycle-0155-noncurrent_liabilities_yield` | `noncurrent_liabilities_yield` | `market_long_debt_burden` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | noncurrent_liabilities_to_equity (0.85) | `research/runs/cycle-0155-noncurrent_liabilities_yield/report.md` |
| `cycle-0156-adv20_change_12m` | `adv20_change_12m` | `trading_liquidity_growth` | `fr-3.14.0` | PROVISIONAL | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | amihud_change_12m (-0.82) | `research/runs/cycle-0156-adv20_change_12m/report.md` |
| `cycle-0157-price_recovery_12m` | `price_recovery_12m` | `price_recovery_from_low` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | return_gain_loss_ratio_12m (0.76) | `research/runs/cycle-0157-price_recovery_12m/report.md` |
| `cycle-0158-return_gain_loss_ratio_12m` | `return_gain_loss_ratio_12m` | `return_magnitude_asymmetry` | `fr-3.14.0` | REJECT | 종착수익률 3점 방향, 다중검정 FDR | price_trend_efficiency_12m (0.99) | `research/runs/cycle-0158-return_gain_loss_ratio_12m/report.md` |

> 위 표는 최근 30건만 담는다. 오래된 128건은 생략됐다. 전문은 `research/history.jsonl`.
