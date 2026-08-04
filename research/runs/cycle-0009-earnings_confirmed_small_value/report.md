# cycle-0009-earnings_confirmed_small_value

- Verdict: **REJECT**
- Definition hash: `89e7b296449ec6b2`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/earnings_confirmed_small_value.py`

## Hypothesis

월별 가치·소형·표준화 이익 서프라이즈 순위를 동일 비중으로 결합하면, 단순 소형가치보다 가격 오류를 해소할 실적 촉매가 있는 종목을 식별해 투자 가능한 롱온리 초과수익을 얻는다.

## Mechanism

소형 저평가주는 정보 반영이 느리지만 가치함정일 수 있다. 예상 밖의 이익 개선은 저평가가 악화된 펀더멘털만 반영한 것이 아님을 확인하고, 제한된 애널리스트 커버리지 아래에서 후속 가격 조정을 유발한다.

## Pre-registered falsification

투자가능 IC 유지율과 비용 후 성과가 충분하지 않거나, 강건성·고정 OOS·다중검정·Gold 직교성 중 하나라도 hard fail이면 실적 촉매 소형가치 가설을 기각한다.

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
| T2.1 | 투자가능 IC 유지율 | Y | 0.551923329254517 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 0.004015343475661524 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0014778931811650724 | <=1.0% |
| T2.3 | 회전율 | Y | 345.4762822237345 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | Y | 7.935710326211466 | >=3.0%/yr |
| T2.4 | net_IR | Y | 1.1136690128387612 | >=0.74 |
| T3.1 | 리밸런싱 고원성 | Y | None | 1/3/6개월 모두 양수, max/min<=3.0 |
| T3.1 | 분위수 강건성 | Y | None | 10/20/30% 모두 순알파 > 0 |
| T3.2 | 2배 비용 스트레스 | Y | 6.245658487682783 | >0%/yr |
| T3.2 | 상폐 -100% 포트폴리오 | Y | 7.710268021588409 | >0%/yr |
| T3.3 | 비중첩 구간 순알파 | Y | 3 | >=3/4 |
| T3.3 | 레짐 집중도 | Y | 0.5693666470130905 | <=0.6 |
| T3.4 | 시장·규모·유동성 중립 | Y | 5.621358446817021 | >0%/yr |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS | N | 0.7371500888687741 | net>0 & HAC p<=0.1 |
| T4.2 | Deflated Sharpe | N | 0.4287438733879923 | >=95% |
| T4.3 | 다중검정 FDR | N | 0.26793619511880734 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.19783961125344407 | median \|rho\|<=0.8 |
| T5.1 | Gold 수익 직교성 | Y | 0.0 | \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.06808847036097229 |
| `ic_t_full` | 5.0190607005275085 |
| `ic_p_full` | 1.244357554345798e-06 |
| `months` | 67 |
| `turnover` | 345.4762822237345 |
| `gross` | 9.625762164740156 |
| `cost` | 1.6900518385286865 |
| `net` | 7.935710326211466 |
| `net_ir` | 1.1136690128387612 |
| `hac_t` | 2.33352450851502 |
| `hac_pvalue` | 0.011338267472357454 |
| `missing_return_rate` | 0.0014778931811650724 |
| `oos_start` | 2023-09 |
| `oos_months` | 30 |
| `oos_net` | -3.662981895590691 |
| `oos_ir` | -0.43451118331114874 |
| `oos_hac_pvalue` | 0.7371500888687741 |
| `n_trials` | 21 |
| `dsr_probability` | 0.4287438733879923 |
| `fdr_qvalue` | 0.26793619511880734 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)
- `T4.1` 고정 OOS: 0.7371500888687741 (net>0 & HAC p<=0.1)
- `T4.2` Deflated Sharpe: 0.4287438733879923 (>=95%)
- `T4.3` 다중검정 FDR: 0.26793619511880734 (BY q<=0.1)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `small_value` | value | 0.808 | 126 |
| `defensive_small_value` | value | 0.690 | 126 |
| `value_bp` | value | 0.649 | 126 |
| `size` | size | 0.561 | 126 |
| `sue` | earnings | 0.554 | 102 |
| `value_sp` | value | 0.492 | 114 |
| `defensive_value` | value | 0.468 | 126 |
| `solvent_value` | value | 0.451 | 126 |
| `value_ep` | value | 0.190 | 114 |
| `asset_turnover` | quality | 0.127 | 114 |
| `low_vol_12m` | other | 0.108 | 126 |
| `mom_12_1` | momentum | -0.089 | 126 |
| `asset_growth_12m` | other | 0.083 | 114 |
| `qual_opm` | quality | -0.039 | 114 |
| `qual_lev` | quality | -0.036 | 126 |

## Expected relationship and data notes

- Expected relationship: small_value 및 value_bp와 양의 관계를 예상하지만 독립성이 높은 sue_score를 결합하므로 단순 가치·규모 복합체보다는 관계가 낮아질 것으로 예상한다.
- Data notes: Silver PIT total_equity, market_cap, sue_score만 사용한다. SUE가 PIT로 제공되지 않는 과거 또는 종목에는 중립 순위 0.5를 부여해 표본을 재정의하거나 미래 가용성을 소급하지 않는다.
