# cycle-0074-noncurrent_liabilities_to_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-004` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `3b7176e14e22e8dd`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_liabilities_to_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT noncurrent_liabilities/total_assets가 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

장기 고정 청구권이 적으면 경기 충격과 금리 상승에 대응할 자본배분 유연성이 커진다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9607462195672294 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.95575739893969 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |

### Failed checks

- `T1.2` 종착수익률 3점 방향: None (세 시나리오 IC > 0)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `noncurrent_asset_encumbrance` | quality | 0.912 | 63 |
| `current_liability_concentration` | quality | -0.825 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.661 | 63 |
| `qual_lev` | quality | 0.598 | 63 |
| `market_leverage` | other | -0.500 | 63 |
| `revenue_to_total_liabilities` | quality | 0.497 | 63 |
| `net_working_capital_to_assets` | quality | 0.413 | 63 |
| `noncurrent_asset_share` | other | 0.405 | 63 |
| `current_ratio` | quality | 0.383 | 63 |
| `solvent_value` | value | 0.367 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.346 | 63 |
| `noncurrent_liabilities_growth_12m` | other | 0.319 | 63 |
| `quality_stability` | quality | 0.297 | 63 |
| `retained_earnings_to_assets` | quality | 0.265 | 63 |
| `current_asset_turnover` | quality | -0.263 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: qual_lev — 차이: 총부채/자본이 아니라 장기부채/총자산만 측정한다.
- Data notes: DART available_date PIT 비유동부채와 양의 총자산을 사용한다.
