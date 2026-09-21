# 연구 지식

> 자동 생성. 지침은 INSTRUCTIONS.md에만 둔다. 외부 문헌과 내부 실증 교훈은 구분한다.
> 사용할 데이터 · 기존 가설/계산의 요약 · 검토된 교훈과 문헌만 담는다.
> 이 파일 생성은 DB 재인증이 아니다. 입력 경계는 아래, 실행 상태는 해당 campaign 원본에서 확인한다.

보유 데이터·적재 범위·운영 상태는 [DATA_INVENTORY.md](DATA_INVENTORY.md)를 참조한다. 아래 입력 목록은 현재 연구 패널에 연결된 데이터만 나타낸다.

## Frozen research state

- Silver source: `RDS public Silver`
- Raw Silver period inside context boundary: `1995-05` ~ `2026-09`
- Visible Silver data period: `2015-01` ~ `2026-09`
- Research input floor: `2015-01`
- Maximum factor lookback: `36` months
- Discovery signal evaluation period: `2018-03` ~ `2026-09`
- Discovery return-support cutoff: `-`
- Rows/months/assets: `320,189` / `141` / `3,155`
- Historical feature return: `adj_close` / `krx_split_adjusted_price_return_v1`
- Forward-label return: `total_return_close` / `krx_gross_dividend_reinvested_v3` / `forward_return_labels_only` / revision=`latest_revision_ex_post_realized` / candidate_access=`False`
- Gate ruleset: `fr-3.16.0`
- Research protocol: `epoch-1.9`
- Strategy context cutoff: `-`

## Available strategy inputs

아래는 원시 컬럼의 결측 비율이며, 후보의 룩백·분모 조건을 적용한 계산 가능 비율이 아니다.

| column | overall coverage | latest-month coverage |
|---|---:|---:|
| `adj_close` | 100.0% | 100.0% |
| `adv20` | 100.0% | 100.0% |
| `amihud_illiquidity_1m` | 97.3% | 96.8% |
| `amihud_observations_1m` | 100.0% | 100.0% |
| `capital_stock` | 80.7% | 99.2% |
| `comprehensive_income` | 28.0% | 98.7% |
| `comprehensive_income_ttm` | 17.7% | 94.8% |
| `current_assets` | 86.2% | 97.1% |
| `current_liabilities` | 86.2% | 97.0% |
| `daily_return_observations_252d` | 100.0% | 100.0% |
| `daily_volatility_252d` | 99.9% | 100.0% |
| `market` | 100.0% | 100.0% |
| `market_cap` | 100.0% | 100.0% |
| `max_daily_return_1m` | 100.0% | 100.0% |
| `max_daily_return_observations_1m` | 100.0% | 100.0% |
| `net_income` | 85.7% | 99.2% |
| `net_income_ttm` | 74.5% | 95.6% |
| `net_income_yoy_change` | 71.8% | 94.3% |
| `noncurrent_assets` | 86.0% | 96.7% |
| `noncurrent_liabilities` | 86.1% | 97.0% |
| `operating_income` | 85.7% | 99.2% |
| `operating_income_ttm` | 74.6% | 95.7% |
| `pretax_income` | 85.7% | 99.2% |
| `pretax_income_ttm` | 74.5% | 95.6% |
| `price_high_252d` | 100.0% | 100.0% |
| `price_high_observations_252d` | 100.0% | 100.0% |
| `retained_earnings` | 86.5% | 99.4% |
| `revenue` | 84.7% | 97.2% |
| `revenue_ttm` | 73.1% | 92.6% |
| `shares` | 100.0% | 100.0% |
| `sue_score` | 62.5% | 89.3% |
| `total_assets` | 87.0% | 99.4% |
| `total_equity` | 87.0% | 99.4% |
| `total_liabilities` | 87.0% | 99.4% |
| `trading_value` | 100.0% | 100.0% |

## 무엇을 이미 정의·시도했나

소스 정의 277개 · 원장 시행 229건. 코드 존재는 평가·사용 승인·Gold 승격이 아니다.
아래는 이름·입력·계산 선언 중심의 탐색 요약이다. 가설 해석을 자동 추출한 것이 아니며 같은 그룹이 같은 신호라는 판정이나 경제적 교훈도 아니다.
가설 원문의 과거 성과 혼입을 막기 위해 검토되지 않은 자연어는 색인에 복사하지 않는다.

