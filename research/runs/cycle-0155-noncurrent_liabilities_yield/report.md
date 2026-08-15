# cycle-0155-noncurrent_liabilities_yield

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-015` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `3563f184ff3b6f7a`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_liabilities_yield.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

비유동부채/시가총액이 높은 종목의 이후 수익률 순위가 낮을 것이다.

## Mechanism

주주가치에 비해 장기 채무가 크면 금리상승과 장기 차환 부담이 지속된다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 시장레버리지 신호 직교성이 실패하면 기각한다.

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
| `noncurrent_liabilities_to_equity` | other | 0.850 | 63 |
| `equity_to_noncurrent_liabilities` | quality | 0.846 | 63 |
| `market_leverage` | other | -0.840 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.827 | 63 |
| `noncurrent_assets_yield` | value | -0.779 | 63 |
| `asset_to_market` | value | -0.748 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.736 | 63 |
| `current_liabilities_yield` | value | 0.710 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.682 | 63 |
| `noncurrent_assets_to_equity` | other | 0.658 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.653 | 63 |
| `value_sp` | value | -0.642 | 63 |
| `qual_lev` | quality | 0.632 | 63 |
| `current_liability_concentration` | quality | -0.612 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.573 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: market_leverage — 차이: 총부채 중 장기 만기 의무만 시장가치와 비교한다.
- Data notes: DART available_date PIT 비유동부채와 동시점 양의 시가총액을 사용한다.
