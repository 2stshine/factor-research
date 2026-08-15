# cycle-0098-noncurrent_assets_to_equity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-008` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `2e53940365dac6af`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_assets_to_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT noncurrent_assets/total_equity가 낮은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

자기자본을 장기 회수자산에 과도하게 묶지 않은 기업은 운전자본과 충격 대응 여력이 크다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자산경직성·레버리지 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9579543976931137 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9536267298547004 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.00767859390671296 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.007335036193118133 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.11347956562086063 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.00767859390671296 |
| `ic_t_full` | 1.1127195909690584 |
| `ic_p_full` | 0.13509737727372415 |
| `ic_investable` | 0.007335036193118133 |
| `ic_std_investable` | 0.06463750678800408 |
| `rank_icir_investable` | 0.11347956562086063 |
| `ic_t_investable` | 0.9929439403134231 |
| `ic_p_investable` | 0.16232990509896167 |
| `ic_retention` | 0.955257731067862 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.00767859390671296 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.007335036193118133 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.11347956562086063 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_assets_to_total_liabilities` | quality | 0.931 | 63 |
| `net_working_capital_to_assets` | quality | 0.926 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.898 | 63 |
| `current_ratio` | quality | 0.850 | 63 |
| `noncurrent_asset_share` | other | 0.751 | 63 |
| `current_assets_to_assets` | quality | 0.742 | 63 |
| `qual_lev` | quality | 0.732 | 63 |
| `noncurrent_liabilities_to_equity` | other | 0.719 | 63 |
| `net_working_capital_yield` | value | 0.651 | 63 |
| `market_leverage` | other | -0.632 | 63 |
| `noncurrent_liabilities_to_assets` | quality | 0.628 | 63 |
| `revenue_to_total_liabilities` | quality | 0.584 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.548 | 63 |
| `current_liabilities_to_assets` | quality | 0.527 | 63 |
| `current_asset_turnover` | quality | -0.466 | 63 |

## Expected relationship and data notes

- Expected relationship: noncurrent_asset_share와 관련되지만 자기자본이 부담하는 장기자산 규모를 측정한다.
- Data notes: DART available_date PIT 비유동자산과 양의 자기자본만 사용한다.
