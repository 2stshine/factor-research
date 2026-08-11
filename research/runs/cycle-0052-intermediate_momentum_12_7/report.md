# cycle-0052-intermediate_momentum_12_7

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260811-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `492fa873c5763b79`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/intermediate_momentum_12_7.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver 총수익지수로 측정한 t-12부터 t-7까지 정확히 6개 월수익의 복리 누적값이 높은 종목은 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

기업 정보에 대한 투자자의 과소반응과 점진적 확산이 수개월 동안 가격 추세를 만들 수 있다. 최근 6개월을 완전히 제외해 단기 반전과 최근 모멘텀의 영향을 줄인다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성·커버리지·투자가능 IC·Rank ICIR·기간 및 중립화 강건성·campaign BY를 통과하지 못하거나 기존 팩터와 중복되면 독립적인 중기 모멘텀 가설을 기각한다. 봉인 OOS는 이번 discovery에서 열지 않는다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 1.0 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 1.0 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | N | 0.005397469736375751 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.00543790095770521 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.05799711899576586 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.005397469736375751 |
| `ic_t_full` | 0.45546629318782483 |
| `ic_p_full` | 0.32519548485925837 |
| `ic_investable` | 0.00543790095770521 |
| `ic_std_investable` | 0.09376157043425226 |
| `rank_icir_investable` | 0.05799711899576586 |
| `ic_t_investable` | 0.42052726267620494 |
| `ic_p_investable` | 0.33778905753501537 |
| `ic_retention` | 1.0074907731407878 |
| `months` | 52 |
| `turnover` | 279.1773119909767 |
| `gross` | -2.163921560341616 |
| `cost` | 1.3429581321018293 |
| `net` | -3.5068796924434444 |
| `net_ir` | -0.6138499860847417 |
| `hac_t` | -1.324223413547039 |
| `hac_pvalue` | 0.9043334458696287 |
| `missing_return_rate` | 0.0004710500490677134 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.005397469736375751 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.00543790095770521 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.05799711899576586 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `mom_12_1` | momentum | 0.693 | 63 |
| `positive_return_share_12m` | momentum | 0.426 | 63 |
| `downside_vol_12m` | other | 0.241 | 63 |
| `max_monthly_return_12m` | other | -0.230 | 63 |
| `high_52w_price_proximity` | momentum | 0.209 | 63 |
| `operating_return_on_capital_employed` | quality | 0.206 | 63 |
| `operating_roa` | quality | 0.204 | 63 |
| `qual_roe` | quality | 0.202 | 63 |
| `net_roa` | quality | 0.197 | 63 |
| `high_12m_proximity` | momentum | 0.196 | 63 |
| `operating_income_to_liabilities` | quality | 0.188 | 63 |
| `qual_opm` | quality | 0.186 | 63 |
| `operating_roa_change_12m` | earnings | 0.186 | 63 |
| `net_profit_margin` | quality | 0.178 | 63 |
| `value_ep` | value | 0.172 | 63 |

## Expected relationship and data notes

- Expected relationship: mom_12_1과 일부 과거수익 구간을 공유하므로 양의 관계는 예상한다. 그러나 t-6부터 t-1까지를 쓰지 않으므로 최근 추세·52주 고점 및 단기 반전과는 구별될 것으로 예상한다.
- Data notes: 인증된 Silver total_return_close에 매핑된 return_close로 월수익을 먼저 계산하고, 다음 달을 formation month t로 두어 t-12~t-7의 6개 수익을 복리 누적한다. 종목별 달력월을 재색인하며 중간 결측을 채우지 않는다. 따라서 정확한 6개 월수익이 없는 관측은 결측이다.
