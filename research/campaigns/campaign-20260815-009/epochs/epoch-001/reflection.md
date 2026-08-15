# campaign-20260815-009 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `current_liabilities_growth_acceleration_12m` | `short_term_debt_acceleration` | WRONG_SIGN_OR_NO_EDGE | RELATED | `research/runs/cycle-0099-current_liabilities_growth_acceleration_12m/report.md` |
| `operating_income_to_equity` | `operating_book_equity_return` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0100-operating_income_to_equity/report.md` |
| `revenue_to_noncurrent_assets` | `long_lived_asset_revenue_productivity` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0101-revenue_to_noncurrent_assets/report.md` |
| `short_term_reversal_3m` | `short_term_reversal_3m` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0102-short_term_reversal_3m/report.md` |
| `noncurrent_liabilities_to_equity` | `long_term_book_leverage` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0103-noncurrent_liabilities_to_equity/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
