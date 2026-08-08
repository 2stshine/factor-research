# cycle-0034-net_working_capital_to_assets

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260807-002` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `8dbeb79579b0e9eb`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.9.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/net_working_capital_to_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 (current_assets-current_liabilities)/total_assets가 높은 종목은 낮은 종목보다 다음 달 총수익률 순위가 높을 것이다.

## Mechanism

순운전자본 완충력은 영업 충격을 흡수하고 강제 차입·증자·자산매각을 피할 여력을 나타낸다. 시장이 이 재무 유연성의 지속성과 하방 보호를 충분히 반영하지 못하면 이후 가격에 점진적으로 반영될 수 있다.

## Pre-registered falsification

현재 ruleset의 무결성·커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9619515174926001 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9494182910709673 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | N | 0.010081605769902118 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.012046946188656607 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.22700549436366926 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.010081605769902118 |
| `ic_t_full` | 2.2307861477506634 |
| `ic_p_full` | 0.013976102856257461 |
| `ic_investable` | 0.012046946188656607 |
| `ic_std_investable` | 0.053068963032925784 |
| `rank_icir_investable` | 0.22700549436366926 |
| `ic_t_investable` | 2.4981786993983173 |
| `ic_p_investable` | 0.0070653227497883804 |
| `ic_retention` | 1.1949431929407384 |
| `months` | 75 |
| `turnover` | 78.45174983485654 |
| `gross` | -1.0692248767460077 |
| `cost` | 0.36671201176914203 |
| `net` | -1.4359368885151496 |
| `net_ir` | -0.34624823736304255 |
| `hac_t` | -0.9349801652848116 |
| `hac_pvalue` | 0.8235801857782976 |
| `missing_return_rate` | 0.0006505122784192552 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.010081605769902118 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.012046946188656607 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `current_ratio` | quality | 0.951 | 101 |
| `qual_lev` | quality | 0.719 | 101 |
| `solvent_value` | value | 0.406 | 101 |
| `quality_stability` | quality | 0.385 | 101 |
| `retained_earnings_to_assets` | quality | 0.354 | 101 |
| `working_capital_accruals_12m` | quality | -0.325 | 101 |
| `value_sp` | value | -0.325 | 101 |
| `net_profit_margin` | quality | 0.290 | 101 |
| `net_roa` | quality | 0.282 | 101 |
| `nonoperating_burden_to_assets` | quality | 0.242 | 101 |
| `qual_roe` | quality | 0.198 | 101 |
| `qual_opm` | quality | 0.193 | 101 |
| `operating_roa` | quality | 0.188 | 101 |
| `value_ep` | value | 0.157 | 101 |
| `paid_in_capital_ratio` | quality | 0.137 | 101 |

## Expected relationship and data notes

- Expected relationship: current_ratio와 양의 관계, current_liability_concentration 및 레버리지와 음의 관계를 예상한다. 유동비율이나 12개월 운전자본 변화가 아니라 총자산 대비 순유동 완충력의 수준이므로 정의는 구별된다.
- Data notes: DART available_date 순으로 재생한 current_assets, current_liabilities, total_assets를 사용한다. 총자산이 양수일 때만 정의하고 음의 순운전자본은 보존한다. 금융업에서는 유동·비유동 분류의 의미가 다를 수 있으나 사후 표본 제외는 하지 않는다.
