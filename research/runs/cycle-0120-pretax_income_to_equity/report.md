# cycle-0120-pretax_income_to_equity

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-012` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `48f4938d8e5af99d`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/pretax_income_to_equity.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT pretax_income_ttm/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

영업·금융성과를 포함하되 세금 변동을 제거한 자기자본 수익성이 기대치에 늦게 반영될 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 인접 ROE 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9320172251585219 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9168338055374261 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.050458169236832724 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05244728095436353 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.691842680645812 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.2749448015688758 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.05145715604056052 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | N | 0.8522143627823369 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.050458169236832724 |
| `ic_t_full` | 6.92214494798434 |
| `ic_p_full` | 1.5763006853147626e-09 |
| `ic_investable` | 0.05244728095436353 |
| `ic_std_investable` | 0.07580810265334563 |
| `rank_icir_investable` | 0.691842680645812 |
| `ic_t_investable` | 6.944255124635073 |
| `ic_p_investable` | 1.4443807453622884e-09 |
| `ic_retention` | 1.0394210045194985 |
| `neutral_ic` | 0.05145715604056052 |
| `neutral_ic_t` | 6.570436338923394 |
| `neutral_ic_p` | 6.306808997654501e-09 |
| `neutral_ic_retention` | 0.981121520586271 |
| `n_trials` | 139 |
| `max_gold_signal_corr` | 0.8522143627823369 |
| `gold_signal_comparison_months` | {'adv20_to_book_equity': 62, 'asset_to_market': 62, 'book_to_market_change_12m': 62, 'capital_stock_to_assets': 62, 'current_asset_turnover': 62, 'current_liabilities_to_sales': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'net_working_capital_yield': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62, 'revenue_to_noncurrent_assets': 62} |

### Failed checks

- `T5.1` Gold 신호 직교성: 0.8522143627823369 (각 Gold 비교월>=36 & max_j median_t |rho|<=0.7)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_roe` | quality | 0.968 | 63 |
| `pretax_roa` | quality | 0.967 | 63 |
| `net_roa` | quality | 0.938 | 63 |
| `pretax_income_to_current_assets` | quality | 0.936 | 63 |
| `net_income_to_noncurrent_assets` | quality | 0.917 | 63 |
| `net_income_to_current_assets` | quality | 0.912 | 63 |
| `pretax_profit_margin` | quality | 0.899 | 63 |
| `pretax_income_to_liabilities` | quality | 0.872 | 63 |
| `net_profit_margin` | quality | 0.872 | 63 |
| `net_income_to_capital_stock` | quality | 0.868 | 63 |
| `operating_roa` | quality | 0.864 | 63 |
| `operating_return_on_capital_employed` | quality | 0.863 | 63 |
| `net_income_to_liabilities` | quality | 0.852 | 63 |
| `operating_income_to_equity` | quality | 0.849 | 63 |
| `value_ep` | value | 0.847 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: operating_income_to_equity — 차이: 영업이익 대신 금융손익까지 포함한 세전이익을 사용한다.
- Data notes: DART available_date PIT 세전이익과 양의 자기자본만 사용한다.
