# cycle-0092-book_to_market_change_12m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-007` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `e73b53f0ffaaf3c5`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/book_to_market_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

PIT 자기자본/시가총액 비율의 12개월 증가폭이 큰 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

시장가격 하락 또는 장부가치 개선에 대한 과잉·지연 반응은 가치 괴리를 만들고 이후 재평가로 해소될 수 있다.

## Pre-registered falsification

양의 방향, 투자 가능 IC, 강건성, BY, 기존 가치·반전 신호 직교성 또는 봉인 OOS가 실패하면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9456168396576385 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.936642366758301 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05852781219663613 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05891879863264305 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6593529327773753 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.35395117120176217 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.026222650297262565 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.22444454660646176 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05852781219663613 |
| `ic_t_full` | 5.54606782891946 |
| `ic_p_full` | 3.333020946718644e-07 |
| `ic_investable` | 0.05891879863264305 |
| `ic_std_investable` | 0.08935851454313083 |
| `rank_icir_investable` | 0.6593529327773753 |
| `ic_t_investable` | 5.697390219538502 |
| `ic_p_investable` | 1.8724423989090036e-07 |
| `ic_retention` | 1.0066803528328263 |
| `neutral_ic` | 0.026222650297262565 |
| `neutral_ic_t` | 3.0389793735912622 |
| `neutral_ic_p` | 0.0017463912876539618 |
| `neutral_ic_retention` | 0.44506423935694966 |
| `n_trials` | 104 |
| `max_gold_signal_corr` | 0.22444454660646176 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `mom_12_1` | momentum | -0.678 | 63 |
| `market_leverage_change_12m` | other | -0.612 | 63 |
| `defensive_value` | value | 0.489 | 63 |
| `value_bp` | value | 0.468 | 63 |
| `defensive_small_value` | value | 0.460 | 63 |
| `positive_return_share_12m` | momentum | -0.443 | 63 |
| `intermediate_momentum_12_7` | momentum | -0.427 | 63 |
| `max_monthly_return_12m` | other | 0.423 | 63 |
| `medium_term_momentum_6_2` | momentum | -0.413 | 63 |
| `high_12m_proximity` | momentum | -0.390 | 63 |
| `profitable_small_value` | quality | 0.366 | 63 |
| `solvent_value` | value | 0.352 | 63 |
| `small_value` | value | 0.352 | 63 |
| `high_52w_price_proximity` | momentum | -0.343 | 63 |
| `low_vol_12m` | other | 0.323 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: value_bp — 차이: 장부가치/시가총액의 절대 수준이 아니라 정확한 12개월 변화만 측정한다.
- Data notes: DART available_date PIT 자기자본과 동월 Silver 시가총액을 사용한다. 현재·12개월 전 시가총액이 양수이고 정확한 달력 간격이 있을 때만 계산한다.
