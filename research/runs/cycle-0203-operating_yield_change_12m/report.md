# cycle-0203-operating_yield_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-005` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `5bed9215eca57393`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_yield_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

operating_income_ttm 대비 시장가치의 12개월 개선이 큰 기업은 펀더멘털 대비 가격이 덜 반영되어 이후 상대수익이 높다.

## Mechanism

가치비율의 현재 수준 대신 사전 고정 기간의 개선을 측정해 기존 Gold 가치 수준 신호와 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.8676905896480774 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8426149044038943 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.02858860757699157 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.029237912985280907 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5513587157136487 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.02858860757699157 |
| `ic_t_full` | 4.023930294699439 |
| `ic_p_full` | 8.020774563887053e-05 |
| `ic_investable` | 0.029237912985280907 |
| `ic_std_investable` | 0.05302883975895247 |
| `rank_icir_investable` | 0.5513587157136487 |
| `ic_t_investable` | 4.032119859266524 |
| `ic_p_investable` | 7.803436854739732e-05 |
| `ic_retention` | 1.0227120333349815 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.02858860757699157 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.029237912985280907 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_income_growth_12m` | earnings | 0.792 | 63 |
| `operating_roa_change_12m` | earnings | 0.760 | 63 |
| `pretax_yield_change_12m` | value | 0.719 | 63 |
| `operating_margin_change_12m` | earnings | 0.715 | 63 |
| `earnings_yield_change_12m` | value | 0.661 | 63 |
| `operating_coverage_change_12m` | earnings | 0.635 | 63 |
| `enterprise_earnings_yield_change_12m` | value | 0.621 | 63 |
| `operating_income_growth_acceleration_12m` | earnings | 0.574 | 51 |
| `pretax_income_growth_12m` | earnings | 0.569 | 63 |
| `operating_margin_acceleration_12m` | earnings | 0.544 | 51 |
| `net_income_growth_12m` | earnings | 0.534 | 63 |
| `pretax_yield_change_6m` | value | 0.520 | 63 |
| `operating_margin_change_6m` | earnings | 0.507 | 63 |
| `operating_earnings_yield` | value | 0.476 | 63 |
| `net_profit_margin_change_12m` | earnings | 0.474 | 63 |

## Expected relationship and data notes

- Expected relationship: 가치 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.
- Data notes: PIT 재무 분자와 동시점 양의 market_cap 또는 enterprise value, 정확한 달력 시차만 사용한다.
