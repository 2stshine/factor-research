# cycle-0093-capital_stock_to_assets

- Verdict: **PRE_FDR / PROVISIONAL**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260815-007` / `epoch-001`
- OOS: **SEALED**
- Definition hash: `dd1d0d32a2a49a3c`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.14.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/capital_stock_to_assets.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

Silver PIT capital_stock/total_assets가 낮은 종목은 이후 수익률 순위가 높을 것이다.

## Mechanism

명목 납입자본을 적게 사용하고 같은 자산기반을 유지하는 기업은 누적 내부성장과 자본효율이 높을 수 있다.

## Pre-registered falsification

자동 gate, BY, 봉인 OOS, 귀무 또는 자본구성 신호 직교성이 실패하면 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.9565852576507392 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9490393818427995 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | Y | 0.040632681056799014 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | Y | 0.04169846153277925 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.5525290762879519 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |
| T3.1 | 비중첩 구간 IC 방향 | Y | 4 | >=3/4 |
| T3.1 | IC 레짐 집중도 | Y | 0.39543221592736927 | <=0.6 |
| T3.2 | 시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율 | Y | 0.026418348505024447 | IC>=0.01 & neutral/investable>=0.3 (size category는 규모 노출 보존; HAC p는 진단값) |
| T4.3 | 다중검정 FDR | PENDING | None | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.5116095116669102 | 각 Gold 비교월>=36 & max_j median_t \|rho\|<=0.7 |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.040632681056799014 |
| `ic_t_full` | 5.686873387639641 |
| `ic_p_full` | 1.949260317483298e-07 |
| `ic_investable` | 0.04169846153277925 |
| `ic_std_investable` | 0.07546835691059268 |
| `rank_icir_investable` | 0.5525290762879519 |
| `ic_t_investable` | 5.88996514151936 |
| `ic_p_investable` | 8.939021715666437e-08 |
| `ic_retention` | 1.0262296370374975 |
| `neutral_ic` | 0.026418348505024447 |
| `neutral_ic_t` | 4.165468482536791 |
| `neutral_ic_p` | 4.9704965100173074e-05 |
| `neutral_ic_retention` | 0.6335569115483296 |
| `n_trials` | 104 |
| `max_gold_signal_corr` | 0.5116095116669102 |
| `gold_signal_comparison_months` | {'current_asset_turnover': 62, 'idiosyncratic_volatility_24m': 62, 'net_income_to_liabilities': 62, 'operating_earnings_yield': 62, 'retained_earnings_to_equity': 62} |

### Failed checks

- 없음

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `paid_in_capital_ratio` | quality | 0.929 | 63 |
| `capital_stock_to_liabilities` | quality | -0.864 | 63 |
| `retained_earnings_to_capital_stock` | quality | 0.772 | 63 |
| `retained_earnings_to_equity` | quality | 0.512 | 63 |
| `operating_earnings_yield` | value | 0.435 | 63 |
| `retained_earnings_to_assets` | quality | 0.434 | 63 |
| `net_roa_volatility_36m` | quality | 0.388 | 52 |
| `size` | size | -0.386 | 63 |
| `value_ep` | value | 0.381 | 63 |
| `pretax_roa_volatility_36m` | quality | 0.369 | 52 |
| `retained_earnings_to_liabilities` | quality | 0.367 | 63 |
| `net_margin_volatility_36m` | quality | 0.366 | 52 |
| `pretax_margin_volatility_36m` | quality | 0.348 | 52 |
| `pretax_income_to_current_assets` | quality | 0.346 | 63 |
| `realized_volatility_252d` | other | 0.344 | 63 |

## Expected relationship and data notes

- Expected relationship: paid_in_capital_ratio와 관련되지만 자기자본이 아닌 총자산 대비 명목자본을 측정한다.
- Data notes: DART available_date PIT 자본금과 양의 총자산만 사용한다.
