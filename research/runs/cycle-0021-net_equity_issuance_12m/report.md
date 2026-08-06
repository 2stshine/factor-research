# cycle-0021-net_equity_issuance_12m

- Verdict: **PROVISIONAL**
- Definition hash: `19650b7013627426`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_equity_issuance_12m.py`

## Hypothesis

Silver PIT에서 12개월 시가총액 성장률을 같은 기간 총주주수익 성장률로 나눈 순주식 발행 대용치가 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

경영자는 주가가 내재가치보다 높다고 판단하거나 외부자금 수요가 클 때 주식을 발행할 유인이 있다. 반대로 환매와 배당은 자본을 주주에게 반환한다. 투자자가 이러한 자금조달 선택의 정보를 늦게 반영하면 순발행이 낮은 기업이 이후 상대적으로 재평가될 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9999604590267649 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 1.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.0447186478099835 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.048213892876565585 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.9064022987519231 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 8.775275188724596e-10 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.30801128968210806 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.025220253420255093 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.0782761848902615 | IC>=0.02 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 4.299884842475053e-09 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.03950893963079239 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.0447186478099835 |
| `ic_t_full` | 6.486027029974189 |
| `ic_p_full` | 7.352240701898258e-09 |
| `ic_investable` | 0.048213892876565585 |
| `ic_std_investable` | 0.053192597749315104 |
| `rank_icir_investable` | 0.9064022987519231 |
| `ic_t_investable` | 7.01443720318404 |
| `ic_p_investable` | 8.775275188724596e-10 |
| `ic_retention` | 1.0781607950543122 |
| `months` | 53 |
| `turnover` | 205.0318531942727 |
| `gross` | 0.5967707215480492 |
| `cost` | 0.9900895469916186 |
| `net` | -0.393318825443569 |
| `net_ir` | -0.0842071394085867 |
| `hac_t` | -0.20920376223451564 |
| `hac_pvalue` | 0.5824467046267879 |
| `missing_return_rate` | 0.0011273957158962795 |
| `neutral_ic` | 0.025220253420255093 |
| `neutral_ic_t` | 3.585563796924489 |
| `neutral_ic_p` | 0.00032523710290738463 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.0782761848902615 |
| `oos_ic_t` | 7.417867311551545 |
| `oos_ic_p` | 6.64870672400065e-09 |
| `n_trials` | 33 |
| `fdr_qvalue` | 4.299884842475053e-09 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `quality_stability` | quality | 0.332 | 102 |
| `defensive_value` | value | 0.316 | 102 |
| `value_ep` | value | 0.314 | 102 |
| `net_roa` | quality | 0.291 | 102 |
| `value_bp` | value | 0.284 | 102 |
| `qual_roe` | quality | 0.282 | 102 |
| `operating_roa` | quality | 0.276 | 102 |
| `value_sp` | value | 0.275 | 102 |
| `downside_vol_12m` | other | 0.271 | 102 |
| `net_profit_margin` | quality | 0.268 | 102 |
| `profitable_small_value` | quality | 0.264 | 102 |
| `low_vol_12m` | other | 0.263 | 102 |
| `qual_opm` | quality | 0.257 | 102 |
| `solvent_value` | value | 0.240 | 102 |
| `defensive_small_value` | value | 0.215 | 102 |

## Expected relationship and data notes

- Expected relationship: 주가 변화를 제거한 기업재무 신호이므로 mom_12_1과 낮은 관계를 예상한다. 주식 발행을 통해 자산을 확장한 기업에서는 asset_growth_12m과 양의 관계가 있을 수 있으나, 환매와 배당도 반영하므로 완전한 중복은 아닐 것으로 예상한다.
- Data notes: Silver PIT market_cap과 total_return_close에 매핑된 return_close를 사용한다. 12개월 이력이 없거나 값이 0 이하인 관측은 결측이다. 이 비율은 주식 수 변화를 직접 쓰지 않아 액면분할 영향을 줄이지만, 합병·분할·대규모 배당을 완벽히 분리하는 정밀 발행량 자료는 아니다.
