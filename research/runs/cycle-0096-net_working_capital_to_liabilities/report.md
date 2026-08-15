# cycle-0096-net_working_capital_to_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-008` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `2314b9f8f2ead59a`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_working_capital_to_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT (current_assets-current_liabilities)/total_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

유동자산에서 단기 의무를 뺀 잔여 완충력이 전체 채무 대비 크면 차환 충격의 하방이 줄어든다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 current_ratio·solvency 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9609144937623816 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9569640847388851 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.013173042566540753 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.013043983623280435 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.21700900448055427 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.013173042566540753 |
| `ic_t_full` | 1.965184671531911 |
| `ic_p_full` | 0.026975473875671382 |
| `ic_investable` | 0.013043983623280435 |
| `ic_std_investable` | 0.0601080294087487 |
| `rank_icir_investable` | 0.21700900448055427 |
| `ic_t_investable` | 1.780305717031424 |
| `ic_p_investable` | 0.04000306818866861 |
| `ic_retention` | 0.9902027991932459 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.013173042566540753 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.013043983623280435 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_ratio` | quality | 0.980 | 63 |
| `net_working_capital_to_assets` | quality | 0.963 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.962 | 63 |
| `noncurrent_assets_to_equity` | other | 0.898 | 63 |
| `qual_lev` | quality | 0.832 | 63 |
| `current_liabilities_to_assets` | quality | 0.747 | 63 |
| `net_working_capital_yield` | value | 0.710 | 63 |
| `market_leverage` | other | -0.695 | 63 |
| `revenue_to_total_liabilities` | quality | 0.624 | 63 |
| `noncurrent_liabilities_to_equity` | other | 0.622 | 63 |
| `current_assets_to_assets` | quality | 0.585 | 63 |
| `noncurrent_asset_share` | other | 0.572 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.533 | 63 |
| `solvent_value` | value | 0.514 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.490 | 63 |

## Expected relationship and data notes

- Expected relationship: net_working_capital_to_assets와 관련되지만 채무 상환범위에 초점을 둔다.
- Data notes: DART available_date PIT 유동자산·유동부채·양의 총부채만 사용한다.
