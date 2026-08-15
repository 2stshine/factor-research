# campaign-20260815-011 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `net_income_to_noncurrent_assets` | `long_asset_net_productivity` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0109-net_income_to_noncurrent_assets/report.md` |
| `net_income_to_current_assets` | `current_asset_net_productivity` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0110-net_income_to_current_assets/report.md` |
| `revenue_to_noncurrent_liabilities` | `long_term_revenue_coverage` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0111-revenue_to_noncurrent_liabilities/report.md` |
| `adv20_to_book_equity` | `book_scaled_trading_activity` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0112-adv20_to_book_equity/report.md` |
| `price_trend_efficiency_12m` | `directional_price_efficiency` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0113-price_trend_efficiency_12m/report.md` |
| `working_capital_to_sales` | `working_capital_sales_buffer` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0114-working_capital_to_sales/report.md` |
| `retained_earnings_yield` | `accumulated_earnings_value` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0115-retained_earnings_yield/report.md` |
| `capital_stock_yield` | `legal_capital_value` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0116-capital_stock_yield/report.md` |
| `current_liabilities_to_sales` | `short_term_funding_sales_burden` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0117-current_liabilities_to_sales/report.md` |
| `asset_to_market` | `asset_backed_value` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0118-asset_to_market/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
