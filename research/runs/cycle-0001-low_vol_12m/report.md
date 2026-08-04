# cycle-0001-low_vol_12m

- Verdict: **REJECT**
- Definition hash: `ae41d1ec7120cde0`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/low_vol_12m.py`

## Hypothesis

월별 총수익률의 최근 12개월 변동성이 낮은 종목을 보유하면 고변동 종목 선호의 가격 왜곡이 교정되며 비용 후 양의 초과수익을 얻는다.

## Mechanism

벤치마크 추종과 레버리지 제약을 받는 투자자는 목표 수익을 높이기 위해 고베타·고변동 종목을 과도하게 매수하고, 복권형 수익 분포 선호도 같은 방향으로 작용한다.

## Pre-registered falsification

투자가능 유니버스에서 IC가 유지되지 않거나 비용 후 순알파가 양수가 아니거나, 규모·시장·유동성 중립화 후 성과가 사라지면 가설을 기각한다.

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
| T2.1 | 투자가능 IC 유지율 | Y | 1.1271991843353066 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 3.63377522314849e-17 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.00048426150121065375 | <=1.0% |
| T2.3 | 회전율 | Y | 206.85901953678876 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | N | 1.0518550896694072 | >=3.0%/yr |
| T2.4 | net_IR | N | 0.15973292237788664 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.0806986547082105 |
| `ic_t_full` | 8.34435924796973 |
| `ic_p_full` | 3.96098354796732e-13 |
| `months` | 79 |
| `turnover` | 206.85901953678876 |
| `gross` | 2.0695177400711167 |
| `cost` | 1.0176626504017092 |
| `net` | 1.0518550896694072 |
| `net_ir` | 0.15973292237788664 |
| `hac_t` | 0.38924692699481 |
| `hac_pvalue` | 0.3490770821869901 |
| `missing_return_rate` | 0.00048426150121065375 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.4` 실비용 순알파: 1.0518550896694072 (>=3.0%/yr)
- `T2.4` net_IR: 0.15973292237788664 (>=0.74)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `value_bp` | value | 0.353 | 126 |
| `value_ep` | value | 0.325 | 114 |
| `mom_12_1` | momentum | -0.282 | 128 |
| `value_sp` | value | 0.266 | 114 |
| `qual_opm` | quality | 0.230 | 114 |
| `qual_roe` | quality | 0.225 | 114 |
| `size` | size | -0.219 | 128 |
| `asset_turnover` | quality | 0.092 | 114 |
| `rev_1m` | momentum | -0.038 | 128 |
| `qual_lev` | quality | 0.021 | 126 |
| `sue` | earnings | -0.016 | 102 |

## Expected relationship and data notes

- Expected relationship: 소형주가 고변동인 경향 때문에 size와 양의 최종점수 상관을 예상하지만, 가격 변동성 자체를 사용하므로 기존 가치·수익성 팩터와의 상관은 낮을 것으로 예상한다.
- Data notes: Silver total_return_close로 만든 월별 수익률만 사용한다. 최초 12개월은 의도적으로 결측이며 분모·재무 정정공시 의존성은 없다.
