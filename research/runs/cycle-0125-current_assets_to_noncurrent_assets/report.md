# cycle-0125-current_assets_to_noncurrent_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ce9ed307736e8971`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_assets_to_noncurrent_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

유동자산/비유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.

## Mechanism

회수 가능한 자산 비중이 크면 수요 충격에 투자와 운전자본을 빠르게 조정할 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자산구성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9593617818707502 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9544116999251134 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.002037154449969794 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0013444540573701045 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.02462081913393545 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.002037154449969794 |
| `ic_t_full` | 0.4374948481417353 |
| `ic_p_full` | 0.3316488089324529 |
| `ic_investable` | 0.0013444540573701045 |
| `ic_std_investable` | 0.05460639022838245 |
| `rank_icir_investable` | 0.02462081913393545 |
| `ic_t_investable` | 0.2774867805972046 |
| `ic_p_investable` | 0.39117231068576686 |
| `ic_retention` | 0.6599666792029635 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.002037154449969794 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0013444540573701045 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.02462081913393545 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_assets_to_assets` | quality | 0.994 | 63 |
| `noncurrent_asset_share` | other | 0.990 | 63 |
| `noncurrent_assets_to_equity` | other | 0.750 | 63 |
| `net_working_capital_to_assets` | quality | 0.714 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.658 | 63 |
| `revenue_to_noncurrent_assets` | quality | 0.649 | 63 |
| `current_assets_to_equity` | quality | 0.627 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.581 | 63 |
| `noncurrent_assets_yield` | value | -0.559 | 63 |
| `working_capital_to_sales` | quality | 0.556 | 63 |
| `current_ratio` | quality | 0.533 | 63 |
| `net_working_capital_yield` | value | 0.523 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.467 | 63 |
| `noncurrent_assets_to_capital_stock` | quality | -0.406 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.404 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: noncurrent_asset_share — 차이: 총자산 비중이 아니라 유동·비유동 자산의 직접 교환비를 측정한다.
- Data notes: DART available_date PIT 유동자산과 양의 비유동자산만 사용한다.
