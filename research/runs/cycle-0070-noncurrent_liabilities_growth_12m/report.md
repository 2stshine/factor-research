# cycle-0070-noncurrent_liabilities_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `3328787c0692acd8`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_liabilities_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT 비유동부채의 정확한 12개월 성장률이 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

장기 차입 확대는 미래 현금흐름의 고정 청구권과 재융자 위험을 높여 시장이 뒤늦게 위험을 재평가하게 할 수 있다.

## Pre-registered falsification

무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 12 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9385875675965091 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9248040387740071 | >=30% |
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
| `liability_growth_12m` | other | 0.429 | 63 |
| `current_liability_concentration` | quality | -0.360 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.340 | 63 |
| `asset_growth_12m` | other | 0.338 | 63 |
| `noncurrent_assets_growth_12m` | other | 0.329 | 63 |
| `working_capital_accruals_12m` | quality | 0.226 | 63 |
| `current_assets_growth_12m` | other | 0.175 | 63 |
| `asset_turnover_change_12m` | quality | 0.150 | 63 |
| `noncurrent_asset_share_change_12m` | other | 0.100 | 63 |
| `sales_growth_12m` | other | 0.093 | 63 |
| `revenue_to_total_liabilities` | quality | 0.086 | 63 |
| `current_ratio` | quality | -0.078 | 63 |
| `size` | size | 0.075 | 63 |
| `long_term_reversal_36_12` | momentum | 0.069 | 63 |
| `earnings_confirmed_small_value` | earnings | 0.066 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: liability_growth_12m — 차이: 단기 운전자금 부채를 제외한 장기 조달 증가만 측정한다.
- Data notes: DART available_date PIT noncurrent_liabilities를 쓰며 정확히 12개월 전 양수 관측이 있을 때만 정의한다.
