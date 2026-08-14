# cycle-0056-current_asset_turnover

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260814-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `05c6633ec72d4e6a`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/current_asset_turnover.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 revenue_ttm/current_assets가 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

같은 유동자산 기반에서 더 많은 매출을 만드는 기업은 재고와 매출채권의 회전, 현금의 배치와 단기 운영규율이 우수할 수 있다. 시장이 운전자본 효율의 지속성을 늦게 반영하면 높은 회전율이 이후 상대수익을 예측할 수 있다.

## Pre-registered falsification

사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9240547961970031 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9068077368534231 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.03197677986699694 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0327352820060551 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5281725367327502 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.33351985729933403 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.02813203036197428 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.03197677986699694 |
| `ic_t_full` | 4.198543721660586 |
| `ic_p_full` | 4.439657579825153e-05 |
| `ic_investable` | 0.0327352820060551 |
| `ic_std_investable` | 0.061978387230343275 |
| `rank_icir_investable` | 0.5281725367327502 |
| `ic_t_investable` | 4.229719696957081 |
| `ic_p_investable` | 3.989803993567289e-05 |
| `ic_retention` | 1.0237204040623553 |
| `months` | 49 |
| `turnover` | 92.74767257623542 |
| `gross` | 1.465291839605783 |
| `cost` | 0.45581614669334325 |
| `net` | 1.0094756929124393 |
| `net_ir` | 0.22620834257270228 |
| `hac_t` | 0.4329470333781658 |
| `hac_pvalue` | 0.33349625186114334 |
| `missing_return_rate` | 0.0005534253073486975 |
| `neutral_ic` | 0.02813203036197428 |
| `neutral_ic_t` | 4.177023397259717 |
| `neutral_ic_p` | 4.77842160527466e-05 |
| `neutral_ic_retention` | 0.8593795024209858 |
| `n_trials` | 69 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `asset_turnover` | quality | 0.723 | 63 |
| `value_sp` | value | 0.636 | 63 |
| `net_working_capital_to_assets` | quality | -0.492 | 63 |
| `current_ratio` | quality | -0.482 | 63 |
| `market_leverage` | other | 0.439 | 63 |
| `noncurrent_asset_share` | other | -0.391 | 63 |
| `qual_lev` | quality | -0.350 | 63 |
| `operating_earnings_yield` | value | 0.337 | 63 |
| `quality_stability` | quality | 0.298 | 63 |
| `operating_return_on_capital_employed` | quality | 0.247 | 63 |
| `value_bp` | value | 0.228 | 63 |
| `profitable_small_value` | quality | 0.221 | 63 |
| `operating_roa` | quality | 0.220 | 63 |
| `asset_turnover_change_12m` | quality | 0.212 | 63 |
| `defensive_value` | value | 0.207 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: asset_turnover — 차이: 전체 자산 효율이 아니라 재고·채권·현금 등 단기 영업자산의 회전효율에만 초점을 둔다.
- Data notes: DART available_date 순으로 재생한 Silver PIT revenue_ttm과 current_assets만 사용한다. 유동자산이 양수인 관측에서 정의하며 업종별 운전자본 구조 차이는 공통 시장·규모·업종 강건성 검사에서 진단한다.
