# cycle-0107-revenue_to_equity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-010` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `69502c479c0d9ebd`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/revenue_to_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT revenue_ttm/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

주주가 제공한 장부자본 한 단위가 만드는 사업규모가 크면 자본효율과 운영 레버리지가 높을 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전·가치 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9225097331324241 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9073090402876232 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.021861305978789294 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.0223065962034272 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.33134353441417513 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.021861305978789294 |
| `ic_t_full` | 2.7557633437176814 |
| `ic_p_full` | 0.0038551483706932197 |
| `ic_investable` | 0.0223065962034272 |
| `ic_std_investable` | 0.0673216582990397 |
| `rank_icir_investable` | 0.33134353441417513 |
| `ic_t_investable` | 2.786423840607441 |
| `ic_p_investable` | 0.003546478743382477 |
| `ic_retention` | 1.0203688757236162 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.021861305978789294 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.0223065962034272 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `asset_turnover` | quality | 0.852 | 63 |
| `current_asset_turnover` | quality | 0.720 | 63 |
| `value_sp` | value | 0.708 | 63 |
| `revenue_to_noncurrent_assets` | quality | 0.667 | 63 |
| `current_liabilities_to_assets` | quality | -0.663 | 63 |
| `qual_lev` | quality | -0.652 | 63 |
| `current_assets_to_equity` | quality | 0.587 | 63 |
| `market_leverage` | other | 0.557 | 63 |
| `current_ratio` | quality | -0.484 | 63 |
| `net_working_capital_to_liabilities` | quality | -0.463 | 63 |
| `pretax_margin_volatility_36m` | quality | 0.454 | 52 |
| `net_margin_volatility_36m` | quality | 0.447 | 52 |
| `noncurrent_liabilities_to_equity` | other | -0.431 | 63 |
| `current_assets_to_total_liabilities` | quality | -0.411 | 63 |
| `capital_stock_to_liabilities` | quality | -0.397 | 63 |

## Expected relationship and data notes

- Expected relationship: asset turnover와 관련되지만 주주자본의 매출 생산성을 측정한다.
- Data notes: DART available_date PIT 매출과 양의 자기자본만 사용한다.
