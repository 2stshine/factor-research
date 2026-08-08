# 널리 쓰이는 주식 팩터 구현 현황

이 문서는 “시중에서 널리 쓰인다”는 이유만으로 유사 proxy를 같은 이름으로 등록하지 않기 위한
구현 대장이다. 데이터 가능 여부는 후보가 볼 수 있는 Silver 구간(`2015-01~2023-05`)과 PIT
가용성을 기준으로 판단한다. 팩터 성과, hidden OOS, Gold 승격 여부는 이 문서의 범위가 아니다.

## 이미 구현된 코어 팩터

| 표준 계열 | 현재 단일 신호 | 구현 상태 |
|---|---|---|
| Book-to-price | `value_bp` | `total_equity / market_cap` |
| Earnings-to-price | `value_ep` | `net_income_ttm / market_cap` |
| Sales-to-price | `value_sp` | `revenue_ttm / market_cap` |
| Size | `size` | 양의 시가총액 로그, 저규모 방향 |
| Momentum | `mom_12_1` | 배당 포함 총수익의 12-1개월 모멘텀 |
| Short reversal | `rev_1m` | 직전 1개월 총수익의 반대 방향 |
| Profitability | `qual_roe`, `qual_opm`, `operating_roa` | 순이익·영업이익 기반 proxy |
| Investment | `asset_growth_12m` | 12개월 총자산 증가율의 반대 방향 |
| Low risk | `low_vol_12m`, `market_beta_36m` | 월별 변동성·내부 시장 beta |
| Trading activity | `trading_turnover_20d` | `ADV20 / market_cap` |
| Accrual proxy | `working_capital_accruals_12m` | 넓은 운전자본 증가 proxy |

[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)는
size, book-to-market, operating profitability, investment, momentum, reversal 및 D/P 연구 포트폴리오를
별도로 제공한다. 여기서 말하는 학술 “팩터”는 포트폴리오 수익률이고, 이 저장소의 후보는 그
포트폴리오를 만들기 전 종목별 단일 특성값이라는 차이가 있다.

## 이번에 추가한 정확한 단일 신호

| 후보 | 정의 | 방향 | 필요한 Silver 입력 |
|---|---|---:|---|
| `net_equity_issuance_price_adjusted_12m` | `(market_cap / adj_close)`의 정확한 12개월 증가율 | 낮을수록 + | 월말 시가총액·분할조정 가격 |
| `high_52w_price_proximity` | `adj_close / 최근 252거래일 최고 adj_close` | 높을수록 + | 일별 분할조정 가격 |
| `amihud_illiquidity_1m` | 월중 평균 `abs(일별 총수익률) / 거래대금` | 높을수록 + | 일별 총수익·거래대금 |
| `realized_volatility_252d` | 최근 252개 일별 총수익률 표준편차 | 낮을수록 + | 일별 총수익 |
| `max_daily_return_1m` | 최근 달의 최대 일별 총수익률 | 낮을수록 + | 일별 총수익 |
| `dividend_yield_ttm` | 알려진 최근 12개월 분할조정 주당 현금배당 / 월말 `adj_close` | 높을수록 + | canonical 배당 audit·가격 |

정의 선택 근거는 다음과 같다.

