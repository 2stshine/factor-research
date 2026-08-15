# cycle-0145-amihud_volatility_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-014` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `bfd49a2484fe9153`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/amihud_volatility_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

12개월 Amihud 비유동성 표준편차가 높은 종목의 이후 순위가 낮을 것이다.

## Mechanism

거래비용의 불안정성은 평시 유동성 수준보다 자금회수 불확실성을 크게 만든다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 유동성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9532197737476958 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9414799154144683 | >=30% |
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
| `amihud_illiquidity_1m` | other | -0.818 | 63 |
| `size` | size | -0.759 | 63 |
| `small_value` | value | -0.652 | 63 |
| `earnings_confirmed_small_value` | earnings | -0.556 | 63 |
| `defensive_small_value` | value | -0.526 | 63 |
| `turnover_volatility_12m` | other | 0.508 | 63 |
| `profitable_small_value` | quality | -0.470 | 63 |
| `capital_stock_yield` | value | -0.384 | 63 |
| `operating_income_to_capital_stock` | quality | 0.306 | 63 |
| `operating_income_to_equity` | quality | 0.292 | 63 |
| `operating_income_to_current_assets` | quality | 0.276 | 63 |
| `operating_return_on_capital_employed` | quality | 0.272 | 63 |
| `long_term_reversal_36_12` | momentum | -0.268 | 63 |
| `net_income_to_capital_stock` | quality | 0.267 | 63 |
| `operating_roa` | quality | 0.267 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: amihud_illiquidity_1m — 차이: 수준이 아니라 12개월 유동성 환경의 불안정성을 측정한다.
- Data notes: 인증된 월별 Amihud 값의 정확한 12개월 달력창을 사용한다.
