# cycle-0061-retained_earnings_to_capital_stock

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ac476a86c1174da7`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_to_capital_stock.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 retained_earnings/capital_stock이 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

자본금은 주주의 납입 기반이고 이익잉여금은 사업에서 누적한 내부자본이다. 내부자본이 납입자본보다 큰 기업은 장기간 이익을 재투자해 성장했을 가능성이 높고, 시장이 그 존속성과 자금조달 자립도를 과소평가할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9548336762557462 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9475105632980835 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05805778905848484 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0605188846422836 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7665364264572725 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.33986591836897634 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03916831675356224 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.8531185570258588 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05805778905848484 |
| `ic_t_full` | 6.945424498297854 |
| `ic_p_full` | 1.4377186586839921e-09 |
| `ic_investable` | 0.0605188846422836 |
| `ic_std_investable` | 0.07895108771540811 |
| `rank_icir_investable` | 0.7665364264572725 |
| `ic_t_investable` | 7.378511438753515 |
| `ic_p_investable` | 2.586277480545621e-10 |
| `ic_retention` | 1.0423904462038602 |
| `months` | 53 |
| `turnover` | 38.012327041637946 |
| `gross` | -1.9934448296862666 |
| `cost` | 0.1937132914287069 |
| `net` | -2.1871581211149738 |
| `net_ir` | -0.4684048525746822 |
| `hac_t` | -1.098294626884113 |
| `hac_pvalue` | 0.8614323322129713 |
| `missing_return_rate` | 0.0003953037909633553 |
| `neutral_ic` | 0.03916831675356224 |
| `neutral_ic_t` | 4.876017679732838 |
| `neutral_ic_p` | 4.042307396654859e-06 |
| `neutral_ic_retention` | 0.6472081728716452 |
| `n_trials` | 74 |
| `max_gold_signal_corr` | 0.8531185570258588 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'operating_income_to_current_liabilities': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.8531185570258588 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `paid_in_capital_ratio` | quality | 0.856 | 63 |
| `retained_earnings_to_equity` | quality | 0.853 | 63 |
| `retained_earnings_to_assets` | quality | 0.831 | 63 |
| `value_ep` | value | 0.535 | 63 |
| `pretax_roa` | quality | 0.533 | 63 |
| `pretax_profit_margin` | quality | 0.527 | 63 |
| `quality_stability` | quality | 0.519 | 63 |
| `net_roa` | quality | 0.518 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.512 | 63 |
| `net_profit_margin` | quality | 0.511 | 63 |
| `operating_income_to_liabilities` | quality | 0.501 | 63 |
| `qual_roe` | quality | 0.488 | 63 |
| `operating_earnings_yield` | value | 0.484 | 63 |
| `qual_opm` | quality | 0.482 | 63 |
| `operating_roa` | quality | 0.474 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: retained_earnings_to_equity — 차이: 기타포괄손익과 자본잉여금을 포함한 총자본 비중이 아니라 법정 납입자본 대비 누적 내부이익의 배율을 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT retained_earnings와 capital_stock만 사용한다. 자본금이 양수인 관측에서 정의하고 누적결손의 음수 이익잉여금은 유지한다.
