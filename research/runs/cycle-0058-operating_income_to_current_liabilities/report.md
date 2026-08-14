# cycle-0058-operating_income_to_current_liabilities

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260814-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `eaf7784cd83b4082`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_income_to_current_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 operating_income_ttm/current_liabilities가 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

유동부채는 영업주기 안에 상환하거나 차환해야 하는 의무다. 핵심 영업이익으로 이를 충분히 덮는 기업은 단기 유동성 충격과 비싼 차환에 덜 노출되며, 시장이 이 회복력을 과소평가하면 향후 상대수익이 높을 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9338758901322483 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9158311986690257 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.048840343824536614 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05047393561067764 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7138639846295586 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.27612555922386667 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.045093514405316615 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.048840343824536614 |
| `ic_t_full` | 6.930368941622186 |
| `ic_p_full` | 1.5258849220149939e-09 |
| `ic_investable` | 0.05047393561067764 |
| `ic_std_investable` | 0.07070525575942845 |
| `rank_icir_investable` | 0.7138639846295586 |
| `ic_t_investable` | 6.615803407384614 |
| `ic_p_investable` | 5.276370567203163e-09 |
| `ic_retention` | 1.0334475898042375 |
| `months` | 46 |
| `turnover` | 98.75905980737893 |
| `gross` | 1.0196818482807795 |
| `cost` | 0.485789616182058 |
| `net` | 0.5338922320987214 |
| `net_ir` | 0.10333320596713537 |
| `hac_t` | 0.23553389054847054 |
| `hac_pvalue` | 0.40743151018613305 |
| `missing_return_rate` | 0.000672016444637704 |
| `neutral_ic` | 0.045093514405316615 |
| `neutral_ic_t` | 5.962462902723987 |
| `neutral_ic_p` | 6.757178135700247e-08 |
| `neutral_ic_retention` | 0.893401987773214 |
| `n_trials` | 69 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_income_to_liabilities` | quality | 0.983 | 63 |
| `qual_opm` | quality | 0.931 | 63 |
| `operating_roa` | quality | 0.931 | 63 |
| `operating_return_on_capital_employed` | quality | 0.864 | 63 |
| `pretax_roa` | quality | 0.848 | 63 |
| `net_roa` | quality | 0.828 | 63 |
| `net_profit_margin` | quality | 0.812 | 63 |
| `qual_roe` | quality | 0.765 | 63 |
| `quality_stability` | quality | 0.743 | 63 |
| `operating_earnings_yield` | value | 0.731 | 63 |
| `value_ep` | value | 0.671 | 63 |
| `retained_earnings_to_assets` | quality | 0.549 | 63 |
| `retained_earnings_to_equity` | quality | 0.469 | 63 |
| `equity_growth_12m` | other | -0.412 | 63 |
| `paid_in_capital_ratio` | quality | 0.410 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: operating_income_to_liabilities — 차이: 전체 부채의 장기 상환능력이 아니라 1년 안에 도래하는 유동부채에 대한 단기 영업 커버리지만 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 current_liabilities만 사용한다. 유동부채가 양수인 관측에서 정의하고 음의 영업이익은 유지한다. 금융업과 비금융업의 유동부채 성격 차이는 공통 강건성 gate에서 진단한다.
