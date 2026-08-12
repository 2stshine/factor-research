# cycle-0045-high_52w_price_proximity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260808-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `559d74ab903459ce`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/high_52w_price_proximity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

월말 분할조정 가격이 최근 252거래일 고가에 가까운 종목은 멀리 있는 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

투자자가 과거 고가를 기준점으로 삼고 새로운 정보를 점진적으로 반영하면 고가 근접 종목의 정보 확산이 이어질 수 있다.

## Pre-registered falsification

현재 gate의 무결성·IC·Rank ICIR·강건성·다중검정 및 confirmation을 통과하지 못하거나 mom_12_1과 독립성을 충족하지 못하면 별도 고가 앵커 가설을 기각한다.

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
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | N | 0.0020108654684385563 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0033650845948951756 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.02293738989332138 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0020108654684385563 |
| `ic_t_full` | 0.14614039892989547 |
| `ic_p_full` | 0.4421462172238377 |
| `ic_investable` | 0.0033650845948951756 |
| `ic_std_investable` | 0.1467073895742156 |
| `rank_icir_investable` | 0.02293738989332138 |
| `ic_t_investable` | 0.24321622370276058 |
| `ic_p_investable` | 0.4043269671170072 |
| `ic_retention` | 1.6734508835681459 |
| `months` | 62 |
| `turnover` | 433.2808196061012 |
| `gross` | 0.5372035033293033 |
| `cost` | 2.0744339700623144 |
| `net` | -1.537230466733012 |
| `net_ir` | -0.15700969628989833 |
| `hac_t` | -0.44668047297708496 |
| `hac_pvalue` | 0.6716561903116434 |
| `missing_return_rate` | 0.0 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0020108654684385563 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0033650845948951756 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.02293738989332138 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `high_12m_proximity` | momentum | 0.931 | 63 |
| `downside_vol_12m` | other | 0.708 | 63 |
| `mom_12_1` | momentum | 0.516 | 63 |
| `realized_volatility_252d` | other | 0.452 | 63 |
| `positive_return_share_12m` | momentum | 0.444 | 63 |
| `rev_1m` | momentum | -0.434 | 63 |
| `low_vol_12m` | other | 0.378 | 63 |
| `quality_stability` | quality | 0.348 | 63 |
| `net_equity_issuance_12m` | other | 0.316 | 63 |
| `net_roa` | quality | 0.279 | 63 |
| `operating_roa` | quality | 0.278 | 63 |
| `operating_return_on_capital_employed` | quality | 0.278 | 63 |
| `value_ep` | value | 0.278 | 63 |
| `qual_opm` | quality | 0.275 | 63 |
| `qual_roe` | quality | 0.274 | 63 |

## Expected relationship and data notes

- Expected relationship: mom_12_1과 양의 관계를 예상하지만 누적수익이 아니라 현재 가격과 고가의 거리만 사용하므로 완전한 중복은 아닐 것으로 예상한다.
- Data notes: 배당재투자 지수인 return_close가 아니라 가격 기준점에 맞는 Silver adj_close를 사용한다. 최근 252거래일 중 최소 200개 가격관측이 있어야 정의한다.
