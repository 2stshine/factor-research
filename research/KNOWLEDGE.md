# 연구 지식

> 자동 생성. 지침은 INSTRUCTIONS.md에만 둔다. 논문 지식은 미포함.
> 데이터 컨텍스트와 연구 원장에서 생성하며 기존 봉인 필터를 적용한다.
> 이 파일 생성은 DB 재인증이 아니다. 아래 cutoff와 campaign 상태를 확인한다.

보유 데이터·적재 범위·운영 상태는 [DATA_INVENTORY.md](DATA_INVENTORY.md)를 참조한다. 아래 입력 목록은 현재 연구 패널에 연결된 데이터만 나타낸다.

## Frozen research state

- Silver source: `RDS public Silver`
- Raw Silver period inside context boundary: `1995-05` ~ `2023-05`
- Visible Silver data period: `2015-01` ~ `2023-05`
- Research input floor: `2015-01`
- Maximum factor lookback: `36` months
- Discovery signal evaluation period: `2018-03` ~ `2023-04`
- Discovery return-support cutoff: `2023-05-31`
- Rows/months/assets: `215,794` / `101` / `2,758`
- Historical feature return: `adj_close` / `krx_split_adjusted_price_return_v1`
- Forward-label return: `total_return_close` / `krx_gross_dividend_reinvested_v3` / `forward_return_labels_only` / revision=`latest_revision_ex_post_realized` / candidate_access=`False`
- Gate ruleset: `fr-3.16.0`
- Research protocol: `epoch-1.9`
- Recorded autonomous cycles: `228`
- Active sealed campaign: `campaign-20260816-007`; OOS rows and post-cutoff outcomes are hidden from strategy context
- Strategy context cutoff: `2023-05-31`

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
| `campaign-20260816-001` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260816-001/epochs/epoch-001/reflection.md` |
| `campaign-20260816-002` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260816-002/epochs/epoch-001/reflection.md` |
| `campaign-20260816-003` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260816-003/epochs/epoch-001/reflection.md` |
| `campaign-20260816-004` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260816-004/epochs/epoch-0001/reflection.md` |
| `campaign-20260816-005` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260816-005/epochs/epoch-0001/reflection.md` |
| `campaign-20260816-006` | REVEALED | `2023-05-31` | REVEALED | `2023-06` | 1 | 1 | `research/campaigns/campaign-20260816-006/epochs/epoch-0001/reflection.md` |
| `campaign-20260816-007` | READY_FOR_CONFIRMATION | `2023-05-31` | SEALED | `2023-06` | 1 | 2 | `research/campaigns/campaign-20260816-007/epochs/epoch-0001/reflection.md` |

## Available strategy inputs

| column | overall coverage | latest-month coverage |
|---|---:|---:|
| `adj_close` | 100.0% | 100.0% |
| `adv20` | 100.0% | 100.0% |
| `amihud_illiquidity_1m` | 97.7% | 96.8% |
| `amihud_observations_1m` | 100.0% | 100.0% |
| `capital_stock` | 72.2% | 93.8% |
| `comprehensive_income` | 0.0% | 0.1% |
| `comprehensive_income_ttm` | 0.0% | 0.0% |
| `current_assets` | 81.5% | 94.1% |
| `current_liabilities` | 81.5% | 94.1% |
| `daily_return_observations_252d` | 100.0% | 100.0% |
| `daily_volatility_252d` | 99.9% | 99.9% |
| `market` | 100.0% | 100.0% |
| `market_cap` | 100.0% | 100.0% |
| `max_daily_return_1m` | 100.0% | 100.0% |
| `max_daily_return_observations_1m` | 100.0% | 100.0% |
| `net_income` | 79.8% | 94.0% |
| `net_income_ttm` | 66.5% | 89.0% |
| `net_income_yoy_change` | 63.3% | 88.8% |
| `noncurrent_assets` | 81.4% | 94.1% |
| `noncurrent_liabilities` | 81.3% | 94.0% |
| `operating_income` | 79.8% | 94.0% |
| `operating_income_ttm` | 66.5% | 89.0% |
| `pretax_income` | 79.9% | 94.0% |
| `pretax_income_ttm` | 66.4% | 88.9% |
| `price_high_252d` | 100.0% | 100.0% |
| `price_high_observations_252d` | 100.0% | 100.0% |
| `retained_earnings` | 80.8% | 94.0% |
| `revenue` | 79.5% | 93.2% |
| `revenue_ttm` | 65.6% | 87.6% |
| `shares` | 100.0% | 100.0% |
| `sue_score` | 51.8% | 84.8% |
| `total_assets` | 81.6% | 94.1% |
| `total_equity` | 81.6% | 94.1% |
| `total_liabilities` | 81.6% | 94.1% |
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
| `adv_turnover_mean_18m` | other | `adv_turnover_mean_18m` | `2f82eb593f49bd3a` | - |
| `adv_turnover_mean_24m` | other | `adv_turnover_mean_24m` | `53d4a37b3c495356` | - |
| `adv_turnover_mean_36m` | other | `adv_turnover_mean_36m` | `c2d05136c022cf48` | - |
| `adv_turnover_volatility_18m` | other | `adv_turnover_volatility_18m` | `88c226260349e7de` | - |
| `adv_turnover_volatility_24m` | other | `adv_turnover_volatility_24m` | `020097c58fdd3ab0` | - |
| `adv_turnover_volatility_36m` | other | `adv_turnover_volatility_36m` | `dc76fe94f34ee1ed` | - |
| `adv_turnover_volatility_6m` | other | `adv_turnover_volatility_6m` | `87902ff1d022efa7` | - |
| `amihud_change_12m` | other | `liquidity_deterioration` | `ae4560c85988cb8d` | - |
| `amihud_illiquidity_1m` | other | `liquidity` | `72bd57d66a5cb84d` | - |
| `amihud_mean_18m` | other | `amihud_mean_18m` | `280fd106447488e4` | - |
| `amihud_mean_24m` | other | `amihud_mean_24m` | `ac31e7289f533021` | - |
| `amihud_mean_36m` | other | `amihud_mean_36m` | `cfe4789e79158516` | - |
| `amihud_mean_6m` | other | `amihud_mean_6m` | `3c2d1554ca544992` | - |
| `amihud_volatility_12m` | other | `liquidity_instability` | `bfd49a2484fe9153` | - |
| `amihud_volatility_18m` | other | `amihud_volatility_18m` | `afb1370c9299bd3f` | - |
| `amihud_volatility_24m` | other | `amihud_volatility_24m` | `751fd2edefd55078` | - |
| `amihud_volatility_36m` | other | `amihud_volatility_36m` | `6f64b3417b70743e` | - |
| `amihud_volatility_6m` | other | `amihud_volatility_6m` | `fe67eaad9ce094a0` | - |
| `asset_growth_12m` | other | `asset_growth` | `8036ceaacef6ac62` | total_assets |
| `asset_growth_acceleration_12m` | other | `investment_acceleration` | `c9ffb35aab06e21f` | total_assets |
| `asset_to_market` | value | `asset_backed_value` | `8b1db811b2216526` | total_assets |
| `asset_turnover_acceleration_12m` | quality | `asset_efficiency_acceleration` | `990062b564c6ae51` | revenue_ttm, total_assets |
| `asset_turnover_change_12m` | quality | `asset_turnover_change` | `8f8e7c42fdc9fce8` | revenue_ttm, total_assets |
| `asset_turnover_volatility_36m` | quality | `asset_efficiency_stability` | `7790b109be96a0c3` | revenue_ttm, total_assets |
| `book_to_market_change_12m` | value | `book_value_repricing` | `e73b53f0ffaaf3c5` | total_equity |
| `book_to_market_change_6m` | value | `book_to_market_change_6m` | `13d7e8d539ebcf9a` | total_equity |
| `capital_stock_growth_12m` | other | `legal_capital_issuance_growth` | `e09f61de6fa86d70` | capital_stock |
| `capital_stock_growth_18m` | other | `capital_stock_growth_18m` | `4f5fb784acc782f3` | capital_stock |
| `capital_stock_growth_6m` | other | `capital_stock_growth_6m` | `d46e7260fb0585fb` | capital_stock |
| `capital_stock_share_change_12m` | other | `contributed_capital_share_change` | `7f5557c0c07307a4` | capital_stock, total_equity |
| `capital_stock_to_assets` | other | `nominal_capital_intensity` | `dd1d0d32a2a49a3c` | capital_stock, total_assets |
| `capital_stock_to_current_assets` | other | `legal_capital_current_asset_intensity` | `479a770e1c7ab82a` | capital_stock, current_assets |
| `capital_stock_to_current_liabilities` | quality | `legal_capital_short_debt_coverage` | `41a5be7768c1c7c1` | capital_stock, current_liabilities |
| `capital_stock_to_liabilities` | quality | `nominal_capital_debt_coverage` | `177e5062f4f3b37c` | capital_stock, total_liabilities |
| `capital_stock_yield` | value | `legal_capital_value` | `1de2eb2066948601` | capital_stock |
| `capital_stock_yield_change_12m` | value | `capital_stock_yield_change_12m` | `4097c7a46278b545` | capital_stock |
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
| `earnings_yield_change_12m` | value | `earnings_yield_change_12m` | `f5e009cd5a309359` | net_income_ttm |
| `enterprise_earnings_yield_change_12m` | value | `enterprise_earnings_yield_change_12m` | `70dc5d379c23c1f4` | net_income_ttm, total_liabilities |
| `enterprise_sales_yield_change_12m` | value | `enterprise_sales_yield_change_12m` | `553ff1ee6fff0380` | revenue_ttm, total_liabilities |
| `enterprise_sales_yield_change_6m` | value | `enterprise_sales_yield_change_6m` | `7db27be88ae7fe84` | revenue_ttm, total_liabilities |
| `equity_debt_coverage_change_12m` | quality | `book_solvency_improvement` | `cd46d2f611150038` | total_equity, total_liabilities |
| `equity_growth_12m` | other | `equity_growth` | `7c69893c5073ff70` | total_equity |
| `equity_growth_24m` | other | `equity_growth_24m` | `1eda12af513e42ee` | total_equity |
| `equity_growth_6m` | other | `equity_growth_6m` | `79a8dad1141661fe` | total_equity |
| `equity_growth_acceleration_12m` | other | `equity_expansion_acceleration` | `aef96b739387ffd1` | total_equity |
| `equity_to_current_liabilities` | quality | `short_term_equity_solvency` | `cb5d900cd356de54` | total_equity, current_liabilities |
| `equity_to_noncurrent_liabilities` | quality | `long_term_equity_solvency` | `dbfa1a3f3bc862d3` | total_equity, noncurrent_liabilities |
| `high_12m_proximity` | momentum | `price_anchoring` | `fce1984269262fba` | - |
| `high_24m_proximity` | momentum | `high_24m_proximity` | `cd05cc73466c7e16` | - |
| `high_52w_price_proximity` | momentum | `price_anchoring` | `559d74ab903459ce` | - |
| `idiosyncratic_volatility_24m` | other | `idiosyncratic_volatility` | `af24645c3a81a842` | - |
| `intermediate_momentum_12_7` | momentum | `intermediate_momentum` | `df9d7a028fded1f2` | - |
| `liability_growth_12m` | other | `liability_growth` | `048bced1c445efe6` | total_liabilities |
| `liability_growth_acceleration_12m` | other | `debt_growth_acceleration` | `f14b34ecb54a5d5b` | total_liabilities |
| `long_term_reversal_36_12` | momentum | `long_term_reversal` | `27b93af8ce3d6c07` | - |
| `low_vol_12m` | other | `low_volatility` | `2dcb671efc74db88` | - |
| `market_beta_12m` | quality | `market_beta_12m` | `87688a5728969be7` | - |
| `market_beta_18m` | quality | `market_beta_18m` | `92fb2aeb033b6297` | - |
| `market_beta_24m` | quality | `market_beta_24m` | `e45a30f4ddf21e70` | - |
| `market_beta_36m` | other | `market_beta` | `2651806103f53620` | - |
| `market_beta_6m` | quality | `market_beta_6m` | `4f5daaf025ecbb6d` | - |
| `market_beta_9m` | quality | `market_beta_9m` | `a5eecfc64ea8f89f` | - |
| `market_leverage` | other | `market_leverage` | `34e619cb846843cc` | total_liabilities |
| `market_leverage_change_12m` | other | `market_leverage_change` | `8dd3424bb7bcc564` | total_liabilities |
| `market_leverage_change_18m` | other | `market_leverage_change_18m` | `5ce10c815bc2ed3b` | total_liabilities |
| `market_leverage_change_24m` | other | `market_leverage_change_24m` | `6eff427d0a489a97` | total_liabilities |
| `market_leverage_change_30m` | other | `market_leverage_change_30m` | `b8a66a0760240074` | total_liabilities |
| `market_leverage_change_6m` | other | `market_leverage_change_6m` | `2bf83eb4aa0573f2` | total_liabilities |
| `market_relative_momentum_12_1` | momentum | `market_relative_momentum` | `8377d93ea80f76dc` | - |
| `market_relative_momentum_18_3` | momentum | `market_relative_momentum_18_3` | `692ba390ba579c1f` | - |
| `market_relative_momentum_24_6` | momentum | `market_relative_momentum_24_6` | `b285481777589b80` | - |
| `market_relative_momentum_6_1` | momentum | `market_relative_momentum_6_1` | `5160f601452bf9ba` | - |
| `market_return_correlation_12m` | quality | `market_return_correlation_12m` | `57553db741f2238a` | - |
| `market_return_correlation_18m` | quality | `market_return_correlation_18m` | `d3b224cbd565b1ac` | - |
| `market_return_correlation_24m` | quality | `market_return_correlation_24m` | `e6e1fca311b334cb` | - |
| `market_return_correlation_6m` | quality | `market_return_correlation_6m` | `5e983a710b3ac447` | - |
| `market_return_correlation_9m` | quality | `market_return_correlation_9m` | `737f9a0075a59652` | - |
| `max_daily_return_1m` | other | `lottery_demand` | `e29c3da27f06a3ba` | - |
| `max_daily_return_change_12m` | other | `lottery_demand_acceleration` | `ce0680b52ff03580` | - |
| `max_daily_return_change_18m` | quality | `max_daily_return_change_18m` | `723f3066c636e349` | - |
| `max_daily_return_change_6m` | quality | `max_daily_return_change_6m` | `fafcc5c9c1e218b7` | - |
| `max_daily_return_instability_18m` | quality | `max_daily_return_instability_18m` | `546716d030be5d4f` | - |
| `max_daily_return_instability_6m` | quality | `max_daily_return_instability_6m` | `f0296fa3fb67c448` | - |
| `max_daily_return_mean_6m` | quality | `max_daily_return_mean_6m` | `31a163e4cf9857a1` | - |
| `max_monthly_return_12m` | other | `lottery_demand` | `54e7c79ca04fdc7e` | - |
| `medium_term_momentum_6_2` | momentum | `medium_term_momentum` | `fe7484d4b16ecc1c` | - |
| `momentum_acceleration_6m` | momentum | `price_momentum_acceleration` | `98a613007a62aa32` | - |
| `net_equity_issuance_12m` | other | `net_equity_issuance` | `45bcea59dbd07918` | - |
| `net_equity_issuance_price_adjusted_12m` | other | `net_equity_issuance` | `01ee73e28cd8f170` | - |
| `net_equity_issuance_price_adjusted_24m` | other | `net_equity_issuance_price_adjusted_24m` | `8becef4650a994b3` | - |
| `net_equity_issuance_price_adjusted_36m` | other | `net_equity_issuance_price_adjusted_36m` | `e7a5c1273e578254` | - |
| `net_income_growth_12m` | earnings | `trailing_net_income_growth` | `6bec9560dceccc6d` | net_income_ttm |
| `net_income_growth_acceleration_12m` | earnings | `net_earnings_acceleration` | `9cf84e9a3afcffa9` | net_income_ttm |
| `net_income_to_capital_stock` | quality | `legal_capital_net_return` | `86f96d4808be68f4` | net_income_ttm, capital_stock |
| `net_income_to_current_assets` | quality | `current_asset_net_productivity` | `6cdf007f39f23b91` | net_income_ttm, current_assets |
| `net_income_to_liabilities` | quality | `posttax_debt_coverage` | `0cb38fb5ad3db869` | net_income_ttm, total_liabilities |
| `net_income_to_noncurrent_assets` | quality | `long_asset_net_productivity` | `976770c25d2e7a5e` | net_income_ttm, noncurrent_assets |
| `net_margin_change_6m` | earnings | `net_margin_change_6m` | `71fc629dd84ab9d6` | net_income_ttm, revenue_ttm |
| `net_margin_volatility_12m` | earnings | `net_margin_volatility_12m` | `229f9382dbbdee96` | net_income_ttm, revenue_ttm |
| `net_margin_volatility_36m` | quality | `net_margin_stability` | `c111dc48be850952` | net_income_ttm, revenue_ttm |
| `net_profit_margin` | quality | `net_profit_margin` | `a1e679b213e5f339` | net_income_ttm, revenue_ttm |
| `net_profit_margin_change_12m` | earnings | `net_margin_expansion` | `7c03a263baafbc66` | net_income_ttm, revenue_ttm |
| `net_roa` | quality | `net_roa` | `ad335843d7d17cec` | net_income_ttm, total_assets |
| `net_roa_volatility_36m` | quality | `net_profitability_stability` | `fc4107bfda24d6d7` | net_income_ttm, total_assets |
| `net_to_operating_income_conversion` | earnings | `net_to_operating_income_conversion` | `03346b560e09419d` | net_income_ttm, operating_income_ttm |
| `net_working_capital_to_assets` | quality | `working_capital_buffer` | `8dbeb79579b0e9eb` | current_assets, current_liabilities, total_assets |
| `net_working_capital_to_liabilities` | quality | `working_capital_debt_coverage` | `2314b9f8f2ead59a` | current_assets, current_liabilities, total_liabilities |
| `net_working_capital_yield` | value | `liquid_asset_value` | `0c14cdb6457bdf0a` | current_assets, current_liabilities |
| `noncurrent_asset_encumbrance` | quality | `long_term_asset_encumbrance` | `8c1ba3eef1fc9629` | noncurrent_liabilities, noncurrent_assets |
| `noncurrent_asset_growth_18m` | quality | `noncurrent_asset_growth_18m` | `a40e6f4a6711b2d4` | noncurrent_assets |
| `noncurrent_asset_growth_24m` | quality | `noncurrent_asset_growth_24m` | `beb4ca235d839b51` | noncurrent_assets |
| `noncurrent_asset_growth_30m` | quality | `noncurrent_asset_growth_30m` | `6a4c3ef01e7100b9` | noncurrent_assets |
| `noncurrent_asset_growth_6m` | quality | `noncurrent_asset_growth_6m` | `e7a529745ed2719c` | noncurrent_assets |
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
| `operating_asset_growth_12m` | quality | `operating_asset_growth_12m` | `623a85a993bff126` | total_assets, current_liabilities |
| `operating_asset_growth_24m` | quality | `operating_asset_growth_24m` | `b2ab8af411cad0e9` | total_assets, current_liabilities |
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
| `operating_margin_change_6m` | earnings | `operating_margin_change_6m` | `15c5cf3d8963ace9` | operating_income_ttm, revenue_ttm |
| `operating_margin_volatility_12m` | earnings | `operating_margin_volatility_12m` | `3ac164c57d2b0b9d` | operating_income_ttm, revenue_ttm |
| `operating_return_on_capital_employed` | quality | `capital_employment_efficiency` | `aa11ccad9cfd19c6` | operating_income_ttm, total_assets, current_liabilities |
| `operating_roa` | quality | `operating_roa` | `0c399c65bc5c8e11` | operating_income_ttm, total_assets |
| `operating_roa_change_12m` | earnings | `profitability_change` | `4c2f3e0638033747` | operating_income_ttm, total_assets |
| `operating_roa_volatility_36m` | quality | `profitability_stability` | `d4b9c4dfb4af6b5f` | operating_income_ttm, total_assets |
| `operating_yield_change_12m` | value | `operating_yield_change_12m` | `5bed9215eca57393` | operating_income_ttm |
| `paid_in_capital_ratio` | quality | `equity_composition` | `8c82db0117290bcd` | capital_stock, total_equity |
| `positive_return_share_12m` | momentum | `return_consistency` | `acae6c61863c2804` | - |
| `positive_return_share_18m` | momentum | `positive_return_share_18m` | `e91acabf4971310f` | - |
| `positive_return_share_24m` | momentum | `positive_return_share_24m` | `923fc8b46eed56ff` | - |
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
| `pretax_to_operating_income_conversion` | earnings | `pretax_to_operating_income_conversion` | `42f0b3cfaf4d713f` | operating_income_ttm, pretax_income_ttm |
| `pretax_yield_change_12m` | value | `pretax_yield_change_12m` | `917126a0bb529a10` | pretax_income_ttm |
| `pretax_yield_change_6m` | value | `pretax_yield_change_6m` | `ffea4912dd9bcb98` | pretax_income_ttm |
| `price_momentum_12_3` | momentum | `price_momentum_12_3` | `ea59fe90641d5356` | - |
| `price_momentum_15_3` | momentum | `price_momentum_15_3` | `89bab38b8f7711de` | - |
| `price_momentum_18_6` | momentum | `price_momentum_18_6` | `9b32d1620cdb42d7` | - |
| `price_momentum_24_6` | momentum | `price_momentum_24_6` | `556298d3f93806f7` | - |
| `price_momentum_6_1` | momentum | `price_momentum_6_1` | `7def462309a0fa60` | - |
| `price_momentum_9_2` | momentum | `price_momentum_9_2` | `ef2e2615147c9a7f` | - |
| `price_range_12m` | other | `price_range_risk` | `b564b360f33b0dca` | - |
| `price_recovery_12m` | momentum | `price_recovery_from_low` | `6c2f9df4e590ffad` | - |
| `price_recovery_24m` | momentum | `price_recovery_24m` | `10c51b9e8a8c37f1` | - |
| `price_reversal_24_12` | momentum | `price_reversal_24_12` | `f76058a52b8e66a6` | - |
| `price_reversal_36_24` | momentum | `price_reversal_36_24` | `0a0bc821219e6f54` | - |
| `price_reversal_3_1` | momentum | `price_reversal_3_1` | `9924ac6aa4005cc6` | - |
| `price_reversal_6_3` | momentum | `price_reversal_6_3` | `5ae8ced7b1a14b5d` | - |
| `price_trend_efficiency_12m` | momentum | `directional_price_efficiency` | `ef0a1d0f9ef6aaff` | - |
| `price_trend_efficiency_24m` | momentum | `price_trend_efficiency_24m` | `1388dbb5a089c6e1` | - |
| `profitable_small_value` | quality | `quality_small_value` | `ec639be0f12aad5a` | total_equity, operating_income_ttm, total_assets |
| `quality_stability` | quality | `quality_stability` | `6ee5f5fd4f04ffe0` | operating_income_ttm, revenue_ttm, total_assets, total_equity |
| `realized_daily_volatility_change_24m` | quality | `realized_daily_volatility_change_24m` | `ac577decfdf6edbd` | - |
| `realized_daily_volatility_change_6m` | quality | `realized_daily_volatility_change_6m` | `935e44dfee85d3c1` | - |
| `realized_daily_volatility_instability_18m` | quality | `realized_daily_volatility_instability_18m` | `a9e069b32208a2bb` | - |
| `realized_daily_volatility_instability_36m` | quality | `realized_daily_volatility_instability_36m` | `9cdd893a91f2c389` | - |
| `realized_daily_volatility_instability_6m` | quality | `realized_daily_volatility_instability_6m` | `33050a6c1055cb3e` | - |
| `realized_volatility_252d` | other | `low_volatility` | `e0668fb0e7c0eb69` | - |
| `retained_earnings_growth_12m` | quality | `internal_capital_accumulation` | `b3c24c1cb9c7a15a` | retained_earnings |
| `retained_earnings_growth_acceleration_12m` | quality | `internal_capital_acceleration` | `34a28f0d2076a197` | retained_earnings |
| `retained_earnings_to_assets` | quality | `internal_financing` | `1489feceb711fd22` | retained_earnings, total_assets |
| `retained_earnings_to_assets_change_12m` | quality | `retained_earnings_accumulation` | `c98308cb4bcfc12b` | retained_earnings, total_assets |
| `retained_earnings_to_assets_change_6m` | earnings | `retained_earnings_to_assets_change_6m` | `7c89e1c5df5d7621` | retained_earnings, total_assets |
| `retained_earnings_to_assets_volatility_12m` | earnings | `retained_earnings_to_assets_volatility_12m` | `b7a8b39202f9a9eb` | retained_earnings, total_assets |
| `retained_earnings_to_capital_stock` | quality | `earned_to_contributed_capital` | `ac476a86c1174da7` | retained_earnings, capital_stock |
| `retained_earnings_to_current_assets` | quality | `internal_capital_current_asset_backing` | `a00c5c91229e2e08` | retained_earnings, current_assets |
| `retained_earnings_to_current_liabilities` | quality | `internal_capital_short_debt_coverage` | `bfc0cf2c33de0169` | retained_earnings, current_liabilities |
| `retained_earnings_to_equity` | quality | `retained_earnings_equity_share` | `ede7286f5e5ca082` | retained_earnings, total_equity |
| `retained_earnings_to_liabilities` | quality | `earned_capital_debt_coverage` | `50d2f8c1276ed5cf` | retained_earnings, total_liabilities |
| `retained_earnings_to_noncurrent_assets` | quality | `internal_capital_long_asset_backing` | `e2cec8a4d63286cb` | retained_earnings, noncurrent_assets |
| `retained_earnings_to_noncurrent_liabilities` | quality | `internal_capital_long_debt_coverage` | `e485b63dd64938fd` | retained_earnings, noncurrent_liabilities |
| `retained_earnings_yield` | value | `accumulated_earnings_value` | `ed934394649254e9` | retained_earnings |
| `retained_earnings_yield_change_12m` | value | `retained_earnings_yield_change_12m` | `3cc4cd00954c9e17` | retained_earnings |
| `return_gain_loss_ratio_12m` | momentum | `return_magnitude_asymmetry` | `b1d121f4359b9bd3` | - |
| `return_kurtosis_24m` | other | `return_tail_concentration` | `28373510626d93b0` | - |
| `return_persistence_12m` | momentum | `monthly_return_persistence` | `82f9ce9d7b871458` | - |
| `return_persistence_24m` | momentum | `return_persistence_24m` | `76fd35034d901197` | - |
| `return_seasonality_12m` | momentum | `return_seasonality_12m` | `4225bbe32cc2bf60` | - |
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
| `total_asset_growth_18m` | quality | `total_asset_growth_18m` | `2472603aca518c03` | total_assets |
| `total_asset_growth_24m` | quality | `total_asset_growth_24m` | `c8b140ad43461a4e` | total_assets |
| `total_asset_growth_30m` | quality | `total_asset_growth_30m` | `b86e2e75202e6433` | total_assets |
| `total_asset_growth_6m` | quality | `total_asset_growth_6m` | `9beb485c745b1cac` | total_assets |
| `trading_turnover_20d` | other | `trading_activity` | `c03efb8638407bd6` | - |
| `trading_value_turnover_change_12m` | other | `trading_value_turnover_change_12m` | `5c9546987122a9f6` | - |
| `trading_value_turnover_change_3m` | other | `trading_value_turnover_change_3m` | `1de516aad267f8a3` | - |
| `trading_value_turnover_change_6m` | other | `trading_value_turnover_change_6m` | `365802732e9a350e` | - |
| `trading_value_turnover_volatility_24m` | other | `trading_value_turnover_volatility_24m` | `6c8fe463aa9a0578` | - |
| `trading_value_turnover_volatility_6m` | other | `trading_value_turnover_volatility_6m` | `7a06ea1a54ceeaa6` | - |
| `trading_value_volatility_12m` | other | `trading_attention_instability` | `74ce4f67d200762d` | - |
| `turnover_change_6m` | other | `trading_attention_change` | `f21fb281d5313d01` | - |
| `turnover_volatility_12m` | other | `trading_activity_instability` | `07f156b1d7953440` | - |
| `working_capital_accruals_12m` | quality | `working_capital_accruals` | `7d539b85a67522d6` | current_assets, current_liabilities, total_assets |
| `working_capital_accruals_24m` | earnings | `working_capital_accruals_24m` | `8676e7864fe77761` | current_assets, current_liabilities, total_assets |
| `working_capital_accruals_6m` | earnings | `working_capital_accruals_6m` | `4cf5edda4d951b21` | current_assets, current_liabilities, total_assets |
| `working_capital_growth_12m` | other | `working_capital_investment` | `3b7ad689dbdebc0a` | current_assets, current_liabilities |
| `working_capital_to_sales` | quality | `working_capital_sales_buffer` | `85cadc517d7da429` | current_assets, current_liabilities, revenue_ttm |














## 공개 가능한 최근 성찰

### 관측된 제약

최신 성찰의 지시는 봉인 경계 안에 있어 공개하지 않는다.


## 탐색 영역 분포


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


## 공개 가능한 구조적 교훈

공개 가능한 교훈 없음. 봉인 시행은 아래 정체성만 제공한다.

## 전체 시행 정체성


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

## 누적 검증 교훈

같은 계열·검사·규칙·단계의 관측을 묶었다. 독립적인 증거 개수가 아니다.

### accumulated_earnings_value / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/retained_earnings_yield

### adv_turnover_mean_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/adv_turnover_mean_18m

### adv_turnover_mean_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/adv_turnover_mean_24m

### adv_turnover_mean_36m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/adv_turnover_mean_36m

### amihud_mean_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/amihud_mean_18m

### amihud_mean_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/amihud_mean_24m

### amihud_mean_36m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/amihud_mean_36m

### amihud_mean_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/amihud_mean_6m

### amihud_volatility_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/amihud_volatility_18m

### amihud_volatility_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/amihud_volatility_24m

### amihud_volatility_36m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/amihud_volatility_36m

### amihud_volatility_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/amihud_volatility_6m

### asset_backed_value / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/asset_to_market

### asset_efficiency_stability / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: FAIL; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-006/epoch-001/asset_turnover_volatility_36m

### asset_liquidity_share / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-007/epoch-001/current_assets_to_assets

### asset_rigidity_change / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-003/epoch-001/noncurrent_asset_share_change_12m

### book_scaled_trading_activity / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/adv20_to_book_equity

### book_solvency_improvement / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/equity_debt_coverage_change_12m

### book_to_market_change_6m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/book_to_market_change_6m

### book_value_repricing / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-007/epoch-001/book_to_market_change_12m

### capital_stock_growth_18m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/capital_stock_growth_18m

### capital_stock_growth_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/capital_stock_growth_6m

### contributed_capital_share_change / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/capital_stock_share_change_12m

### current_asset_net_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/net_income_to_current_assets

### current_asset_operating_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/operating_income_to_current_assets

### current_asset_turnover / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260814-002/epoch-001/current_asset_turnover

### debt_growth_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-010/epoch-001/liability_growth_acceleration_12m

### directional_price_efficiency / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/price_trend_efficiency_12m

### earned_capital_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-004/epoch-001/retained_earnings_to_liabilities

### earned_to_contributed_capital / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-001/epoch-001/retained_earnings_to_capital_stock

### earnings_yield_change_12m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/earnings_yield_change_12m

### enterprise_earnings_yield_change_12m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/enterprise_earnings_yield_change_12m

### enterprise_sales_yield_change_6m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/enterprise_sales_yield_change_6m

### equity_asset_rigidity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-008/epoch-001/noncurrent_assets_to_equity

### equity_expansion_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-010/epoch-001/equity_growth_acceleration_12m

### equity_growth_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/equity_growth_24m

### equity_growth_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/equity_growth_6m

### equity_liquidity_capacity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-008/epoch-001/current_assets_to_equity

### equity_revenue_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-010/epoch-001/revenue_to_equity

### flexible_asset_mix / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/current_assets_to_noncurrent_assets

### high_24m_proximity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/high_24m_proximity

### idiosyncratic_volatility / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260814-002/epoch-001/idiosyncratic_volatility_24m

### internal_capital_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/retained_earnings_growth_acceleration_12m

### internal_capital_accumulation / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-002/epoch-001/retained_earnings_growth_12m

### internal_capital_current_asset_backing / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/retained_earnings_to_current_assets

### internal_capital_long_asset_backing / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/retained_earnings_to_noncurrent_assets

### internal_capital_long_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/retained_earnings_to_noncurrent_liabilities

### internal_capital_short_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/retained_earnings_to_current_liabilities

### investment_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-007/epoch-001/asset_growth_acceleration_12m

### legal_capital_current_asset_intensity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/capital_stock_to_current_assets

### legal_capital_issuance_growth / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-002/epoch-001/capital_stock_growth_12m

### legal_capital_long_asset_backing / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/noncurrent_assets_to_capital_stock

### legal_capital_net_return / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/net_income_to_capital_stock

### legal_capital_operating_return / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/operating_income_to_capital_stock

### legal_capital_revenue_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/revenue_to_capital_stock

### legal_capital_short_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/capital_stock_to_current_liabilities

### legal_capital_value / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/capital_stock_yield

### liability_maturity_change / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-005/epoch-001/noncurrent_liability_share_change_12m

### liquid_asset_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-001/epoch-001/current_assets_to_total_liabilities

### liquid_asset_value / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-008/epoch-001/net_working_capital_yield

### liquid_asset_value / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/current_assets_yield

### liquidity_deterioration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/amihud_change_12m

### liquidity_instability / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/amihud_volatility_12m

### long_asset_net_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/net_income_to_noncurrent_assets

### long_lived_asset_investment_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-003/epoch-001/noncurrent_assets_growth_12m

### long_lived_asset_operating_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-001/epoch-001/operating_income_to_noncurrent_assets

### long_lived_asset_revenue_productivity / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-009/epoch-001/revenue_to_noncurrent_assets

### long_lived_asset_value / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/noncurrent_assets_yield

### long_term_book_leverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-009/epoch-001/noncurrent_liabilities_to_equity

### long_term_debt_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-003/epoch-001/noncurrent_liabilities_growth_12m

### long_term_equity_solvency / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/equity_to_noncurrent_liabilities

### long_term_liability_burden / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-004/epoch-001/noncurrent_liabilities_to_assets

### long_term_operating_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-010/epoch-001/operating_income_to_noncurrent_liabilities

### long_term_revenue_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/revenue_to_noncurrent_liabilities

### lottery_demand_acceleration / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/max_daily_return_change_12m

### market_beta_12m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/market_beta_12m

### market_beta_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/market_beta_18m

### market_beta_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/market_beta_24m

### market_beta_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/market_beta_6m

### market_beta_9m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/market_beta_9m

### market_leverage_change / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-005/epoch-001/market_leverage_change_12m

### market_leverage_change_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/market_leverage_change_18m

### market_leverage_change_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/market_leverage_change_24m

### market_leverage_change_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/market_leverage_change_6m

### market_long_debt_burden / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/noncurrent_liabilities_yield

### market_relative_momentum / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/market_relative_momentum_12_1

### market_relative_momentum_6_1 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/market_relative_momentum_6_1

### market_return_correlation_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/market_return_correlation_6m

### market_return_correlation_9m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/market_return_correlation_9m

### market_short_debt_burden / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/current_liabilities_yield

### max_daily_return_change_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/max_daily_return_change_18m

### max_daily_return_change_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/max_daily_return_change_6m

### max_daily_return_instability_18m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/max_daily_return_instability_18m

### max_daily_return_mean_6m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/max_daily_return_mean_6m

### medium_term_momentum / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-010/epoch-001/medium_term_momentum_6_2

### monthly_return_persistence / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/return_persistence_12m

### net_equity_issuance_price_adjusted_36m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/net_equity_issuance_price_adjusted_36m

### net_margin_change_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/net_margin_change_6m

### net_margin_expansion / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-005/epoch-001/net_profit_margin_change_12m

### net_margin_stability / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: FAIL; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-006/epoch-001/net_margin_volatility_36m

### net_margin_volatility_12m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/net_margin_volatility_12m

### net_profitability_stability / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: FAIL; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-006/epoch-001/net_roa_volatility_36m

### net_to_operating_income_conversion / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/net_to_operating_income_conversion

### nominal_capital_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-007/epoch-001/capital_stock_to_liabilities

### nominal_capital_intensity / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-007/epoch-001/capital_stock_to_assets

### noncurrent_asset_growth_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/noncurrent_asset_growth_18m

### noncurrent_asset_growth_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/noncurrent_asset_growth_24m

### noncurrent_asset_growth_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/noncurrent_asset_growth_6m

### nonoperating_sales_burden / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/nonoperating_burden_margin

### operating_book_equity_return / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-009/epoch-001/operating_income_to_equity

### operating_earnings_yield / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260814-002/epoch-001/operating_earnings_yield

### operating_income_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-002/epoch-001/operating_income_growth_12m

### operating_margin_change_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/operating_margin_change_6m

### operating_yield_change_12m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/operating_yield_change_12m

### positive_return_share_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/positive_return_share_24m

### posttax_debt_coverage / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-004/epoch-001/net_income_to_liabilities

### pretax_book_equity_return / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/pretax_income_to_equity

### pretax_debt_coverage / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-004/epoch-001/pretax_income_to_liabilities

### pretax_margin_stability / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: FAIL; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-006/epoch-001/pretax_margin_volatility_36m

### pretax_profitability_margin / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-001/epoch-001/pretax_profit_margin

### pretax_profitability_stability / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: FAIL; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-006/epoch-001/pretax_roa_volatility_36m

### pretax_to_operating_income_conversion / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/pretax_to_operating_income_conversion

### pretax_yield_change_12m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/pretax_yield_change_12m

### pretax_yield_change_6m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/pretax_yield_change_6m

### price_momentum_15_3 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/price_momentum_15_3

### price_momentum_18_6 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/price_momentum_18_6

### price_momentum_24_6 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/price_momentum_24_6

### price_momentum_6_1 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/price_momentum_6_1

### price_momentum_9_2 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/price_momentum_9_2

### price_momentum_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/momentum_acceleration_6m

### price_range_risk / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/price_range_12m

### price_recovery_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/price_recovery_24m

### price_recovery_from_low / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/price_recovery_12m

### price_reversal_3_1 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/price_reversal_3_1

### price_reversal_6_3 / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/price_reversal_6_3

### price_trend_efficiency_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/price_trend_efficiency_24m

### realized_daily_volatility_change_24m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/realized_daily_volatility_change_24m

### realized_daily_volatility_change_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/realized_daily_volatility_change_6m

### realized_daily_volatility_instability_6m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/realized_daily_volatility_instability_6m

### retained_earnings_accumulation / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-005/epoch-001/retained_earnings_to_assets_change_12m

### retained_earnings_equity_share / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260814-002/epoch-001/retained_earnings_to_equity

### retained_earnings_to_assets_change_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/retained_earnings_to_assets_change_6m

### retained_earnings_to_assets_volatility_12m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/retained_earnings_to_assets_volatility_12m

### return_magnitude_asymmetry / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/return_gain_loss_ratio_12m

### return_seasonality_12m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/return_seasonality_12m

### revenue_debt_turnover / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-001/epoch-001/revenue_to_total_liabilities

### risk_deterioration / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/daily_volatility_change_12m

### short_term_debt_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-009/epoch-001/current_liabilities_growth_acceleration_12m

### short_term_equity_solvency / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/equity_to_current_liabilities

### short_term_financing_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-002/epoch-001/current_liabilities_growth_12m

### short_term_funding_sales_burden / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/current_liabilities_to_sales

### short_term_liability_burden / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-004/epoch-001/current_liabilities_to_assets

### short_term_operating_coverage / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 검사 통과를 미래 수익 보장으로 해석하지 않는다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260814-002/epoch-001/operating_income_to_current_liabilities

### short_term_operating_coverage_improvement / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/operating_coverage_change_12m

### short_term_revenue_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/revenue_to_current_liabilities

### short_term_reversal_3m / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: FAIL; T4.2 OOS 다중검정 FDR: FAIL; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-009/epoch-001/short_term_reversal_3m

### short_term_solvency_change / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-005/epoch-001/current_ratio_change_12m

### total_asset_growth_18m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-002/epoch-001/total_asset_growth_18m

### total_asset_growth_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-003/epoch-001/total_asset_growth_24m

### total_asset_growth_30m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-004/epoch-0001/total_asset_growth_30m

### total_asset_growth_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-001/epoch-001/total_asset_growth_6m

### trading_attention_change / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-013/epoch-001/turnover_change_6m

### trading_attention_instability / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-014/epoch-001/trading_value_volatility_12m

### trading_liquidity_growth / confirmation

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS; T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: PASS; T5.1 Gold 신호 직교성: PASS; T4.1 고정 OOS IC: PASS; T4.2 OOS 다중검정 FDR: PASS; T4.4 게이트 귀무 보정: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/adv20_change_12m

### trading_value_turnover_change_3m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: FAIL; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-007/epoch-0001/trading_value_turnover_change_3m

### trailing_net_income_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-003/epoch-001/net_income_growth_12m

### trailing_pretax_income_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-003/epoch-001/pretax_income_growth_12m

### working_asset_acceleration / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-008/epoch-001/current_assets_growth_acceleration_12m

### working_asset_revenue_productivity / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: PASS; T2.1 투자가능 IC 최소요건: PASS; T2.1 투자가능 Rank ICIR 최소요건: PASS; T3.1 비중첩 구간 IC 방향: PASS; T3.1 IC 레짐 집중도: PASS; T3.2 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: PASS; T4.3 다중검정 FDR: UNVERIFIED; T5.1 Gold 신호 직교성: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-012/epoch-001/revenue_to_current_assets

### working_capital_accruals_24m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-006/epoch-0001/working_capital_accruals_24m

### working_capital_accruals_6m / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260816-005/epoch-0001/working_capital_accruals_6m

### working_capital_debt_coverage / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-008/epoch-001/net_working_capital_to_liabilities

### working_capital_investment / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-015/epoch-001/working_capital_growth_12m

### working_capital_investment_growth / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: FAIL; T1.3 배당 포함 총수익 계약: PASS
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-002/epoch-001/current_assets_growth_12m

### working_capital_sales_buffer / discovery

- 확인된 검사: T0.1 미선언 상수: PASS; T0.2 단일 팩터 계약: PASS; T0.3 최대 룩백: PASS; T0.4 연구 입력 하한: PASS; T0.5 label 전용 입력 차단: PASS; T0.6 입력 계약: PASS; T0.8 출력 타입·인덱스: PASS; T0.9 유한값: PASS; T0.10 결정성: PASS; T0.11 36개월 인과성: PASS; T0.12 캐시 정의 일치: PASS; T1.1 전체 커버리지: PASS; T1.1 월별 커버리지 하위10%: PASS; T1.2 종착수익률 3점 방향: PASS; T1.3 배당 포함 총수익 계약: PASS; T2.1 전체 IC 최소요건: FAIL; T2.1 투자가능 IC 최소요건: FAIL; T2.1 투자가능 Rank ICIR 최소요건: FAIL
- 해석(추정): 원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.
- 교훈: 실패 검사와 경제적 원인을 구분해야 한다.
- 적용 한계: 해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기.
- 근거: campaign-20260815-011/epoch-001/working_capital_to_sales
