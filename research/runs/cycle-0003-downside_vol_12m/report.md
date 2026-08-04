# cycle-0003-downside_vol_12m

- Verdict: **REJECT**
- Definition hash: `57a4463adb3b9ee7`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/downside_vol_12m.py`

## Hypothesis

월별 총수익률의 최근 12개월 하방 준편차가 낮은 종목을 보유하면, 전체 변동성이 낮은 종목을 고르는 것보다 상승 잠재력을 덜 훼손하면서 비용 후 양의 초과수익을 얻는다.

## Mechanism

투자자는 복권형 종목과 극단적 반등 가능성을 선호하고 하락위험을 충분히 가격에 반영하지 않을 수 있다. 전체 변동성과 달리 하방 준편차는 좋은 상승 변동성을 벌하지 않고 반복적인 손실과 취약성에 집중한다.

## Pre-registered falsification

상폐 종착수익률 세 시나리오에서 방향이 유지되지 않거나, 투자가능 유니버스에서 IC가 유지되지 않거나, 비용 후 순알파와 OOS 성과가 양수가 아니거나, 중립화 후 성과가 사라지면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.926431503979891 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9995883414380524 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | Y | 1.1737493978020743 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 1.0691982872402716e-06 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0005649717514124294 | <=1.0% |
| T2.3 | 회전율 | Y | 230.0734873197583 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | N | 0.3804493724045214 | >=3.0%/yr |
| T2.4 | net_IR | N | 0.05901819086905792 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.043137062232856564 |
| `ic_t_full` | 4.070553283164354 |
| `ic_p_full` | 5.0291177895892526e-05 |
| `months` | 77 |
| `turnover` | 230.0734873197583 |
| `gross` | 1.5142113862371278 |
| `cost` | 1.1337620138326066 |
| `net` | 0.3804493724045214 |
| `net_ir` | 0.05901819086905792 |
| `hac_t` | 0.15331561808409133 |
| `hac_pvalue` | 0.43927786761909277 |
| `missing_return_rate` | 0.0005649717514124294 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.4` 실비용 순알파: 0.3804493724045214 (>=3.0%/yr)
- `T2.4` net_IR: 0.05901819086905792 (>=0.74)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `value_ep` | value | 0.371 | 114 |
| `qual_roe` | quality | 0.341 | 114 |
| `qual_opm` | quality | 0.336 | 114 |
| `mom_12_1` | momentum | 0.313 | 128 |
| `size` | size | -0.282 | 128 |
| `value_bp` | value | 0.202 | 126 |
| `value_sp` | value | 0.201 | 114 |
| `rev_1m` | momentum | -0.200 | 128 |
| `asset_turnover` | quality | 0.158 | 114 |
| `sue` | earnings | 0.114 | 102 |
| `qual_lev` | quality | 0.019 | 126 |

## Expected relationship and data notes

- Expected relationship: low_vol_12m과 높은 양의 관계를 예상하지만 상승 변동성을 제외하므로 완전한 중복은 아닐 것으로 예상한다. 가치·수익성 팩터와는 낮거나 중간 수준의 관계를 예상한다.
- Data notes: Silver total_return_close에서 계산한 월별 수익률의 음수 부분만 사용한다. 최초 12개월은 의도적으로 결측이며 일별 꼬리위험이 아니라 월별 하방 준편차를 측정한다.
