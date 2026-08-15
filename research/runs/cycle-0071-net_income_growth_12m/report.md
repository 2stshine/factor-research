# cycle-0071-net_income_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `6bec9560dceccc6d`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_income_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT net_income_ttm의 정확한 12개월 성장률이 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

연간 누적 순이익 개선의 지속성을 투자자가 한 번에 반영하지 못하면 공시 뒤에도 가격 조정이 이어질 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.5707248793397532 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.5352622513044186 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.02328860438406947 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.022798939717352633 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.36472642613204886 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.02328860438406947 |
| `ic_t_full` | 3.4259148811549185 |
| `ic_p_full` | 0.0005509106709102409 |
| `ic_investable` | 0.022798939717352633 |
| `ic_std_investable` | 0.06250970065190257 |
| `rank_icir_investable` | 0.36472642613204886 |
| `ic_t_investable` | 3.2486546739694795 |
| `ic_p_investable` | 0.0009438315153551222 |
| `ic_retention` | 0.9789740656571163 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.02328860438406947 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.022798939717352633 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `pretax_income_growth_12m` | earnings | 0.941 | 63 |
| `qual_roe` | quality | 0.709 | 63 |
| `operating_income_growth_12m` | earnings | 0.687 | 63 |
| `net_roa` | quality | 0.682 | 63 |
| `pretax_roa` | quality | 0.650 | 63 |
| `retained_earnings_growth_12m` | quality | 0.645 | 63 |
| `net_profit_margin` | quality | 0.643 | 63 |
| `value_ep` | value | 0.641 | 63 |
| `operating_roa_change_12m` | earnings | 0.624 | 63 |
| `operating_margin_change_12m` | earnings | 0.620 | 63 |
| `pretax_profit_margin` | quality | 0.617 | 63 |
| `operating_roa` | quality | 0.517 | 63 |
| `equity_growth_12m` | other | -0.516 | 63 |
| `operating_return_on_capital_employed` | quality | 0.508 | 63 |
| `sue` | earnings | 0.501 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: earnings_change_to_assets — 차이: 단일 분기 변화액이 아니라 양의 TTM 순이익의 연간 성장률이다.
- Data notes: DART available_date PIT net_income_ttm을 쓰며 전기 TTM 순이익이 양수이고 월 간격이 정확할 때만 정의한다.
