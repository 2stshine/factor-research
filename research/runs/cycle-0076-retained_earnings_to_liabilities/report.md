# cycle-0076-retained_earnings_to_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-004` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `50d2f8c1276ed5cf`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_to_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT retained_earnings/total_liabilities가 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

누적 내부자본이 부채보다 충분하면 외부조달 의존과 파산비용이 낮고 이익의 역사적 지속성을 나타낼 수 있다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9598283603209448 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.95575739893969 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.05491723902253785 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05706512253237996 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.9351000662827912 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.29288858090675324 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.03735741075088903 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.8272243275832745 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05491723902253785 |
| `ic_t_full` | 7.0280027790834945 |
| `ic_p_full` | 1.0371084618137803e-09 |
| `ic_investable` | 0.05706512253237996 |
| `ic_std_investable` | 0.06102568547473767 |
| `rank_icir_investable` | 0.9351000662827912 |
| `ic_t_investable` | 7.467073420196565 |
| `ic_p_investable` | 1.8201919521521437e-10 |
| `ic_retention` | 1.0391112799563835 |
| `neutral_ic` | 0.03735741075088903 |
| `neutral_ic_t` | 4.930278348473741 |
| `neutral_ic_p` | 3.3161229513162447e-06 |
| `neutral_ic_retention` | 0.6546452385113454 |
| `n_trials` | 89 |
| `max_gold_signal_corr` | 0.8272243275832745 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.8272243275832745 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `retained_earnings_to_assets` | quality | 0.962 | 63 |
| `retained_earnings_to_equity` | quality | 0.827 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.767 | 63 |
| `pretax_income_to_liabilities` | quality | 0.645 | 63 |
| `net_income_to_liabilities` | quality | 0.638 | 63 |
| `solvent_value` | value | 0.610 | 63 |
| `quality_stability` | quality | 0.605 | 63 |
| `qual_lev` | quality | 0.600 | 63 |
| `revenue_to_total_liabilities` | quality | 0.589 | 63 |
| `operating_income_to_liabilities` | quality | 0.575 | 63 |
| `pretax_profit_margin` | quality | 0.569 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.563 | 63 |
| `net_profit_margin` | quality | 0.561 | 63 |
| `paid_in_capital_ratio` | quality | 0.559 | 63 |
| `pretax_roa` | quality | 0.557 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: retained_earnings_to_assets — 차이: 자산 내 유보 비중이 아니라 채권자 청구권을 덮는 누적 유보 규모다.
- Data notes: DART available_date PIT 이익잉여금과 양의 총부채를 사용하며 음의 유보는 보존한다.
