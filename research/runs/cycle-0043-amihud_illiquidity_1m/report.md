# cycle-0043-amihud_illiquidity_1m

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260808-001` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `72bd57d66a5cb84d`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.10.1`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/amihud_illiquidity_1m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 한 달의 일별 |총수익률|/거래대금 평균이 큰 종목은 작은 종목보다 이후 총수익률 순위가 높을 것이다.

## Mechanism

투자자는 현금화가 어렵고 주문의 가격충격이 큰 자산을 보유하기 위해 추가 보상을 요구할 수 있다.

## Pre-registered falsification

투자가능 유니버스 IC와 기간 강건성이 유지되지 않거나 trading_turnover_20d·size와의 중복이 기준을 넘거나 정식 confirmation에 실패하면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.966171755087154 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9539384174356479 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | Silver total_return_close / krx_gross_dividend_reinvested_v1 / CERTIFIED |
| T2.1 | 전체 IC 최소요건 | Y | 0.08603294288231207 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.08603294288231207 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.962809542052087 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.33112798002001775 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | N | 0.01835219260533601 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 직교성 | Y | 0.0 | 기존 APPROVED와 비교 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.08603294288231207 |
| `ic_t_full` | 8.123797207051451 |
| `ic_p_full` | 1.3470884073516229e-11 |
| `ic_investable` | 0.08603294288231207 |
| `ic_std_investable` | 0.08935613859719908 |
| `rank_icir_investable` | 0.962809542052087 |
| `ic_t_investable` | 8.123797207051451 |
| `ic_p_investable` | 1.3470884073516229e-11 |
| `ic_retention` | 1.0 |
| `months` | 62 |
| `turnover` | 281.88832418227065 |
| `gross` | 18.889985585200197 |
| `cost` | 1.3504780890254788 |
| `net` | 17.539507496174718 |
| `net_ir` | 2.8200747397676214 |
| `hac_t` | 6.899400074310541 |
| `hac_pvalue` | 1.7245489309219637e-09 |
| `missing_return_rate` | 0.0 |
| `neutral_ic` | 0.01835219260533601 |
| `neutral_ic_t` | 3.0614156881671297 |
| `neutral_ic_p` | 0.0016369850555439274 |
| `neutral_ic_retention` | 0.2133158763433295 |
| `n_trials` | 2 |
| `max_gold_signal_corr` | 0.0 |
| `gold_signal_comparison_months` | {} |

### Failed checks

- `T3.2` 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율: 0.01835219260533601 (IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `size` | size | 0.746 | 63 |
| `small_value` | value | 0.698 | 63 |
| `defensive_small_value` | value | 0.649 | 63 |
| `earnings_confirmed_small_value` | earnings | 0.590 | 63 |
| `profitable_small_value` | quality | 0.512 | 63 |
| `trading_turnover_20d` | other | 0.425 | 63 |
| `value_bp` | value | 0.354 | 63 |
| `defensive_value` | value | 0.343 | 63 |
| `solvent_value` | value | 0.308 | 63 |
| `mom_12_1` | momentum | -0.278 | 63 |
| `turnover_volatility_12m` | other | -0.270 | 63 |
| `operating_return_on_capital_employed` | quality | -0.249 | 63 |
| `operating_roa` | quality | -0.245 | 63 |
| `max_daily_return_1m` | other | 0.239 | 63 |
| `equity_growth_12m` | other | 0.230 | 63 |

## Expected relationship and data notes

- Expected relationship: 낮은 거래활동을 나타내는 trading_turnover_20d의 최종 방향 및 소형주 방향과 관계가 예상되지만, 거래량 수준이 아니라 단위 거래대금당 가격충격을 측정한다.
- Data notes: 인증된 Silver 일별 total_return_close 수익률과 양의 trading_value만 사용해 월별 평균을 만든다. 월중 최소 10개 유효 관측이 필요하며 호가스프레드의 직접 측정치는 아니다.
