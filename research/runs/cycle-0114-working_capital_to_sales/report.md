# cycle-0114-working_capital_to_sales

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-011` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `85cadc517d7da429`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/working_capital_to_sales.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

(유동자산-유동부채)/TTM 매출이 높은 종목의 이후 순위가 높을 것이다.

## Mechanism

매출 규모 대비 운전자본 여유는 재고·채권과 단기부채 충격의 흡수력을 나타낸다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 유동성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9204216033471267 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.903684431682891 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.0019523673682305444 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0017283209416775146 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.027387076280976978 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0019523673682305444 |
| `ic_t_full` | 0.2814314094042886 |
| `ic_p_full` | 0.3896660140297735 |
| `ic_investable` | 0.0017283209416775146 |
| `ic_std_investable` | 0.06310717230075427 |
| `rank_icir_investable` | 0.027387076280976978 |
| `ic_t_investable` | 0.22974835281231984 |
| `ic_p_investable` | 0.4095279918534996 |
| `ic_retention` | 0.8852437147850479 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0019523673682305444 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0017283209416775146 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.027387076280976978 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_ratio` | quality | 0.926 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.916 | 63 |
| `net_working_capital_to_assets` | quality | 0.911 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.846 | 63 |
| `noncurrent_assets_to_equity` | other | 0.819 | 63 |
| `equity_to_current_liabilities` | quality | 0.729 | 63 |
| `qual_lev` | quality | 0.712 | 63 |
| `current_liabilities_to_assets` | quality | 0.685 | 63 |
| `current_asset_turnover` | quality | -0.683 | 63 |
| `revenue_to_current_assets` | quality | -0.683 | 63 |
| `net_working_capital_yield` | value | 0.671 | 63 |
| `current_liabilities_yield` | value | 0.655 | 63 |
| `market_leverage` | other | -0.641 | 63 |
| `revenue_to_equity` | quality | -0.597 | 63 |
| `current_assets_to_noncurrent_assets` | other | 0.556 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: net_working_capital_to_assets — 차이: 자산 규모가 아니라 영업 매출로 완충력을 정규화한다.
- Data notes: DART available_date PIT 유동자산·유동부채와 양의 TTM 매출만 사용한다.
