# cycle-0011-profitable_small_value

- Verdict: **REJECT**
- Definition hash: `ec639be0f12aad5a`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/profitable_small_value.py`

## Hypothesis

월별 장부가치/시가총액·소형주·영업ROA 순위를 동일 비중으로 결합하면, 단순 소형가치의 가격 오류 프리미엄을 유지하면서 영업 기반이 취약한 가치함정을 줄여 롱온리 초과수익을 얻는다.

## Mechanism

소형 저평가주는 정보 비대칭 때문에 천천히 재평가되지만 낮은 가격이 영업 부진을 정당하게 반영한 경우도 많다. 높은 영업ROA는 자산이 실제 영업이익을 창출한다는 지속적인 확인 신호로, 가격 오류와 구조적 부실을 구분한다.

## Pre-registered falsification

투자가능 IC 유지율과 비용 후 성과가 충분하지 않거나, 강건성·고정 OOS·다중검정·Gold 직교성 중 하나라도 hard fail이면 수익성 소형가치 가설을 기각한다.

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
| T2.1 | 투자가능 IC 유지율 | Y | 0.7629826206303265 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 3.7817421719135656e-06 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0015189457695307688 | <=1.0% |
| T2.3 | 회전율 | Y | 286.5309776771699 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | Y | 6.209542860021518 | >=3.0%/yr |
| T2.4 | net_IR | Y | 0.9625915755480452 | >=0.74 |
| T3.1 | 리밸런싱 고원성 | Y | None | 1/3/6개월 모두 양수, max/min<=3.0 |
| T3.1 | 분위수 강건성 | Y | None | 10/20/30% 모두 순알파 > 0 |
| T3.2 | 2배 비용 스트레스 | Y | 4.796867338714657 | >0%/yr |
| T3.2 | 상폐 -100% 포트폴리오 | Y | 5.915373585677515 | >0%/yr |
| T3.3 | 비중첩 구간 순알파 | Y | 3 | >=3/4 |
| T3.3 | 레짐 집중도 | N | 0.6317150283677198 | <=0.6 |
| T3.4 | 시장·규모·유동성 중립 | Y | 5.5085566697122905 | >0%/yr |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS | N | 0.5336822878528704 | net>0 & HAC p<=0.1 |
| T4.2 | Deflated Sharpe | N | 0.32098033449296287 | >=95% |
| T4.3 | 다중검정 FDR | N | 0.24387152470865328 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.27996431509641784 | median \|rho\|<=0.8 |
| T5.1 | Gold 수익 직교성 | Y | 0.0 | \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.08267626926029238 |
| `ic_t_full` | 6.064185205783879 |
| `ic_p_full` | 1.4112639841269587e-08 |
| `months` | 66 |
| `turnover` | 286.5309776771699 |
| `gross` | 7.622218381328377 |
| `cost` | 1.4126755213068605 |
| `net` | 6.209542860021518 |
| `net_ir` | 0.9625915755480452 |
| `hac_t` | 2.189671666559609 |
| `hac_pvalue` | 0.016071715261072452 |
| `missing_return_rate` | 0.0015189457695307688 |
| `oos_start` | 2023-09 |
| `oos_months` | 33 |
| `oos_net` | -0.5557751922685877 |
| `oos_ir` | -0.05800599886524301 |
| `oos_hac_pvalue` | 0.5336822878528704 |
| `n_trials` | 23 |
| `dsr_probability` | 0.32098033449296287 |
| `fdr_qvalue` | 0.24387152470865328 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.3` 레짐 집중도: 0.6317150283677198 (<=0.6)
- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)
- `T4.1` 고정 OOS: 0.5336822878528704 (net>0 & HAC p<=0.1)
- `T4.2` Deflated Sharpe: 0.32098033449296287 (>=95%)
- `T4.3` 다중검정 FDR: 0.24387152470865328 (BY q<=0.1)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `small_value` | value | 0.783 | 126 |
| `defensive_small_value` | value | 0.760 | 126 |
| `value_bp` | value | 0.737 | 126 |
| `earnings_confirmed_small_value` | earnings | 0.712 | 126 |
| `defensive_value` | value | 0.607 | 126 |
| `value_sp` | value | 0.607 | 114 |
| `solvent_value` | value | 0.584 | 126 |
| `value_ep` | value | 0.551 | 114 |
| `quality_stability` | quality | 0.467 | 126 |
| `size` | size | 0.409 | 126 |
| `qual_opm` | quality | 0.408 | 114 |
| `qual_roe` | quality | 0.393 | 114 |
| `asset_turnover` | quality | 0.320 | 114 |
| `low_vol_12m` | other | 0.247 | 126 |
| `downside_vol_12m` | other | 0.162 | 126 |

## Expected relationship and data notes

- Expected relationship: small_value와 가장 높은 양의 관계를, qual_roe·qual_opm과 중간 정도의 양의 관계를 예상한다. 수익성 축 때문에 단순 가치·규모 복합체와 완전히 같지는 않을 것으로 예상한다.
- Data notes: Silver PIT total_equity, operating_income_ttm, total_assets와 월말 market_cap을 사용한다. 영업ROA가 없는 관측은 해당 축에만 중립 순위 0.5를 부여해 표본을 재정의하지 않는다.
