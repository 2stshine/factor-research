# cycle-0022-operating_roa_volatility_36m

- Verdict: **REJECT**
- Definition hash: `d4b9c4dfb4af6b5f`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_roa_volatility_36m.py`

## Hypothesis

Silver PIT operating_income_ttm/total_assets의 최근 36개월 표준편차가 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

영업 ROA가 안정적이면 수요·원가 충격에도 자산에서 이익을 창출하는 능력이 지속된다는 뜻이다. 투자자가 변동성이 큰 기업의 상방 가능성을 과대평가하거나 안정적 기업을 지루한 종목으로 할인하면 낮은 수익성 변동성이 미래 수익을 예측할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.7692828146143437 | >=50% |
| T1.1 | 월별 커버리지 하위10% | N | 0.018120257939721284 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T1.1` 월별 커버리지 하위10%: 0.018120257939721284 (>=30%)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `defensive_value` | value | 0.369 | 91 |
| `value_bp` | value | 0.367 | 91 |
| `value_sp` | value | 0.314 | 91 |
| `value_ep` | value | 0.269 | 91 |
| `defensive_small_value` | value | 0.258 | 91 |
| `profitable_small_value` | quality | 0.258 | 91 |
| `downside_vol_12m` | other | 0.256 | 91 |
| `low_vol_12m` | other | 0.248 | 91 |
| `net_equity_issuance_12m` | other | 0.213 | 91 |
| `solvent_value` | value | 0.197 | 91 |
| `qual_opm` | quality | 0.182 | 91 |
| `operating_roa` | quality | 0.180 | 91 |
| `quality_stability` | quality | 0.179 | 91 |
| `small_value` | value | 0.177 | 91 |
| `net_profit_margin` | quality | 0.163 | 91 |

## Expected relationship and data notes

- Expected relationship: 수익성 수준인 operating_roa·qual_roe와는 약한 관계, 가격 안정성인 low_vol_12m과는 중간 정도의 양의 관계를 예상한다. 회계 수익성의 시계열 표준편차만 사용하므로 기존 복합 quality_stability와 동일한 정의는 아니다.
- Data notes: DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 total_assets를 사용한다. 36개월 창에서 최소 24개 월 관측을 사전 고정한다. 회계 수치는 공시 사이에 반복되므로 실제로는 약 8개 이상 분기 정보의 변동성을 월 패널에서 측정하는 근사치다.
