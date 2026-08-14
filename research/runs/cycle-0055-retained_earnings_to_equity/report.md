# cycle-0055-retained_earnings_to_equity

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260814-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ede7286f5e5ca082`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_to_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 retained_earnings/total_equity가 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

이익잉여금은 외부 출자 없이 누적한 내부자본이다. 자기자본에서 그 비중이 높으면 장기간 이익을 축적하고 희석성 자금조달 의존을 낮춘 기업일 가능성이 높으며, 시장이 이 자본의 질과 생존력을 과소평가하면 이후 상대수익이 높을 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9575566586863904 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9539363448212752 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.060886849441899614 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0637771384452184 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.9194985653092674 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.33132485337693474 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.04390166651858735 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.060886849441899614 |
| `ic_t_full` | 7.316162919798104 |
| `ic_p_full` | 3.3117102829324825e-10 |
| `ic_investable` | 0.0637771384452184 |
| `ic_std_investable` | 0.06936078081184104 |
| `rank_icir_investable` | 0.9194985653092674 |
| `ic_t_investable` | 8.014658306750494 |
| `ic_p_investable` | 2.0752529312956006e-11 |
| `ic_retention` | 1.0474698400362594 |
| `months` | 51 |
| `turnover` | 41.31303283666122 |
| `gross` | -0.7375574735427195 |
| `cost` | 0.20976198518734757 |
| `net` | -0.9473194587300674 |
| `net_ir` | -0.24243855970354256 |
| `hac_t` | -0.4979680882425996 |
| `hac_pvalue` | 0.6896551040916857 |
| `missing_return_rate` | 0.0004348341700596909 |
| `neutral_ic` | 0.04390166651858735 |
| `neutral_ic_t` | 5.734335775116926 |
| `neutral_ic_p` | 1.6255583086623218e-07 |
| `neutral_ic_retention` | 0.6883605566012787 |
| `n_trials` | 69 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `retained_earnings_to_assets` | quality | 0.934 | 63 |
| `paid_in_capital_ratio` | quality | 0.592 | 63 |
| `pretax_roa` | quality | 0.520 | 63 |
| `quality_stability` | quality | 0.518 | 63 |
| `net_roa` | quality | 0.510 | 63 |
| `value_ep` | value | 0.498 | 63 |
| `net_profit_margin` | quality | 0.483 | 63 |
| `operating_income_to_liabilities` | quality | 0.478 | 63 |
| `qual_roe` | quality | 0.477 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.469 | 63 |
| `operating_roa` | quality | 0.453 | 63 |
| `operating_earnings_yield` | value | 0.439 | 63 |
| `qual_opm` | quality | 0.430 | 63 |
| `solvent_value` | value | 0.428 | 63 |
| `operating_return_on_capital_employed` | quality | 0.426 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: retained_earnings_to_assets — 차이: 자산 대비 누적 수익성이 아니라 자기자본이 내부이익과 외부출자 중 무엇으로 구성됐는지를 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT retained_earnings와 total_equity만 사용한다. 자기자본이 양수인 관측에서 정의하고 결손 누적의 음수 이익잉여금은 유지한다. 자사주·기타 포괄손익누계액도 총자본에 포함되므로 순수한 존속연령 지표는 아니다.
