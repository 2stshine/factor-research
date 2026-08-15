# cycle-0097-net_working_capital_yield

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-008` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `0c14cdb6457bdf0a`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_working_capital_yield.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

PIT 유동자산에서 유동부채를 뺀 순운전자본/시가총액 비율이 높은 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

단기 의무를 차감한 유동자산 완충력은 하방 위험을 제한하며, 시장이 이를 낮게 평가한 기업에는 가치 재평가 여지가 있다.

## Pre-registered falsification

양의 방향, 입력·표본 무결성, 투자 가능 IC, 강건성, BY, 기존 가치 신호 직교성 또는 봉인 OOS가 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9610139285140624 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9569640847388851 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05262022356131212 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05396543286061297 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.211530353094456 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3456821399569455 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03247307850704446 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.31823487073510903 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05262022356131212 |
| `ic_t_full` | 7.333131288638806 |
| `ic_p_full` | 3.0962200911455436e-10 |
| `ic_investable` | 0.05396543286061297 |
| `ic_std_investable` | 0.04454319507784185 |
| `rank_icir_investable` | 1.211530353094456 |
| `ic_t_investable` | 7.836526529683633 |
| `ic_p_investable` | 4.2040504478455016e-11 |
| `ic_retention` | 1.0255644922856215 |
| `neutral_ic` | 0.03247307850704446 |
| `neutral_ic_t` | 5.191172380381098 |
| `neutral_ic_p` | 1.26620368968429e-06 |
| `neutral_ic_retention` | 0.6017384978810232 |
| `n_trials` | 109 |
| `max_gold_signal_corr` | 0.31823487073510903 |
| `gold_signal_comparison_months` | {'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_working_capital_to_assets` | quality | 0.730 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.710 | 63 |
| `current_ratio` | quality | 0.708 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.657 | 63 |
| `noncurrent_assets_to_equity` | other | 0.651 | 63 |
| `solvent_value` | value | 0.594 | 63 |
| `current_assets_to_assets` | quality | 0.525 | 63 |
| `noncurrent_asset_share` | other | 0.514 | 63 |
| `qual_lev` | quality | 0.483 | 63 |
| `revenue_to_total_liabilities` | quality | 0.464 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.446 | 63 |
| `current_liabilities_to_assets` | quality | 0.440 | 63 |
| `retained_earnings_to_assets` | quality | 0.416 | 63 |
| `quality_stability` | quality | 0.412 | 63 |
| `profitable_small_value` | quality | 0.397 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: net_working_capital_to_assets — 차이: 자산 내 운전자본 구성이 아니라 시장가치 대비 유동 청산가치의 가격 괴리를 측정한다.
- Data notes: DART available_date PIT 유동자산·유동부채와 동월 Silver 시가총액을 사용하며 시가총액이 양수일 때만 계산한다.
