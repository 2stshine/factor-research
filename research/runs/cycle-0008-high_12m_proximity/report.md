# cycle-0008-high_12m_proximity

- Verdict: **REJECT**
- Definition hash: `5bc5c56e28ba5b4f`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/high_12m_proximity.py`

## Hypothesis

현재 총수익지수가 최근 12개월 월말 최고치에 가까운 종목을 보유하면, 단순 시작점-종점 모멘텀과 다른 고점 기준점 효과로 이후 롱온리 초과수익을 얻는다.

## Mechanism

투자자는 이전 고점을 매도 또는 가치판단의 기준점으로 삼아 호재를 한 번에 가격에 반영하지 않는다. 고점에 가까운 가격은 누적된 긍정적 정보와 매도 저항의 소진을 나타내므로 가격 발견이 계속될 수 있다.

## Pre-registered falsification

투자가능 IC와 비용 후 성과가 충분하지 않거나, 강건성·고정 OOS·다중검정·Gold 직교성 중 하나라도 hard fail이면 고점 앵커링 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9324943443653121 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9995889340498191 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | N | None | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | N | 0.6848183345518924 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.00056 | <=1.0% |
| T2.3 | 회전율 | Y | 337.9168493939455 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | N | 1.0984180532756616 | >=3.0%/yr |
| T2.4 | net_IR | N | 0.13663647424259576 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | -0.010316067851198402 |
| `ic_t_full` | -0.9156337724381538 |
| `ic_p_full` | 0.8188604795336758 |
| `months` | 80 |
| `turnover` | 337.9168493939455 |
| `gross` | 2.7620945149115967 |
| `cost` | 1.6636764616359359 |
| `net` | 1.0984180532756616 |
| `net_ir` | 0.13663647424259576 |
| `hac_t` | 0.3283445035011205 |
| `hac_pvalue` | 0.37175995851567906 |
| `missing_return_rate` | 0.00056 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 투자가능 IC 유지율: None (>=0.5 & 양수)
- `T2.1` 투자가능 IC HAC 유의성: 0.6848183345518924 (one-sided p<=0.05)
- `T2.4` 실비용 순알파: 1.0984180532756616 (>=3.0%/yr)
- `T2.4` net_IR: 0.13663647424259576 (>=0.74)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `downside_vol_12m` | other | 0.675 | 128 |
| `rev_1m` | momentum | -0.500 | 129 |
| `mom_12_1` | momentum | 0.482 | 128 |
| `low_vol_12m` | other | 0.265 | 128 |
| `qual_roe` | quality | 0.229 | 114 |
| `qual_opm` | quality | 0.221 | 114 |
| `value_ep` | value | 0.213 | 114 |
| `size` | size | -0.189 | 129 |
| `sue` | earnings | 0.163 | 102 |
| `defensive_value` | value | 0.163 | 126 |
| `asset_turnover` | quality | 0.114 | 114 |
| `small_value` | value | -0.094 | 126 |
| `value_sp` | value | 0.074 | 114 |
| `defensive_small_value` | value | 0.063 | 126 |
| `value_bp` | value | 0.041 | 126 |

## Expected relationship and data notes

- Expected relationship: mom_12_1과는 양의 관계를 예상하지만, 12개월 시작점 대비 수익률이 아니라 기간 중 최고점과의 거리이므로 완전히 같지는 않을 것으로 예상한다. 가치·품질 팩터와는 낮은 관계를 예상한다.
- Data notes: Silver PIT total_return_close의 월말 관측치로 12개월 이동 최고치를 계산한다. 일별 52주 고가가 아니며, 최초 11개월은 의도적으로 결측이다.
