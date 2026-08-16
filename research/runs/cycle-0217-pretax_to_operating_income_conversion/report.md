# cycle-0217-pretax_to_operating_income_conversion

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-006` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `42f0b3cfaf4d713f`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_to_operating_income_conversion.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

PIT pretax_income_ttm/operating_income_ttm 비율이 높은 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.

## Mechanism

서로 다른 포괄·영업·세전 이익 단계의 변환 또는 자본 효율성을 하나의 경제 비율로 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 0 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9333404722385822 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9163325021032259 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |

### Failed checks

- `T1.2` 종착수익률 3점 방향: None (세 시나리오 IC > 0)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_to_operating_income_conversion` | earnings | 0.881 | 63 |
| `operating_income_to_equity` | quality | -0.257 | 63 |
| `operating_earnings_yield` | value | -0.234 | 63 |
| `operating_return_on_capital_employed` | quality | -0.211 | 63 |
| `pretax_income_growth_12m` | earnings | 0.195 | 63 |
| `net_income_growth_12m` | earnings | 0.195 | 63 |
| `operating_income_to_current_assets` | quality | -0.190 | 63 |
| `retained_earnings_to_assets_volatility_12m` | earnings | -0.174 | 63 |
| `operating_roa` | quality | -0.164 | 63 |
| `qual_lev` | quality | 0.160 | 63 |
| `net_income_growth_acceleration_12m` | earnings | 0.159 | 51 |
| `pretax_income_growth_acceleration_12m` | earnings | 0.159 | 51 |
| `revenue_to_equity` | quality | -0.156 | 63 |
| `pretax_margin_volatility_36m` | quality | -0.152 | 52 |
| `operating_income_to_capital_stock` | quality | -0.152 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 수익성 신호와 관련될 수 있으나 분자·분모 단계가 다르다.
- Data notes: 동일 available_date PIT 재무값과 0이 아닌 분모만 사용한다.
