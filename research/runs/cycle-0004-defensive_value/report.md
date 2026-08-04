# cycle-0004-defensive_value

- Verdict: **REJECT**
- Definition hash: `89e8c8685bac02ac`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/defensive_value.py`

## Hypothesis

월별 장부가치/시가총액 순위와 12개월 저변동성 순위를 동등 결합한 종목을 보유하면, 단순 가치 또는 단순 저변동성보다 비용 후 안정적인 초과수익을 얻는다.

## Mechanism

가치주는 과잉반응 교정의 수익원을 제공하지만 일부는 사업 악화와 재무적 취약성으로 싼 가치함정이다. 낮은 가격 변동성 조건은 시장이 지속적으로 재평가하는 취약 종목을 줄여 가치 프리미엄의 질을 높인다.

## Pre-registered falsification

상폐 종착수익률 세 시나리오에서 방향이 유지되지 않거나, 투자가능 유니버스 IC와 비용 후 순알파가 기준을 충족하지 않거나, 강건성·OOS·다중검정 또는 기존 Gold 직교성 검사를 통과하지 못하면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.8801675743611227 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.6048051684183939 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | Y | 1.1187580893130387 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 1.940652564996149e-11 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0005336836487540539 | <=1.0% |
| T2.3 | 회전율 | Y | 198.6987569044228 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | Y | 3.094200353168915 | >=3.0%/yr |
| T2.4 | net_IR | N | 0.4672789116823071 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.08238936400716848 |
| `ic_t_full` | 5.455861094481605 |
| `ic_p_full` | 2.1254224353794385e-07 |
| `months` | 78 |
| `turnover` | 198.6987569044228 |
| `gross` | 4.071010682837654 |
| `cost` | 0.9768103296687388 |
| `net` | 3.094200353168915 |
| `net_ir` | 0.4672789116823071 |
| `hac_t` | 0.9535878287297556 |
| `hac_pvalue` | 0.1716381742001006 |
| `missing_return_rate` | 0.0005336836487540539 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.4` net_IR: 0.4672789116823071 (>=0.74)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `value_bp` | value | 0.830 | 126 |
| `low_vol_12m` | other | 0.809 | 126 |
| `value_sp` | value | 0.627 | 114 |
| `downside_vol_12m` | other | 0.541 | 126 |
| `value_ep` | value | 0.422 | 114 |
| `mom_12_1` | momentum | -0.244 | 126 |
| `qual_roe` | quality | 0.176 | 114 |
| `qual_opm` | quality | 0.174 | 114 |
| `asset_turnover` | quality | 0.152 | 114 |
| `asset_growth_12m` | other | 0.087 | 114 |
| `size` | size | -0.059 | 126 |
| `qual_lev` | quality | -0.055 | 126 |
| `sue` | earnings | -0.035 | 102 |
| `rev_1m` | momentum | 0.011 | 126 |

## Expected relationship and data notes

- Expected relationship: value_bp와 low_vol_12m 모두에 중간 이상의 양의 관계를 예상한다. 두 신호를 동등 결합하므로 어느 하나와 완전히 동일하지 않고, 수익성 팩터와는 낮거나 중간 수준의 관계를 예상한다.
- Data notes: Silver PIT total_equity와 월말 total_return_close를 사용한다. 각 월의 횡단면 백분위 순위로 단위 차이를 제거하며 최초 12개월은 변동성 계산 때문에 의도적으로 결측이다.
