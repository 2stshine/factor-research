# cycle-0028-trading_turnover_20d

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260806-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `c03efb8638407bd6`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.5.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/trading_turnover_20d.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 ADV20/시가총액이 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

시가총액 대비 거래대금이 크다는 것은 기업 규모에 비해 투자자 관심과 의견 교환이 집중됐다는 뜻이다. 과도한 관심이나 투기적 수요가 현재 가격에 먼저 반영되고 천천히 되돌려진다면 낮은 거래회전 종목이 이후 상대적으로 높은 수익을 낼 수 있다.

## Pre-registered falsification

현재 ruleset의 전체·투자 가능 IC, Rank ICIR, 기간 강건성 및 시장구분·유동성·비의도 규모 노출 제거 후 IC를 통과하지 못하면 단순 유동성·규모를 넘어선 거래활동 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 1.0 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 1.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.11903226781315458 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.12177200445921663 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.9107049636808925 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.29740912134819814 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC | Y | 0.020098776762474898 | IC>=0.01 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.0 | median \|rho\|<=0.8 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.11903226781315458 |
| `ic_t_full` | 9.80348082345518 |
| `ic_p_full` | 1.4680101723534543e-16 |
| `ic_investable` | 0.12177200445921663 |
| `ic_std_investable` | 0.1337118049373947 |
| `rank_icir_investable` | 0.9107049636808925 |
| `ic_t_investable` | 10.88281669030472 |
| `ic_p_investable` | 6.553308729998895e-19 |
| `ic_retention` | 1.0230167558460923 |
| `months` | 99 |
| `turnover` | 342.33296776009155 |
| `gross` | 1.5086797544051185 |
| `cost` | 1.5305519498044298 |
| `net` | -0.02187219539931034 |
| `net_ir` | -0.002693286213143998 |
| `hac_t` | -0.009120640289963943 |
| `hac_pvalue` | 0.5036292880289673 |
| `missing_return_rate` | 2.320239448711107e-05 |
| `neutral_ic` | 0.020098776762474898 |
| `neutral_ic_t` | 3.1568197159189864 |
| `neutral_ic_p` | 0.0010570159174463972 |
| `n_trials` | 40 |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.579 | 101 |
| `defensive_value` | value | 0.562 | 101 |
| `max_monthly_return_12m` | other | 0.524 | 101 |
| `defensive_small_value` | value | 0.438 | 101 |
| `downside_vol_12m` | other | 0.385 | 101 |
| `value_bp` | value | 0.380 | 101 |
| `quality_stability` | quality | 0.324 | 101 |
| `solvent_value` | value | 0.315 | 101 |
| `profitable_small_value` | quality | 0.276 | 101 |
| `return_skewness_24m` | other | 0.254 | 101 |
| `value_sp` | value | 0.250 | 101 |
| `retained_earnings_to_assets` | quality | 0.218 | 101 |
| `net_equity_issuance_12m` | other | 0.214 | 101 |
| `small_value` | value | 0.213 | 101 |
| `value_ep` | value | 0.208 | 101 |

## Expected relationship and data notes

- Expected relationship: 유동성·관심도와 연결되므로 size 및 lottery-demand 계열과 일부 관계가 있을 수 있다. 그러나 가격경로나 회계값이 아니라 최근 거래대금/기업가치 비율만 사용하므로 가치·수익성 팩터와의 관계는 제한적일 것으로 예상한다.
- Data notes: 인증된 KRX Silver의 월말 시점 ADV20과 market_cap만 사용한다. ADV20은 직전 20거래일 일평균 거래대금이며 시가총액이 양수인 관측에서만 정의한다. free-float 회전율이 아니고 거래정지·기업행위·시장별 거래관행의 영향을 받을 수 있으며, 목표 AUM의 체결 가능성을 직접 보장하지 않는다.