- [Amihud (2002)](https://www.sciencedirect.com/science/article/pii/S1386418101000246)는
  일별 절대수익률을 금액 거래량으로 나눈 값의 기간평균을 가격충격 proxy로 정의한다.
- [Bali, Cakici and Whitelaw (2011)](https://pages.stern.nyu.edu/~rwhitela/papers/max%20jfe11.pdf)은
  과거 한 달의 최대 **일수익률**을 사용한다. 기존 `max_monthly_return_12m`과 다르다.
- [George and Hwang (2004)](https://onlinelibrary.wiley.com/doi/pdf/10.1111/j.1540-6261.2004.00695.x)은
  현재 가격과 52주 최고가격의 근접도를 사용한다. 배당재투자 지수의 고점이 아니다.
- [French D/P portfolios](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_port_form_dp.html)는
  과거 12개월 배당을 현재 equity value로 나누며 무배당 기업을 별도 0 그룹으로 둔다.
- 순발행은 시가총액 증가 중 주가수익으로 설명되지 않는 부분이라는
  [학술 정의](https://academic.oup.com/rfs/article/30/4/1270/2965095)를 따른다. 배당 포함
  총수익을 가격수익 대신 사용하면 배당을 음의 발행처럼 섞으므로 `adj_close`를 사용한다.

## 정확히 구현하지 않은 팩터와 필요한 데이터

| 팩터 | 필요한 원천 | 현재 상태 |
|---|---|---|
| Gross profitability | `gross_profit` 또는 `revenue - COGS` | `gross_profit`, COGS 없음 |
| Fama-French operating profitability | revenue, COGS, SG&A, interest expense, book equity | COGS·SG&A·이자비용 없음 |
| Cash-flow-to-price | 영업현금흐름 TTM, 시가총액 | CFO 없음 |
| Sloan total accruals | CFO 또는 cash·current debt·depreciation | 전부 미보강 |
| EBITDA/EV | EBITDA, 현금, 이자부채 | EBITDA·현금·이자부채 분리 없음 |
| CAPEX investment | CAPEX, 총자산 | CAPEX 없음 |
| Piotroski F-score | CFO, ROA 변화, accrual, issuance 등 | CFO와 일부 세부계정 없음; 합성점수이기도 함 |
| Net payout/shareholder yield | 배당 + 자사주 순매입 | 자사주 매입·소각 PIT 이벤트 없음 |
| Analyst revisions/sentiment | PIT 컨센서스·등급·목표가 이력 | 원천·테이블·parser 없음 |
| Short-interest factor | 공매도·대차 잔고와 거래 | 원천·테이블·parser 없음 |
| Exact idiosyncratic volatility | 일별 주식수익과 같은 시점의 시장/FF 요인 회귀잔차 | 인증된 일별 요인 패널 없음 |
| Sector/industry-neutral factors | 과거 시점별 업종·산업 분류 | PIT 업종 이력 파일·테이블 없음 |
| Free-float adjusted size/liquidity | PIT 유동주식수·유동비율 | 인증된 유동주식 이력 없음 |
| Quoted-spread liquidity | PIT bid/ask 호가 | 호가·스프레드 원천 없음 |
| Commodity-exposure factors | 원자재 가격 + 기업별 매출·비용 노출도 | 원자재 시계열만으로는 종목 횡단면 신호를 만들 수 없고, PIT 기업 노출도 매핑이 없음 |

[French의 operating-profitability 정의](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios_me_op.html)는
`(revenue - COGS - SG&A - interest) / book equity`이다. 또한
[Novy-Marx gross profitability](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1598056)는
`gross profits / assets`다. 따라서 현재의 `revenue_ttm / total_assets`를 gross profitability라고
부를 수 없으며, 그것은 이미 구현된 `asset_turnover`다.

재무 공백은 factor-research에서 컬럼명만 추가해서 해결할 수 없다. OpenDART 전체재무제표를 전
종목·전 기간에 대해 backfill하고, 계정 ID/이름 표준화, 정정공시 PIT 재생, 단위·커버리지 DQ를
거쳐 Silver에 올려야 한다. 일부 기업에만 있는 full-statement raw 파일을 사용하면 선택편향이 생긴다.

## 기존 정의에서 발견한 주의사항

- `net_equity_issuance_12m`은 배당 포함 `return_close`를 가격수익처럼 사용한다. 기존 시행은
  보존하고 새 `net_equity_issuance_price_adjusted_12m`으로 교정한다.
- `high_12m_proximity`는 배당재투자 지수 고점을 사용한다. 가격 앵커 후보는 새 52주 가격 정의다.
- `max_monthly_return_12m`은 문헌의 MAX가 아니라 최대 월수익 proxy다.
- `working_capital_accruals_12m`은 현금·단기차입금·감가상각을 제외하지 못한 넓은 proxy다.
- 여러 횡단면 rank를 합치는 기존 후보 7개(`small_value`, `defensive_value` 등)는 현재의
  “한 후보=한 단일 신호” 계약에 맞지 않아 새 epoch 대상에서 제외한다.
- DART `total_cash_dividend`가 0행인 현상은 원천 결측이 아니라 `stock_knd='-'`를 버리는
  parser 결함이다. 주당 현금배당 기반 `dividend_yield_ttm`에는 이 총액을 사용하지 않는다.

## Silver 원천 검증

2026-08-08 읽기 전용 검증에서 `total_return_close` 계약은 `CERTIFIED`였고,
2015-01-02~2026-08-06의 6,769,127행·3,301종목에 결측·비양수·키 중복이 없었다.
같은 계약에 묶인 canonical·applied·positive 현금배당은 13,594건·1,751종목이며,
공시일·적용일·금액·lineage 결측과 중복은 0건이다. 가격·배당 SQL의 PostgreSQL
`EXPLAIN`도 모두 통과했다.

전략이 볼 수 있는 2015-01~2023-05 투자가능 패널 199,904행에서 신규 후보의
유효값 커버리지는 다음과 같다. 이는 입력·구현 검증이지 IC나 수익률 판정이 아니다.

| 후보 | 유효 행 | 커버리지 |
|---|---:|---:|
| `net_equity_issuance_price_adjusted_12m` | 178,182 | 89.13% |
| `high_52w_price_proximity` | 183,567 | 91.83% |
| `amihud_illiquidity_1m` | 198,944 | 99.52% |
| `realized_volatility_252d` | 188,977 | 94.53% |
| `max_daily_return_1m` | 199,797 | 99.95% |
| `dividend_yield_ttm` | 199,904 | 100.00% |

배당 입력의 100% 커버리지는 모든 기업이 배당했다는 뜻이 아니다. 인증 범위 안에서 PIT상
알려진 적용 배당이 없는 121,452행을 명시적 0으로 표시했고, 78,452행은 양의
추적 12개월 배당이 있었다.

## 현재 검증 범위

- 구현·PIT·결측률 검증까지만 수행한다.
- 결과를 본 뒤 정의나 방향을 바꾸지 않는다.
- campaign 사전등록, discovery gate, hidden OOS, Gold SQL parity·승격은 별도 요청 전에는
  실행하지 않는다.
