# cycle-0079-current_ratio_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-005` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `6b612f0530a1e066`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_ratio_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT current_assets/current_liabilities의 12개월 변화가 큰 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

단기 지급능력의 개선은 불리한 차환·증자 위험을 낮추며, 공시 후 점진적으로 가격에 반영될 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9442324019611592 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9347679243176683 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.0027938568875218216 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0025444240790089 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.0964165541420215 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0027938568875218216 |
| `ic_t_full` | 1.0793520102754572 |
| `ic_p_full` | 0.14234011040736777 |
| `ic_investable` | 0.0025444240790089 |
| `ic_std_investable` | 0.026389908887025415 |
| `rank_icir_investable` | 0.0964165541420215 |
| `ic_t_investable` | 0.9626993659978224 |
| `ic_p_investable` | 0.1697496423685751 |
| `ic_retention` | 0.9107209787205061 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0027938568875218216 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0025444240790089 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.0964165541420215 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_liabilities_growth_12m` | other | 0.700 | 63 |
| `working_capital_accruals_12m` | quality | -0.663 | 63 |
| `liability_growth_12m` | other | 0.475 | 63 |
| `noncurrent_liability_share_change_12m` | other | 0.453 | 63 |
| `noncurrent_asset_share_change_12m` | other | 0.311 | 63 |
| `retained_earnings_to_assets_change_12m` | quality | 0.289 | 63 |
| `noncurrent_assets_growth_12m` | other | 0.274 | 63 |
| `market_leverage_change_12m` | other | 0.238 | 63 |
| `equity_growth_12m` | other | -0.234 | 63 |
| `net_income_to_liabilities` | quality | 0.166 | 63 |
| `current_ratio` | quality | 0.165 | 63 |
| `pretax_income_to_liabilities` | quality | 0.165 | 63 |
| `net_roa` | quality | 0.162 | 63 |
| `pretax_roa` | quality | 0.160 | 63 |
| `current_liabilities_to_assets` | quality | 0.159 | 63 |

## Expected relationship and data notes

- Expected relationship: current_ratio 수준과 양의 관계를 예상하지만, 최근 12개월 개선폭만 측정하므로 정의상 구별된다.
- Data notes: DART available_date PIT 유동자산과 양의 유동부채를 쓰며 정확히 12개월 전 비율이 있을 때만 정의한다.
