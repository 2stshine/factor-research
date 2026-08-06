# cycle-0024-retained_earnings_to_assets

- Verdict: **PROVISIONAL**
- Definition hash: `1489feceb711fd22`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_to_assets.py`

## Hypothesis

Silver PIT의 retained_earnings/total_assets가 높은 종목은 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

이익잉여금은 과거 이익 중 배당하지 않고 내부에 축적한 자본이다. 자산 대비 비중이 높으면 손실과 외부조달에 의존해 성장한 기업보다 누적 수익성과 자금 자립도가 높아, 재무곤경과 비싼 증자 위험이 작을 수 있다. 시장이 이 장기 생존력 차이를 충분히 가격에 반영하지 않으면 미래 횡단면 수익률을 예측한다.

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
| T1.1 | 전체 커버리지 | Y | 0.969737975150695 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9485634847080631 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.05329949219037301 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06173497384840352 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.986172760165482 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 3.5901481520430813e-12 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.28012800249822667 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.04428394056065851 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.07689020198981322 | IC>=0.02 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 3.903003919578264e-11 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.07000290187260706 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.05329949219037301 |
| `ic_t_full` | 7.992407187990193 |
| `ic_p_full` | 1.66229605714813e-11 |
| `ic_investable` | 0.06173497384840352 |
| `ic_std_investable` | 0.06260056690071651 |
| `rank_icir_investable` | 0.986172760165482 |
| `ic_t_investable` | 8.370348902706507 |
| `ic_p_investable` | 3.5901481520430813e-12 |
| `ic_retention` | 1.1582657040690179 |
| `months` | 55 |
| `turnover` | 138.6522683097556 |
| `gross` | 0.5149109984812553 |
| `cost` | 0.6716924157729246 |
| `net` | -0.15678141729166892 |
| `net_ir` | -0.036778255771758826 |
| `hac_t` | -0.08035808205578432 |
| `hac_pvalue` | 0.5318752270639734 |
| `missing_return_rate` | 0.0005905406130885274 |
| `neutral_ic` | 0.04428394056065851 |
| `neutral_ic_t` | 5.696462312446523 |
| `neutral_ic_p` | 1.6620754969953675e-07 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.07689020198981322 |
| `oos_ic_t` | 7.033795514088677 |
| `oos_ic_p` | 2.0247091364303337e-08 |
| `n_trials` | 36 |
| `fdr_qvalue` | 3.903003919578264e-11 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `quality_stability` | quality | 0.609 | 102 |
| `net_roa` | quality | 0.594 | 102 |
| `net_profit_margin` | quality | 0.571 | 102 |
| `operating_roa` | quality | 0.532 | 102 |
| `qual_roe` | quality | 0.519 | 102 |
| `qual_opm` | quality | 0.518 | 102 |
| `value_ep` | value | 0.502 | 102 |
| `solvent_value` | value | 0.500 | 102 |
| `qual_lev` | quality | 0.434 | 102 |
| `net_equity_issuance_12m` | other | 0.411 | 102 |
| `profitable_small_value` | quality | 0.380 | 102 |
| `defensive_value` | value | 0.315 | 102 |
| `downside_vol_12m` | other | 0.309 | 102 |
| `value_bp` | value | 0.265 | 102 |
| `low_vol_12m` | other | 0.265 | 102 |

## Expected relationship and data notes

- Expected relationship: 현재 이익 수준을 쓰는 qual_roe·net_roa와 양의 관계가 예상되지만, 장기간 누적된 내부자금 재원을 측정하므로 완전한 중복은 아닐 것으로 예상한다. 부채비율 qual_lev와는 음의 관계, net_equity_issuance_12m과는 약한 양의 관계를 예상한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT retained_earnings와 total_assets만 사용한다. 총자산이 양수인 관측에서 정의하며, 결손 누적으로 이익잉여금이 음수인 값도 그대로 유지한다. 회사 연령과 과거 배당정책이 함께 반영될 수 있다.
