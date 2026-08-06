# cycle-0023-annual_seasonality_5y

- Verdict: **REJECT**
- Definition hash: `e2712bceedbcdebd`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/annual_seasonality_5y.py`

## Hypothesis

Silver PIT 총수익지수로 계산한 과거 1~5년 동일 월 수익률의 평균이 높은 종목은 낮은 종목보다 이후 한 달 수익률 순위가 높을 것이다.

## Mechanism

정기 공시, 배당·주주총회 일정, 업종별 수요와 기관 리밸런싱이 매년 비슷한 달에 반복되면 종목별 수익률에도 달력 기반 지속성이 생길 수 있다. 시장이 이 반복 패턴을 완전히 차익거래하지 못하면 과거 동일 월 성과가 다음 동일 월을 예측할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9127989736920725 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9037848593664367 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | -0.0017988705407684085 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0008150690757476935 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.01471506033839405 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | N | 0.4573059946042699 | one-sided p<=0.1 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | -0.0017988705407684085 |
| `ic_t_full` | -0.2586660887242587 |
| `ic_p_full` | 0.6016385077408556 |
| `ic_investable` | 0.0008150690757476935 |
| `ic_std_investable` | 0.05539012800518678 |
| `rank_icir_investable` | 0.01471506033839405 |
| `ic_t_investable` | 0.10764760901292905 |
| `ic_p_investable` | 0.4573059946042699 |
| `ic_retention` | None |
| `months` | 65 |
| `turnover` | 943.4230244026592 |
| `gross` | -2.911720755694127 |
| `cost` | 4.482223359659716 |
| `net` | -7.393944115353844 |
| `net_ir` | -1.7822179572409844 |
| `hac_t` | -3.680429720058236 |
| `hac_pvalue` | 0.9997601293085778 |
| `missing_return_rate` | 0.0 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 전체 IC 최소요건: -0.0017988705407684085 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0008150690757476935 (>=0.02)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.01471506033839405 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))
- `T2.1` 투자가능 IC HAC 유의성: 0.4573059946042699 (one-sided p<=0.1)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `long_term_reversal_36_12` | momentum | -0.141 | 102 |
| `small_value` | value | -0.106 | 102 |
| `defensive_small_value` | value | -0.087 | 102 |
| `earnings_confirmed_small_value` | earnings | -0.080 | 102 |
| `qual_roe` | quality | 0.073 | 102 |
| `size` | size | -0.071 | 102 |
| `net_roa` | quality | 0.070 | 102 |
| `value_bp` | value | -0.067 | 102 |
| `net_profit_margin` | quality | 0.067 | 102 |
| `asset_growth_12m` | other | -0.062 | 102 |
| `qual_opm` | quality | 0.057 | 102 |
| `operating_roa` | quality | 0.055 | 102 |
| `defensive_value` | value | -0.047 | 102 |
| `value_sp` | value | -0.047 | 102 |
| `value_ep` | value | 0.046 | 102 |

## Expected relationship and data notes

- Expected relationship: 현재와 가까운 수익률을 쓰지 않으므로 mom_12_1·rev_1m과 낮은 관계를 예상한다. 회계 입력을 사용하지 않아 품질·가치 팩터와도 독립적일 것으로 예상한다.
- Data notes: Silver total_return_close에 매핑된 return_close로 월수익률을 계산하고 12·24·36·48·60개월 전 동일 월 관측 중 최소 3개를 사용한다. 상장 이력이 짧은 종목은 결측이며, 거래일 수와 정확한 공시일을 직접 모델링하지 않는 월 단위 근사치다.
