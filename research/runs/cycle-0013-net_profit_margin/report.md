# cycle-0013-net_profit_margin

- Verdict: **PROVISIONAL**
- Definition hash: `a1e679b213e5f339`
- Data cutoff / ruleset: `2026-08-03` / `fr-3.2.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_profit_margin.py`

## Hypothesis

Silver PIT의 최근 12개월 순이익을 같은 기간 매출액으로 나눈 단일 순이익률이 높은 종목은 이후 수익률 순위도 높을 것이다.

## Mechanism

높은 순이익률은 가격결정력과 비용 통제뿐 아니라 이자·세금·비영업 항목까지 통과한 최종 수익성을 뜻한다. 투자자가 일시적 비용 충격과 지속 가능한 전사적 효율을 충분히 구분하지 못하면 높은 최종 마진 기업이 점진적으로 재평가될 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, 고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 T0~T5 게이트를 순차 적용했다. 앞 단계 hard fail 이후의 검사는 실행하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.1 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.926871166722317 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9001897703170382 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.04469877984247859 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.0617219865528497 | >=0.02 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7579601536707269 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 1.6063264635396346e-09 | one-sided p<=0.1 |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.30275229066571574 | <=0.6 |
| T3.2 | 시장·규모·유동성 중립 IC | Y | 0.04580850551272796 | IC>=0.01 & p<=0.1 |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS IC | Y | 0.09099468977840146 | IC>=0.02 & p<=0.1 |
| T4.3 | 다중검정 FDR | Y | 1.6063264635396346e-09 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.20015894284932986 | median \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `ic_full` | 0.04469877984247859 |
| `ic_t_full` | 6.701029019812438 |
| `ic_p_full` | 3.104230935188937e-09 |
| `ic_investable` | 0.0617219865528497 |
| `ic_std_investable` | 0.08143170357166687 |
| `rank_icir_investable` | 0.7579601536707269 |
| `ic_t_investable` | 6.8646635264974085 |
| `ic_p_investable` | 1.6063264635396346e-09 |
| `ic_retention` | 1.3808427605935107 |
| `months` | 59 |
| `turnover` | 139.40276327219672 |
| `gross` | 2.8705143388628014 |
| `cost` | 0.6733933577587651 |
| `net` | 2.1971209811040358 |
| `net_ir` | 0.3639219989725929 |
| `hac_t` | 0.7896637952110316 |
| `hac_pvalue` | 0.21647033138274108 |
| `missing_return_rate` | 0.0003221130616846513 |
| `neutral_ic` | 0.04580850551272796 |
| `neutral_ic_t` | 5.33133646586696 |
| `neutral_ic_p` | 6.779487234948833e-07 |
| `oos_start` | 2023-09 |
| `oos_months` | 35 |
| `oos_ic` | 0.09099468977840146 |
| `oos_ic_t` | 7.749684163284097 |
| `oos_ic_p` | 2.571827460808977e-09 |
| `n_trials` | 25 |
| `fdr_qvalue` | 1.6063264635396346e-09 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_roe` | quality | 0.903 | 102 |
| `qual_opm` | quality | 0.840 | 102 |
| `operating_roa` | quality | 0.791 | 102 |
| `value_ep` | value | 0.783 | 102 |
| `quality_stability` | quality | 0.614 | 102 |
| `profitable_small_value` | quality | 0.366 | 102 |
| `asset_growth_12m` | other | -0.323 | 102 |
| `qual_lev` | quality | 0.320 | 102 |
| `downside_vol_12m` | other | 0.318 | 102 |
| `solvent_value` | value | 0.270 | 102 |
| `size` | size | -0.260 | 102 |
| `sue` | earnings | 0.250 | 102 |
| `high_12m_proximity` | momentum | 0.206 | 102 |
| `low_vol_12m` | other | 0.198 | 102 |
| `mom_12_1` | momentum | 0.187 | 102 |

## Expected relationship and data notes

- Expected relationship: 영업이익률인 qual_opm 및 자기자본 수익성인 qual_roe와 양의 관계를 예상한다. 다만 분모가 매출이고 이자·세금·비영업손익을 포함하므로 두 팩터와 완전히 같지는 않을 것으로 예상한다. 가치·모멘텀 팩터와의 관계는 상대적으로 낮을 것으로 예상한다.
- Data notes: DART available_date 순으로 정정공시를 재생한 Silver PIT net_income_ttm과 revenue_ttm만 사용한다. 매출액이 0 이하인 관측은 비율이 정의되지 않아 결측으로 두며, 금융업처럼 매출 정의가 일반 제조업과 다른 업종에서는 경제적 의미가 달라질 수 있다.
