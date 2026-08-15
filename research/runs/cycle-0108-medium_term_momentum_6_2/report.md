# cycle-0108-medium_term_momentum_6_2

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-010` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `fe7484d4b16ecc1c`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/medium_term_momentum_6_2.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver 분할조정 가격으로 측정한 t-6부터 t-2까지 다섯 월수익의 복리 누적값이 높은 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

기업 정보의 점진적 확산과 투자자 과소반응은 수개월 동안 가격 추세를 만들 수 있으며, 가장 최근 한 달을 제외하면 단기 반전과 미시구조 잡음을 줄일 수 있다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성·입력 커버리지·투자가능 IC·Rank ICIR·기간 및 중립화 강건성·campaign BY를 통과하지 못하거나 기존 신호와 중복되면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9999082140753716 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.999509393297173 | >=30% |
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
| `high_12m_proximity` | momentum | 0.587 | 63 |
| `mom_12_1` | momentum | 0.581 | 63 |
| `high_52w_price_proximity` | momentum | 0.529 | 63 |
| `short_term_reversal_3m` | momentum | -0.438 | 63 |
| `book_to_market_change_12m` | value | -0.413 | 63 |
| `positive_return_share_12m` | momentum | 0.373 | 63 |
| `market_leverage_change_12m` | other | 0.330 | 63 |
| `downside_vol_12m` | other | 0.285 | 63 |
| `amihud_illiquidity_1m` | other | -0.206 | 63 |
| `trading_turnover_20d` | other | -0.199 | 63 |
| `max_monthly_return_12m` | other | -0.173 | 63 |
| `sue` | earnings | 0.150 | 63 |
| `pretax_income_to_current_assets` | quality | 0.143 | 63 |
| `net_income_to_current_assets` | quality | 0.142 | 63 |
| `pretax_income_to_equity` | quality | 0.141 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: intermediate_momentum_12_7 — 차이: 더 최근인 t-6~t-2 구간만 사용하며 t-12~t-7의 오래된 정보확산과 구별한다. mom_12_1과 양의 관계는 예상하지만 정확한 형성 구간은 겹치지 않는다.
- Data notes: Silver PIT adj_close로 월 가격수익을 만들고 종목별 달력월을 재색인한다. 결측 월은 채우지 않으며 정확한 다섯 월수익이 모두 있을 때만 신호를 낸다.
