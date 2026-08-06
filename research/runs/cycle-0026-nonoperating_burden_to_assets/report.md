# cycle-0026-nonoperating_burden_to_assets

- Verdict: **REJECT**
- Definition hash: `bafec4ce16293b98`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/nonoperating_burden_to_assets.py`

## Hypothesis

Silver PIT의 (operating_income_ttm-net_income_ttm)/total_assets가 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

영업이익과 순이익의 차이는 이자비용, 세금, 관계기업·기타 비영업 손익을 함께 반영한다. 같은 자산 기반의 영업성과가 있어도 이 차이가 크면 주주에게 남는 이익의 변환 효율이 낮고 재무구조나 일회성 손실에 취약할 수 있다. 시장이 그 부담의 지속성을 과소평가하면 이후 상대수익률이 낮아질 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9452621127181343 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9136708979509247 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.025655774066441383 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.022345659793357002 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.39692233997065435 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 0.0019947969034602854 | one-sided p<=0.1 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.025655774066441383 |
| `ic_t_full` | 4.53273702899123 |
| `ic_p_full` | 1.304907783295294e-05 |
| `ic_investable` | 0.022345659793357002 |
| `ic_std_investable` | 0.056297309430880314 |
| `rank_icir_investable` | 0.39692233997065435 |
| `ic_t_investable` | 2.987042012533807 |
| `ic_p_investable` | 0.0019947969034602854 |
| `ic_retention` | 0.8709797543230582 |
| `months` | 59 |
| `turnover` | 199.76986403057936 |
| `gross` | 0.5616061310296102 |
| `cost` | 0.9607465162005789 |
| `net` | -0.39914038517096845 |
| `net_ir` | -0.09547193033726571 |
| `hac_t` | -0.17522191032636197 |
| `hac_pvalue` | 0.5692422252664263 |
| `missing_return_rate` | 0.00042948408224620176 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.025655774066441383 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_profit_margin` | quality | 0.290 | 102 |
| `qual_lev` | quality | 0.281 | 102 |
| `current_ratio` | quality | 0.254 | 102 |
| `solvent_value` | value | 0.254 | 102 |
| `net_roa` | quality | 0.228 | 102 |
| `value_ep` | value | 0.227 | 102 |
| `qual_roe` | quality | 0.195 | 102 |
| `retained_earnings_to_assets` | quality | 0.188 | 102 |
| `operating_roa` | quality | -0.151 | 102 |
| `asset_turnover` | quality | -0.150 | 102 |
| `asset_turnover_change_12m` | quality | -0.135 | 102 |
| `earnings_confirmed_small_value` | earnings | 0.113 | 102 |
| `net_equity_issuance_12m` | other | 0.107 | 102 |
| `operating_roa_change_12m` | earnings | -0.097 | 102 |
| `qual_opm` | quality | -0.090 | 102 |

## Expected relationship and data notes

- Expected relationship: 순이익 수준을 포함하므로 net_roa·qual_roe와 양의 관계가 일부 예상되고, 이자 부담을 통해 qual_lev와도 관계가 있을 수 있다. 다만 영업이익과 순이익 사이의 차이만 사용하므로 현재 수익성 수준과 완전히 같지는 않을 것으로 예상한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT operating_income_ttm, net_income_ttm, total_assets만 사용한다. 총자산이 양수인 관측에서 정의한다. 세금과 일회성 비영업손익을 분리할 세부 계정이 없어 경제적 원인이 혼합될 수 있다.
