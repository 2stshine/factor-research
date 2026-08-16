# cycle-0162-amihud_volatility_6m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `fe67eaad9ce094a0`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/amihud_volatility_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 6개월 Amihud 가격충격 비유동성의 std가 낮은 종목은 유동성 보상 또는 과도한 관심 교정으로 이후 상대수익이 높다.

## Mechanism

거래 규모를 기업가치로 정규화하거나 가격충격을 직접 측정해 단순 대형주 노출과 구분한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9704066881343746 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9604828247429498 | >=30% |
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
| `amihud_mean_6m` | other | -0.957 | 63 |
| `amihud_volatility_12m` | other | 0.939 | 63 |
| `amihud_mean_18m` | other | -0.914 | 63 |
| `amihud_volatility_18m` | other | 0.896 | 63 |
| `amihud_mean_24m` | other | -0.885 | 63 |
| `amihud_volatility_24m` | other | 0.868 | 63 |
| `amihud_illiquidity_1m` | other | -0.844 | 63 |
| `amihud_mean_36m` | other | -0.836 | 63 |
| `amihud_volatility_36m` | other | 0.812 | 63 |
| `size` | size | -0.766 | 63 |
| `small_value` | value | -0.669 | 63 |
| `earnings_confirmed_small_value` | earnings | -0.572 | 63 |
| `defensive_small_value` | value | -0.565 | 63 |
| `profitable_small_value` | quality | -0.476 | 63 |
| `turnover_volatility_12m` | other | 0.454 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 유동성 수준·변화 신호와 관련될 수 있어 Gold 상관 gate로 독립성을 확인한다.
- Data notes: 인증된 월말 거래·시가총액·Amihud 입력만 사용하며 결측을 채우지 않는다.
