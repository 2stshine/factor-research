# cycle-0073-noncurrent_asset_share_change_12m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-003` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `ea299e63f30cf0b9`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_asset_share_change_12m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT noncurrent_assets/total_assets의 12개월 변화가 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.

## Mechanism

자산구성이 고정자산 중심으로 이동하면 충격 대응력과 자본 회수 유연성이 낮아져 위험이 뒤늦게 가격에 반영될 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9434981145641316 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9338777997413908 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.00760486763505718 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.007255863249874661 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.21523252310685542 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.00760486763505718 |
| `ic_t_full` | 1.8156508007492727 |
| `ic_p_full` | 0.03716981304987605 |
| `ic_investable` | 0.007255863249874661 |
| `ic_std_investable` | 0.03371174181827706 |
| `rank_icir_investable` | 0.21523252310685542 |
| `ic_t_investable` | 1.698668836532673 |
| `ic_p_investable` | 0.047238576915029994 |
| `ic_retention` | 0.9541077633522947 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.00760486763505718 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.007255863249874661 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_assets_growth_12m` | other | -0.681 | 63 |
| `noncurrent_assets_growth_12m` | other | 0.569 | 63 |
| `working_capital_accruals_12m` | quality | -0.551 | 63 |
| `operating_income_growth_12m` | earnings | 0.196 | 63 |
| `operating_roa_change_12m` | earnings | 0.192 | 63 |
| `pretax_income_growth_12m` | earnings | 0.182 | 63 |
| `noncurrent_asset_share` | other | 0.178 | 63 |
| `operating_margin_change_12m` | earnings | 0.168 | 63 |
| `net_income_growth_12m` | earnings | 0.167 | 63 |
| `asset_growth_12m` | other | -0.164 | 63 |
| `sales_growth_12m` | other | -0.158 | 63 |
| `earnings_change_to_assets` | earnings | 0.136 | 63 |
| `sue` | earnings | 0.135 | 63 |
| `current_liabilities_growth_12m` | other | -0.132 | 63 |
| `operating_income_to_noncurrent_assets` | quality | 0.107 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: noncurrent_asset_share — 차이: 자산 경직성 수준이 아니라 최근 12개월 구성 변화만 측정한다.
- Data notes: DART available_date PIT 비유동자산과 양의 총자산을 쓰며 정확히 12개월 전 비율이 있을 때만 정의한다.
