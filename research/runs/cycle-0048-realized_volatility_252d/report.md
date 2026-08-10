# cycle-0048-realized_volatility_252d

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260808-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `e0668fb0e7c0eb69`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/realized_volatility_252d.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 252거래 관측의 일별 총수익률 표준편차가 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

직접 레버리지가 어려운 투자자와 복권형 수익을 선호하는 투자자의 고변동 종목 수요가 저변동 종목에 상대적 기대수익 보상을 남길 수 있다.

## Pre-registered falsification

현재 gate를 통과하지 못하거나 월별 low_vol_12m과의 중복이 허용 기준을 넘거나 정식 confirmation에 실패하면 일별 저변동성 후보를 기각한다.

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
| T2.1 | 전체 IC 최소요건 | Y | 0.10352338520215972 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.10939565284808546 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7999053130598551 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3657851421647753 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.05116507168691829 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.10352338520215972 |
| `ic_t_full` | 8.333593920715334 |
| `ic_p_full` | 5.876623659821375e-12 |
| `ic_investable` | 0.10939565284808546 |
| `ic_std_investable` | 0.13676075288163467 |
| `rank_icir_investable` | 0.7999053130598551 |
| `ic_t_investable` | 8.624420716131688 |
| `ic_p_investable` | 1.866865836207049e-12 |
| `ic_retention` | 1.0567240690058428 |
| `months` | 62 |
| `turnover` | 106.7406572765608 |
| `gross` | 0.7188564735646272 |
| `cost` | 0.5178046698901237 |
| `net` | 0.20105180367450265 |
| `net_ir` | 0.02249889521821162 |
| `hac_t` | 0.05534738024333331 |
| `hac_pvalue` | 0.47802129989606307 |
| `missing_return_rate` | 0.0 |
| `neutral_ic` | 0.05116507168691829 |
| `neutral_ic_t` | 5.257527798116527 |
| `neutral_ic_p` | 9.885904000943792e-07 |
| `neutral_ic_retention` | 0.4677066259476483 |
| `n_trials` | 7 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.815 | 63 |
| `defensive_value` | value | 0.741 | 63 |
| `max_monthly_return_12m` | other | 0.709 | 63 |
| `trading_turnover_20d` | other | 0.664 | 63 |
| `downside_vol_12m` | other | 0.655 | 63 |
| `quality_stability` | quality | 0.533 | 63 |
| `defensive_small_value` | value | 0.532 | 63 |
| `max_daily_return_1m` | other | 0.518 | 63 |
| `turnover_volatility_12m` | other | 0.510 | 63 |
| `net_equity_issuance_12m` | other | 0.471 | 63 |
| `dividend_yield_ttm` | value | 0.458 | 63 |
| `high_52w_price_proximity` | momentum | 0.452 | 63 |
| `value_bp` | value | 0.437 | 63 |
| `return_skewness_24m` | other | 0.394 | 63 |
| `solvent_value` | value | 0.375 | 63 |

## Expected relationship and data notes

- Expected relationship: low_vol_12m 및 market_beta_36m과 양의 최종점수 관계가 예상된다. 다만 일별 충격을 사용하므로 월수익 표준편차보다 급격한 변동을 더 많이 반영한다.
- Data notes: 인증된 Silver 일별 total_return_close로 계산한 표준편차이며 최소 126개 유효 수익률을 요구한다. 시장요인을 회귀 제거한 idiosyncratic volatility는 아니다.
