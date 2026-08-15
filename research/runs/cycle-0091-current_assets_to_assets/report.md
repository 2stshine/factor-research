# cycle-0091-current_assets_to_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-007` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `7986938fba4179c9`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_assets_to_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT current_assets/total_assets가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

회수 가능한 단기자산 비중이 높으면 충격 시 차입·증자·강제매각 의존도가 낮아진다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 current_ratio·asset rigidity 신호 직교성이 실패하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 0 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9611210120927955 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9569648550421535 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.0025879168896836245 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0018790043054431249 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.03455092470513988 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0025879168896836245 |
| `ic_t_full` | 0.5506617917293483 |
| `ic_p_full` | 0.2919383341998761 |
| `ic_investable` | 0.0018790043054431249 |
| `ic_std_investable` | 0.05438361842638612 |
| `rank_icir_investable` | 0.03455092470513988 |
| `ic_t_investable` | 0.3837050570896325 |
| `ic_p_investable` | 0.3512656112842368 |
| `ic_retention` | 0.7260682570346512 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0025879168896836245 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0018790043054431249 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.03455092470513988 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `noncurrent_asset_share` | other | 0.976 | 63 |
| `noncurrent_assets_to_equity` | other | 0.742 | 63 |
| `net_working_capital_to_assets` | quality | 0.718 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.664 | 63 |
| `revenue_to_noncurrent_assets` | quality | 0.637 | 63 |
| `current_assets_to_equity` | quality | 0.628 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.585 | 63 |
| `current_ratio` | quality | 0.536 | 63 |
| `net_working_capital_yield` | value | 0.525 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.464 | 63 |
| `current_asset_turnover` | quality | -0.400 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.400 | 63 |
| `current_liability_concentration` | quality | -0.378 | 63 |
| `noncurrent_liabilities_to_equity` | other | 0.368 | 63 |
| `revenue_to_total_liabilities` | quality | 0.362 | 63 |

## Expected relationship and data notes

- Expected relationship: noncurrent_asset_share의 보완적 구성비지만 직접 유동자산을 측정한다.
- Data notes: DART available_date PIT 유동자산과 양의 총자산만 사용한다.
