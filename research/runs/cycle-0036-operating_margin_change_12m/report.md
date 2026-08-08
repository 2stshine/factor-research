# cycle-0036-operating_margin_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `9700ff68f8b1878b`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_margin_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 TTM 영업이익률이 정확히 12개월 전보다 많이 개선된 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

마진 확장은 단순 매출 성장과 달리 판매 한 단위에서 남기는 영업이익의 개선을 측정한다. 영업 레버리지, 구조조정 또는 가격결정력의 지속성을 투자자가 후속 공시에 걸쳐 반영하면 수익률 예측력이 생길 수 있다.

## Pre-registered falsification

자동 gate의 양의 방향이 실패하거나 investable·기간·중립화 강건성이 없고, 또는 qual_opm·operating_roa_change_12m·asset_turnover_change_12m와 중복되면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.8640118219343595 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8045719000045206 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.01931214585366388 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.02056111646317344 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5023618479725254 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.01931214585366388 |
| `ic_t_full` | 4.797712040144744 |
| `ic_p_full` | 2.8395522727437495e-06 |
| `ic_investable` | 0.02056111646317344 |
| `ic_std_investable` | 0.040928897260322894 |
| `rank_icir_investable` | 0.5023618479725254 |
| `ic_t_investable` | 4.586465847628621 |
| `ic_p_investable` | 6.605844583958902e-06 |
| `ic_retention` | 1.06467280326969 |
| `months` | 74 |
| `turnover` | 171.59648771060142 |
| `gross` | 0.9514286573809752 |
| `cost` | 0.7827120308204927 |
| `net` | 0.16871662656048267 |
| `net_ir` | 0.05136560256858089 |
| `hac_t` | 0.15103548905955605 |
| `hac_pvalue` | 0.44018215579941 |
| `missing_return_rate` | 0.001008182692082249 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.01931214585366388 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.02056111646317344 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_roa_change_12m` | earnings | 0.876 | 101 |
| `sales_growth_12m` | other | -0.458 | 101 |
| `sue` | earnings | 0.363 | 101 |
| `earnings_change_to_assets` | earnings | 0.354 | 101 |
| `asset_turnover_change_12m` | quality | 0.333 | 101 |
| `operating_return_on_capital_employed` | quality | 0.319 | 101 |
| `operating_roa` | quality | 0.305 | 101 |
| `qual_opm` | quality | 0.292 | 101 |
| `qual_roe` | quality | 0.249 | 101 |
| `net_roa` | quality | 0.236 | 101 |
| `net_profit_margin` | quality | 0.215 | 101 |
| `value_ep` | value | 0.206 | 101 |
| `working_capital_accruals_12m` | quality | -0.196 | 101 |
| `mom_12_1` | momentum | 0.193 | 101 |
| `quality_stability` | quality | 0.162 | 101 |

## Expected relationship and data notes

- Expected relationship: 영업이익률 수준 및 operating_roa_change_12m와 양의 관계를 예상하지만, 매출 한 단위당 이익의 12개월 변화만 측정하므로 수준·자산효율 변화와 정의상 구별된다.
- Data notes: DART available_date 순으로 재생한 operating_income_ttm과 revenue_ttm을 사용한다. 현재·과거 매출이 양수이고 정확히 12개월 전 관측이 있을 때 정의한다. 음의 영업마진은 보존하며 M&A·사업 재분류가 불연속을 만들 수 있다.
