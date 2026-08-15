# cycle-0102-short_term_reversal_3m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-009` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `bb5c9a621d0bd540`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/short_term_reversal_3m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver 분할조정 가격의 최근 3개월 누적수익률이 낮은 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

일시적 주문 불균형과 투자자 과잉반응은 수개월 내 평균회귀할 수 있으며, 최근 패자에 유동성 공급 보상을 제공한다.

## Pre-registered falsification

사전등록한 음의 방향, 투자 가능 IC, 종착수익 스트레스, 강건성, BY, 기존 반전·저위험 신호 직교성 또는 봉인 OOS가 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 3 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9999541070376857 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 1.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.06181969443887339 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.06299892166110042 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5470449342986707 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3092376953274988 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03221843280862374 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.3158983064306463 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.06181969443887339 |
| `ic_t_full` | 5.194061934778372 |
| `ic_p_full` | 1.252656624988201e-06 |
| `ic_investable` | 0.06299892166110042 |
| `ic_std_investable` | 0.11516224301001357 |
| `rank_icir_investable` | 0.5470449342986707 |
| `ic_t_investable` | 5.608887302692091 |
| `ic_p_investable` | 2.624774325153782e-07 |
| `ic_retention` | 1.0190752677270678 |
| `neutral_ic` | 0.03221843280862374 |
| `neutral_ic_t` | 2.87986668991413 |
| `neutral_ic_p` | 0.0027405772565181476 |
| `neutral_ic_retention` | 0.5114124489612887 |
| `n_trials` | 114 |
| `max_gold_signal_corr` | 0.3158983064306463 |
| `gold_signal_comparison_months` | {'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `high_12m_proximity` | momentum | -0.645 | 63 |
| `high_52w_price_proximity` | momentum | -0.580 | 63 |
| `rev_1m` | momentum | 0.504 | 63 |
| `medium_term_momentum_6_2` | momentum | -0.438 | 63 |
| `book_to_market_change_12m` | value | 0.322 | 63 |
| `positive_return_share_12m` | momentum | -0.319 | 63 |
| `max_daily_return_1m` | other | 0.319 | 63 |
| `downside_vol_12m` | other | -0.266 | 63 |
| `mom_12_1` | momentum | -0.256 | 63 |
| `market_leverage_change_12m` | other | -0.251 | 63 |
| `trading_turnover_20d` | other | 0.245 | 63 |
| `amihud_illiquidity_1m` | other | 0.157 | 63 |
| `sue` | earnings | -0.127 | 63 |
| `small_value` | value | 0.122 | 63 |
| `earnings_change_to_assets` | earnings | -0.117 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: rev_1m — 차이: 한 달 미시구조 반전이 아니라 정확한 3개월 누적 과잉반응의 되돌림을 측정한다.
- Data notes: Silver PIT adj_close만 사용하고 정확히 3개월 전 양의 가격과 달력 간격이 있는 관측에서만 누적 가격수익을 계산한다.
