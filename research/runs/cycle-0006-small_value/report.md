# cycle-0006-small_value

- Verdict: **REJECT**
- Definition hash: `764fa5bbc3b80dc4`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/small_value.py`

## Hypothesis

월별 장부가치/시가총액 순위와 소형주 순위를 동등 결합한 종목을 보유하면, 단독 가치나 단독 규모 신호보다 비용 후 안정적인 초과수익을 얻는다.

## Mechanism

소형주는 애널리스트와 기관의 관심이 적어 공시 정보가 가격에 늦게 반영되고, 저평가까지 겹치면 과도한 비관이 교정되는 폭이 커질 수 있다. 고정 유동성 유니버스는 체결 불가능한 초소형주 효과와 이 메커니즘을 구분한다.

## Pre-registered falsification

투자가능 유니버스에서 IC가 유지되지 않거나, 비용·회전율 반영 후 성과가 부족하거나, 중립화·기간분할·OOS·다중검정 또는 Gold 직교성 검사를 통과하지 못하면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 T0~T5 게이트를 순차 적용했다. 앞 단계 hard fail 이후의 검사는 실행하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8807842480100545 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.6048051684183939 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | N | 0.44481923796842815 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 0.03015866376898271 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0014778931811650724 | <=1.0% |
| T2.3 | 회전율 | Y | 302.1915246509489 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | Y | 7.539364613202146 | >=3.0%/yr |
| T2.4 | net_IR | Y | 1.0599140170215673 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.06600140948850984 |
| `ic_t_full` | 4.51170264193752 |
| `ic_p_full` | 9.384300171872015e-06 |
| `months` | 67 |
| `turnover` | 302.1915246509489 |
| `gross` | 9.026045628229323 |
| `cost` | 1.4866810150271788 |
| `net` | 7.539364613202146 |
| `net_ir` | 1.0599140170215673 |
| `hac_t` | 2.2353857149709215 |
| `hac_pvalue` | 0.014390267742166332 |
| `missing_return_rate` | 0.0014778931811650724 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 투자가능 IC 유지율: 0.44481923796842815 (>=0.5 & 양수)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `value_bp` | value | 0.778 | 126 |
| `size` | size | 0.690 | 126 |
| `value_sp` | value | 0.574 | 114 |
| `defensive_value` | value | 0.551 | 126 |
| `solvent_value` | value | 0.538 | 126 |
| `mom_12_1` | momentum | -0.211 | 126 |
| `asset_growth_12m` | other | 0.186 | 114 |
| `qual_opm` | quality | -0.155 | 114 |
| `qual_roe` | quality | -0.134 | 114 |
| `low_vol_12m` | other | 0.120 | 126 |
| `asset_turnover` | quality | 0.108 | 114 |
| `value_ep` | value | 0.097 | 114 |
| `sue` | earnings | -0.063 | 102 |
| `qual_lev` | quality | -0.054 | 126 |
| `rev_1m` | momentum | 0.040 | 126 |

## Expected relationship and data notes

- Expected relationship: value_bp와 size 모두에 중간 이상의 양의 관계를 예상한다. 동등 결합으로 어느 하나와 완전히 같지 않으며 수익성·SUE 팩터와는 낮은 관계를 예상한다.
- Data notes: Silver PIT total_equity와 월말 market_cap을 사용한다. 팩터 내부에서 유니버스를 자르지 않고 월별 횡단면 순위만 결합하며, 실제 투자 가능성은 공통 게이트가 판정한다.
