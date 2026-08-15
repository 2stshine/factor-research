# cycle-0095-current_assets_to_equity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-008` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `cd296082edb97588`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_assets_to_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT current_assets/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

자기자본에 비해 회수 가능한 단기자산이 많으면 영업충격 때 외부조달 필요성이 낮다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 유동성·레버리지 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9587498757065605 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9547009176622014 | >=30% |
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
| `current_liabilities_to_assets` | quality | -0.634 | 63 |
| `current_assets_to_assets` | quality | 0.628 | 63 |
| `noncurrent_asset_share` | other | 0.616 | 63 |
| `revenue_to_equity` | quality | 0.587 | 63 |
| `qual_lev` | quality | -0.580 | 63 |
| `revenue_to_noncurrent_assets` | quality | 0.562 | 63 |
| `solvent_value` | value | -0.522 | 63 |
| `asset_turnover` | quality | 0.378 | 63 |
| `noncurrent_asset_encumbrance` | quality | -0.370 | 63 |
| `retained_earnings_to_liabilities` | quality | -0.365 | 63 |
| `market_leverage` | other | 0.323 | 63 |
| `retained_earnings_to_assets` | quality | -0.314 | 63 |
| `asset_turnover_volatility_36m` | quality | -0.288 | 52 |
| `noncurrent_liabilities_to_equity` | other | -0.285 | 63 |
| `value_sp` | value | 0.275 | 63 |

## Expected relationship and data notes

- Expected relationship: current_assets_to_assets와 관련되지만 자기자본 대비 유동성 용량을 측정한다.
- Data notes: DART available_date PIT 유동자산과 양의 자기자본만 사용한다.
