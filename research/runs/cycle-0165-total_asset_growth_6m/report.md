# cycle-0165-total_asset_growth_6m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `9beb485c745b1cac`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/total_asset_growth_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 6개월 total_assets 증가율이 낮은 기업은 과잉투자·자산팽창 위험이 작아 이후 상대수익이 높다.

## Mechanism

PIT 재무규모의 시간 변화를 이용해 경영자의 자본배분과 투자 확대를 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 6 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9582985949104704 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9547102763123679 | >=30% |
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
| `asset_growth_12m` | other | 0.670 | 63 |
| `total_asset_growth_18m` | quality | 0.586 | 63 |
| `current_assets_growth_12m` | other | 0.496 | 63 |
| `total_asset_growth_24m` | quality | 0.494 | 63 |
| `liability_growth_12m` | other | 0.490 | 63 |
| `operating_asset_growth_12m` | quality | 0.475 | 63 |
| `total_asset_growth_30m` | quality | 0.473 | 60 |
| `noncurrent_asset_growth_6m` | quality | 0.455 | 63 |
| `equity_growth_12m` | other | 0.428 | 63 |
| `asset_growth_acceleration_12m` | other | 0.405 | 63 |
| `operating_asset_growth_24m` | quality | 0.392 | 63 |
| `current_liabilities_growth_12m` | other | 0.385 | 63 |
| `noncurrent_assets_growth_12m` | other | 0.385 | 63 |
| `market_leverage_change_6m` | other | 0.371 | 63 |
| `equity_growth_24m` | other | 0.364 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 12개월 자산성장과 관련되지만 기간 또는 영업자산 범위가 다르다.
- Data notes: DART available_date PIT 값의 정확한 달력 시차와 양의 전기 분모만 사용한다.
