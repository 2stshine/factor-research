# cycle-0081-market_leverage_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-005` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `8dd3424bb7bcc564`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/market_leverage_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

총부채/월말 시가총액의 12개월 변화가 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

부채 축소 또는 주주가치 회복으로 낮아진 잔여청구권 위험이 신용·주식시장에 점진적으로 반영될 수 있다.

## Pre-registered falsification

음의 방향, 강건성, BY, 봉인 OOS, 귀무 또는 market_leverage·size·value 직교성 gate가 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9456780302740575 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.936642366758301 | >=30% |
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
| `mom_12_1` | momentum | 0.551 | 63 |
| `liability_growth_12m` | other | 0.434 | 63 |
| `market_leverage` | other | -0.402 | 63 |
| `intermediate_momentum_12_7` | momentum | 0.356 | 63 |
| `positive_return_share_12m` | momentum | 0.352 | 63 |
| `current_liabilities_growth_12m` | other | 0.337 | 63 |
| `defensive_value` | value | -0.326 | 63 |
| `max_monthly_return_12m` | other | -0.318 | 63 |
| `high_12m_proximity` | momentum | 0.316 | 63 |
| `defensive_small_value` | value | -0.305 | 63 |
| `value_bp` | value | -0.297 | 63 |
| `high_52w_price_proximity` | momentum | 0.282 | 63 |
| `asset_growth_12m` | other | 0.269 | 63 |
| `value_sp` | value | -0.266 | 63 |
| `qual_lev` | quality | 0.259 | 63 |

## Expected relationship and data notes

- Expected relationship: market_leverage 수준과 관련되지만 레버리지의 최근 변화만 측정한다.
- Data notes: DART available_date PIT 비음수 총부채와 양의 월말 시가총액을 사용하며 정확히 12개월 전 관측을 요구한다.
