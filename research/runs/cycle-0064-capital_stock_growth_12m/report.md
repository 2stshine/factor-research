# cycle-0064-capital_stock_growth_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `e09f61de6fa86d70`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/capital_stock_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 12개월 capital_stock 성장률이 낮은 기업은 높은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

자본금 증가는 유상증자·주식전환·합병 등 법정 납입자본 확대를 포착한다. 경영자가 높은 평가나 자금수요를 이용해 자본을 늘린 뒤 희석과 투자수익성 저하가 나타나면 낮은 자본금 성장 기업의 상대수익이 높을 수 있다.

## Pre-registered falsification

음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 12 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8805329702690092 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.45202846448942113 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05160339717005967 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05463583348127087 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.8155744321017474 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.34060172913373016 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | N | 0.014875094492953829 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.38905744323171587 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05160339717005967 |
| `ic_t_full` | 6.006066363584689 |
| `ic_p_full` | 5.708479225822008e-08 |
| `ic_investable` | 0.05463583348127087 |
| `ic_std_investable` | 0.06699061585399817 |
| `rank_icir_investable` | 0.8155744321017474 |
| `ic_t_investable` | 6.354669530153779 |
| `ic_p_investable` | 1.469803764550258e-08 |
| `ic_retention` | 1.0587642767242198 |
| `neutral_ic` | 0.014875094492953829 |
| `neutral_ic_t` | 2.366701819142702 |
| `neutral_ic_p` | 0.010568739252236059 |
| `neutral_ic_retention` | 0.27225894701602754 |
| `n_trials` | 79 |
| `max_gold_signal_corr` | 0.38905744323171587 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- `T3.2` 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: 0.014875094492953829 (IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_equity_issuance_12m` | other | 0.658 | 63 |
| `net_equity_issuance_price_adjusted_12m` | other | 0.658 | 63 |
| `retained_earnings_to_equity` | quality | 0.389 | 63 |
| `retained_earnings_to_assets` | quality | 0.377 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.363 | 63 |
| `defensive_value` | value | 0.294 | 63 |
| `quality_stability` | quality | 0.291 | 63 |
| `realized_volatility_252d` | other | 0.285 | 63 |
| `idiosyncratic_volatility_24m` | other | 0.278 | 63 |
| `value_bp` | value | 0.273 | 63 |
| `value_sp` | value | 0.266 | 63 |
| `equity_growth_12m` | other | 0.258 | 63 |
| `solvent_value` | value | 0.253 | 63 |
| `paid_in_capital_ratio` | quality | 0.253 | 63 |
| `revenue_to_total_liabilities` | quality | 0.253 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: net_equity_issuance_price_adjusted_12m — 차이: 시장가격으로 역산한 주식수 변화가 아니라 DART PIT 장부의 법정 자본금 변동만 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT capital_stock을 사용한다. 정확히 12개월 전 자본금이 양수인 관측에서 정의하며 액면분할 자체는 자본금을 바꾸지 않는다.
