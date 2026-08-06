# Factor research context

> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.

## Frozen research state

- Silver source: `RDS public Silver`
- Silver data period: `2015-01` ~ `2026-08`
- Common evaluation period: `2018-03` ~ `2026-08`
- Rows/months/assets: `334,354` / `140` / `3,301`
- Return field: `total_return_close`
- Gate ruleset: `fr-3.5.0`
- Research protocol: `epoch-1.2`
- Recorded autonomous cycles: `27`

## Sealed-OOS campaigns

아직 campaign 없음. 새 연구는 campaign과 epoch을 먼저 사전등록한다.

## Available strategy inputs

| column | overall coverage | latest-month coverage |
|---|---:|---:|
| `adv20` | 100.0% | 100.0% |
| `capital_stock` | 76.5% | 95.4% |
| `comprehensive_income` | 26.1% | 94.8% |
| `comprehensive_income_ttm` | 16.2% | 89.8% |
| `current_assets` | 81.9% | 93.3% |
| `current_liabilities` | 81.9% | 93.2% |
| `market` | 100.0% | 100.0% |
| `market_cap` | 100.0% | 100.0% |
| `net_income` | 81.4% | 95.3% |
| `net_income_ttm` | 70.7% | 90.6% |
| `net_income_yoy_change` | 68.0% | 90.8% |
| `noncurrent_assets` | 81.7% | 92.9% |
| `noncurrent_liabilities` | 81.8% | 93.2% |
| `operating_income` | 81.4% | 95.3% |
| `operating_income_ttm` | 70.7% | 90.7% |
| `pretax_income` | 81.4% | 95.3% |
| `pretax_income_ttm` | 70.7% | 90.7% |
| `retained_earnings` | 82.1% | 95.5% |
| `return_close` | 100.0% | 100.0% |
| `revenue` | 80.5% | 93.3% |
| `revenue_ttm` | 69.3% | 87.9% |
| `shares` | 100.0% | 100.0% |
| `sue_score` | 59.2% | 86.0% |
| `total_assets` | 82.6% | 95.5% |
| `total_equity` | 82.6% | 95.5% |
| `total_liabilities` | 82.6% | 95.5% |
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
| `annual_seasonality_5y` | momentum | `return_seasonality` | `e2712bceedbcdebd` | - |
| `asset_growth_12m` | other | `asset_growth` | `8036ceaacef6ac62` | total_assets |
| `asset_turnover_change_12m` | quality | `asset_turnover_change` | `8f8e7c42fdc9fce8` | revenue_ttm, total_assets |
| `current_ratio` | quality | `short_term_solvency` | `27ae11f304c7e10a` | current_assets, current_liabilities |
| `defensive_small_value` | value | `small_value` | `5ca0936652af719a` | total_equity |
| `defensive_value` | value | `defensive_value` | `89e8c8685bac02ac` | total_equity |
| `downside_vol_12m` | other | `low_volatility` | `57a4463adb3b9ee7` | - |
| `earnings_confirmed_small_value` | earnings | `catalyst_small_value` | `89e7b296449ec6b2` | total_equity, sue_score |
| `high_12m_proximity` | momentum | `price_anchoring` | `5bc5c56e28ba5b4f` | - |
| `liability_growth_12m` | other | `liability_growth` | `048bced1c445efe6` | total_liabilities |
| `long_term_reversal_36_12` | momentum | `long_term_reversal` | `b0a25a07020a622f` | - |
| `low_vol_12m` | other | `low_volatility` | `ae41d1ec7120cde0` | - |
| `max_monthly_return_12m` | other | `lottery_demand` | `c0ea1874070bbd0b` | - |
| `net_equity_issuance_12m` | other | `net_equity_issuance` | `19650b7013627426` | - |
| `net_profit_margin` | quality | `net_profit_margin` | `a1e679b213e5f339` | net_income_ttm, revenue_ttm |
| `net_roa` | quality | `net_roa` | `ad335843d7d17cec` | net_income_ttm, total_assets |
| `nonoperating_burden_to_assets` | quality | `nonoperating_burden` | `bafec4ce16293b98` | operating_income_ttm, net_income_ttm, total_assets |
| `operating_roa` | quality | `operating_roa` | `0c399c65bc5c8e11` | operating_income_ttm, total_assets |
| `operating_roa_change_12m` | earnings | `profitability_change` | `4c2f3e0638033747` | operating_income_ttm, total_assets |
| `operating_roa_volatility_36m` | quality | `profitability_stability` | `d4b9c4dfb4af6b5f` | operating_income_ttm, total_assets |
| `profitable_small_value` | quality | `quality_small_value` | `ec639be0f12aad5a` | total_equity, operating_income_ttm, total_assets |
| `quality_stability` | quality | `quality_stability` | `c4315c8db6ef4e63` | operating_income_ttm, revenue_ttm, total_assets, total_equity |
| `retained_earnings_to_assets` | quality | `internal_financing` | `1489feceb711fd22` | retained_earnings, total_assets |
| `return_skewness_24m` | other | `return_skewness` | `ae94a83fc4d5f034` | - |
| `sales_growth_12m` | other | `sales_growth` | `17b53e851b0e2994` | revenue_ttm |
| `small_value` | value | `small_value` | `764fa5bbc3b80dc4` | total_equity |
| `solvent_value` | value | `defensive_value` | `fb56009a013e76e1` | total_equity, total_liabilities |

