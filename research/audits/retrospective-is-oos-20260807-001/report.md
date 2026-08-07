# retrospective-is-oos-20260807-001

> 이 결과는 이미 discovery에 노출된 과거 구간을 다시 나눈 회고 감사다.
> campaign confirmation, 최종 OOS, Gold 승격 증거로 사용할 수 없다.

## 고정 감사 계약

- Labels: `NON_CONFIRMATORY_RETROSPECTIVE_AUDIT, PSEUDO_OOS_ALREADY_EXPOSED, DISCOVERY_CONTAMINATED, NO_VERDICT_OR_PROMOTION_EFFECT`
- Silver source: `RDS public Silver`
- Ruleset: `fr-3.7.0`
- IS signal months: `2018-03 ~ 2023-04` (62개월)
- Boundary embargo: `2023-05`
- Retrospective audit signal months: `2023-06 ~ 2026-05` (36개월)
- 모든 6개 정의를 같은 분할에서 동시에 계산했고 결과에 따른 정의 수정은 없었다.
- 기존 campaign manifest, verdict, history, trial ledger 및 Gold는 변경하지 않았다.

## 원래 discovery와 과거 IS 재현

| factor | original full IC | original | historical IS IC | IS ICIR | IS BY q | replay verdict | auto qualified |
|---|---:|---|---:|---:|---:|---|---:|
| `trading_turnover_20d` | 0.122 | PROVISIONAL | 0.109 | 0.876 | 0.000 | PROVISIONAL | Y |
| `working_capital_accruals_12m` | - | REJECT | - | - | - | REJECT | N |
| `earnings_change_to_assets` | 0.023 | REJECT | 0.023 | 0.594 | - | REJECT | N |
| `market_beta_36m` | 0.015 | REJECT | 0.003 | 0.029 | - | REJECT | N |
| `paid_in_capital_ratio` | 0.058 | PROVISIONAL | 0.041 | 0.538 | 0.000 | PROVISIONAL | Y |
| `current_liability_concentration` | 0.008 | REJECT | 0.009 | 0.207 | - | REJECT | N |

## 후반기 성능 지속성

OOS IC 효과 기준은 현재 ruleset의 `0.05`를 그대로 표시한다. 관측기간은 `36`개월로 공식 최소 `36`개월을 충족한다. 표의 formal T4는 현재 수치 기준을 회고적으로 재현한 값일 뿐이며, 이미 노출된 구간이므로 공식 confirmation이나 Gold 승격 효력은 없다.

| factor | later IC | ICIR | IS 대비 IC | neutral IC | positive years | qualified BY q | IC>=0.05 | formal T4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `trading_turnover_20d` | 0.138 | 0.967 | 1.268 | 0.025 | 4/4 | 0.000 | Y | Y |
| `working_capital_accruals_12m` | -0.028 | -0.627 | - | -0.020 | 0/4 | - | N | N |
| `earnings_change_to_assets` | 0.021 | 0.414 | 0.877 | 0.021 | 4/4 | - | N | N |
| `market_beta_36m` | 0.025 | 0.176 | 8.329 | 0.004 | 3/4 | - | N | N |
| `paid_in_capital_ratio` | 0.087 | 1.115 | 2.147 | 0.042 | 4/4 | 0.000 | Y | Y |
| `current_liability_concentration` | 0.009 | 0.300 | 1.003 | -0.013 | 4/4 | - | N | N |

## 포트폴리오 진단값

수익률·비용·회전율은 승격 기준이 아니라 상위 20% 동일가중 포트폴리오 진단값이다.

| factor | gross %/yr | cost %/yr | net %/yr | net IR | turnover %/yr |
|---|---:|---:|---:|---:|---:|
| `trading_turnover_20d` | 3.655 | 1.523 | 2.132 | 0.232 | 380.2 |
| `working_capital_accruals_12m` | - | - | - | - | - |
| `earnings_change_to_assets` | - | - | - | - | - |
| `market_beta_36m` | - | - | - | - | - |
| `paid_in_capital_ratio` | - | - | - | - | - |
| `current_liability_concentration` | - | - | - | - | - |

## 연도별 후반기 IC

| factor | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|
| `trading_turnover_20d` | 0.170 | 0.132 | 0.111 | 0.175 |
| `working_capital_accruals_12m` | -0.007 | -0.035 | -0.028 | -0.043 |
| `earnings_change_to_assets` | 0.014 | 0.024 | 0.027 | 0.006 |
| `market_beta_36m` | 0.026 | 0.051 | -0.012 | 0.051 |
| `paid_in_capital_ratio` | 0.090 | 0.062 | 0.096 | 0.121 |
| `current_liability_concentration` | 0.022 | 0.005 | 0.008 | 0.001 |

## 해석 제한

- 이 후반 구간은 후보 생성과 기존 discovery에 이미 포함됐으므로 진짜 미관측 표본이 아니다.
- audit 결과는 현재 campaign의 qualified, FDR, verdict 또는 Gold 적재 여부를 바꾸지 않는다.
- 이 숫자를 보고 같은 후보의 부호·룩백·산식·표본을 수정하면 안 된다.
- 다음 clean campaign부터 historical holdout과 자동 qualified 규칙을 결과 전에 고정해야 한다.
