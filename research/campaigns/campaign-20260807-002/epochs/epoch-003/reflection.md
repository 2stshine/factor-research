# campaign-20260807-002 / epoch-003 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `equity_growth_12m` | `equity_growth` | DATA_OR_INTEGRITY | RELATED | `research/runs/cycle-0040-equity_growth_12m/report.md` |
| `positive_return_share_12m` | `return_consistency` | DATA_OR_INTEGRITY | RELATED | `research/runs/cycle-0041-positive_return_share_12m/report.md` |
| `return_kurtosis_24m` | `return_tail_concentration` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0042-return_kurtosis_24m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
