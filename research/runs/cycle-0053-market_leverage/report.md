# cycle-0053-market_leverage

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260811-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `34e619cb846843cc`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/market_leverage.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

공시시점에 사용 가능했던 총부채를 월말 시가총액으로 나눈 값이 높은 종목은 낮은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

부채가 고정적인 선순위 청구권을 만들기 때문에 기업가치 변화가 주주가치에 더 크게 전달될 수 있다. 투자자가 이 재무위험을 완전히 가격에 반영한다면 높은 시장 레버리지에 기대수익 보상이 나타날 수 있다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성·커버리지·투자가능 IC·Rank ICIR·기간 및 중립화 강건성·campaign BY를 통과하지 못하거나 book leverage·가치·규모 신호와 중복되면 독립적인 시장 레버리지 가설을 기각한다. 봉인 OOS는 이번 discovery에서 열지 않는다.

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
| T1.1 | 전체 커버리지 | Y | 0.9557011078522256 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9495937290741797 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | Y | 0.0464460208283708 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04755360791896933 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.4699045198035168 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.44993765419137854 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.029702391136432808 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.09919118082232882 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0464460208283708 |
| `ic_t_full` | 3.3944234817876215 |
| `ic_p_full` | 0.0006069160433591354 |
| `ic_investable` | 0.04755360791896933 |
| `ic_std_investable` | 0.10119844758857209 |
| `rank_icir_investable` | 0.4699045198035168 |
| `ic_t_investable` | 3.3538469694421345 |
| `ic_p_investable` | 0.0006870459365388319 |
| `ic_retention` | 1.0238467595467722 |
| `neutral_ic` | 0.029702391136432808 |
| `neutral_ic_t` | 2.654277211883393 |
| `neutral_ic_p` | 0.005061106664703184 |
| `neutral_ic_retention` | 0.6246085720150879 |
| `n_trials` | 63 |
| `max_gold_signal_corr` | 0.09919118082232882 |
| `gold_signal_comparison_months` | {'max_daily_return_1m': 42, 'net_equity_issuance_price_adjusted_12m': 42, 'operating_income_to_liabilities': 41, 'realized_volatility_252d': 42} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `value_sp` | value | 0.812 | 63 |
| `qual_lev` | quality | -0.738 | 63 |
| `current_ratio` | quality | -0.676 | 63 |
| `value_bp` | value | 0.633 | 63 |
| `net_working_capital_to_assets` | quality | -0.627 | 63 |
| `defensive_value` | value | 0.482 | 63 |
| `small_value` | value | 0.480 | 63 |
| `defensive_small_value` | value | 0.450 | 63 |
| `noncurrent_asset_encumbrance` | quality | -0.439 | 63 |
| `earnings_confirmed_small_value` | earnings | 0.402 | 63 |
| `profitable_small_value` | quality | 0.379 | 63 |
| `asset_turnover` | quality | 0.263 | 63 |
| `noncurrent_asset_share` | other | -0.256 | 63 |
| `operating_roa_volatility_36m` | quality | 0.247 | 52 |
| `posttax_income_conversion` | quality | -0.236 | 63 |

## Expected relationship and data notes

- Expected relationship: 분자에 총부채를 쓰므로 qual_lev와 양의 관계가 예상되고, 시가총액이 분모라 size 및 value 계열과도 관계가 예상된다. 다만 장부자본 대신 시장가치 자기자본을 쓰므로 정의상 동일하지 않으며 실측 중복도를 별도로 판정한다.
- Data notes: Silver PIT의 total_liabilities를 Bhandari가 말한 noncommon-equity liabilities의 한국 재무제표 대응값으로 사용하고 같은 월말의 양의 market_cap으로 나눈다. 총부채가 음수인 관측과 시가총액이 0 이하인 관측은 결측 처리한다. 이자부채만을 뜻하는 net-debt/market-equity 팩터는 아니며, 그 정의에는 차입금·현금 세부 데이터가 더 필요하다.
