# cycle-0010-quality_stability

- Verdict: **REJECT**
- Definition hash: `c4315c8db6ef4e63`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/quality_stability.py`

## Hypothesis

월별 영업ROA·자산회전율·자기자본비율·12개월 저변동성 순위를 동일 비중으로 결합하면, 단일 회계비율의 잡음을 줄이고 지속 가능한 품질을 가진 종목에서 롱온리 초과수익을 얻는다.

## Mechanism

높은 수익성과 효율성은 경쟁우위를, 높은 자기자본비율은 재무 충격 흡수력을, 낮은 가격 변동성은 취약성과 복권형 수요의 부재를 나타낸다. 네 신호가 함께 높은 기업의 이익 지속성을 시장이 보수적으로 평가하면 점진적인 재평가가 발생한다.

## Pre-registered falsification

투자가능 IC와 비용 후 성과가 충분하지 않거나, 리밸런싱·비용·기간·중립화 강건성, 고정 OOS, 다중검정 또는 Gold 직교성 중 하나라도 hard fail이면 안정적 품질 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.926431503979891 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9995883414380524 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | Y | 1.1406840255340207 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 6.097969036772269e-15 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0003228410008071025 | <=1.0% |
| T2.3 | 회전율 | Y | 163.1789289461385 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | Y | 3.176021683157032 | >=3.0%/yr |
| T2.4 | net_IR | N | 0.5406030719256092 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.06654787254015121 |
| `ic_t_full` | 9.13113490003376 |
| `ic_p_full` | 9.179576006704757e-15 |
| `months` | 83 |
| `turnover` | 163.1789289461385 |
| `gross` | 3.982739847566199 |
| `cost` | 0.8067181644091672 |
| `net` | 3.176021683157032 |
| `net_ir` | 0.5406030719256092 |
| `hac_t` | 1.3545001555311262 |
| `hac_pvalue` | 0.08964871178076504 |
| `missing_return_rate` | 0.0003228410008071025 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.4` net_IR: 0.5406030719256092 (>=0.74)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `qual_roe` | quality | 0.666 | 114 |
| `qual_opm` | quality | 0.649 | 114 |
| `value_ep` | value | 0.625 | 114 |
| `low_vol_12m` | other | 0.567 | 128 |
| `asset_turnover` | quality | 0.538 | 114 |
| `downside_vol_12m` | other | 0.493 | 128 |
| `defensive_value` | value | 0.456 | 126 |
| `solvent_value` | value | 0.436 | 126 |
| `qual_lev` | quality | 0.412 | 126 |
| `defensive_small_value` | value | 0.303 | 126 |
| `value_sp` | value | 0.256 | 114 |
| `high_12m_proximity` | momentum | 0.246 | 128 |
| `size` | size | -0.200 | 128 |
| `value_bp` | value | 0.189 | 126 |
| `sue` | earnings | 0.130 | 102 |

## Expected relationship and data notes

- Expected relationship: qual_opm, asset_turnover, qual_lev 및 low_vol_12m과 양의 관계를 예상하지만 네 축의 동등 결합이므로 어느 단일 팩터와도 완전히 같지는 않을 것으로 예상한다. 가치·소형 팩터와는 낮은 관계를 예상한다.
- Data notes: Silver PIT operating_income_ttm, revenue_ttm, total_assets, total_equity와 total_return_close를 사용한다. 회계항목이 없는 관측은 해당 회계축만 중립 순위 0.5로 두며, 최초 12개월은 가격 안정성 계산 때문에 의도적으로 결측이다.
