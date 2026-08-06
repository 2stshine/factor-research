# cycle-0016-long_term_reversal_36_12

- Verdict: **REJECT**
- Definition hash: `b0a25a07020a622f`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/long_term_reversal_36_12.py`

## Hypothesis

Silver PIT 총수익지수로 측정한 36~12개월 전 누적수익률이 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

장기간의 나쁜 뉴스와 실적 부진에 투자자가 과도하게 반응하면 비관적 기대가 가격에 과잉 반영될 수 있다. 최근 12개월은 단기 모멘텀과 겹치지 않도록 제외하고, 더 오래된 가격 충격이 정상화되는 평균회귀를 포착한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9163137268685306 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.90946700072058 | >=30% |
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
| `qual_roe` | quality | -0.250 | 102 |
| `operating_roa` | quality | -0.245 | 102 |
| `small_value` | value | 0.235 | 102 |
| `qual_opm` | quality | -0.224 | 102 |
| `net_profit_margin` | quality | -0.214 | 102 |
| `earnings_confirmed_small_value` | earnings | 0.208 | 102 |
| `defensive_small_value` | value | 0.201 | 102 |
| `asset_growth_12m` | other | 0.196 | 102 |
| `size` | size | 0.188 | 102 |
| `value_ep` | value | -0.181 | 102 |
| `quality_stability` | quality | -0.168 | 102 |
| `value_bp` | value | 0.156 | 102 |
| `sales_growth_12m` | other | 0.117 | 102 |
| `defensive_value` | value | 0.105 | 102 |
| `solvent_value` | value | 0.090 | 102 |

## Expected relationship and data notes

- Expected relationship: 최근 12개월을 제외하므로 mom_12_1 및 high_12m_proximity와 낮은 관계를 예상한다. 오래된 가격 하락 종목은 가치주가 되었을 수 있어 value 계열과 약한 양의 관계를 예상하지만, 회계 입력을 사용하지 않으므로 동일 신호는 아닐 것으로 예상한다.
- Data notes: Silver total_return_close에 매핑된 return_close만 사용한다. 36개월 이력이 없는 관측은 결측이며, 12개월 skip은 사전 고정한다. 상장폐지 종착수익률 처리는 공통 게이트가 세 시나리오로 적용한다.
