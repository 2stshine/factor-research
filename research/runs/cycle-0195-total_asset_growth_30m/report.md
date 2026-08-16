# cycle-0195-total_asset_growth_30m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-004` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `b86e2e75202e6433`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/total_asset_growth_30m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 30개월 total_assets 증가율이 낮은 기업은 과잉투자·자산팽창 위험이 작아 이후 상대수익이 높다.

## Mechanism

PIT 재무규모의 시간 변화를 이용해 경영자의 자본배분과 투자 확대를 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 30 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.794759023703715 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.6173169524428255 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.013158164278798977 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.015020544879916328 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | Y | 0.1937999779610551 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.013158164278798977 |
| `ic_t_full` | 1.4498372994500361 |
| `ic_p_full` | 0.07624503683889637 |
| `ic_investable` | 0.015020544879916328 |
| `ic_std_investable` | 0.07750540035115364 |
| `rank_icir_investable` | 0.1937999779610551 |
| `ic_t_investable` | 1.5387315514055004 |
| `ic_p_investable` | 0.06465403637566872 |
| `ic_retention` | 1.1415380262517396 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.013158164278798977 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.015020544879916328 (>=0.03)

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `total_asset_growth_24m` | quality | 0.899 | 60 |
| `total_asset_growth_18m` | quality | 0.788 | 60 |
| `operating_asset_growth_24m` | quality | 0.718 | 60 |
| `noncurrent_asset_growth_30m` | quality | 0.708 | 60 |
| `noncurrent_asset_growth_24m` | quality | 0.661 | 60 |
| `asset_growth_12m` | other | 0.642 | 60 |
| `equity_growth_24m` | other | 0.625 | 60 |
| `noncurrent_asset_growth_18m` | quality | 0.585 | 60 |
| `noncurrent_assets_growth_12m` | other | 0.493 | 60 |
| `operating_asset_growth_12m` | quality | 0.492 | 60 |
| `total_asset_growth_6m` | quality | 0.473 | 60 |
| `equity_growth_12m` | other | 0.453 | 60 |
| `liability_growth_12m` | other | 0.426 | 60 |
| `current_assets_growth_12m` | other | 0.379 | 60 |
| `noncurrent_asset_growth_6m` | quality | 0.357 | 60 |

## Expected relationship and data notes

- Expected relationship: 기존 12개월 자산성장과 관련되지만 기간 또는 영업자산 범위가 다르다.
- Data notes: DART available_date PIT 값의 정확한 달력 시차와 양의 전기 분모만 사용한다.
