# retrospective-qualified-oos-20260807-003

> 이 결과는 이미 discovery에 노출된 과거 구간을 다시 나눈 회고 감사다.
> campaign confirmation, 최종 OOS, Gold 승격 증거로 사용할 수 없다.

## 고정 감사 계약

- Labels: `NON_CONFIRMATORY_RETROSPECTIVE_AUDIT, PSEUDO_OOS_ALREADY_EXPOSED, DISCOVERY_CONTAMINATED, NO_VERDICT_OR_PROMOTION_EFFECT`
- Silver source: `RDS public Silver`
- Ruleset: `fr-3.9.0`
- RDS Gold APPROVED: `0`개 (없음)
- IS signal months: `2018-03 ~ 2023-04` (62개월)
- Boundary embargo: `2023-05`
- Retrospective audit signal months: `2023-06 ~ 2026-05` (36개월)
- 자동 기준 통과 후보 3개를 같은 분할에서 동시에 계산했고 결과에 따른 정의 수정은 없었다.
- 기존 campaign manifest, verdict, history, trial ledger 및 Gold는 변경하지 않았다.

## 원래 discovery와 과거 IS 재현

| factor | original full IC | original | historical IS IC | IS ICIR | IS BY q | T5 | replay verdict | auto qualified |
|---|---:|---|---:|---:|---:|---:|---|---:|
| `operating_return_on_capital_employed` | 0.065 | PROVISIONAL | 0.046 | 0.665 | 0.000 | Y | PROVISIONAL | Y |
| `return_kurtosis_24m` | 0.046 | PROVISIONAL | 0.036 | 0.637 | 0.000 | Y | PROVISIONAL | Y |
| `turnover_volatility_12m` | 0.066 | PROVISIONAL | 0.039 | 0.361 | 0.002 | Y | PROVISIONAL | Y |

## 후반기 성능 지속성

OOS IC 기준은 절대값 `0.02`와 Discovery 대비 유지율 `0.5`를 함께 표시한다. 관측기간은 `36`개월로 공식 최소 `36`개월을 충족한다. 표의 T4 effect+BY는 현재 수치 기준을 회고적으로 재현한 값일 뿐이며, 이미 노출된 구간이므로 공식 confirmation이나 Gold 승격 효력은 없다.

| factor | later IC | ICIR | OOS/IS | neutral IC | neutral/investable | positive years | qualified BY q | IC>=0.02 | retention>=0.5 | T4 effect+BY |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `operating_return_on_capital_employed` | 0.093 | 1.049 | 2.025 | 0.067 | 0.719 | 4/4 | 0.000 | Y | Y | Y |
| `return_kurtosis_24m` | 0.060 | 1.348 | 1.673 | 0.028 | 0.470 | 4/4 | 0.000 | Y | Y | Y |
| `turnover_volatility_12m` | 0.110 | 1.168 | 2.850 | 0.035 | 0.314 | 4/4 | 0.000 | Y | Y | Y |

## 포트폴리오 진단값

수익률·비용·회전율은 승격 기준이 아니라 상위 20% 동일가중 포트폴리오 진단값이다.

| factor | gross %/yr | cost %/yr | net %/yr | net IR | turnover %/yr |
|---|---:|---:|---:|---:|---:|
| `operating_return_on_capital_employed` | - | - | - | - | - |
| `return_kurtosis_24m` | - | - | - | - | - |
| `turnover_volatility_12m` | - | - | - | - | - |

## 연도별 후반기 IC

| factor | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|
| `operating_return_on_capital_employed` | 0.070 | 0.086 | 0.090 | 0.145 |
| `return_kurtosis_24m` | 0.075 | 0.033 | 0.058 | 0.106 |
| `turnover_volatility_12m` | 0.096 | 0.094 | 0.113 | 0.164 |

## 해석 제한

- 이 후반 구간은 후보 생성과 기존 discovery에 이미 포함됐으므로 진짜 미관측 표본이 아니다.
- 따라서 이번 값은 지금 성능 지속성을 판단하는 회고 검증이며 기존 campaign의 공식 confirmation은 아니다.
- T4 effect+BY는 OOS 효과·유지율·동시 후보 BY까지만 뜻한다. campaign 귀무 보정과 Gold SQL parity는 별도다.
- 이 숫자를 보고 같은 후보의 부호·룩백·산식·표본을 수정하면 안 된다.
- 다음 clean campaign부터 historical holdout과 자동 qualified 규칙을 결과 전에 고정해야 한다.
