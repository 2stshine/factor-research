# 다음 회차 지침과 누적 시행

> 결정론 코드가 만든다. 새 후보를 세우기 전에 위에서부터 읽는다.
> **판정 결과는 담기지 않는다** — 봉인 OOS 를 지키기 위해 정체성과 구조적 교훈만 남긴다.

## 1. 이번 회차의 제약

아래는 `campaign-20260807-002` / `epoch-003` 의 `reflection.json` 에 엔진이 기록한 지시다. **원문 그대로 옮겼다.**

**해도 되는 것**

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.

**하면 안 되는 것**

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.

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

붙일 대상이 떠오르지 않으면 4절을 다시 읽는다. 목록이 42건이라 "없다"는 답은 거의 틀린다.
같은 변수를 부호나 표현만 뒤집은 것(예: 고점 대비 근접도 ↔ 고점 대비 낙폭,
변동성 ↔ 안정성)은 **새 후보가 아니라 같은 후보**다.

## 3. 어느 쪽이 이미 채워졌나

- Accruals: 1건 등록
- Debt Issuance: 1건 등록
- Investment: 4건 등록
- Low Leverage: 5건 등록
- Low Risk: 7건 등록
- Momentum: 1건 등록
- Profit Growth: 3건 등록
- Profitability: 3건 등록
- Quality: 4건 등록
- Seasonality: 1건 등록
- Short-Term Reversal: 1건 등록
- Size: 0건 등록
- Value: 7건 등록
- (미매칭): 4건

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

## 4. 시행 전량

시행 42건 · 생략 없음

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