| 계산 유형 | 정의/시행 | 포함한 변형 | 예시 |
|---|---:|---|---|
| 과거 복합 점수 (`composite`) | 7/7 | 기간 12개월 | `defensive_small_value`, `defensive_value` |
| 배당 수준·빈도 (`dividend`) | 2/2 | 기간 12개월 | `dividend_event_frequency_ttm`, `dividend_yield_ttm` |
| 수익률 계절성 (`seasonality`) | 2/2 | 기간 13/60개월 | `annual_seasonality_5y`, `return_seasonality_12m` |
| 기업 규모 (`size`) | 1/0 | 수준·비율 정의 | `size` |
| 시가 대비 재무가치 (`valuation`) | 23/17 | 시차 변화·기간 6/12개월 | `asset_to_market`, `book_to_market_change_12m` |
| 이익 서프라이즈 (`surprise`) | 2/1 | 시차 변화 | `earnings_change_to_assets`, `sue` |
| 운전자본 발생액 (`accruals`) | 3/3 | 기간 6/12/24개월 | `working_capital_accruals_12m`, `working_capital_accruals_24m` |
| 자산·운전자본 성장 (`investment`) | 16/14 | 성장 가속·성장률·기간 6/12/18/24/30개월 | `asset_growth_12m`, `asset_growth_acceleration_12m` |
| 이익·매출 성장 (`earnings_growth`) | 8/4 | 성장 가속·성장률·기간 12개월 | `net_income_growth_12m`, `net_income_growth_acceleration_12m` |
| 자본·부채 변화와 발행 (`financing`) | 16/15 | 성장 가속·성장률·기간 6/12/18/24/36개월 | `capital_stock_growth_12m`, `capital_stock_growth_18m` |
| 자산 대비 매출·회전율 (`asset_efficiency`) | 12/10 | 성장 가속·시차 변화·변동성·기간 12/24/36개월 | `asset_turnover`, `asset_turnover_acceleration_12m` |
| 이익률·자산/자본 수익성 (`profitability`) | 40/34 | 성장 가속·시차 변화·변동성·기간 6/12/24/36개월 | `net_income_to_capital_stock`, `net_income_to_current_assets` |
| 재무구조·부채 상환 여력 (`capital_structure`) | 27/25 | 시차 변화·기간 6/12/18/24/30개월 | `capital_stock_to_current_liabilities`, `capital_stock_to_liabilities` |
| 자산·자본 구성비 (`balance_mix`) | 23/23 | 성장 가속·성장률·시차 변화·변동성·기간 6/12개월 | `capital_stock_share_change_12m`, `capital_stock_to_assets` |
| 가격 반전 (`reversal`) | 7/4 | 기간 3/6/24/36개월 | `long_term_reversal_36_12`, `price_reversal_24_12` |
| 가격·시장대비 모멘텀 (`momentum`) | 14/10 | 성장 가속·기간 6/9/12/15/18/24개월 | `intermediate_momentum_12_7`, `market_relative_momentum_12_1` |
| 추세 지속·회복·고점 거리 (`trend_shape`) | 14/12 | 기간 12/13/18/24개월 | `high_12m_proximity`, `high_24m_proximity` |
| 가격충격·Amihud 유동성 (`illiquidity`) | 11/11 | 시차 변화·변동성·기간 평균·기간 6/12/18/24/36개월 | `amihud_change_12m`, `amihud_illiquidity_1m` |
| 거래대금·회전율 (`trading`) | 18/10 | 시차 변화·변동성·기간 평균·기간 3/6/12/18/24/36개월 | `adv20_change_12m`, `adv20_to_book_equity` |
| 극단 수익·분포 비대칭 (`extremes`) | 10/9 | 시차 변화·불안정성·기간 평균·기간 6/12/18/24개월 | `max_daily_return_1m`, `max_daily_return_change_12m` |
| 시장 민감도·동조성 (`market_exposure`) | 11/8 | 기간 6/9/12/18/24/36개월 | `market_beta_12m`, `market_beta_18m` |
| 수익률 변동성·안정성 (`volatility`) | 10/8 | 시차 변화·변동성·불안정성·기간 6/12/18/24/36개월 | `daily_volatility_change_12m`, `downside_vol_12m` |