## Prior autonomous cycles

| cycle | factor | family | ruleset | verdict | failed checks | strongest relation | report |
|---|---|---|---|---|---|---|---|
| `cycle-0001-low_vol_12m` | `low_vol_12m` | `low_volatility` | `fr-2.0.0` | REJECT | 실비용 순알파, net_IR | value_bp (0.35) | `research/runs/cycle-0001-low_vol_12m/report.md` |
| `cycle-0002-asset_growth_12m` | `asset_growth_12m` | `asset_growth` | `fr-2.0.0` | REJECT | 월별 커버리지 하위10%, 종착수익률 3점 방향 | qual_roe (-0.35) | `research/runs/cycle-0002-asset_growth_12m/report.md` |
| `cycle-0003-downside_vol_12m` | `downside_vol_12m` | `low_volatility` | `fr-2.0.0` | REJECT | 실비용 순알파, net_IR | value_ep (0.37) | `research/runs/cycle-0003-downside_vol_12m/report.md` |
| `cycle-0004-defensive_value` | `defensive_value` | `defensive_value` | `fr-2.0.0` | REJECT | net_IR | value_bp (0.83) | `research/runs/cycle-0004-defensive_value/report.md` |
| `cycle-0005-solvent_value` | `solvent_value` | `defensive_value` | `fr-2.0.0` | REJECT | 실비용 순알파, net_IR | value_bp (0.67) | `research/runs/cycle-0005-solvent_value/report.md` |
| `cycle-0006-small_value` | `small_value` | `small_value` | `fr-2.0.0` | REJECT | 투자가능 IC 유지율 | value_bp (0.78) | `research/runs/cycle-0006-small_value/report.md` |
| `cycle-0007-defensive_small_value` | `defensive_small_value` | `small_value` | `fr-2.0.0` | REJECT | 섹터 중립화 가능, 고정 OOS, Deflated Sharpe, 다중검정 FDR | defensive_value (0.87) | `research/runs/cycle-0007-defensive_small_value/report.md` |
| `cycle-0008-high_12m_proximity` | `high_12m_proximity` | `price_anchoring` | `fr-2.0.0` | REJECT | 투자가능 IC 유지율, 투자가능 IC HAC 유의성, 실비용 순알파, net_IR | downside_vol_12m (0.68) | `research/runs/cycle-0008-high_12m_proximity/report.md` |
| `cycle-0009-earnings_confirmed_small_value` | `earnings_confirmed_small_value` | `catalyst_small_value` | `fr-2.0.0` | REJECT | 섹터 중립화 가능, 고정 OOS, Deflated Sharpe, 다중검정 FDR | small_value (0.81) | `research/runs/cycle-0009-earnings_confirmed_small_value/report.md` |
| `cycle-0010-quality_stability` | `quality_stability` | `quality_stability` | `fr-2.0.0` | REJECT | net_IR | qual_roe (0.67) | `research/runs/cycle-0010-quality_stability/report.md` |
| `cycle-0011-profitable_small_value` | `profitable_small_value` | `quality_small_value` | `fr-2.0.0` | REJECT | 레짐 집중도, 섹터 중립화 가능, 고정 OOS, Deflated Sharpe, 다중검정 FDR | small_value (0.78) | `research/runs/cycle-0011-profitable_small_value/report.md` |
| `cycle-0012-operating_roa` | `operating_roa` | `operating_roa` | `fr-3.1.0` | PROVISIONAL | 섹터 중립화 가능 | qual_opm (0.92) | `research/runs/cycle-0012-operating_roa/report.md` |
| `cycle-0013-net_profit_margin` | `net_profit_margin` | `net_profit_margin` | `fr-3.2.0` | PROVISIONAL | 섹터 중립화 가능 | qual_roe (0.90) | `research/runs/cycle-0013-net_profit_margin/report.md` |
| `cycle-0014-sales_growth_12m` | `sales_growth_12m` | `sales_growth` | `fr-3.2.0` | REJECT | 종착수익률 3점 방향 | asset_growth_12m (0.38) | `research/runs/cycle-0014-sales_growth_12m/report.md` |
| `cycle-0015-operating_roa_change_12m` | `operating_roa_change_12m` | `profitability_change` | `fr-3.2.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건 | sales_growth_12m (-0.46) | `research/runs/cycle-0015-operating_roa_change_12m/report.md` |
| `cycle-0016-long_term_reversal_36_12` | `long_term_reversal_36_12` | `long_term_reversal` | `fr-3.2.0` | REJECT | 종착수익률 3점 방향 | qual_roe (-0.25) | `research/runs/cycle-0016-long_term_reversal_36_12/report.md` |
| `cycle-0017-net_roa` | `net_roa` | `net_roa` | `fr-3.2.0` | PROVISIONAL | 섹터 중립화 가능 | qual_roe (0.97) | `research/runs/cycle-0017-net_roa/report.md` |
| `cycle-0018-liability_growth_12m` | `liability_growth_12m` | `liability_growth` | `fr-3.2.0` | REJECT | 종착수익률 3점 방향 | asset_growth_12m (0.70) | `research/runs/cycle-0018-liability_growth_12m/report.md` |
| `cycle-0019-asset_turnover_change_12m` | `asset_turnover_change_12m` | `asset_turnover_change` | `fr-3.2.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건, 투자가능 Rank ICIR 최소요건, 투자가능 IC HAC 유의성 | sales_growth_12m (-0.65) | `research/runs/cycle-0019-asset_turnover_change_12m/report.md` |
| `cycle-0020-return_skewness_24m` | `return_skewness_24m` | `return_skewness` | `fr-3.2.0` | PROVISIONAL | 섹터 중립화 가능 | low_vol_12m (0.49) | `research/runs/cycle-0020-return_skewness_24m/report.md` |
| `cycle-0021-net_equity_issuance_12m` | `net_equity_issuance_12m` | `net_equity_issuance` | `fr-3.2.0` | PROVISIONAL | 섹터 중립화 가능 | quality_stability (0.33) | `research/runs/cycle-0021-net_equity_issuance_12m/report.md` |
| `cycle-0022-operating_roa_volatility_36m` | `operating_roa_volatility_36m` | `profitability_stability` | `fr-3.2.0` | REJECT | 월별 커버리지 하위10% | defensive_value (0.37) | `research/runs/cycle-0022-operating_roa_volatility_36m/report.md` |
| `cycle-0023-annual_seasonality_5y` | `annual_seasonality_5y` | `return_seasonality` | `fr-3.2.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건, 투자가능 Rank ICIR 최소요건, 투자가능 IC HAC 유의성 | long_term_reversal_36_12 (-0.14) | `research/runs/cycle-0023-annual_seasonality_5y/report.md` |
| `cycle-0024-retained_earnings_to_assets` | `retained_earnings_to_assets` | `internal_financing` | `fr-3.2.0` | PROVISIONAL | 섹터 중립화 가능 | quality_stability (0.61) | `research/runs/cycle-0024-retained_earnings_to_assets/report.md` |
| `cycle-0025-current_ratio` | `current_ratio` | `short_term_solvency` | `fr-3.2.0` | REJECT | 전체 IC 최소요건, 투자가능 IC 최소요건, 투자가능 Rank ICIR 최소요건, 투자가능 IC HAC 유의성 | qual_lev (0.80) | `research/runs/cycle-0025-current_ratio/report.md` |
| `cycle-0026-nonoperating_burden_to_assets` | `nonoperating_burden_to_assets` | `nonoperating_burden` | `fr-3.2.0` | REJECT | 전체 IC 최소요건 | net_profit_margin (0.29) | `research/runs/cycle-0026-nonoperating_burden_to_assets/report.md` |
| `cycle-0027-max_monthly_return_12m` | `max_monthly_return_12m` | `lottery_demand` | `fr-3.2.0` | PROVISIONAL | 섹터 중립화 가능 | low_vol_12m (0.92) | `research/runs/cycle-0027-max_monthly_return_12m/report.md` |
