# campaign-20260815-002 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `capital_stock_growth_12m` | `legal_capital_issuance_growth` | ROBUSTNESS_OR_DATA_GAP | RELATED | `research/runs/cycle-0064-capital_stock_growth_12m/report.md` |
| `current_assets_growth_12m` | `working_capital_investment_growth` | DATA_OR_INTEGRITY | RELATED | `research/runs/cycle-0065-current_assets_growth_12m/report.md` |
| `current_liabilities_growth_12m` | `short_term_financing_growth` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0066-current_liabilities_growth_12m/report.md` |
| `operating_income_growth_12m` | `operating_income_growth` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0067-operating_income_growth_12m/report.md` |
| `retained_earnings_growth_12m` | `internal_capital_accumulation` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0068-retained_earnings_growth_12m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
