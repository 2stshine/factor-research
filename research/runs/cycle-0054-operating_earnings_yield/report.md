# cycle-0054-operating_earnings_yield

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260814-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `692110a461d94df5`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.13.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/operating_earnings_yield.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 operating_income_ttm/market_cap이 높은 기업은 낮은 기업보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

순이익에는 자본구조, 세율과 비경상손익이 섞인다. 핵심 영업이익을 현재 자기자본 시장가치와 직접 비교하면 영업사업의 수익창출력에 비해 주가가 낮은 기업을 포착할 수 있고, 이 가격 괴리가 해소되면서 초과수익이 발생할 수 있다.

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
| T1.1 | 전체 커버리지 | Y | 0.9346254751833807 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9168338055374261 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.06816206301111535 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.07146562218492317 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 1.0140319646223952 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.32503900892110144 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.05875033304297221 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.06816206301111535 |
| `ic_t_full` | 8.60953544579285 |
| `ic_p_full` | 1.979504903767214e-12 |
| `ic_investable` | 0.07146562218492317 |
| `ic_std_investable` | 0.07047669568437669 |
| `rank_icir_investable` | 1.0140319646223952 |
| `ic_t_investable` | 9.839167139084884 |
| `ic_p_investable` | 1.6514026925511236e-14 |
| `ic_retention` | 1.0484662439467112 |
| `months` | 51 |
| `turnover` | 100.42195391547995 |
| `gross` | 2.566907731022114 |
| `cost` | 0.49217509339201904 |
| `net` | 2.0747326376300954 |
| `net_ir` | 0.42019243634181774 |
| `hac_t` | 0.9715328425779828 |
| `hac_pvalue` | 0.16797982431735545 |
| `missing_return_rate` | 0.0005534253073486975 |
| `neutral_ic` | 0.05875033304297221 |
| `neutral_ic_t` | 7.557006787508668 |
| `neutral_ic_p` | 1.2740113380461484e-10 |
| `neutral_ic_retention` | 0.8220782419126066 |
| `n_trials` | 69 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_return_on_capital_employed` | quality | 0.834 | 63 |
| `operating_roa` | quality | 0.814 | 63 |
| `value_ep` | value | 0.801 | 63 |
| `qual_opm` | quality | 0.740 | 63 |
| `operating_income_to_liabilities` | quality | 0.733 | 63 |
| `operating_income_to_current_liabilities` | quality | 0.731 | 63 |
| `qual_roe` | quality | 0.689 | 63 |
| `pretax_roa` | quality | 0.684 | 63 |
| `net_roa` | quality | 0.653 | 63 |
| `quality_stability` | quality | 0.610 | 63 |
| `net_profit_margin` | quality | 0.585 | 63 |
| `profitable_small_value` | quality | 0.543 | 63 |
| `value_sp` | value | 0.451 | 63 |
| `retained_earnings_to_equity` | quality | 0.439 | 63 |
| `paid_in_capital_ratio` | quality | 0.413 | 63 |

## Expected relationship and data notes

- Expected relationship: 가장 가까운 기존 팩터: value_ep — 차이: 세후 순이익 대신 핵심 영업이익을 사용해 자본구조·세금·비경상손익 이전의 영업가치 저평가를 측정한다.
- Data notes: DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 동월 양의 market_cap을 사용한다. 음의 영업이익은 그대로 유지하며 기업가치 대신 자기자본 시가총액을 분모로 써 부채가 큰 기업의 값이 높아질 수 있는 한계는 leverage 중립화 gate로 진단한다.
