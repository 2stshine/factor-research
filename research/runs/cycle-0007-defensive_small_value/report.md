# cycle-0007-defensive_small_value

- Verdict: **REJECT**
- Definition hash: `5ca0936652af719a`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/defensive_small_value.py`

## Hypothesis

월별 가치·소형·12개월 저변동성 순위를 동등 결합한 종목을 보유하면, 소형가치의 높은 초과수익을 유지하면서 투자 가능 유니버스의 신호 보존성과 수익 안정성을 개선한다.

## Mechanism

저평가된 소형주는 정보 반영이 느리지만 일부 성과는 거래가 어렵고 취약한 종목에서 나온다. 가격 안정성은 지속적인 악재 재평가와 복권형 변동이 큰 종목을 줄여, 거래 가능한 정보 비대칭 프리미엄을 분리한다.

## Pre-registered falsification

투자가능 IC 유지율과 비용 후 성과가 충분하지 않거나, 리밸런싱·분위수·비용·기간·중립화 강건성, 고정 OOS, 다중검정 또는 Gold 직교성 중 하나라도 hard fail이면 가설을 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 T0~T5 게이트를 순차 적용했다. 앞 단계 hard fail 이후의 검사는 실행하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.3 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.3 | 유한값 | Y | None | ±inf 없음 |
| T0.4 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.4 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8801675743611227 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.6048051684183939 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | Y | 0.8247982635604296 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 2.6593761862478902e-06 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0011494724742395009 | <=1.0% |
| T2.3 | 회전율 | Y | 293.30779073016527 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | Y | 5.1830286329359 | >=3.0%/yr |
| T2.4 | net_IR | Y | 0.7802811816959629 | >=0.74 |
| T3.1 | 리밸런싱 고원성 | Y | None | 1/3/6개월 모두 양수, max/min<=3.0 |
| T3.1 | 분위수 강건성 | Y | None | 10/20/30% 모두 순알파 > 0 |
| T3.2 | 2배 비용 스트레스 | Y | 3.7427330049609795 | >0%/yr |
| T3.2 | 상폐 -100% 포트폴리오 | Y | 5.085265440600552 | >0%/yr |
| T3.3 | 비중첩 구간 순알파 | Y | 3 | >=3/4 |
| T3.3 | 레짐 집중도 | Y | 0.5064973932543774 | <=0.6 |
| T3.4 | 시장·규모·유동성 중립 | Y | 2.7964684732935265 | >0%/yr |
| T3.4 | 섹터 중립화 가능 | N | 0.0 | >=80% sector coverage |
| T4.1 | 고정 OOS | N | 0.5367684641536954 | net>0 & HAC p<=0.1 |
| T4.2 | Deflated Sharpe | N | 0.17769063138683222 | >=95% |
| T4.3 | 다중검정 FDR | N | 0.5362189197265829 | BY q<=0.1 |
| T5.1 | Gold 신호 직교성 | Y | 0.5875503781156431 | median \|rho\|<=0.8 |
| T5.1 | Gold 수익 직교성 | Y | 0.0 | \|rho\|<=0.8 |
| T4.4 | 게이트 귀무 보정 | Y | 0.0 | n>=100 & FPR<=10% |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.0817702733388386 |
| `ic_t_full` | 5.167316595079461 |
| `ic_p_full` | 7.090798557788639e-07 |
| `months` | 70 |
| `turnover` | 293.30779073016527 |
| `gross` | 6.623324260910819 |
| `cost` | 1.4402956279749204 |
| `net` | 5.1830286329359 |
| `net_ir` | 0.7802811816959629 |
| `hac_t` | 1.6197653397086205 |
| `hac_pvalue` | 0.05492230095018244 |
| `missing_return_rate` | 0.0011494724742395009 |
| `oos_start` | 2023-09 |
| `oos_months` | 31 |
| `oos_net` | -0.6102548926192001 |
| `oos_ir` | -0.05568364238617479 |
| `oos_hac_pvalue` | 0.5367684641536954 |
| `n_trials` | 19 |
| `dsr_probability` | 0.17769063138683222 |
| `fdr_qvalue` | 0.5362189197265829 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T3.4` 섹터 중립화 가능: 0.0 (>=80% sector coverage)
- `T4.1` 고정 OOS: 0.5367684641536954 (net>0 & HAC p<=0.1)
- `T4.2` Deflated Sharpe: 0.17769063138683222 (>=95%)
- `T4.3` 다중검정 FDR: 0.5362189197265829 (BY q<=0.1)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `defensive_value` | value | 0.866 | 126 |
| `small_value` | value | 0.847 | 126 |
| `value_bp` | value | 0.813 | 126 |
| `low_vol_12m` | other | 0.613 | 126 |
| `value_sp` | value | 0.597 | 114 |
| `solvent_value` | value | 0.563 | 126 |
| `size` | size | 0.407 | 126 |
| `downside_vol_12m` | other | 0.353 | 126 |
| `mom_12_1` | momentum | -0.284 | 126 |
| `value_ep` | value | 0.242 | 114 |
| `asset_growth_12m` | other | 0.164 | 114 |
| `asset_turnover` | quality | 0.138 | 114 |
| `sue` | earnings | -0.061 | 102 |
| `qual_lev` | quality | -0.048 | 126 |
| `qual_opm` | quality | -0.012 | 114 |

## Expected relationship and data notes

- Expected relationship: small_value와 가장 높은 양의 관계를 예상하고 value_bp, size, low_vol_12m과도 중간 이상의 양의 관계를 예상한다. 세 축 결합으로 단일 팩터와 완전히 같지는 않을 것으로 예상한다.
- Data notes: Silver PIT total_equity, 월말 market_cap 및 total_return_close를 사용한다. 각 구성요소는 월별 횡단면 순위이며 최초 12개월은 변동성 계산 때문에 의도적으로 결측이다.
