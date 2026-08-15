# cycle-0139-operating_coverage_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-014` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `299bdf764c5cdf8e`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_coverage_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

영업이익/유동부채의 12개월 변화가 큰 종목의 이후 순위가 높을 것이다.

## Mechanism

본업 현금창출력에 가까운 이익이 단기 의무보다 빨리 개선되면 차환위험이 줄어든다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 이익개선 신호 직교성이 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 12 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8668492186723166 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8416063222258543 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.005868108064018134 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.006046331025867077 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.1462500630164458 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.005868108064018134 |
| `ic_t_full` | 1.2511583019313024 |
| `ic_p_full` | 0.1078270151601461 |
| `ic_investable` | 0.006046331025867077 |
| `ic_std_investable` | 0.041342416551213165 |
| `rank_icir_investable` | 0.1462500630164458 |
| `ic_t_investable` | 1.2262965296710844 |
| `ic_p_investable` | 0.11239995112025589 |
| `ic_retention` | 1.0303714519065803 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.005868108064018134 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.006046331025867077 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.1462500630164458 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_roa_change_12m` | earnings | 0.828 | 63 |
| `operating_margin_change_12m` | earnings | 0.781 | 63 |
| `operating_income_growth_12m` | earnings | 0.758 | 63 |
| `operating_margin_acceleration_12m` | earnings | 0.584 | 51 |
| `operating_income_growth_acceleration_12m` | earnings | 0.566 | 51 |
| `pretax_income_growth_12m` | earnings | 0.560 | 63 |
| `net_profit_margin_change_12m` | earnings | 0.525 | 63 |
| `net_income_growth_12m` | earnings | 0.523 | 63 |
| `retained_earnings_growth_acceleration_12m` | quality | 0.418 | 63 |
| `pretax_income_growth_acceleration_12m` | earnings | 0.406 | 51 |
| `sales_growth_12m` | other | -0.376 | 63 |
| `net_income_growth_acceleration_12m` | earnings | 0.374 | 51 |
| `asset_turnover_change_12m` | quality | 0.347 | 63 |
| `sales_growth_acceleration_12m` | earnings | 0.338 | 51 |
| `sue` | earnings | 0.306 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: operating_income_to_current_liabilities — 차이: 충당력 수준이 아니라 12개월 개선폭을 측정한다.
- Data notes: DART available_date PIT 영업이익·양의 유동부채와 정확한 12개월 시차를 사용한다.
