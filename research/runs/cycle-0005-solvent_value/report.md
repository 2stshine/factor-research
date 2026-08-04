# cycle-0005-solvent_value

- Verdict: **REJECT**
- Definition hash: `fb56009a013e76e1`
- Data cutoff / ruleset: `2026-08-03` / `fr-2.0.0`
- Strategy file: `factors/candidates/solvent_value.py`

## Hypothesis

월별 장부가치/시가총액 순위와 저부채 순위를 동등 결합한 종목을 보유하면, 가격 변동성으로 가치함정을 거르는 방식보다 펀더멘털에 기반한 안정적인 비용 후 초과수익을 얻는다.

## Mechanism

가치 프리미엄에는 과잉반응 교정과 재무적 곤경 보상이 함께 섞인다. 낮은 레버리지는 값이 싼 이유가 지급능력 악화인 기업을 줄여, 회복 가능한 저평가와 구조적 부실을 구분한다.

## Pre-registered falsification

투자가능 유니버스에서 IC가 유지되지 않거나, 비용 후 순알파와 IR이 충분하지 않거나, 강건성·OOS·다중검정 또는 기존 Gold 직교성 검사를 통과하지 못하면 가설을 기각한다.

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
| T1.1 | 전체 커버리지 | Y | 0.8777913699204022 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.6023217247097846 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 총수익 필드 | Y | None | Silver total_return_close |
| T2.1 | 투자가능 IC 유지율 | Y | 0.9942928517583594 | >=0.5 & 양수 |
| T2.1 | 투자가능 IC HAC 유의성 | Y | 2.8858366303706097e-09 | one-sided p<=0.05 |
| T2.2 | 미래수익 결측 | Y | 0.0009442095324110185 | <=1.0% |
| T2.3 | 회전율 | Y | 211.1181529916456 | <=400.0%/yr |
| T2.4 | 실비용 순알파 | N | 1.6923260244596259 | >=3.0%/yr |
| T2.4 | net_IR | N | 0.3720984437985027 | >=0.74 |

## Result

| metric | value |
|---|---:|
| `ic_full` | 0.04945188586373906 |
| `ic_t_full` | 4.464755768755978 |
| `ic_p_full` | 1.124579892267654e-05 |
| `months` | 71 |
| `turnover` | 211.1181529916456 |
| `gross` | 2.7327325415288577 |
| `cost` | 1.0404065170692325 |
| `net` | 1.6923260244596259 |
| `net_ir` | 0.3720984437985027 |
| `hac_t` | 0.6944494108876049 |
| `hac_pvalue` | 0.24484946280512407 |
| `missing_return_rate` | 0.0009442095324110185 |
| `null_count` | 100 |
| `realized_fdr` | 0.0 |

### Failed checks

- `T2.4` 실비용 순알파: 1.6923260244596259 (>=3.0%/yr)
- `T2.4` net_IR: 0.3720984437985027 (>=0.74)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `value_bp` | value | 0.667 | 126 |
| `qual_lev` | quality | 0.661 | 126 |
| `defensive_value` | value | 0.578 | 126 |
| `value_ep` | value | 0.338 | 114 |
| `low_vol_12m` | other | 0.283 | 126 |
| `value_sp` | value | 0.219 | 114 |
| `qual_opm` | quality | 0.183 | 114 |
| `downside_vol_12m` | other | 0.180 | 126 |
| `qual_roe` | quality | 0.153 | 114 |
| `asset_growth_12m` | other | 0.116 | 114 |
| `mom_12_1` | momentum | -0.111 | 126 |
| `size` | size | 0.100 | 126 |
| `asset_turnover` | quality | -0.058 | 114 |
| `rev_1m` | momentum | 0.023 | 126 |
| `sue` | earnings | -0.020 | 102 |

## Expected relationship and data notes

- Expected relationship: value_bp 및 저부채 방향의 qual_lev와 높은 양의 관계를 예상한다. 가격 변동성을 쓰지 않으므로 low_vol_12m 및 defensive_value와는 중간 수준의 관계를 예상한다.
- Data notes: Silver PIT total_equity, total_liabilities와 월말 market_cap을 사용한다. 부채비율이 정의되지 않는 자기자본 0 이하 기업은 신호가 결측이며 재무상태표 stock 값을 분기 차감하지 않는다.