전체 이름·계산 코드·입력·params·정의 파일·모든 시행 식별자는 `memory/factor_index.json`에 보존한다.
조회: `python -m scripts.factor_memory --query total_assets` 또는 `--group investment`, `--factor NAME`.
후보를 만들기 전 해당 그룹과 입력을 검색해 수식·기간까지 비교한다. 이름만 바꾼 정의와 실패한 시행도 제외하지 않는다.
검색은 결과 없는 색인만 읽는다. 원본이 바뀌면 갱신 전 사용을 거부한다. 역사 hash와 현재 파일의 동일성은 미확인으로 보존하며, 엔진 구조·상관 검사는 그대로 필요하다.

## 누적 검증 교훈

검토된 일반 교훈만 축약한다. 같은 표본의 반복은 독립 증거가 아니다.
경제적 해석 검토 대기: 175건. 상세 검사 기록은 candidate_lessons.jsonl에 보존한다.

### balance_sheet_growth_requires_construct_and_distribution_checks

- 검사 규칙: fr-3.16.0
- 교훈: 재무 항목의 증감이 낮다는 사실만으로 보수적 투자를 측정했다고 볼 수 없다. 실제 투자행동과 자금조달·기업 규모의 동반 변화를 구분하고, 실적의 순위 관계와 평균 차이가 엇갈리면 분포·분모·결측을 확인한 뒤 경제적 교훈을 내려야 한다.
- 적용 한계: 종료된 국내 주식 Discovery의 사후 관측에 한정한다. 당시 업종과 공식 레짐이 연결되지 않았고 실적 비율의 큰 값도 미해명이다. 일반적인 투자 메커니즘의 기각, 인과 증명, 독립 재현 또는 비용 후 운용성과로 해석하지 않는다.
- 레짐 기준: 미연결/기준 미상
- 근거 수준: 잠정 관찰 (독립 재현 미확인)
- SUPPORTS 관측 1건: 추정: 낮은 자산 확장이 보수적 투자뿐 아니라 기업 규모·거래활동·재무 구성 차이를 함께 반영했을 가능성이 있다. 통제 후 수익 관계가 약해지는 관측은 이 가능성과 양립하지만 원인을 증명하지 않는다. 공개 실적의 순위와 평균이 엇갈려 과잉투자 회피가 실적 개선을 만들었는지는 판단을 보류한다.
- 근거: campaign-20260920-001/epoch-001/operating_asset_growth_12m

## 외부 문헌 지식

원문 확인: 2026-09-20 · 선별 문헌 10건 · 저장 원본: `research/memory/literature.json`.
논문 관측과 우리 프로젝트 적용 제안을 구분한다. 국내 실증 교훈·독립 재현·사용 가능한 데이터 인증이 아니다.
현재 시점의 연구 참고자료다. 과거 시점에도 이 문헌을 알았다는 뜻이 아니며, 재사용한 과거 OOS가 새 독립 검증이 되지 않는다.
논문 수익률·최적 파라미터를 옮겨 합격 기준으로 쓰지 않는다. 원문 전체 대신 해당 주장과 한계만 요약했다.
입력 연결 상태는 검토일의 KNOWLEDGE/DATA_INVENTORY 기준이며 새 후보마다 가용성과 중복을 다시 확인한다.

### 가설과 경제적 메커니즘

#### amihud_2002_illiquidity — 비유동성 보상과 유동성 악화 충격을 구분한다

