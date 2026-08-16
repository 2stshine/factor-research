# cycle-0186-equity_growth_6m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `79a8dad1141661fe`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/equity_growth_6m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 6개월 book_equity 확대가 큰 기업은 외부자금 수요나 고평가 활용 가능성이 높아 이후 상대수익이 낮다.

## Mechanism

발행·부채조달·자본금 변화 중 하나를 PIT 시점에서 분리하여 경영자의 자금조달 결정을 측정한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9566464482671583 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9532796169319525 | >=30% |
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
| `equity_growth_12m` | other | 0.712 | 63 |
| `retained_earnings_growth_12m` | quality | -0.565 | 63 |
| `total_asset_growth_6m` | quality | 0.552 | 63 |
| `operating_asset_growth_12m` | quality | 0.540 | 63 |
| `capital_stock_share_change_12m` | other | -0.535 | 63 |
| `equity_growth_24m` | other | 0.525 | 63 |
| `working_capital_accruals_6m` | earnings | 0.484 | 63 |
| `qual_roe` | quality | -0.482 | 63 |
| `pretax_income_to_equity` | quality | -0.471 | 63 |
| `net_roa` | quality | -0.468 | 63 |
| `pretax_roa` | quality | -0.458 | 63 |
| `net_income_to_current_assets` | quality | -0.452 | 63 |
| `net_income_growth_12m` | earnings | -0.450 | 63 |
| `net_income_to_noncurrent_assets` | quality | -0.449 | 63 |
| `asset_growth_12m` | other | 0.447 | 63 |

## Expected relationship and data notes

- Expected relationship: 자산성장과 일부 관계가 예상되지만 조달 측면만 측정한다.
- Data notes: 정확한 달력 시차와 양의 분모만 사용하며 기업행사 후행 라벨은 사용하지 않는다.
