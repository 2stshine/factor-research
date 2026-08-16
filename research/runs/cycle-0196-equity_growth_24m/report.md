# cycle-0196-equity_growth_24m

- Verdict: **PRE_FDR / REJECT**
- Research phase: **DISCOVERY**
- Campaign / epoch: `campaign-20260816-004` / `epoch-0001`
- OOS: **SEALED**
- Definition hash: `1eda12af513e42ee`
- Data cutoff / ruleset: `2023-05-31` / `fr-3.16.0`
- Common evaluation start: `2018-03`
- Strategy file: `factors/candidates/equity_growth_24m.py`
- Final discovery decision: campaign freeze의 `multiple-testing.json`을 확인

## Hypothesis

최근 24개월 book_equity 확대가 큰 기업은 외부자금 수요나 고평가 활용 가능성이 높아 이후 상대수익이 낮다.

## Mechanism

발행·부채조달·자본금 변화 중 하나를 PIT 시점에서 분리하여 경영자의 자금조달 결정을 측정한다.

## Pre-registered falsification

사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다.

## Validation performed

동일 Silver 월말 PIT 패널과 고정 유니버스에서 discovery 검사를 실행했다. 최종 OOS IC와 귀무 보정은 campaign reveal 전까지 계산·기록하지 않았다.

| tier | check | pass | value | threshold |
|---|---|---:|---:|---|
| T0.1 | 미선언 상수 | Y | 0 | 0개 |
| T0.2 | 단일 팩터 계약 | Y | 0 | 합성 신호 0개 |
| T0.3 | 최대 룩백 | Y | 24 | <=36개월 |
| T0.4 | 연구 입력 하한 | Y | None | >=2015-01 |
| T0.5 | label 전용 입력 차단 | Y | 0 | 0개 |
| T0.6 | 입력 계약 | Y | 0 | 누락 0개 |
| T0.8 | 출력 타입·인덱스 | Y | None | numeric Series / 동일 index |
| T0.9 | 유한값 | Y | None | ±inf 없음 |
| T0.10 | 결정성 | Y | None | 동일 입력 2회 일치 |
| T0.11 | 36개월 인과성 | Y | None | 36개월 이전·미래 행 비의존 |
| T0.12 | 캐시 정의 일치 | Y | None | 현재 정의와 캐시 일치 |
| T1.1 | 전체 커버리지 | Y | 0.8911495422177009 | >=50% |
| T1.1 | 월별 커버리지 하위10% | Y | 0.8845518376092905 | >=30% |
| T1.2 | 종착수익률 3점 방향 | Y | None | 세 시나리오 IC > 0 |
| T1.3 | 배당 포함 총수익 계약 | Y | None | feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단 |
| T2.1 | 전체 IC 최소요건 | N | 0.00380708655393319 | >=0.03 |
| T2.1 | 투자가능 IC 최소요건 | N | 0.00512101405335953 | >=0.03 |
| T2.1 | 투자가능 Rank ICIR 최소요건 | N | 0.07904371348042048 | >=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화) |

## Result

| metric | value |
|---|---:|
| `research_start` | 2018-03 |
| `evaluation_phase` | discovery |
| `ic_full` | 0.00380708655393319 |
| `ic_t_full` | 0.5225151682518718 |
| `ic_p_full` | 0.30160214370272376 |
| `ic_investable` | 0.00512101405335953 |
| `ic_std_investable` | 0.06478711371054233 |
| `rank_icir_investable` | 0.07904371348042048 |
| `ic_t_investable` | 0.6649110822128199 |
| `ic_p_investable` | 0.25430672369996693 |
| `ic_retention` | 1.345126773666044 |

### Failed checks

- `T2.1` 전체 IC 최소요건: 0.00380708655393319 (>=0.03)
- `T2.1` 투자가능 IC 최소요건: 0.00512101405335953 (>=0.03)
- `T2.1` 투자가능 Rank ICIR 최소요건: 0.07904371348042048 (>=0.15 (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화))

## Relationship with registered factors

| factor | category | median monthly Spearman | months |
|---|---|---:|---:|
| `operating_asset_growth_24m` | quality | 0.822 | 63 |
| `equity_growth_12m` | other | 0.729 | 63 |
| `total_asset_growth_24m` | quality | 0.667 | 63 |
| `total_asset_growth_30m` | quality | 0.625 | 60 |
| `total_asset_growth_18m` | quality | 0.591 | 63 |
| `operating_asset_growth_12m` | quality | 0.588 | 63 |
| `retained_earnings_growth_12m` | quality | -0.574 | 63 |
| `equity_growth_6m` | other | 0.525 | 63 |
| `capital_stock_share_change_12m` | other | -0.522 | 63 |
| `asset_growth_12m` | other | 0.505 | 63 |
| `working_capital_accruals_24m` | earnings | 0.473 | 63 |
| `qual_roe` | quality | -0.467 | 63 |
| `pretax_income_to_equity` | quality | -0.453 | 63 |
| `net_roa` | quality | -0.447 | 63 |
| `noncurrent_asset_growth_24m` | quality | 0.442 | 63 |

## Expected relationship and data notes

- Expected relationship: 자산성장과 일부 관계가 예상되지만 조달 측면만 측정한다.
- Data notes: 정확한 달력 시차와 양의 분모만 사용하며 기업행사 후행 라벨은 사용하지 않는다.
