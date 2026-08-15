# cycle-0124-equity_to_noncurrent_liabilities

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `dbfa1a3f3bc862d3`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/equity_to_noncurrent_liabilities.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

자기자본/비유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

장기 채무를 흡수할 손실완충 자본이 크면 차환과 금리 충격에 견고하다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 레버리지 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.956332846358011 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9461054354358194 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.0008889864568851952 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0007237905352889784 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.01340334462887067 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0008889864568851952 |
| `ic_t_full` | 0.14224528540189194 |
| `ic_p_full` | 0.4436775233937888 |
| `ic_investable` | 0.0007237905352889784 |
| `ic_std_investable` | 0.054000740511434796 |
| `rank_icir_investable` | 0.01340334462887067 |
| `ic_t_investable` | 0.11123428376772573 |
| `ic_p_investable` | 0.4558978810012389 |
| `ic_retention` | 0.8141749851004193 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0008889864568851952 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0007237905352889784 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.01340334462887067 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `noncurrent_liabilities_to_equity` | other | 1.000 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.961 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.898 | 63 |
| `noncurrent_liabilities_yield` | value | 0.846 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.800 | 63 |
| `qual_lev` | quality | 0.761 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.753 | 63 |
| `noncurrent_assets_to_equity` | other | 0.720 | 63 |
| `current_liability_concentration` | quality | -0.683 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.621 | 63 |
| `market_leverage` | other | -0.609 | 63 |
| `retained_earnings_to_noncurrent_liabilities` | quality | 0.574 | 63 |
| `revenue_to_total_liabilities` | quality | 0.559 | 63 |
| `equity_to_current_liabilities` | quality | 0.541 | 63 |
| `net_working_capital_to_assets` | quality | 0.538 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: noncurrent_liabilities_to_equity — 차이: 부채 부담이 아니라 장기부채를 덮는 양의 자본 완충력으로 해석한다.
- Data notes: DART available_date PIT 자기자본과 양의 비유동부채만 사용한다.
