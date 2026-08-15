# cycle-0063-revenue_to_total_liabilities

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `50c3bd228268077e`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/revenue_to_total_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 revenue_ttm/total_liabilities가 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

매출은 이익률 선택 이전의 사업 처리 규모이고 총부채는 단기·장기 자금조달 의무다. 같은 부채로 더 큰 매출 기반을 운영하는 기업은 수요 충격을 흡수하고 채무를 차환할 여력이 높다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 0 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9246437558800358 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9078103437218233 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.03910357431546803 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04021375016401035 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7234338135555403 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2992553926176026 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.029325351678900585 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.455116976396596 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.03910357431546803 |
| `ic_t_full` | 5.310750890510227 |
| `ic_p_full` | 8.100106769512758e-07 |
| `ic_investable` | 0.04021375016401035 |
| `ic_std_investable` | 0.05558732452159982 |
| `rank_icir_investable` | 0.7234338135555403 |
| `ic_t_investable` | 5.155564572975948 |
| `ic_p_investable` | 1.4454422508143048e-06 |
| `ic_retention` | 1.028390648885086 |
| `months` | 50 |
| `turnover` | 90.8773892344582 |
| `gross` | 0.2942754897436284 |
| `cost` | 0.44630087161068344 |
| `net` | -0.1520253818670549 |
| `net_ir` | -0.039168350082762565 |
| `hac_t` | -0.07418866749362604 |
| `hac_pvalue` | 0.5294188470138609 |
| `missing_return_rate` | 0.000592955686445033 |
| `neutral_ic` | 0.029325351678900585 |
| `neutral_ic_t` | 3.827894567565004 |
| `neutral_ic_p` | 0.00015352981849866946 |
| `neutral_ic_retention` | 0.72923692914235 |
| `n_trials` | 74 |
| `max_gold_signal_corr` | 0.455116976396596 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'operating_income_to_current_liabilities': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `quality_stability` | quality | 0.748 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.667 | 63 |
| `qual_lev` | quality | 0.605 | 63 |
| `current_ratio` | quality | 0.564 | 63 |
| `net_working_capital_to_assets` | quality | 0.556 | 63 |
| `asset_turnover` | quality | 0.550 | 63 |
| `retained_earnings_to_assets` | quality | 0.527 | 63 |
| `operating_income_to_liabilities` | quality | 0.501 | 63 |
| `solvent_value` | value | 0.476 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.454 | 63 |
| `pretax_roa` | quality | 0.444 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.430 | 63 |
| `net_roa` | quality | 0.430 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.420 | 63 |
| `market_leverage` | other | -0.398 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: operating_income_to_liabilities — 차이: 이익률과 비용구조를 섞지 않고 총부채가 뒷받침하는 매출 규모의 회전만 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT revenue_ttm과 total_liabilities만 사용한다. 총부채가 양수인 관측에서 정의하며 업종별 회전 차이는 공통 강건성 gate가 진단한다.
