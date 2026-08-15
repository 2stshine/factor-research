# campaign-20260815-001 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `pretax_profit_margin` | `pretax_profitability_margin` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0059-pretax_profit_margin/report.md` |
| `operating_income_to_noncurrent_assets` | `long_lived_asset_operating_productivity` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0060-operating_income_to_noncurrent_assets/report.md` |
| `retained_earnings_to_capital_stock` | `earned_to_contributed_capital` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0061-retained_earnings_to_capital_stock/report.md` |
| `current_assets_to_total_liabilities` | `liquid_asset_debt_coverage` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0062-current_assets_to_total_liabilities/report.md` |
| `revenue_to_total_liabilities` | `revenue_debt_turnover` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0063-revenue_to_total_liabilities/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
