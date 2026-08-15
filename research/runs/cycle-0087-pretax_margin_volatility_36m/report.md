# cycle-0087-pretax_margin_volatility_36m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-006` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `d15d6923d7e4e417`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_margin_volatility_36m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT pretax_income_ttm/revenue_ttm의 36개월 표준편차가 낮은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

세전 마진 안정성은 영업과 금융비용을 함께 반영하되 세금의 일회성 변동을 제거한 이익 지속성을 포착한다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 인접 마진 안정성 신호와의 직교성이 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 36 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.6798200995877283 | >=50% |
| T1.1 | 월별 커버리지 하위10% | N | 0.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |

### Failed checks

- `T1.1` 월별 커버리지 하위10%: 0.0 (>=30%)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_margin_volatility_36m` | quality | 0.970 | 52 |
| `pretax_roa_volatility_36m` | quality | 0.834 | 52 |
| `net_roa_volatility_36m` | quality | 0.820 | 52 |
| `operating_roa_volatility_36m` | quality | 0.593 | 52 |
| `asset_turnover` | quality | 0.540 | 52 |
| `value_sp` | value | 0.508 | 52 |
| `operating_earnings_yield` | value | 0.475 | 52 |
| `current_asset_turnover` | quality | 0.474 | 52 |
| `revenue_to_equity` | quality | 0.454 | 52 |
| `revenue_to_noncurrent_assets` | quality | 0.449 | 52 |
| `quality_stability` | quality | 0.439 | 52 |
| `retained_earnings_to_equity` | quality | 0.420 | 52 |
| `retained_earnings_to_capital_stock` | quality | 0.418 | 52 |
| `operating_income_to_equity` | quality | 0.411 | 52 |
| `operating_return_on_capital_employed` | quality | 0.402 | 52 |

## Expected relationship and data notes

- Expected relationship: net_margin_volatility_36m과 관련되지만 세전 이익 정의로 구별된다.
- Data notes: DART available_date PIT 세전이익과 양의 매출을 쓰며 36개월 창에서 최소 24개 월 관측을 요구한다.
