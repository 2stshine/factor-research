# cycle-0025-current_ratio

- Verdict: **REJECT**
- Definition hash: `27ae11f304c7e10a`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_ratio.py`

## Hypothesis

Silver PIT의 current_assets/current_liabilities가 높은 종목은 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

유동비율이 높으면 가까운 만기의 의무를 내부 유동자산으로 감당할 여력이 크다. 신용경색이나 영업 충격 때 불리한 조건의 차입·증자·자산매각 가능성이 낮아 손실 꼬리가 줄 수 있고, 시장이 이 재무 유연성을 충분히 보상하지 않으면 횡단면 수익률을 예측할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9620230919283693 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9494937656287704 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.010010761372831519 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.00641454327675399 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.10063203067481431 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | N | 0.19894939331952805 | one-sided p<=0.1 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.010010761372831519 |
| `ic_t_full` | 1.5542372094821493 |
| `ic_p_full` | 0.0625296914925841 |
| `ic_investable` | 0.00641454327675399 |
| `ic_std_investable` | 0.06374256023394935 |
| `rank_icir_investable` | 0.10063203067481431 |
| `ic_t_investable` | 0.8510787331117661 |
| `ic_p_investable` | 0.19894939331952805 |
| `ic_retention` | 0.640764776809344 |
| `months` | 61 |
| `turnover` | 154.49478771931112 |
| `gross` | 0.8810460824432962 |
| `cost` | 0.7449754356048576 |
| `net` | 0.13607064683843867 |
| `net_ir` | 0.025424188531911408 |
| `hac_t` | 0.055025088349486925 |
| `hac_pvalue` | 0.4781506471803293 |
| `missing_return_rate` | 0.00021474204112310088 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.010010761372831519 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.00641454327675399 (>=0.02)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.10063203067481431 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))
- `T2.1` 투자가능 IC HAC 유의성: 0.19894939331952805 (one-sided p<=0.1)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_lev` | quality | 0.804 | 102 |
| `solvent_value` | value | 0.471 | 102 |
| `value_sp` | value | -0.382 | 102 |
| `quality_stability` | quality | 0.351 | 102 |
| `retained_earnings_to_assets` | quality | 0.345 | 102 |
| `net_profit_margin` | quality | 0.289 | 102 |
| `net_roa` | quality | 0.263 | 102 |
| `qual_opm` | quality | 0.200 | 102 |
| `operating_roa` | quality | 0.166 | 102 |
| `qual_roe` | quality | 0.165 | 102 |
| `value_bp` | value | -0.142 | 102 |
| `asset_turnover` | quality | -0.126 | 102 |
| `value_ep` | value | 0.118 | 102 |
| `operating_roa_volatility_36m` | quality | -0.116 | 91 |
| `small_value` | value | -0.099 | 102 |

## Expected relationship and data notes

- Expected relationship: 장기 레버리지를 보는 qual_lev·solvent_value와 중간 정도 관계를 예상하지만, 만기 1년 내 지급능력에 집중하므로 수익성·가치 팩터와의 관계는 낮을 것으로 예상한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT current_assets와 current_liabilities만 사용한다. 유동부채가 양수인 관측에서 정의한다. 금융업은 유동·비유동 분류의 경제적 의미가 일반 기업과 다를 수 있으나 섹터 정보를 결과에 맞춰 사후 제외하지 않는다.
