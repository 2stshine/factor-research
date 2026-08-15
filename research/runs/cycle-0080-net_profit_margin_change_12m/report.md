# cycle-0080-net_profit_margin_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-005` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `7c03a263baafbc66`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_profit_margin_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT TTM 순이익률의 12개월 개선폭이 큰 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

영업외손익과 세금까지 반영한 최종 마진 개선의 지속성이 후속 공시에 걸쳐 늦게 반영될 수 있다.

## Pre-registered falsification

양의 방향과 자동 gate, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.846763398832789 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8093975458137869 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.01911758302438318 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.01978154872899189 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5224049508111935 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.01911758302438318 |
| `ic_t_full` | 4.503824722959815 |
| `ic_p_full` | 1.536272392151998e-05 |
| `ic_investable` | 0.01978154872899189 |
| `ic_std_investable` | 0.037866311753506514 |
| `rank_icir_investable` | 0.5224049508111935 |
| `ic_t_investable` | 4.337261324751373 |
| `ic_p_investable` | 2.7523747517752213e-05 |
| `ic_retention` | 1.034730630109563 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.01911758302438318 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.01978154872899189 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `net_income_growth_12m` | earnings | 0.888 | 63 |
| `pretax_income_growth_12m` | earnings | 0.831 | 63 |
| `operating_margin_change_12m` | earnings | 0.654 | 63 |
| `operating_roa_change_12m` | earnings | 0.601 | 63 |
| `operating_income_growth_12m` | earnings | 0.568 | 63 |
| `retained_earnings_growth_12m` | quality | 0.463 | 63 |
| `sue` | earnings | 0.419 | 63 |
| `earnings_change_to_assets` | earnings | 0.413 | 63 |
| `qual_roe` | quality | 0.404 | 63 |
| `net_roa` | quality | 0.397 | 63 |
| `net_profit_margin` | quality | 0.390 | 63 |
| `value_ep` | value | 0.374 | 63 |
| `pretax_roa` | quality | 0.368 | 63 |
| `pretax_profit_margin` | quality | 0.365 | 63 |
| `retained_earnings_to_assets_change_12m` | quality | 0.362 | 63 |

## Expected relationship and data notes

- Expected relationship: net_profit_margin 및 operating_margin_change_12m와 관련되지만 최종 순이익률의 변화만 측정한다.
- Data notes: DART available_date PIT net_income_ttm과 양의 revenue_ttm을 사용하고 정확한 12개월 간격만 허용한다.
