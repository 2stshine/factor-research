# cycle-0078-net_income_to_liabilities

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-004` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `0cb38fb5ad3db869`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_income_to_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT net_income_ttm/total_liabilities가 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

세금과 비영업비용을 지불한 뒤 남는 이익이 부채보다 충분하면 자기자본 축적과 부채 축소 여력이 크다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9346943146268519 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9178364124058264 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05058276847849688 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05235981371371877 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7153909935418671 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2529196671798098 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.04428551334839163 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.5864084382299295 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05058276847849688 |
| `ic_t_full` | 6.712428774925656 |
| `ic_p_full` | 3.606701745006208e-09 |
| `ic_investable` | 0.05235981371371877 |
| `ic_std_investable` | 0.07319048490460832 |
| `rank_icir_investable` | 0.7153909935418671 |
| `ic_t_investable` | 6.600917875655829 |
| `ic_p_investable` | 5.594523714940961e-09 |
| `ic_retention` | 1.035131434847765 |
| `neutral_ic` | 0.04428551334839163 |
| `neutral_ic_t` | 5.764796575766635 |
| `neutral_ic_p` | 1.446441505140356e-07 |
| `neutral_ic_retention` | 0.8457920341452323 |
| `n_trials` | 89 |
| `max_gold_signal_corr` | 0.5864084382299295 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `pretax_income_to_liabilities` | quality | 0.979 | 63 |
| `net_roa` | quality | 0.959 | 63 |
| `net_profit_margin` | quality | 0.944 | 63 |
| `pretax_roa` | quality | 0.934 | 63 |
| `pretax_profit_margin` | quality | 0.926 | 63 |
| `qual_roe` | quality | 0.883 | 63 |
| `operating_income_to_liabilities` | quality | 0.862 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.849 | 63 |
| `operating_roa` | quality | 0.795 | 63 |
| `value_ep` | value | 0.791 | 63 |
| `qual_opm` | quality | 0.784 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.783 | 63 |
| `operating_return_on_capital_employed` | quality | 0.731 | 63 |
| `quality_stability` | quality | 0.701 | 63 |
| `retained_earnings_growth_12m` | quality | 0.687 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: pretax_income_to_liabilities — 차이: 세금·비지배 영향까지 반영한 최종 이익의 부채 커버리지다.
- Data notes: DART available_date PIT TTM 순이익과 양의 총부채를 사용한다.
