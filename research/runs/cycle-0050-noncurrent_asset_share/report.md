# cycle-0050-noncurrent_asset_share

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260809-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `1ce4e1a937a3b221`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_asset_share.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

신호시점에 알려진 Silver PIT noncurrent_assets/total_assets가 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

높은 비유동자산 비중은 수요 충격 때 자산을 빠르게 재배치하기 어렵고 고정비·감손 위험을 키울 수 있다. 반대로 자산구조가 덜 경직된 기업의 적응력이 가격에 늦게 반영되면 낮은 비유동자산 비중이 양의 미래수익 신호가 될 수 있다.

## Pre-registered falsification

사전등록한 음의 방향이 무결성, 커버리지, 전체·투자가능 IC와 Rank ICIR, 기간·중립화 강건성, 다중검정, Gold SQL parity 또는 일회성 OOS 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9541966171755087 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9471027951265236 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | N | 0.0022624682996594332 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0015686419612789384 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.02936207539321066 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0022624682996594332 |
| `ic_t_full` | 0.4975797859048631 |
| `ic_p_full` | 0.31028461763652104 |
| `ic_investable` | 0.0015686419612789384 |
| `ic_std_investable` | 0.05342408328675747 |
| `rank_icir_investable` | 0.02936207539321066 |
| `ic_t_investable` | 0.3304748170642958 |
| `ic_p_investable` | 0.3710868103584634 |
| `ic_retention` | 0.693332128240234 |
| `months` | 45 |
| `turnover` | 96.48921701603953 |
| `gross` | 0.2356364901554243 |
| `cost` | 0.4748890855739784 |
| `net` | -0.23925259541855395 |
| `net_ir` | -0.06668335764198574 |
| `hac_t` | -0.11673646655577603 |
| `hac_pvalue` | 0.5461999459849567 |
| `missing_return_rate` | 0.0009813542688910696 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0022624682996594332 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0015686419612789384 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.02936207539321066 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_working_capital_to_assets` | quality | 0.703 | 63 |
| `current_ratio` | quality | 0.526 | 63 |
| `current_liability_concentration` | quality | -0.357 | 63 |
| `working_capital_accruals_12m` | quality | -0.229 | 63 |
| `asset_turnover` | quality | 0.211 | 63 |
| `quality_stability` | quality | 0.192 | 63 |
| `value_bp` | value | -0.190 | 63 |
| `qual_lev` | quality | 0.173 | 63 |
| `defensive_value` | value | -0.167 | 63 |
| `operating_roa_volatility_36m` | quality | -0.152 | 52 |
| `operating_return_on_capital_employed` | quality | 0.147 | 63 |
| `operating_income_to_liabilities` | quality | 0.138 | 63 |
| `operating_roa` | quality | 0.126 | 63 |
| `net_roa` | quality | 0.114 | 63 |
| `qual_roe` | quality | 0.108 | 63 |

## Expected relationship and data notes

- Expected relationship: asset_turnover와 음의 관계, noncurrent_asset_encumbrance와 일부 관계를 예상한다. 그러나 부채 청구나 매출 효율이 아니라 자산의 유동·비유동 구성 자체를 측정하며, 기존 팩터와 고상관이면 새 정보로 보지 않는다.
- Data notes: DART available_date 순으로 재생한 noncurrent_assets와 total_assets만 사용한다. 총자산이 양수이고 비유동자산이 음수가 아닌 관측에서 정의한다. 업종별 자산구조 차이가 크므로 사후 업종 제외 없이 시장·유동성·규모 중립화 강건성을 그대로 적용한다.
