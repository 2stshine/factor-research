# cycle-0062-current_assets_to_total_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `35b5c72f04c6c4fa`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_assets_to_total_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 current_assets/total_liabilities가 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

유동자산은 영업주기 안에 현금화 가능한 완충재이고 총부채는 단기·장기 채무를 모두 담는다. 이 비율이 높으면 차환시장 경색에도 대응할 수 있어 부실 확률과 강제 자산매각 위험이 낮다.

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
| T1.1 | 전체 커버리지 | Y | 0.9610215773411147 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9569648550421535 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.010507513756274272 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.010330318789299357 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.17306709694167063 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.010507513756274272 |
| `ic_t_full` | 1.5756792747436141 |
| `ic_p_full` | 0.06013614760602129 |
| `ic_investable` | 0.010330318789299357 |
| `ic_std_investable` | 0.05968967511358336 |
| `rank_icir_investable` | 0.17306709694167063 |
| `ic_t_investable` | 1.4314842522967572 |
| `ic_p_investable` | 0.07869764919930884 |
| `ic_retention` | 0.9831363564126567 |
| `months` | 48 |
| `turnover` | 84.02414046218574 |
| `gross` | 1.5999753679907303 |
| `cost` | 0.41461222862445646 |
| `net` | 1.1853631393662734 |
| `net_ir` | 0.292816657614782 |
| `hac_t` | 0.6389132827855702 |
| `hac_pvalue` | 0.2629904679891093 |
| `missing_return_rate` | 0.000592955686445033 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.010507513756274272 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.010330318789299357 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_working_capital_to_assets` | quality | 0.917 | 63 |
| `current_ratio` | quality | 0.907 | 63 |
| `qual_lev` | quality | 0.823 | 63 |
| `market_leverage` | other | -0.693 | 63 |
| `revenue_to_total_liabilities` | quality | 0.667 | 63 |
| `noncurrent_asset_share` | other | 0.641 | 63 |
| `solvent_value` | value | 0.494 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.484 | 63 |
| `current_asset_turnover` | quality | -0.481 | 63 |
| `quality_stability` | quality | 0.439 | 63 |
| `retained_earnings_to_assets` | quality | 0.406 | 63 |
| `value_sp` | value | -0.342 | 63 |
| `operating_income_to_liabilities` | quality | 0.341 | 63 |
| `current_liability_concentration` | quality | -0.306 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.300 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: current_ratio — 차이: 유동부채만의 단기 지급능력이 아니라 유동자산이 장기부채까지 포함한 전체 채무를 얼마나 덮는지 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT current_assets와 total_liabilities만 사용한다. 총부채가 양수인 관측에서 정의하며 자산 유동성의 업종 차이는 공통 강건성 gate가 진단한다.
