# cycle-0101-revenue_to_noncurrent_assets

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-009` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `29eedb3de737a6f9`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/revenue_to_noncurrent_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT revenue_ttm/noncurrent_assets가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

회수기간이 긴 자산 한 단위가 만드는 매출이 많으면 고정비와 자본집약 위험을 흡수할 여력이 크다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전·수익성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9237335454608036 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9063064334192229 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.030262984032990763 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0305599445033665 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5127548908687894 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3466316698798254 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03254050747041802 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.34057568418161555 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.030262984032990763 |
| `ic_t_full` | 4.597257909108747 |
| `ic_p_full` | 1.1031891875079012e-05 |
| `ic_investable` | 0.0305599445033665 |
| `ic_std_investable` | 0.05959951830315468 |
| `rank_icir_investable` | 0.5127548908687894 |
| `ic_t_investable` | 4.70585134066536 |
| `ic_p_investable` | 7.481522371245735e-06 |
| `ic_retention` | 1.0098126632209175 |
| `neutral_ic` | 0.03254050747041802 |
| `neutral_ic_t` | 5.003651006352988 |
| `neutral_ic_p` | 2.5339376188087618e-06 |
| `neutral_ic_retention` | 1.0648091153056034 |
| `n_trials` | 114 |
| `max_gold_signal_corr` | 0.34057568418161555 |
| `gold_signal_comparison_months` | {'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `asset_turnover` | quality | 0.837 | 63 |
| `revenue_to_equity` | quality | 0.667 | 63 |
| `noncurrent_asset_share` | other | 0.652 | 63 |
| `current_assets_to_assets` | quality | 0.637 | 63 |
| `revenue_to_total_liabilities` | quality | 0.587 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.565 | 63 |
| `current_assets_to_equity` | quality | 0.562 | 63 |
| `quality_stability` | quality | 0.471 | 63 |
| `net_margin_volatility_36m` | quality | 0.455 | 52 |
| `pretax_margin_volatility_36m` | quality | 0.449 | 52 |
| `value_sp` | value | 0.434 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.423 | 63 |
| `noncurrent_assets_to_equity` | other | 0.369 | 63 |
| `operating_return_on_capital_employed` | quality | 0.369 | 63 |
| `operating_income_to_noncurrent_liabilities` | quality | 0.358 | 63 |

## Expected relationship and data notes

- Expected relationship: operating_income_to_noncurrent_assets와 관련되지만 이익률을 섞지 않은 매출 생산성이다.
- Data notes: DART available_date PIT 매출과 양의 비유동자산만 사용한다.