- 출처: [Illiquidity and Stock Returns: Cross-Section and Time-Series Effects (2002)](<https://archive.nyu.edu/jspui/bitstream/2451/27420/2/S-AM-00-10.pdf>) — Yakov Amihud.
- 확인 범위: 원논문 해당 절 확인 · JFM 5(1) 출판본 초록·Introduction 및 링크의 2000 NYU 저자판 §2.1 식(1), 인쇄 p.5.
- 논문 관측: 일별 절대수익률/거래대금 평균을 거친 가격충격 측정치로 사용한다. 예상 비유동성과 이후 요구수익의 양의 관계를, 예상 밖 비유동성 증가와 동시 가격하락에서 구분한다.
- 프로젝트 적용 **제안**: amihud\_illiquidity\_1m을 거래마찰 관련 특성으로 해석하되, 수준에 대한 보상과 갑작스러운 악화의 충격을 같은 가설로 섞지 않는다. 기존 유동성 정의와의 중복을 먼저 확인한다.
- 구별할 질문: 높은 값이 거래마찰인가, 높은 변동성·소형주 노출인가? 같은 표본의 통제와 비용 후에도 관계가 남는지, 가격 급변이 측정치를 지배하는지 구별할 수 있는가?
- 필요한 입력/현재 제약: 연결된 amihud\_illiquidity\_1m의 일별 수익률·거래대금 산식과 통화 단위·무거래일·관측일 조건을 확인한다. 월간 변형은 원논문 연간 측정과 다르며 adv20의 역수도 같은 지표가 아니다.
- 해석 한계: 실제 거래비용을 직접 측정한 값이 아니다. 보상 가능성이 곧 비용 후 수익성을 뜻하지 않으며 측정 지평과 시장 제도에 의존한다. 국내 동일 정의 재현은 미확인.

#### cooper_2008_asset_growth — 기업의 자산 확장과 주주의 수익은 다른 질문이다

- 출처: [Asset Growth and the Cross-Section of Stock Returns (2008)](<https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2008.01370.x>) — Michael J. Cooper, Huseyin Gulen, Michael J. Schill.
- 확인 범위: 원저자/출판사 초록 확인 · The Journal of Finance 63(4), 1609–1651: 출판사 Abstract.
- 논문 관측: 연간 총자산 증가율이 기존 기업특성과 함께 미국 주식의 이후 수익률을 설명하는 중요한 변수였다고 보고한다. 확인한 초록만으로 방향·특정 인과 경로·상세 구현 조건을 확정하지 않는다.
- 프로젝트 적용 **제안**: 자산 성장 후보에서 무엇이 늘었는지와 그 확장이 이후 영업성과로 이어졌는지를 구별한다. 영업자산·유동자산 등 일부 계정의 변화는 총자산 성장과 다른 정의임을 남긴다.
- 구별할 질문: 생산적 투자, 낮은 할인율, 과도한 확장 중 어떤 설명과 일치하는가? 합병·연결 범위 변화·작은 전년 분모가 성장률을 왜곡하지 않았는가?
- 필요한 입력/현재 제약: total\_assets 외에 회계기간·공시시점·양의 전년 분모가 필요하다. 월별 PIT snapshot의 12행 차이를 같은 회계연도의 전년 대비 성장률로 가정하지 않는다. 실제 입력 커버리지를 확인해야 한다.
- 해석 한계: 초록 수준의 근거다. 단순 성장률과 수익의 관계가 과잉투자 원인을 증명하지 않으며 한국의 최근 단기 표본에 효과를 보장하지 않는다. 국내 동일 정의 재현은 미확인.

#### jegadeesh_titman_1993_momentum — 과거 승자의 연속성과 영구적인 상승 추세는 다르다

- 출처: [Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency (1993)](<https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x>) — Narasimhan Jegadeesh, Sheridan Titman.
- 확인 범위: 원저자/출판사 초록 확인 · The Journal of Finance 48(1), 65–91: 출판사 Abstract.
- 논문 관측: 과거 승자를 사고 패자를 파는 전략에서 중기 수익의 연속성을 보고하지만, 이후에는 일부 소멸한다. 체계적 위험이나 공통요인 반응 지연만으로 설명되지 않았다는 결과이며 특정 행동 원인의 확정은 아니다.
- 프로젝트 적용 **제안**: 비회계 탐색 축으로 과거 가격의 상대적 강도를 고려할 수 있다. 형성 기간·건너뛸 기간·보유 규칙을 가설과 함께 먼저 고정하고, 추세 지속과 단기 반전이라는 경쟁 설명을 구별한다.
- 구별할 질문: 기업 정보의 느린 반영인가, 업종 공동 움직임·유동성·단기 반전인가? 같은 표본의 통제 및 비용 진단이 설명을 구분할 수 있는가?
- 필요한 입력/현재 제약: asset\_id별 인증 adj\_close 이력과 달력 연결·기업행사·거래정지 처리가 필요하다. ex-post total\_return\_close는 신호 입력이 아니다. 특정 기간이나 skip-month를 이 초록이 보장하는 표준으로 간주하지 않는다.
- 해석 한계: 과거 미국 전략의 관측이다. 한국시장, 월별 IC, 현재 비용 조건에서 같은 효과를 뜻하지 않으며 결과를 본 뒤 기간을 바꾸는 근거로 사용하지 않는다. 국내 동일 정의 재현은 미확인.

#### novy_marx_2013_profitability — 순이익과 기업의 생산성을 같은 것으로 보지 않는다

- 출처: [The Other Side of Value: The Gross Profitability Premium (2013)](<https://mysimon.rochester.edu/novy-marx/research/OSoV.pdf>) — Robert Novy-Marx.
- 확인 범위: 원논문 해당 절 확인 · JFE 108(1) 출판본 초록 및 링크의 June 2012 저자판 §2·§2.1, 인쇄 pp.4–7.
- 논문 관측: 매출총이익/총자산의 수익률 설명력을 보고한다. 연구개발·광고처럼 비용으로 처리되는 투자는 순이익을 낮출 수 있어, 순이익이 낮다는 사실을 생산성이 낮다는 뜻으로 해석하기 어렵다는 측정 논리를 제시한다.
- 프로젝트 적용 **제안**: 수익성 후보마다 분자가 매출총이익·영업이익·순이익 중 무엇인지와 포함 비용을 구분한다. 이익 계정 이름만 바꾼 후보를 늘리기보다 어떤 경제적 특성을 새로 측정하는지 설명한다.
- 구별할 질문: 관측 비율이 생산성인가, 업종·자산집약도·비용 인식 차이인가? 이후 수익성이 지속되는지와 현재 가격 수준이 다른지를 별도로 관찰할 수 있는가?
- 필요한 입력/현재 제약: 인증된 매출총이익과 총자산이 필요하다. 현재 gross\_profit\_ttm의 패널 연결은 확인되지 않았다. operating\_income\_ttm·net\_income\_ttm으로 바꾸면 원논문의 재현이 아니다.
- 해석 한계: 회계 측정의 유용성은 실증 문제이며 순이익이 항상 무의미하다는 뜻이 아니다. 미국 표본·계정·산업 통제를 한국에 그대로 옮기지 않는다. 국내 동일 정의 재현은 미확인.

#### sloan_1996_accruals — 같은 이익도 현금과 발생액의 지속성이 다르다

- 출처: [Do Stock Prices Fully Reflect Information in Accruals and Cash Flows About Future Earnings? (1996)](<https://www.cuhk.edu.hk/acy2/workshop/June2009Wasley/1996TAR%29.pdf>) — Richard G. Sloan.
- 확인 범위: 원논문 해당 절 확인 · The Accounting Review 71(3), pp.289–292: 초록·서론·§II 가설.
- 논문 관측: 미국 표본에서 이익의 발생액 부분은 현금흐름 부분보다 지속성이 낮았고, 주가는 이 차이를 충분히 반영하지 않는 양상을 보였다. 미래 이익의 변화와 그 정보의 가격 반영을 별도 가설로 검토한다.
- 프로젝트 적용 **제안**: 재무 후보의 교훈을 입력이 특성을 측정했는가 → 이후 실적이 예상대로 변했는가 → 가격이 어떻게 반응했는가로 나눈다. 수익률 검사 탈락만으로 경제적 변화까지 없었다고 결론내리지 않는다.
- 구별할 질문: 낮은 지속성이 실제 발생액에서 오는가, 일회성 손익·산업 구성 때문인가? 이후 실적 변화는 있었지만 이미 가격에 반영됐을 가능성을 구분할 자료가 있는가?
- 필요한 입력/현재 제약: 발생액·현금흐름 분해에 필요한 PIT 계정과 후속 실적이 필요하다. 현재 패널의 net\_income\_ttm−operating\_income\_ttm은 발생액이 아니다. 현재 ROA 변화 진단도 이 논문의 재현은 아니다.
- 해석 한계: 과거 미국 관측 결과이며 특정 기업의 원인이나 한국의 동일 효과를 입증하지 않는다. 회계 정의·공시 시점·표본 및 기대 정보가 다르면 별도 가설이다. 국내 동일 정의 재현은 미확인.

### 검증과 재현성

#### harvey_liu_zhu_2016_multiple_tests — 많이 찾을수록 우연히 좋아 보이는 결과도 늘어난다

- 출처: [… and the Cross-Section of Expected Returns (2016)](<https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF>) — Campbell R. Harvey, Yan Liu, Heqing Zhu.
- 확인 범위: 원논문 해당 절 확인 · RFS 29(1): 초록·§1 The Search Process·§3.1·§3.3·§3.4.3.
- 논문 관측: 수많은 팩터 가설을 검사한 환경에서는 개별 검정의 통상 기준만으로 신뢰성을 판단하기 어렵다고 논의한다. 공개되지 않은 실패와 전체 탐색 규모, 서로 다른 오류 통제 방식이 중요하다.
- 프로젝트 적용 **제안**: 실패 정의·시행 이력과 동일 연구 요청의 전체 후보 범위를 보존한다. 교훈을 보고 다시 탐색한 과거 OOS는 새 독립 검증으로 부르지 않고, 경제적 설명 탐색 자체에도 선택 편향이 있음을 기록한다.
- 구별할 질문: 좋은 결과만 남겼는가? 비슷한 아이디어의 여러 변형과 실패까지 전체 탐색 범위에 잡히는가? 현재 증거가 신규 시점의 검증인가, 과거 자료를 재사용한 연구인가?
- 필요한 입력/현재 제약: 후보·program·campaign 식별자, 동결 정의, 실패 원장, 검정 결과와 OOS 노출 이력이 필요하다. 새로운 가격 데이터나 후보 계산 없이 연구 과정 점검에 참고할 수 있다.
- 해석 한계: 논문의 임계값을 한국 월별 IC gate에 그대로 이식하지 않는다. 기존 BY를 유지하며, 다중검정 보정이 잘못된 p값·자료 누출·적응적 재사용을 모두 해결하지는 않는다. 국내 동일 정의 재현은 미확인.

#### jensen_kelly_pedersen_2023_replication — 효과가 약하거나 유의하지 않다는 것과 존재하지 않는 것은 다르다

- 출처: [Is There a Replication Crisis in Finance? (2023)](<https://onlinelibrary.wiley.com/doi/10.1111/jofi.13249>) — Theis Ingerslev Jensen, Bryan Kelly, Lasse Heje Pedersen.
- 확인 범위: 원논문 해당 절 확인 · The Journal of Finance 78(5): 초록·서론·§I.B.2–3·§II.A–C·§III.B.1–2·§III.C.1–2·§III.D.2·결론.
- 논문 관측: 여러 국가와 팩터를 다루는 계층적 베이지안 분석으로 상당수 팩터의 재현 가능성을 보고한다. 초기 추정의 축소, 표본 밖 성과 약화와 검정력 문제를 효과의 완전한 부재와 구분한다.
- 프로젝트 적용 **제안**: 다중검정 경계 문헌과 함께 읽고, 미통과·효과 약화·증거 부족을 구분한다. 짧은 한국 표본의 단일 IC 실패를 경제 원리의 보편적 반박으로 확대하지 않는다.
- 구별할 질문: 정밀하게 반대 방향이 관측됐는가, 추정 범위가 넓어 결론을 못 내리는가? 정의·입력·기간 차이를 제거하지 않고 재현 실패라고 부르고 있지는 않은가?
- 필요한 입력/현재 제약: 동일 정의·기간·표본의 추정치와 불확실성을 구분한 진단이 필요하다. 여러 국가를 묶는 이 논문의 자료·모형은 현재 국내 패널에 구현되어 있지 않다.
- 해석 한계: 모형 가정과 통합 표본에 의존한다. 국내 후보의 승격 근거가 아니며 BY 완화·사후 팩터 합성·유리한 검정 선택을 정당화하지 않는다. 국내 동일 정의 재현은 미확인.

#### mclean_pontiff_2016_publication — 효과 약화는 과최적화와 시장의 학습을 구분해서 본다

- 출처: [Does Academic Research Destroy Stock Return Predictability? (2016)](<https://onlinelibrary.wiley.com/doi/10.1111/jofi.12365>) — R. David McLean, Jeffrey Pontiff.
- 확인 범위: 원저자/출판사 초록 확인 · The Journal of Finance 71(1), 5–32: 출판사 Abstract.
- 논문 관측: 발표된 수익률 예측변수들을 조사해 원래 표본 밖과 출판 후의 성과 약화를 보고한다. 저자들은 표본 밖 약화와 추가 출판 후 약화를 데이터 마이닝 및 정보를 활용한 거래의 가능성과 연결해 해석한다.
- 프로젝트 적용 **제안**: 문헌 기반 후보에 발표 시점·확인한 버전을 기록한다. 유명한 이상현상이 현재도 같은 크기로 작동한다고 가정하지 않고, 관측된 약화와 그 이유에 대한 추정을 분리한다.
- 구별할 질문: 효과가 약해졌다는 관측만 있는가, 투자자의 정보 활용·거래비용·표본 변화라는 설명을 구분할 자료도 있는가? 원논문의 조건과 현재 조건은 얼마나 다른가?
- 필요한 입력/현재 제약: 논문 발표 이력과 시점이 명확한 검증 자료가 필요하다. 현재 후보의 한 번 탈락만으로 출판 후 차익거래가 원인이라고 판정할 수 없다.
- 해석 한계: 초록만 확인했으며 상세 식별 전략을 재현하지 않았다. 여러 미국 변수의 평균 약화를 개별 한국 팩터의 예상 수익 할인율이나 새 합격 기준으로 사용하지 않는다. 국내 동일 정의 재현은 미확인.

### 레짐·AI 연구 과정

#### shu_yu_mulvey_2024_jump — 레짐의 안정성과 변화 감지 속도에는 절충이 있다

- 출처: [Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach (2024)](<https://arxiv.org/html/2402.05272>) — Yizhan Shu, Chenyu Yu, John M. Mulvey.
- 확인 범위: 원논문 해당 절 확인 · arXiv:2402.05272v3 (2024-09-17): 초록·§3.4, 특히 온라인 추론·하이퍼파라미터 절.
- 논문 관측: 상태가 자주 바뀌는 데 벌점을 주는 jump model로 지속성 있는 시장 상태를 추정한다. 사후 전체 구간의 분류와, 그날까지의 정보로 마지막 상태를 판독하는 온라인 추론을 구별한다.
- 프로젝트 적용 **제안**: 현재 고정 추세·변동성 네 축 진단과 비교할 미래 대안으로 보존한다. 어떤 방식이든 그 시점에 알 수 있던 상태를 따로 기록하고, 나중에 얻은 전체 기간의 상태로 과거 판단을 덮어쓰지 않는다.
- 구별할 질문: 전환 감소가 잡음 억제인가, 실제 충격 인지의 지연인가? 레짐 설명이 당시 정보로 가능했는가? 상태별 관측이 적거나 한 위기 구간에 몰리지 않았는가?
- 필요한 입력/현재 제약: 공식 시장지수 이력과 known\_at 확인이 필요하다. 현재 공식 지수의 인증 패널 경로는 미연결이며 Bronze 거시 자료의 보유가 PIT 승인은 아니다. 이 논문의 모델을 이번에 구현하거나 실행하지 않았다.
- 해석 한계: 시장지수 자산배분 연구이지 한국 개별주식 팩터의 원인 판독을 입증한 것은 아니다. 전환 벌점은 안정성과 지연을 맞바꾸며, 현재 팩터 결과에 맞춰 선택하면 사후 최적화가 된다. 국내 동일 정의 재현은 미확인.

#### yamada_2025_ai_scientist — AI의 설명보다 실제 실험 산출물과 검토가 먼저다

- 출처: [The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search (2025)](<https://arxiv.org/html/2504.08066v1>) — Yutaro Yamada 외.
- 확인 범위: 원논문 해당 절 확인 · arXiv:2504.08066v1: §3.1–3.2·§3.4·§4.1–4.2·§5.
- 논문 관측: 문헌 기반 아이디어와 구조화된 실험 산출물을 연결하고, 시각언어모델로 그림과 설명을 점검하는 연구 자동화 구조를 제시한다. 저자들은 인용 오류·오해를 부르는 그림·학습/시험 중복 가능성 같은 실패도 보고한다.
- 프로젝트 적용 **제안**: 우리의 증거 묶음 → 해석자 → 별도 비평자 → 축약 교훈 흐름에서 관측마다 근거 ID를 연결한다. 실제 그래프 열람과 수치표만 읽은 경우를 구별하고, 없는 실험·원인·입력을 서술로 만들어내지 않는다.
- 구별할 질문: 주장이 실제 표·그림에서 확인되는가? 다른 설명도 가능한가? 비평자도 같은 추정을 반복할 뿐인지, 빠진 데이터와 미실행 분석을 지적했는지 확인할 수 있는가?
- 필요한 입력/현재 제약: 공개가 허용된 진단 표·차트·evidence\_id와 현재 후보의 동결 가설이 필요하다. 기존 원본과 해석의 연결을 사용하며 상세 봉인 OOS를 읽을 권한을 추가하지 않는다.
- 해석 한계: 기계학습 워크숍 연구 자동화 사례이며 금융 알파나 인과 추론의 검증이 아니다. 사람의 선택이 포함된 평가를 완전 무인 증명으로 부르지 않으며 성과 기반 tree search를 동결 팩터의 재튜닝에 이식하지 않는다. 국내 동일 정의 재현은 미확인.
