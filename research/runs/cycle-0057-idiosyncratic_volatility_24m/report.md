# cycle-0057-idiosyncratic_volatility_24m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260814-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `af24645c3a81a842`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/idiosyncratic_volatility_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT 분할조정 가격의 최근 24개월 월수익률에서 동월 시장수익으로 설명되지 않는 잔차변동성이 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

분산되지 않은 투자자와 복권형 상승을 선호하는 투자자가 고유위험이 큰 종목에 높은 가격을 지불하면 그 종목의 기대수익률이 낮아질 수 있다. 시장 공통위험을 제거한 잔차분산은 이 수요를 총변동성과 분리해 측정한다.

## Pre-registered falsification

사전등록한 음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 못하거나 기존 저변동성 신호와 중복되면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 24 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9780631640137984 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9717577132282306 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.09671563544189589 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.10103740261944796 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.8868660243140166 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3699332969620814 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.05040676513962411 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.09671563544189589 |
| `ic_t_full` | 8.743929004466127 |
| `ic_p_full` | 1.1669127728985716e-12 |
| `ic_investable` | 0.10103740261944796 |
| `ic_std_investable` | 0.11392634270503207 |
| `rank_icir_investable` | 0.8868660243140166 |
| `ic_t_investable` | 8.796273000816285 |
| `ic_p_investable` | 9.501071990878842e-13 |
| `ic_retention` | 1.0446852999290737 |
| `months` | 42 |
| `turnover` | 123.0504256020382 |
| `gross` | 1.4287177803491269 |
| `cost` | 0.6011062665421489 |
| `net` | 0.8276115138069788 |
| `net_ir` | 0.10731867043327423 |
| `hac_t` | 0.22316350882422115 |
| `hac_pvalue` | 0.41225820071837116 |
| `missing_return_rate` | 0.0009882594774083884 |
| `neutral_ic` | 0.05040676513962411 |
| `neutral_ic_t` | 5.930040326140333 |
| `neutral_ic_p` | 7.658686060727946e-08 |
| `neutral_ic_retention` | 0.49889213135732047 |
| `n_trials` | 69 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `low_vol_12m` | other | 0.800 | 63 |
| `realized_volatility_252d` | other | 0.780 | 63 |
| `defensive_value` | value | 0.745 | 63 |
| `max_monthly_return_12m` | other | 0.708 | 63 |
| `downside_vol_12m` | other | 0.628 | 63 |
| `return_skewness_24m` | other | 0.601 | 63 |
| `defensive_small_value` | value | 0.561 | 63 |
| `trading_turnover_20d` | other | 0.552 | 63 |
| `quality_stability` | quality | 0.512 | 63 |
| `value_bp` | value | 0.451 | 63 |
| `return_kurtosis_24m` | other | 0.430 | 63 |
| `max_daily_return_1m` | other | 0.414 | 63 |
| `solvent_value` | value | 0.409 | 63 |
| `high_52w_price_proximity` | momentum | 0.404 | 63 |
| `retained_earnings_to_equity` | quality | 0.357 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: realized_volatility_252d — 차이: 총 일별 변동성이 아니라 PIT 시장별 월수익 요인을 제거한 24개월 고유변동성만 측정한다. market_beta_36m은 공분산의 기울기를 측정하므로 잔차분산과 다르다.
- Data notes: Silver PIT adj_close로 연속 월 가격수익률을 만들고 전월 market과 전월 market_cap으로 KOSPI·KOSDAQ별 동월 가치가중 수익률을 구성한다. 24개월 달력창에서 최소 18개 동일월 관측을 요구하고 결측을 채우지 않는다. 공식 지수나 일별 잔차변동성이 아니라 월별 내부 벤치마크를 사용한다는 한계가 있다.
