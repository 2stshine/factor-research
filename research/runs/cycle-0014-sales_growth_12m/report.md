# cycle-0014-sales_growth_12m

- Verdict: **REJECT**
- Definition hash: `17b53e851b0e2994`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/sales_growth_12m.py`

## Hypothesis

Silver PIT의 최근 12개월 매출 증가율이 낮은 종목은 높은 성장률을 기록한 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

투자자는 최근의 높은 외형 성장을 장기간 지속될 것으로 외삽하고 성장 기업에 높은 기대를 부여할 수 있다. 경쟁과 기저효과로 매출 성장이 정상화되면 고성장 종목의 가격이 조정되고, 낮은 기대를 가진 저성장 종목은 작은 개선에도 재평가될 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.8674586577157619 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8126934497736988 | >=30% |
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
| `asset_growth_12m` | other | 0.379 | 102 |
| `operating_roa` | quality | -0.306 | 102 |
| `qual_opm` | quality | -0.287 | 102 |
| `qual_roe` | quality | -0.283 | 102 |
| `sue` | earnings | -0.242 | 102 |
| `net_profit_margin` | quality | -0.230 | 102 |
| `value_ep` | value | -0.213 | 102 |
| `quality_stability` | quality | -0.167 | 102 |
| `mom_12_1` | momentum | -0.148 | 102 |
| `small_value` | value | 0.141 | 102 |
| `asset_turnover` | quality | -0.139 | 102 |
| `size` | size | 0.127 | 102 |
| `solvent_value` | value | 0.115 | 102 |
| `defensive_small_value` | value | 0.113 | 102 |
| `value_bp` | value | 0.098 | 102 |

## Expected relationship and data notes

- Expected relationship: 낮은 성장을 선호하므로 asset_growth_12m과 양의 관계, 성장 기대가 낮은 가치주를 일부 포착해 value_sp와 양의 관계를 예상한다. 매출 변화율이므로 수익성 수준 및 모멘텀과는 완전히 다른 신호일 것으로 예상한다.
- Data notes: DART available_date 순으로 정정공시를 재생한 Silver PIT revenue_ttm을 사용한다. 현재와 12개월 전 매출이 모두 양수인 관측만 정의되며 최초 12개월은 결측이다. 공시 간에는 같은 TTM 값이 유지될 수 있고, 인수합병·사업분할의 구조적 매출 변화는 별도로 조정하지 않는다.
