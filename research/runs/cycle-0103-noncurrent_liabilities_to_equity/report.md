# cycle-0103-noncurrent_liabilities_to_equity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-009` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `c58df5bf5f733ad0`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/noncurrent_liabilities_to_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT noncurrent_liabilities/total_equity가 낮은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

장기 선순위 청구권이 주주자본 대비 작으면 장기간의 이자·차환 위험과 잔여청구권 민감도가 낮다.

## Pre-registered falsification

음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 book leverage 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9583750831809942 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9543618913090088 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.0001990688428023572 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0001630160641416761 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.0030237233632649323 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.0001990688428023572 |
| `ic_t_full` | 0.03143033762762515 |
| `ic_p_full` | 0.4875144802704608 |
| `ic_investable` | 0.0001630160641416761 |
| `ic_std_investable` | 0.053912360542683994 |
| `rank_icir_investable` | 0.0030237233632649323 |
| `ic_t_investable` | 0.025102698744298234 |
| `ic_p_investable` | 0.4900274939782511 |
| `ic_retention` | 0.818892910848557 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.0001990688428023572 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0001630160641416761 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.0030237233632649323 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `noncurrent_liabilities_to_assets` | quality | 0.963 | 63 |
| `noncurrent_asset_encumbrance` | quality | 0.899 | 63 |
| `revenue_to_noncurrent_liabilities` | quality | 0.800 | 63 |
| `qual_lev` | quality | 0.761 | 63 |
| `current_assets_to_total_liabilities` | quality | 0.752 | 63 |
| `noncurrent_assets_to_equity` | other | 0.719 | 63 |
| `current_liability_concentration` | quality | -0.693 | 63 |
| `net_working_capital_to_liabilities` | quality | 0.622 | 63 |
| `market_leverage` | other | -0.610 | 63 |
| `revenue_to_total_liabilities` | quality | 0.556 | 63 |
| `net_working_capital_to_assets` | quality | 0.536 | 63 |
| `current_ratio` | quality | 0.527 | 63 |
| `solvent_value` | value | 0.487 | 63 |
| `capital_stock_to_liabilities` | quality | 0.465 | 63 |
| `retained_earnings_to_liabilities` | quality | 0.443 | 63 |

## Expected relationship and data notes

- Expected relationship: market_leverage와 관련되지만 장부 자기자본 대비 장기부채만 측정한다.
- Data notes: DART available_date PIT 비유동부채와 양의 자기자본만 사용한다.
