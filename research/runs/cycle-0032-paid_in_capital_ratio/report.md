# cycle-0032-paid_in_capital_ratio

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260806-001` / `epoch-002`
- OOS: **SEALED**
- Definition hash: `8c82db0117290bcd`
- Data cutoff / ruleset: `2026-07-31` / `fr-3.5.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/paid_in_capital_ratio.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT의 자본금/자기자본 비율이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

자기자본에서 명목 자본금이 차지하는 비중이 낮으면 이익잉여금·자본잉여 등 사업을 통해 축적되거나 명목 자본금 밖에서 형성된 완충력이 상대적으로 크다는 뜻일 수 있다. 시장이 이 자본 구성의 질을 충분히 구분하지 않으면 이후 재평가가 나타날 수 있다.

## Pre-registered falsification

낮은 자본금 비중 방향이 전체·투자 가능 IC, Rank ICIR, 기간·중립화 강건성을 통과하지 못하거나 기존 내부금융 신호와 중복되면 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다.

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
| T1.1 | 전체 커버리지 | Y | 0.9633933263563559 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9424408520086033 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 전체 IC 최소요건 | Y | 0.05288540710165645 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.05794639793821009 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.7391553836966577 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.3595843915124998 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC | Y | 0.03232602275053229 | IC>=0.01 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.0 | median \|rho\|<=0.8 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.05288540710165645 |
| `ic_t_full` | 8.523666904125344 |
| `ic_p_full` | 8.94804330272179e-14 |
| `ic_investable` | 0.05794639793821009 |
| `ic_std_investable` | 0.07839542160730678 |
| `rank_icir_investable` | 0.7391553836966577 |
| `ic_t_investable` | 8.55564811626292 |
| `ic_p_investable` | 7.630161380255281e-14 |
| `ic_retention` | 1.0956973031676847 |
| `months` | 82 |
| `turnover` | 31.734923127652742 |
| `gross` | 0.6745393248734999 |
| `cost` | 0.15549130667490968 |
| `net` | 0.5190480181985901 |
| `net_ir` | 0.10299539436526332 |
| `hac_t` | 0.2835770851138811 |
| `hac_pvalue` | 0.3887290280972716 |
| `missing_return_rate` | 0.00044141904607020887 |
| `neutral_ic` | 0.03232602275053229 |
| `neutral_ic_t` | 6.945708630204122 |
| `neutral_ic_p` | 2.0050205587372383e-10 |
| `n_trials` | 44 |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `retained_earnings_to_assets` | quality | 0.584 | 101 |
| `value_ep` | value | 0.431 | 101 |
| `net_profit_margin` | quality | 0.409 | 101 |
| `net_roa` | quality | 0.408 | 101 |
| `qual_opm` | quality | 0.403 | 101 |
| `size` | size | -0.401 | 101 |
| `operating_roa` | quality | 0.385 | 101 |
| `quality_stability` | quality | 0.383 | 101 |
| `qual_roe` | quality | 0.380 | 101 |
| `solvent_value` | value | 0.376 | 101 |
| `defensive_value` | value | 0.339 | 101 |
| `value_bp` | value | 0.313 | 101 |
| `downside_vol_12m` | other | 0.287 | 101 |
| `operating_roa_volatility_36m` | quality | 0.277 | 90 |
| `net_equity_issuance_12m` | other | 0.273 | 101 |

## Expected relationship and data notes

- Expected relationship: retained_earnings_to_assets의 내부축적 방향과 일부 관계가 예상되지만, 본 후보는 총자산이 아니라 자기자본 내부의 명목 자본금 구성만 본다. net_equity_issuance_12m은 최근 조달 변화량이므로 현재 구성 수준인 본 후보와 구별된다.
- Data notes: DART available_date 순으로 재생한 Silver PIT capital_stock과 total_equity를 사용하고 양의 자기자본에서만 정의한다. capital_stock은 총 외부조달액이 아니라 법정 명목 자본금이며, 주식발행초과금·기타자본은 포함하지 않는다. 감자·증자·합병으로 구조적 단절이 생길 수 있다.
