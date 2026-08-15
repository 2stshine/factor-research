# cycle-0060-operating_income_to_noncurrent_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `78eae3fe699e6c63`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_income_to_noncurrent_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 operating_income_ttm/noncurrent_assets가 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

비유동자산은 장기간 자본을 묶는 생산설비·투자자산의 기반이다. 같은 장기자산으로 더 많은 영업이익을 만드는 기업은 자본집약 위험을 덜 부담하며 시장이 이 효율의 지속성을 과소평가할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9330651144646969 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9148285918006255 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.04805233782073136 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.049810761267819366 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7038821387433222 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.27408324375933535 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.04986333208001814 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.9023971737228575 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.04805233782073136 |
| `ic_t_full` | 6.408822698609974 |
| `ic_p_full` | 1.1890706738661639e-08 |
| `ic_investable` | 0.049810761267819366 |
| `ic_std_investable` | 0.07076576961698323 |
| `rank_icir_investable` | 0.7038821387433222 |
| `ic_t_investable` | 6.432036513635543 |
| `ic_p_investable` | 1.0857032230456417e-08 |
| `ic_retention` | 1.0365939208545514 |
| `months` | 48 |
| `turnover` | 95.47415825382556 |
| `gross` | 2.2294700065473654 |
| `cost` | 0.4698463061665905 |
| `net` | 1.7596237003807753 |
| `net_ir` | 0.34875059470897296 |
| `hac_t` | 0.7349783565188613 |
| `hac_pvalue` | 0.23300217150540403 |
| `missing_return_rate` | 0.000592955686445033 |
| `neutral_ic` | 0.04986333208001814 |
| `neutral_ic_t` | 6.297867741399377 |
| `neutral_ic_p` | 1.8351780386213696e-08 |
| `neutral_ic_retention` | 1.0010554107357668 |
| `n_trials` | 74 |
| `max_gold_signal_corr` | 0.9023971737228575 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'operating_income_to_current_liabilities': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.9023971737228575 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_roa` | quality | 0.966 | 63 |
| `operating_return_on_capital_employed` | quality | 0.958 | 63 |
| `operating_income_to_liabilities` | quality | 0.924 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.902 | 63 |
| `qual_opm` | quality | 0.889 | 63 |
| `pretax_roa` | quality | 0.850 | 63 |
| `net_roa` | quality | 0.826 | 63 |
| `qual_roe` | quality | 0.815 | 63 |
| `operating_earnings_yield` | value | 0.783 | 63 |
| `pretax_profit_margin` | quality | 0.774 | 63 |
| `net_profit_margin` | quality | 0.756 | 63 |
| `quality_stability` | quality | 0.726 | 63 |
| `value_ep` | value | 0.687 | 63 |
| `retained_earnings_to_assets` | quality | 0.466 | 63 |
| `equity_growth_12m` | other | -0.455 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: operating_roa — 차이: 유동자산을 포함한 총자산 수익성이 아니라 회수기간이 긴 비유동자산의 본업 생산성만 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 noncurrent_assets만 사용한다. 비유동자산이 양수인 관측에서 정의하고 영업손실은 유지한다.
