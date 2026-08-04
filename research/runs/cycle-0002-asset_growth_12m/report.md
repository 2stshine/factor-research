# cycle-0002-asset_growth_12m

- Verdict: **REJECT**
- Definition hash: `8036ceaacef6ac62`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/asset_growth_12m.py`

## Hypothesis

공시 시점에 알 수 있는 총자산의 12개월 증가율이 낮은 종목을 보유하면, 공격적으로 자산을 확장한 종목보다 비용 후 양의 초과수익을 얻는다.

## Mechanism

경영자의 과잉투자와 제국 확장은 자본수익률을 낮출 수 있고, 투자자는 최근 성장률을 과도하게 외삽해 공격적 투자 기업을 고평가할 수 있다. 낮은 자산 증가는 이러한 대리인 비용과 기대 과잉의 반대편을 포착한다.

## Pre-registered falsification

상폐 종착수익률 세 시나리오에서 방향이 유지되지 않거나, 투자가능 유니버스의 IC가 유지되지 않거나, 거래비용 후 순알파가 양수가 아니거나, 규모·시장·유동성 중립화 후 성과가 사라지면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.7970272308336824 | >=50% |
| T1.1 | 월별 커버리지 하위10% | N | 0.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |

## Result

| metric | value |
|---|---:|
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T1.1` 월별 커버리지 하위10%: 0.0 (>=30%)
- `T1.2` 종착수익률 3점 방향: None (세 시나리오 IC > 0)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_roe` | quality | -0.349 | 114 |
| `qual_opm` | quality | -0.299 | 114 |
| `value_ep` | value | -0.261 | 114 |
| `size` | size | 0.165 | 114 |
| `sue` | earnings | -0.141 | 102 |
| `mom_12_1` | momentum | -0.128 | 114 |
| `value_bp` | value | 0.120 | 114 |
| `value_sp` | value | 0.108 | 114 |
| `qual_lev` | quality | 0.052 | 114 |
| `asset_turnover` | quality | 0.044 | 114 |
| `rev_1m` | momentum | -0.005 | 114 |

## Expected relationship and data notes

- Expected relationship: 성숙한 저성장 기업을 선호하므로 value_bp와 약한 양의 관계를 예상한다. 자산을 빠르게 늘리지 않고 매출을 만드는 기업과 겹칠 수 있어 asset_turnover와도 일부 양의 관계를 예상하지만, 성장 변화율을 사용하므로 두 팩터와 완전히 같지는 않을 것으로 예상한다.
- Data notes: DART available_date 순으로 정정공시를 재생한 Silver PIT total_assets를 사용한다. 재무상태표 stock 항목이므로 분기 차감 없이 당시 최신 잔액을 사용하며 최초 12개월은 의도적으로 결측이다. 공시 사이에는 같은 잔액이 유지되어 신호가 계단형일 수 있다.
