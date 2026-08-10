# cycle-0049-operating_income_to_liabilities

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260809-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `5ff8c69343b28a3f`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_income_to_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

신호시점에 알려진 Silver PIT operating_income_ttm/total_liabilities가 높은 종목은 낮은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

영업이익은 기업의 반복 영업이 채권자·거래상대방에 대한 총의무를 지탱하는 완충력이다. 이 완충력이 높으면 불리한 차환, 강제 자산매각 또는 주식 희석 가능성이 낮고, 시장이 그 차이를 천천히 반영하면 횡단면 수익률을 예측할 수 있다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성, 커버리지, 전체·투자가능 IC와 Rank ICIR, 기간·중립화 강건성, 다중검정, Gold SQL parity 또는 일회성 OOS 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9287570475510235 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9098895231015566 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | Y | 0.049009232373271046 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.050723931543203295 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7072032682424024 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2720979895318606 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.045683214095992276 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.049009232373271046 |
| `ic_t_full` | 6.633409163985266 |
| `ic_p_full` | 4.923245937863868e-09 |
| `ic_investable` | 0.050723931543203295 |
| `ic_std_investable` | 0.0717246848551286 |
| `rank_icir_investable` | 0.7072032682424024 |
| `ic_t_investable` | 6.4329692159767164 |
| `ic_p_investable` | 1.0817421593666897e-08 |
| `ic_retention` | 1.0349872684573493 |
| `months` | 47 |
| `turnover` | 92.43156645809884 |
| `gross` | 2.6373292937799904 |
| `cost` | 0.4546309207280031 |
| `net` | 2.1826983730519873 |
| `net_ir` | 0.41157684228422997 |
| `hac_t` | 0.8836553132887742 |
| `hac_pvalue` | 0.19073874354218273 |
| `missing_return_rate` | 0.0006280667320902846 |
| `neutral_ic` | 0.045683214095992276 |
| `neutral_ic_t` | 5.837623456308641 |
| `neutral_ic_p` | 1.0935021738048171e-07 |
| `neutral_ic_retention` | 0.9006244726334419 |
| `n_trials` | 8 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_roa` | quality | 0.944 | 63 |
| `qual_opm` | quality | 0.920 | 63 |
| `operating_return_on_capital_employed` | quality | 0.887 | 63 |
| `net_roa` | quality | 0.839 | 63 |
| `net_profit_margin` | quality | 0.806 | 63 |
| `qual_roe` | quality | 0.773 | 63 |
| `quality_stability` | quality | 0.773 | 63 |
| `value_ep` | value | 0.672 | 63 |
| `retained_earnings_to_assets` | quality | 0.558 | 63 |
| `dividend_event_frequency_ttm` | quality | 0.467 | 63 |
| `dividend_yield_ttm` | value | 0.444 | 63 |
| `net_equity_issuance_12m` | other | 0.416 | 63 |
| `equity_growth_12m` | other | -0.415 | 63 |
| `paid_in_capital_ratio` | quality | 0.402 | 63 |
| `profitable_small_value` | quality | 0.392 | 63 |

## Expected relationship and data notes

- Expected relationship: operating_roa 및 operating_return_on_capital_employed와 양의 관계, qual_lev와 음의 관계를 예상한다. 다만 분모가 자산이나 자기자본이 아닌 총부채이므로 어느 하나의 단순 재표현으로 판정될 만큼 중복되면 독립 후보로 인정하지 않는다.
- Data notes: DART available_date 순으로 재생한 operating_income_ttm과 total_liabilities만 사용한다. 총부채가 양수일 때 정의하며 적자 영업이익은 삭제하지 않는다. 이자비용이 없어 정식 이자보상배율이 아니라 총의무 대비 영업 완충력이다.
