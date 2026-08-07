# cycle-0033-current_liability_concentration

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260806-001` / `epoch-002`
- OOS: **SEALED**
- Definition hash: `38c06f992e387d49`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.5.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_liability_concentration.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 유동부채/총부채 비율이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

전체 의무 중 1년 안에 결제해야 할 몫이 크면 차환과 운전자금 충격에 취약해 불리한 증자나 자산매각 가능성이 커진다. 시장이 이 만기 집중 위험을 충분히 반영하지 않으면 낮은 집중도의 기업이 이후 상대적으로 재평가될 수 있다.

## Pre-registered falsification

낮은 유동부채 집중 방향이 전체·투자 가능 IC, Rank ICIR, 기간·중립화 강건성을 통과하지 못하거나 current_ratio와 중복되면 별도의 부채 만기구조 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다.

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
| T1.1 | 전체 커버리지 | Y | 0.9619515174926001 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9494182910709673 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.006795915010556067 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.008308249926676243 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.21905471180627015 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.006795915010556067 |
| `ic_t_full` | 1.8271916200886011 |
| `ic_p_full` | 0.03534182167182838 |
| `ic_investable` | 0.008308249926676243 |
| `ic_std_investable` | 0.0379277389569414 |
| `rank_icir_investable` | 0.21905471180627015 |
| `ic_t_investable` | 2.367313773364785 |
| `ic_p_investable` | 0.00993112085667508 |
| `ic_retention` | 1.2225358783579654 |
| `months` | 75 |
| `turnover` | 112.31670387633197 |
| `gross` | 0.116745063045098 |
| `cost` | 0.5189247177919935 |
| `net` | -0.4021796547468956 |
| `net_ir` | -0.14313854481610833 |
| `hac_t` | -0.35088879725136474 |
| `hac_pvalue` | 0.6366656197350398 |
| `missing_return_rate` | 0.0006737448597913714 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.006795915010556067 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.008308249926676243 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `asset_turnover` | quality | -0.182 | 101 |
| `size` | size | -0.176 | 101 |
| `quality_stability` | quality | -0.131 | 101 |
| `operating_roa_volatility_36m` | quality | 0.124 | 90 |
| `qual_lev` | quality | -0.122 | 101 |
| `paid_in_capital_ratio` | quality | 0.091 | 101 |
| `trading_turnover_20d` | other | 0.086 | 101 |
| `liability_growth_12m` | other | -0.080 | 101 |
| `profitable_small_value` | quality | -0.078 | 101 |
| `working_capital_accruals_12m` | quality | -0.073 | 101 |
| `value_bp` | value | 0.073 | 101 |
| `earnings_confirmed_small_value` | earnings | -0.071 | 101 |
| `defensive_value` | value | 0.068 | 101 |
| `small_value` | value | -0.064 | 101 |
| `asset_growth_12m` | other | -0.054 | 101 |

## Expected relationship and data notes

- Expected relationship: current_ratio와 단기 재무위험이라는 개념을 공유하지만, 유동자산의 상환 능력이 아니라 총부채 안의 단기 의무 비중만 측정한다. qual_lev는 부채 총량, liability_growth_12m은 변화량을 보므로 구조적으로 구별된다.
- Data notes: DART available_date 순으로 재생한 Silver PIT current_liabilities와 total_liabilities를 사용하고 양의 총부채에서만 정의한다. 유동부채에는 단기차입금뿐 아니라 매입채무·선수금도 포함되므로 순수 차환위험으로 해석하지 않는다. PIT 업종 이력이 없어 업종별 정상구조를 통제하지 못하는 한계가 있다.
