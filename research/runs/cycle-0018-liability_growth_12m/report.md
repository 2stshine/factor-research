# cycle-0018-liability_growth_12m

- Verdict: **REJECT**
- Definition hash: `048bced1c445efe6`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/liability_growth_12m.py`

## Hypothesis

Silver PIT의 최근 12개월 총부채 증가율이 낮은 종목은 부채가 빠르게 증가한 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

급격한 부채 증가는 투자와 운전자본을 위한 선제 조달일 수 있지만, 동시에 이자 부담과 차환 위험, 경영자의 과잉 확장을 높인다. 투자자가 외형 확장에 먼저 반응하고 재무 위험을 늦게 반영하면 저부채성장 기업이 이후 상대적으로 재평가될 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, 고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 T0~T5 게이트를 순차 적용했다. 앞 단계 hard fail 이후의 검사는 실행하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.955116601936629 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9317981076197459 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T1.2` 종착수익률 3점 방향: None (세 시나리오 IC > 0)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `asset_growth_12m` | other | 0.703 | 102 |
| `sales_growth_12m` | other | 0.276 | 102 |
| `solvent_value` | value | 0.202 | 102 |
| `qual_lev` | quality | 0.163 | 102 |
| `small_value` | value | 0.131 | 102 |
| `defensive_small_value` | value | 0.119 | 102 |
| `value_bp` | value | 0.103 | 102 |
| `quality_stability` | quality | 0.097 | 102 |
| `profitable_small_value` | quality | 0.091 | 102 |
| `size` | size | 0.091 | 102 |
| `defensive_value` | value | 0.085 | 102 |
| `earnings_confirmed_small_value` | earnings | 0.083 | 102 |
| `long_term_reversal_36_12` | momentum | 0.082 | 102 |
| `value_sp` | value | 0.078 | 102 |
| `asset_turnover` | quality | 0.076 | 102 |

## Expected relationship and data notes

- Expected relationship: 재무 팽창을 측정하므로 asset_growth_12m과 양의 관계를 예상한다. 부채 수준을 측정하는 qual_lev와도 일부 관련되지만 변화율과 수준의 차이 때문에 완전한 중복은 아닐 것으로 예상한다. 수익성·모멘텀과의 관계는 낮을 것으로 예상한다.
- Data notes: DART available_date 순으로 정정공시를 재생한 Silver PIT total_liabilities를 사용한다. 12개월 전 부채가 0 이하인 관측과 최초 12개월은 결측이다. 인수합병·사업분할과 리스 회계 변화로 생긴 구조적 부채 증가는 별도로 조정하지 않는다.
