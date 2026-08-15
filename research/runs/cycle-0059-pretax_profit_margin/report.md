# cycle-0059-pretax_profit_margin

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `76ccaa1e135def8b`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_profit_margin.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 pretax_income_ttm/revenue_ttm이 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

세전 마진은 본업의 원가 구조뿐 아니라 금융비용과 비영업손익까지 매출 한 단위에 대해 얼마나 남기는지 측정한다. 시장이 이 종합 수익성의 지속성을 과소평가하면 이후 상대수익으로 이어질 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9188688914554953 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9026732750376956 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.04924501233047977 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.050952399615872696 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.671634082670124 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2635786229051421 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.044244735755693355 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.830079554227616 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.04924501233047977 |
| `ic_t_full` | 6.360778802930424 |
| `ic_p_full` | 1.4350952665824492e-08 |
| `ic_investable` | 0.050952399615872696 |
| `ic_std_investable` | 0.07586333232719249 |
| `rank_icir_investable` | 0.671634082670124 |
| `ic_t_investable` | 6.243468216312258 |
| `ic_p_investable` | 2.269250701534225e-08 |
| `ic_retention` | 1.034671273385714 |
| `months` | 49 |
| `turnover` | 97.83228611163383 |
| `gross` | -0.04228620461149854 |
| `cost` | 0.4797572498824795 |
| `net` | -0.5220434544939778 |
| `net_ir` | -0.09982104738410454 |
| `hac_t` | -0.219768536239382 |
| `hac_pvalue` | 0.5865083044797444 |
| `missing_return_rate` | 0.0006324860655413686 |
| `neutral_ic` | 0.044244735755693355 |
| `neutral_ic_t` | 5.663659972879221 |
| `neutral_ic_p` | 2.13001438880711e-07 |
| `neutral_ic_retention` | 0.8683543089089416 |
| `n_trials` | 74 |
| `max_gold_signal_corr` | 0.830079554227616 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'operating_income_to_current_liabilities': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.830079554227616 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_profit_margin` | quality | 0.974 | 63 |
| `pretax_roa` | quality | 0.943 | 63 |
| `net_roa` | quality | 0.927 | 63 |
| `qual_roe` | quality | 0.885 | 63 |
| `qual_opm` | quality | 0.843 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.830 | 63 |
| `operating_income_to_liabilities` | quality | 0.824 | 63 |
| `operating_roa` | quality | 0.802 | 63 |
| `value_ep` | value | 0.785 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.774 | 63 |
| `operating_return_on_capital_employed` | quality | 0.750 | 63 |
| `quality_stability` | quality | 0.612 | 63 |
| `operating_earnings_yield` | value | 0.604 | 63 |
| `retained_earnings_to_assets` | quality | 0.560 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.527 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: net_profit_margin — 차이: 세후 순이익 대신 법인세 전 이익을 써 세율·세액공제 차이를 제거하면서 비영업손익은 포함한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT pretax_income_ttm과 revenue_ttm만 사용한다. 매출이 양수인 관측에서 정의하고 세전손실은 음수로 유지한다.
