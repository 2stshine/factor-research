# cycle-0191-amihud_mean_36m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-004` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `cfe4789e79158516`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/amihud_mean_36m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 36개월 Amihud 가격충격 비유동성의 mean가 높은 종목은 유동성 보상 또는 과도한 관심 교정으로 이후 상대수익이 높다.

## Mechanism

거래 규모를 기업가치로 정규화하거나 가격충격을 직접 측정해 단순 대형주 노출과 구분한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 36 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.9201538944002937 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.9069474979872422 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.02747370757937356 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.02724255297181629 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.35302936711939936 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.02747370757937356 |
| `ic_t_full` | 2.9882121269706006 |
| `ic_p_full` | 0.0020195938288482375 |
| `ic_investable` | 0.02724255297181629 |
| `ic_std_investable` | 0.07716795119371042 |
| `rank_icir_investable` | 0.35302936711939936 |
| `ic_t_investable` | 2.9252465894382618 |
| `ic_p_investable` | 0.002413625814274669 |
| `ic_retention` | 0.9915863337014327 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.02747370757937356 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.02724255297181629 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `amihud_volatility_36m` | other | -0.977 | 63 |
| `amihud_mean_24m` | other | 0.961 | 63 |
| `amihud_volatility_24m` | other | -0.951 | 63 |
| `amihud_mean_18m` | other | 0.932 | 63 |
| `amihud_volatility_18m` | other | -0.926 | 63 |
| `amihud_volatility_12m` | other | -0.891 | 63 |
| `amihud_mean_6m` | other | 0.841 | 63 |
| `amihud_volatility_6m` | other | -0.836 | 63 |
| `amihud_illiquidity_1m` | other | 0.758 | 63 |
| `size` | size | 0.723 | 63 |
| `small_value` | value | 0.601 | 63 |
| `earnings_confirmed_small_value` | earnings | 0.522 | 63 |
| `defensive_small_value` | value | 0.466 | 63 |
| `turnover_volatility_12m` | other | -0.464 | 63 |
| `profitable_small_value` | quality | 0.448 | 63 |

## Expected relationship and data notes

- Expected relationship: 기존 유동성 수준·변화 신호와 관련될 수 있어 Gold 상관 gate로 독립성을 확인한다.
- Data notes: 인증된 월말 거래·시가총액·Amihud 입력만 사용하며 결측을 채우지 않는다.
