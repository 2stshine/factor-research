# cycle-0082-retained_earnings_to_assets_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-005` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `c98308cb4bcfc12b`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/retained_earnings_to_assets_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT retained_earnings/total_assets의 12개월 변화가 큰 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

배당·증자와 구별되는 누적 내부이익의 증가가 자금조달 의존도와 부도위험을 낮출 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 보정 또는 retained_earnings 수준·성장 신호와의 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9402397142398213 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9170976027801517 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.028477481839485966 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.02837079810042502 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.6129405977909096 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.028477481839485966 |
| `ic_t_full` | 4.787781788701049 |
| `ic_p_full` | 5.568221913912187e-06 |
| `ic_investable` | 0.02837079810042502 |
| `ic_std_investable` | 0.04628637457312472 |
| `rank_icir_investable` | 0.6129405977909096 |
| `ic_t_investable` | 5.2668580933749665 |
| `ic_p_investable` | 9.547017148242893e-07 |
| `ic_retention` | 0.996253750957958 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.028477481839485966 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.02837079810042502 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `retained_earnings_growth_12m` | quality | 0.662 | 63 |
| `net_roa` | quality | 0.552 | 63 |
| `qual_roe` | quality | 0.542 | 63 |
| `net_income_to_liabilities` | quality | 0.530 | 63 |
| `pretax_roa` | quality | 0.528 | 63 |
| `pretax_income_to_liabilities` | quality | 0.516 | 63 |
| `net_profit_margin` | quality | 0.513 | 63 |
| `pretax_profit_margin` | quality | 0.493 | 63 |
| `value_ep` | value | 0.485 | 63 |
| `operating_income_to_liabilities` | quality | 0.462 | 63 |
| `operating_roa` | quality | 0.460 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.455 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.451 | 63 |
| `operating_return_on_capital_employed` | quality | 0.451 | 63 |
| `qual_opm` | quality | 0.420 | 63 |

## Expected relationship and data notes

- Expected relationship: retained_earnings_to_assets 및 retained_earnings_growth_12m와 관련되지만 자산 대비 축적 속도만 측정한다.
- Data notes: DART available_date PIT 이익잉여금과 양의 총자산을 사용하며 정확한 12개월 간격만 허용한다.
