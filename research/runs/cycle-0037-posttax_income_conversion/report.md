# cycle-0037-posttax_income_conversion

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-002`
- OOS: **SEALED**
- Definition hash: `3d16d45df92eff5a`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/posttax_income_conversion.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 net_income_ttm/pretax_income_ttm이 높은 기업은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

낮은 전환율은 높은 세부담이나 세후 비경상 누수를 나타낸다. 시장이 headline 세전성과를 먼저 반영하고 이 누수를 늦게 평가하면 이후 가격 조정이 발생할 수 있다.

## Pre-registered falsification

사전등록한 양의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.6096111607684257 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.5740597679197937 | >=30% |
| T1.2 | 종착수익률 3점 방향 | N | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |

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
| `nonoperating_burden_to_assets` | quality | 0.418 | 101 |
| `net_profit_margin` | quality | 0.329 | 101 |
| `net_roa` | quality | 0.267 | 101 |
| `value_sp` | value | -0.250 | 101 |
| `qual_roe` | quality | 0.225 | 101 |
| `value_bp` | value | -0.177 | 101 |
| `size` | size | 0.173 | 101 |
| `qual_lev` | quality | 0.170 | 101 |
| `defensive_value` | value | -0.167 | 101 |
| `operating_roa_volatility_36m` | quality | -0.157 | 90 |
| `asset_turnover` | quality | -0.149 | 101 |
| `paid_in_capital_ratio` | quality | -0.137 | 101 |
| `current_ratio` | quality | 0.135 | 101 |
| `turnover_volatility_12m` | other | -0.120 | 101 |
| `trading_turnover_20d` | other | -0.113 | 101 |

## Expected relationship and data notes

- Expected relationship: operating_income과 net_income의 차이를 보는 nonoperating_burden_to_assets와 일부 관계가 가능하지만, 이 후보는 세전 이후 구간의 전환율만 분리하므로 정의상 다르다.
- Data notes: DART available_date 순으로 재생한 pretax_income_ttm과 net_income_ttm을 사용한다. 양의 세전이익만 분모로 인정하며 적자와 결측을 다른 값으로 대체하지 않는다.
