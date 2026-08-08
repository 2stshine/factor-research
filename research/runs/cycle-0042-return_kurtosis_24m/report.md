# cycle-0042-return_kurtosis_24m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-003`
- OOS: **SEALED**
- Definition hash: `be70b24e1222fb72`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/return_kurtosis_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver 총수익지수로 계산한 최근 24개월 월수익률 초과첨도가 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

극단 수익이 자주 나타나는 종목은 복권형 상승 가능성에 대한 과잉수요나 집중된 사건위험을 포함할 수 있다. 이런 수요가 가격을 높이면 높은 꼬리 집중도의 미래 기대수익이 낮아진다.

## Pre-registered falsification

사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9617673612202824 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.956434658207377 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.04285144413285035 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04550329555197513 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.8583036080259664 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.32290816971625547 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.025019884928358348 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.04285144413285035 |
| `ic_t_full` | 8.216643878615987 |
| `ic_p_full` | 4.1129957901178294e-13 |
| `ic_investable` | 0.04550329555197513 |
| `ic_std_investable` | 0.05301538421425174 |
| `rank_icir_investable` | 0.8583036080259664 |
| `ic_t_investable` | 8.499835808952195 |
| `ic_p_investable` | 1.0075516502705187e-13 |
| `ic_retention` | 1.061884761944157 |
| `months` | 90 |
| `turnover` | 148.38755622719935 |
| `gross` | 1.6624984485546477 |
| `cost` | 0.6720613797585648 |
| `net` | 0.990437068796083 |
| `net_ir` | 0.31468264636097326 |
| `hac_t` | 0.9185990006081795 |
| `hac_pvalue` | 0.1803941008267007 |
| `missing_return_rate` | 0.00023232581372116255 |
| `neutral_ic` | 0.025019884928358348 |
| `neutral_ic_t` | 6.061480762975246 |
| `neutral_ic_p` | 1.2289079082733573e-08 |
| `neutral_ic_retention` | 0.5498477555275076 |
| `n_trials` | 54 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `return_skewness_24m` | other | 0.679 | 101 |
| `max_monthly_return_12m` | other | 0.341 | 101 |
| `low_vol_12m` | other | 0.311 | 101 |
| `turnover_volatility_12m` | other | 0.292 | 101 |
| `defensive_value` | value | 0.215 | 101 |
| `quality_stability` | quality | 0.215 | 101 |
| `trading_turnover_20d` | other | 0.164 | 101 |
| `downside_vol_12m` | other | 0.163 | 101 |
| `paid_in_capital_ratio` | quality | 0.153 | 101 |
| `operating_roa` | quality | 0.140 | 101 |
| `qual_opm` | quality | 0.137 | 101 |
| `positive_return_share_12m` | momentum | 0.136 | 101 |
| `operating_return_on_capital_employed` | quality | 0.132 | 101 |
| `net_roa` | quality | 0.128 | 101 |
| `qual_roe` | quality | 0.126 | 101 |

## Expected relationship and data notes

- Expected relationship: return_skewness_24m, max_monthly_return_12m 및 변동성 계열과 일부 관계가 가능하지만, 방향이나 분산이 아니라 분포 양쪽 꼬리의 집중도를 측정한다.
- Data notes: Silver total_return_close로 월수익률을 계산한다. 연속 24개월 창에서 최소 18개 유효 관측을 요구하며 분산이 없어 첨도가 정의되지 않으면 결측으로 둔다.
