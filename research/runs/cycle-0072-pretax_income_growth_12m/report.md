# cycle-0072-pretax_income_growth_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `2bf41bc52822d174`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_income_growth_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT pretax_income_ttm의 정확한 12개월 성장률이 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

세율 변동을 제거한 이익 성장의 지속성을 시장이 늦게 학습하면 후속 상대수익을 예측할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.5813873442507591 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.5483564128992018 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.02380359071088441 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.023273696462188756 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.3842473665686206 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.02380359071088441 |
| `ic_t_full` | 3.737364036278002 |
| `ic_p_full` | 0.00020605725859502085 |
| `ic_investable` | 0.023273696462188756 |
| `ic_std_investable` | 0.06056956660503863 |
| `rank_icir_investable` | 0.3842473665686206 |
| `ic_t_investable` | 3.5303609029291407 |
| `ic_p_investable` | 0.00039819503367647025 |
| `ic_retention` | 0.9777388943066747 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.02380359071088441 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.023273696462188756 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_income_growth_12m` | earnings | 0.941 | 63 |
| `operating_income_growth_12m` | earnings | 0.735 | 63 |
| `qual_roe` | quality | 0.681 | 63 |
| `pretax_roa` | quality | 0.670 | 63 |
| `operating_roa_change_12m` | earnings | 0.662 | 63 |
| `operating_margin_change_12m` | earnings | 0.661 | 63 |
| `net_roa` | quality | 0.643 | 63 |
| `pretax_profit_margin` | quality | 0.627 | 63 |
| `retained_earnings_growth_12m` | quality | 0.623 | 63 |
| `net_profit_margin` | quality | 0.610 | 63 |
| `value_ep` | value | 0.607 | 63 |
| `operating_roa` | quality | 0.534 | 63 |
| `operating_return_on_capital_employed` | quality | 0.529 | 63 |
| `equity_growth_12m` | other | -0.505 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.503 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: net_income_growth_12m — 차이: 세금·세액공제 변동을 제외한 세전 이익 성장만 측정한다.
- Data notes: DART available_date PIT pretax_income_ttm을 쓰며 전기 TTM 세전이익이 양수이고 월 간격이 정확할 때만 정의한다.
