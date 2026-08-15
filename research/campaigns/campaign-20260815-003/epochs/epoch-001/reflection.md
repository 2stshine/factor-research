# campaign-20260815-003 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `noncurrent_assets_growth_12m` | `long_lived_asset_investment_growth` | NO_PREDICTIVE_EVIDENCE | INDEPENDENT | `research/runs/cycle-0069-noncurrent_assets_growth_12m/report.md` |
| `noncurrent_liabilities_growth_12m` | `long_term_debt_growth` | DATA_OR_INTEGRITY | INDEPENDENT | `research/runs/cycle-0070-noncurrent_liabilities_growth_12m/report.md` |
| `net_income_growth_12m` | `trailing_net_income_growth` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0071-net_income_growth_12m/report.md` |
| `pretax_income_growth_12m` | `trailing_pretax_income_growth` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0072-pretax_income_growth_12m/report.md` |
| `noncurrent_asset_share_change_12m` | `asset_rigidity_change` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0073-noncurrent_asset_share_change_12m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
