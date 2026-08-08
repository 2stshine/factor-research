# cycle-0035-operating_return_on_capital_employed

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `aa11ccad9cfd19c6`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_return_on_capital_employed.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 operating_income_ttm/(total_assets-current_liabilities)가 높은 종목은 낮은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

유동부채를 제외한 자본은 사업에 장기간 투입된 자금에 가깝다. 이 자본에서 높은 영업이익을 만드는 기업은 가격결정력, 자산 규율 또는 공급자 금융 활용에서 우위가 있고 그 지속성이 천천히 가격에 반영될 수 있다.

## Pre-registered falsification

자동 gate의 예측 방향이 실패하거나 investable·중립화 검사를 통과하지 못하고, 또는 operating_roa·qual_roe·asset_turnover의 단순 재표현으로 판정되면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9386400283870157 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9127495206502524 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.059504616186373836 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06529854752184967 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.8111864455748949 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.35838200129559267 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.05752236699540043 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.059504616186373836 |
| `ic_t_full` | 9.179425308651073 |
| `ic_p_full` | 3.370353207256435e-15 |
| `ic_investable` | 0.06529854752184967 |
| `ic_std_investable` | 0.08049758212561357 |
| `rank_icir_investable` | 0.8111864455748949 |
| `ic_t_investable` | 8.96515269886638 |
| `ic_p_investable` | 9.863302507200364e-15 |
| `ic_retention` | 1.0973694430248693 |
| `months` | 76 |
| `turnover` | 90.48450869238096 |
| `gross` | 5.299816999758048 |
| `cost` | 0.4200962859045023 |
| `net` | 4.879720713853546 |
| `net_ir` | 0.9341821680495443 |
| `hac_t` | 2.3153922041769137 |
| `hac_pvalue` | 0.011664110799912477 |
| `missing_return_rate` | 0.0007434426039077201 |
| `neutral_ic` | 0.05752236699540043 |
| `neutral_ic_t` | 8.973593535530785 |
| `neutral_ic_p` | 9.455115230699321e-15 |
| `neutral_ic_retention` | 0.8809134227090236 |
| `n_trials` | 47 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_roa` | quality | 0.983 | 101 |
| `qual_opm` | quality | 0.891 | 101 |
| `qual_roe` | quality | 0.836 | 101 |
| `net_roa` | quality | 0.814 | 101 |
| `net_profit_margin` | quality | 0.728 | 101 |
| `value_ep` | value | 0.705 | 101 |
| `quality_stability` | quality | 0.703 | 101 |
| `retained_earnings_to_assets` | quality | 0.440 | 101 |
| `profitable_small_value` | quality | 0.408 | 101 |
| `asset_turnover` | quality | 0.398 | 101 |
| `paid_in_capital_ratio` | quality | 0.356 | 101 |
| `operating_roa_change_12m` | earnings | 0.343 | 101 |
| `downside_vol_12m` | other | 0.328 | 101 |
| `size` | size | -0.325 | 101 |
| `asset_growth_12m` | other | -0.325 | 101 |

## Expected relationship and data notes

- Expected relationship: operating_roa, qual_roe, asset_turnover와 양의 관계를 예상한다. 다만 유동부채 금융이 분모에서 제외되므로 총자산 수익성이나 자기자본 수익성과 기계적으로 같지는 않다.
- Data notes: DART available_date 순으로 재생한 operating_income_ttm, total_assets, current_liabilities를 사용한다. 투입자본이 양수일 때만 정의한다. 평균 투입자본이 아닌 최신 PIT 재무상태를 쓰며 유동부채에는 영업성·금융성 항목이 함께 포함된다.
