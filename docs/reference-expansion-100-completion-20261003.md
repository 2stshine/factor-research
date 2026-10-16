# 레퍼런스 100개 이상 확장: 실제 적재 결과

기존 45개 + 신규 55개 = **100개**, **25,936,708행**, 58개 불변 Gold 데이터셋.

모두 한국 KOSPI/KOSDAQ 보통주의 레퍼런스 측정값이다. 수익성이 확인된 독립 알파의 개수가 아니다. `PIT_ASSUMED`이며 최초 발표 빈티지의 완전한 검증은 아니다.

기준일은 **2026-09 월말**이다. 이번 작업은 일회성 역사 스냅샷 적재이며 일일 자동 갱신 배포, 신규 수익률 백테스트, 알파 승인, 커밋·푸시·웹사이트 배포를 수행했다는 뜻이 아니다.

## 출처별 신규 적재

| 구분 | 요구 | 실제 신규 |
|---|---:|---:|
| academic | 20 | 20 |
| aqr | 10 | 10 |
| other_quant_firm | 10 | 25 |

한 지표는 출처 한 곳에만 집계했다. AQR/WorldQuant 이름은 한국 수익률 검증을 대신하지 않는다.

## 검증과 해석

- 원천 바이트 고정 → 가용시각/FY·단위 검증 → 서로 다른 계산기 대조 → DB 원자적 적재 → 전체 행 바이너리 해시 재조회 → 별도 커밋 후 재조회 순서.
- 신규 지표는 100종목·60개 관측월 이상. 이것은 각 종목마다 5년을 보유한다는 의미가 아니다.
- 모든 100개가 동시에 존재하는 종목-월은 32,127개이며 최초는 2021-02-28다. 전체 열을 일괄 완전관측 처리하면 표본이 크게 바뀐다. 가격군·재무군·장기 FY군을 가용 이력에 따라 분리하고 결측을 0으로 채우지 않는다.
- 이름·부호·단조변환·기간만 바꾼 항목은 추가하지 않았다. 전 지표 수식 대조와 결정론적 측정값 표본의 순위상관 검사, 의심 쌍의 전체 교집합 검사를 수행했다.
- 비가격 규모 4종은 매출·자산·자본·설비 규모라는 다른 통제 측정이다. AQR 수익성 종합은 기존 6구성요소를 문헌의 고정 방식으로 요약하므로 독립 정보 6개를 새로 얻었다는 뜻이 아니다.
- WQ 지표는 일별 원식을 한국 월말에 표본화했다. 원 논문의 단기 보유 성과를 월 리밸런싱 수익성으로 옮겨 해석하면 안 된다.
- 시장 입력은 전일 시가총액 가중 보통주 가격수익률 대용이며 공식 시장 TR이 아니다. 순주식수/거래량 조정도 가격조정 계수를 이용한 대용이라는 제한을 각 정의에 보존했다.
- 기존 45개 데이터셋·정의와 레거시 승인 메타데이터는 변경하지 않았다. 이 작업에서 봉인 OOS나 미래 수익률로 선별하지 않았다.

문헌 우선순위·한국 근거·최신 평가 절차는 [방법론 보고서](reference-expansion-100-methods-20261003.md)를 참고한다.

## 중복 검사 상세와 사용 제한

100개 수식 정의를 대조하고, 320,056종목-월에서 결정론적으로 선택한 15,241행의 순위상관을 검사했다. 절대 순위상관 0.98 초과 쌍은 전체 공통 관측치로 다시 확인했다. 동일 단조변환 쌍은 발견되지 않았다. 다만 아래는 매우 관련된 측정치이므로 회귀·차원축소에서 독립 증거 두 개처럼 세지 않는다.

| 지표 쌍 | 전체 공통 관측 수 | Spearman 상관 | 해석 |
|---|---:|---:|---|
| 시장모형 잔차 변동성 / 총변동성 | 277,586 | 0.983763 | 시장 공통 위험 제거 여부가 다르지만 매우 유사 |
| 회전율 변동계수 / 거래대금 변동계수 | 310,355 | 0.996113 | 기존 45개에 포함된 두 통제 측정, 분모와 가격 영향이 다름 |

수식 중복 검사와 수치 검사는 경제적 독립성의 증명이 아니다. 특히 AQR 수익성 종합은 기존 구성요소의 고정 요약이며 독립 원천 정보가 아니다. 신규 적재 기준은 **구별된 레퍼런스 측정 정의**이지 독립적인 수익 원천 55개의 입증이 아니다.

## 전체 적재 목록

| ID / 한국어 이름 | 범주 | 구간 / 관측월 / 종목 | 값 행 | 출처 |
|---|---|---|---:|---|
| `kr_abnormal_capex_fy_v1`<br>매출 대비 비정상 설비투자 | capital_expenditure | 2019-03-31~2026-09-30 / 91월 / 1803종목 | 105,746 | [Titman, Wei and Xie (2004), Capital Investments and Stock Returns](https://doi.org/10.1017/S0022109000003173); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_amihud_1m_v1`<br>Amihud 거래대금 대비 가격 충격 | liquidity | 2015-01-31~2026-09-30 / 141월 / 3132종목 | 307,900 | [Amihud (2002): Illiquidity and stock returns](https://archive.nyu.edu/jspui/bitstream/2451/27420/2/S-AM-00-10.pdf) |
| `kr_asset_growth_fy_v1`<br>총자산 성장 | investment | 2016-06-30~2026-09-30 / 124월 / 2792종목 | 216,354 | [Cooper, Gulen, Schill (2008): Asset Growth and the Cross-Section of Stock Returns](https://doi.org/10.1111/j.1540-6261.2008.01370.x); [Kenneth French: Variable Definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/variable_definitions.html) |
| `kr_asset_turnover_change_fy_v1`<br>총자산 회전율 변화 | profitability | 2016-06-30~2026-09-30 / 124월 / 2692종목 | 210,607 | [Soliman (2008): The Use of DuPont Analysis by Market Participants](https://doi.org/10.2308/accr.2008.83.3.823); [Piotroski (2000): Value Investing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455) |
| `kr_bab_beta_reference_v1`<br>AQR 방식 축소 베타 | market_beta | 2016-01-31~2026-09-30 / 129월 / 2567종목 | 241,373 | [Frazzini and Pedersen (2014), Betting Against Beta; attached 20 for Twenty chapter14](https://doi.org/10.1016/j.jfineco.2013.10.005) |
| `kr_calendar_seasonality_reference_v1`<br>종목별 달력 계절성 | calendar_seasonality | 2018-01-31~2026-09-30 / 105월 / 2326종목 | 177,996 | [Heston and Sadka (2008), Seasonality in the cross-section of stock returns; JKP seas_2_5an](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_capex_growth_2fy_v1`<br>설비투자 증가율 | capital_expenditure | 2018-03-31~2026-09-30 / 103월 / 2133종목 | 135,132 | [Anderson and Garcia-Feijoo (2006), Empirical Evidence on Capital Investment, Growth Options, and Security Returns](https://doi.org/10.1111/j.1540-6261.2006.00833.x); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_cash_assets_fy_v1`<br>현금/자산 | quality | 2016-01-31~2026-09-30 / 129월 / 2893종목 | 253,901 | [Palazzo (2012): Cash holdings, risk, and expected returns](https://www.sciencedirect.com/science/article/pii/S0304405X11002856) |
| `kr_cashflow_accruals_fy_v1`<br>현금흐름 방식 발생액 | quality | 2016-01-31~2026-09-30 / 129월 / 2916종목 | 250,387 | [Desai, Rajgopal, Venkatachalam (2004): Value-Glamour and Accruals Mispricing](https://business.columbia.edu/sites/default/files-efs/pubfiles/12921/desai%20rajgopal%20venkatachalam.pdf); [Ball, Gerakos, Linnainmaa, Nikolaev (2016): Accruals, cash flows, and operating profitability](https://jlinnainmaa.com/publications.html) |
| `kr_cfo_assets_change_fy_v1`<br>영업현금흐름 수익성 개선 | profit_growth | 2017-02-28~2026-09-30 / 116월 / 2740종목 | 209,606 | [Bouchaud et al. (2019), Sticky Expectations and the Profitability Anomaly](https://doi.org/10.1111/jofi.12734); [JKP author replication documentation](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_cfo_assets_fy_v1`<br>영업현금흐름/자산 | profitability | 2016-01-31~2026-09-30 / 129월 / 2919종목 | 252,592 | [Ball, Gerakos, Linnainmaa, Nikolaev (2016): Accruals, cash flows, and operating profitability](https://jlinnainmaa.com/publications.html); [Piotroski (2000): Value Investing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455) |
| `kr_cfo_to_issue_cap_fy_v1`<br>영업현금흐름/종목시총 | value | 2016-01-31~2026-09-30 / 129월 / 2919종목 | 252,810 | [Desai, Rajgopal, Venkatachalam (2004): Value-Glamour and Accruals Mispricing](https://business.columbia.edu/sites/default/files-efs/pubfiles/12921/desai%20rajgopal%20venkatachalam.pdf) |
| `kr_cokurtosis_reference_v1`<br>시장 공동첨도 진단 | higher_order_market_risk | 2015-01-31~2026-09-30 / 141월 / 3034종목 | 292,825 | [Dittmar (2002), Nonlinear Pricing Kernels, Kurtosis Preference, and Evidence from the Cross Section of Equity Returns](https://doi.org/10.1111/1540-6261.00425) |
| `kr_coskewness_reference_v1`<br>시장 공동왜도 | higher_order_market_risk | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 306,815 | [Harvey and Siddique (2000), Conditional Skewness in Asset Pricing Tests](https://doi.org/10.1111/0022-1082.00247) |
| `kr_current_ratio_fy_v1`<br>유동비율 | quality | 2015-06-30~2026-09-30 / 136월 / 2845종목 | 257,192 | [Piotroski (2000): Value Investing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455) |
| `kr_downside_beta_reference_v1`<br>하락시장 민감도 | asymmetric_market_risk | 2015-01-31~2026-09-30 / 141월 / 3034종목 | 292,825 | [Ang, Chen and Xing (2006), Downside Risk](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_downside_risk_252d_v1`<br>하방 반편차 | risk | 2015-10-31~2026-09-30 / 132월 / 3046종목 | 291,010 | [Bawa, Lindenberg (1977): Capital market equilibrium in a mean-lower partial moment framework](https://www.sciencedirect.com/science/article/pii/0304405X77900174); [Ang, Chen, Xing (2006): Downside Risk](https://www.ruf.rice.edu/~yxing/downside.pdf) |
| `kr_earnings_stability_5fy_v1`<br>5개 FY 이익 안정성 | earnings_stability | 2019-06-30~2026-09-30 / 88월 / 2116종목 | 118,680 | [Asness, Frazzini and Pedersen (2019), Quality minus junk, annual EVOL fallback](https://d-nb.info/1174954515/34); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_earnings_to_issue_cap_fy_v1`<br>연간 순이익/종목시총 | value | 2015-06-30~2026-09-30 / 136월 / 2956종목 | 258,048 | [Kenneth French: Variable Definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/variable_definitions.html); [Haugen, Baker (1996): Commonality in the Determinants of Expected Stock Returns](https://quantitativeinvestment.com/documents/common.pdf) |
| `kr_edge_spread_reference_v1`<br>EDGE 유효 스프레드 추정 | transaction_cost | 2015-01-31~2026-09-30 / 141월 / 3131종목 | 304,844 | [Ardia, Guidotti and Kroencke (2024), Efficient Estimation of Bid-Ask Spreads from Open, High, Low, and Close Prices](https://doi.org/10.1016/j.jfineco.2024.103916) |
| `kr_equity_growth_fy_v1`<br>장부 총자본 성장 | investment | 2016-06-30~2026-09-30 / 124월 / 2787종목 | 215,040 | [Bradshaw, Richardson, Sloan (2006): Corporate Financing Activities, Analysts' Forecasts and Stock Returns](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=904226); [Jensen, Kelly, Pedersen (2023): Is There a Replication Crisis in Finance?](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13249) |
| `kr_equity_to_issue_cap_fy_v1`<br>총자본/보통주 종목시총 대용 | value | 2015-06-30~2026-09-30 / 136월 / 2958종목 | 259,766 | [Kenneth French: Variable Definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/variable_definitions.html) |
| `kr_external_financing_fy_v1`<br>외부조달 현금흐름 강도 | external_financing | 2017-02-28~2026-09-30 / 116월 / 2725종목 | 209,235 | [Bradshaw, Richardson and Sloan (2006), The relation between corporate financing activities, analysts forecasts and stock returns](https://www.sciencedirect.com/science/article/abs/pii/S0165410106000371); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_free_cashflow_yield_fy_v1`<br>잉여현금흐름 수익률 | cash_distribution | 2016-03-31~2026-09-30 / 127월 / 2481종목 | 197,926 | [Lakonishok, Shleifer and Vishny (1994); JKP fcf_me](https://doi.org/10.1111/j.1540-6261.1994.tb04772.x); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_gross_margin_fy_v1`<br>매출총이익률 | profitability | 2016-02-29~2026-09-30 / 128월 / 2527종목 | 232,260 | [Soliman (2008): The Use of DuPont Analysis by Market Participants](https://doi.org/10.2308/accr.2008.83.3.823); [Novy-Marx (2013): The Other Side of Value](https://www.nber.org/papers/w15940) |
| `kr_gross_profit_assets_fy_v1`<br>매출총이익/자산 | profitability | 2016-02-29~2026-09-30 / 128월 / 2557종목 | 234,324 | [Novy-Marx (2013): The Other Side of Value](https://www.nber.org/papers/w15940) |
| `kr_gross_profit_growth_per_share_5fy_reference_v1`<br>5년 주당 매출총이익 성장 | profit_growth | 2021-02-28~2026-09-30 / 68월 / 1814종목 | 89,756 | [Asness, Frazzini and Pedersen (2019), Quality minus junk, GMAR growth](https://d-nb.info/1174954515/34) |
| `kr_gross_profit_sales_gap_fy_v1`<br>매출총이익과 매출의 기대 대비 차이 | fundamental_divergence | 2018-02-28~2026-09-30 / 104월 / 2248종목 | 159,163 | [Abarbanell and Bushee (1998), Abnormal Returns to a Fundamental Analysis Strategy](https://www.jstor.org/stable/248340); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_high_252d_v1`<br>52주 고점 근접도 | momentum | 2016-01-31~2026-09-30 / 129월 / 3021종목 | 282,465 | [George and Hwang (2004): The 52-Week High and Momentum Investing](https://doi.org/10.1111/j.1540-6261.2004.00695.x) |
| `kr_idiosyncratic_volatility_reference_v1`<br>시장모형 잔차 변동성 | idiosyncratic_risk | 2015-01-31~2026-09-30 / 141월 / 3034종목 | 292,825 | [Ali, Hwang and Trombley (2003), Arbitrage risk and the book-to-market anomaly; JKP ivol_capm_252d](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_information_discreteness_12_2_v1`<br>정보 불연속성 | momentum | 2016-01-31~2026-09-30 / 129월 / 3025종목 | 282,871 | [Da, Gurun, Warachka (2014): Frog in the Pan](https://www.umitgurun.com/work/Frog.pdf) |
| `kr_intraday_momentum_1m_v1`<br>장중 구간 가격 지속성 | momentum | 2015-01-31~2026-09-30 / 141월 / 3124종목 | 305,030 | [Lou, Polk, Skouras (2019): A tug of war: Overnight versus intraday expected returns](https://www.fmg.ac.uk/pwc/publications/academic-journals/tug-war-overnight-versus-intraday-expected-returns) |
| `kr_inventory_investment_fy_v1`<br>재고 증가/전기자산 | investment | 2017-02-28~2026-09-30 / 116월 / 2388종목 | 193,423 | [Thomas, Zhang (2002): Inventory change reproduction](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Predictors/ChInv.py) |
| `kr_liabilities_assets_fy_v1`<br>총부채 비율 | quality | 2015-06-30~2026-09-30 / 136월 / 2958종목 | 260,104 | [Piotroski (2000): Value Investing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455); [Altman (1968): Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x) |
| `kr_liquidity_reversal_reference_v1`<br>거래대금 조건부 반전 계수 | liquidity_resiliency | 2015-01-31~2026-09-30 / 141월 / 3128종목 | 306,305 | [Pastor and Stambaugh (2003), Liquidity Risk and Expected Stock Returns](https://doi.org/10.1086/374184) |
| `kr_low_volatility_252d_v1`<br>일간 저변동성 | low_risk | 2015-10-31~2026-09-30 / 132월 / 3046종목 | 291,010 | [AQR: Betting Against Correlation](https://www.aqr.com/Insights/Perspectives/Betting-Against-Correlation) |
| `kr_max_1m_v1`<br>복권형 극단 상승: 월간 최대 일수익 | lottery | 2015-01-31~2026-09-30 / 141월 / 3145종목 | 318,685 | [Bali, Cakici and Whitelaw (2011): Maxing out](https://pages.stern.nyu.edu/~rwhitela/papers/max%20jfe11.pdf) |
| `kr_momentum_12_2_price_v1`<br>최근 한 달 제외 12–2 가격 모멘텀 | momentum | 2016-01-31~2026-09-30 / 129월 / 3025종목 | 282,871 | [Kenneth French: Monthly Momentum Factor](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html) |
| `kr_net_margin_fy_v1`<br>순이익률 | profitability | 2015-06-30~2026-09-30 / 136월 / 2755종목 | 249,484 | [Soliman (2008): The Use of DuPont Analysis by Market Participants](https://doi.org/10.2308/accr.2008.83.3.823) |
| `kr_net_payout_profit_5fy_v1`<br>5년 이익 대비 순지급 | payout_policy | 2021-02-28~2026-09-30 / 68월 / 1794종목 | 87,982 | [Asness, Frazzini and Pedersen (2019), Quality minus junk, alternative payout NPOP](https://d-nb.info/1174954515/34); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_net_share_issuance_reference_v1`<br>분할조정 대용 주식수 순발행 | equity_supply | 2015-01-31~2026-09-30 / 141월 / 3041종목 | 290,463 | [Asness, Frazzini and Pedersen (2019), Quality minus junk, alternative payout EISS](https://d-nb.info/1174954515/34) |
| `kr_nominal_price_v1`<br>명목 주가 | lottery | 2015-01-31~2026-09-30 / 141월 / 3160종목 | 320,056 | [Kumar (2009): Who Gambles in the Stock Market?](https://doi.org/10.1111/j.1540-6261.2009.01483.x) |
| `kr_nonprice_size_property_plant_and_equipment_v1`<br>비가격 기업규모: 유형자산 | nonprice_size | 2016-02-29~2026-09-30 / 128월 / 2743종목 | 250,513 | [Asness et al. (2018), Size matters, if you control your junk](https://doi.org/10.1016/j.jfineco.2018.05.006); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_nonprice_size_revenue_v1`<br>비가격 기업규모: 매출 | nonprice_size | 2015-06-30~2026-09-30 / 136월 / 2758종목 | 251,654 | [Asness et al. (2018), Size matters, if you control your junk](https://doi.org/10.1016/j.jfineco.2018.05.006); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_nonprice_size_total_assets_v1`<br>비가격 기업규모: 총자산 | nonprice_size | 2015-06-30~2026-09-30 / 136월 / 2958종목 | 260,258 | [Asness et al. (2018), Size matters, if you control your junk](https://doi.org/10.1016/j.jfineco.2018.05.006); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_nonprice_size_total_equity_v1`<br>비가격 기업규모: 장부자본 | nonprice_size | 2015-06-30~2026-09-30 / 136월 / 2954종목 | 259,186 | [Asness et al. (2018), Size matters, if you control your junk](https://doi.org/10.1016/j.jfineco.2018.05.006); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_operating_margin_fy_v1`<br>영업이익률 | profitability | 2015-06-30~2026-09-30 / 136월 / 2758종목 | 251,225 | [Soliman (2008): The Use of DuPont Analysis by Market Participants](https://doi.org/10.2308/accr.2008.83.3.823) |
| `kr_operating_profit_assets_fy_v1`<br>연간 영업이익/자산 | profitability | 2015-06-30~2026-09-30 / 136월 / 2958종목 | 259,634 | [Ball, Gerakos, Linnainmaa, Nikolaev (2016): Accruals, cash flows, and operating profitability](https://jlinnainmaa.com/publications.html); [Novy-Marx, Medhat (2025): Profitability Retrospective](https://www.nber.org/papers/w33601) |
| `kr_overnight_momentum_1m_v1`<br>장외 구간 가격 지속성 | momentum | 2015-02-28~2026-09-30 / 140월 / 3121종목 | 302,902 | [Lou, Polk, Skouras (2019): A tug of war: Overnight versus intraday expected returns](https://www.fmg.ac.uk/pwc/publications/academic-journals/tug-war-overnight-versus-intraday-expected-returns) |
| `kr_parkinson_1m_v1`<br>고저가 범위 분산 | risk | 2015-01-31~2026-09-30 / 141월 / 3132종목 | 307,954 | [Parkinson (1980): The Extreme Value Method for Estimating the Variance of the Rate of Return](https://www.cmegroup.com/trading/fx/files/michael_parkinson.pdf) |
| `kr_percent_accruals_fy_v1`<br>이익 대비 발생액 | earnings_quality | 2016-01-31~2026-09-30 / 129월 / 2916종목 | 250,557 | [Hafzalla, Lundholm and Van Winkle (2011), Percent Accruals](https://doi.org/10.2308/accr.00000011); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_ppe_inventory_investment_fy_v1`<br>유형자산·재고 투자 | investment_composition | 2017-02-28~2026-09-30 / 116월 / 2387종목 | 193,060 | [Lyandres, Sun and Zhang (2008), The New Issues Puzzle: Testing the Investment-Based Explanation](https://doi.org/10.1093/rfs/hhm058); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_price_delay_reference_v1`<br>시장정보 반영 지연 | information_diffusion | 2015-01-31~2026-09-30 / 141월 / 3064종목 | 294,307 | [Hou and Moskowitz (2005), Market Frictions, Price Delay, and the Cross-Section of Expected Returns](https://doi.org/10.1093/rfs/hhi023) |
| `kr_quality_profitability_composite_reference_v1`<br>AQR 수익성 품질 종합측정 | quality_composite | 2016-03-31~2026-09-30 / 127월 / 2516종목 | 226,834 | [Asness, Frazzini and Pedersen (2019), Quality minus junk; JKP qmj_prof](https://d-nb.info/1174954515/34) |
| `kr_receivables_investment_fy_v1`<br>매출·기타 유동채권 증가/전기자산 | investment | 2017-02-28~2026-09-30 / 116월 / 2219종목 | 145,731 | [Richardson, Sloan, Soliman, Tuna (2005): Accrual reliability, earnings persistence and stock prices](https://doi.org/10.1016/j.jacceco.2005.04.005); [Hirshleifer, Hou, Teoh, Zhang (2004): Bloated Balance Sheets](https://www.sciencedirect.com/science/article/pii/S0165410104000795) |
| `kr_retained_earnings_assets_fy_v1`<br>이익잉여금/자산 | quality | 2015-06-30~2026-09-30 / 136월 / 2945종목 | 246,193 | [Altman (1968): Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x) |
| `kr_return_autocorrelation_reference_v1`<br>일별 수익률 자기상관 | market_friction | 2015-01-31~2026-09-30 / 141월 / 3128종목 | 306,450 | [Campbell, Grossman and Wang (1993), Trading Volume and Serial Correlation in Stock Returns](https://www.nber.org/papers/w4193) |
| `kr_return_skew_252d_v1`<br>일수익 왜도 | lottery | 2015-10-31~2026-09-30 / 132월 / 3046종목 | 287,303 | [Bali, Engle, Murray: Empirical Asset Pricing; ReturnSkew reproduction](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Predictors/ReturnSkew.py) |
| `kr_reversal_1m_price_v1`<br>직전 한 달 가격 반전 | reversal | 2015-02-28~2026-09-30 / 140월 / 3143종목 | 316,894 | [Kenneth French: Short-Term Reversal](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_st_rev_factor.html) |
| `kr_reversal_36_13_price_v1`<br>장기 가격 반전 | reversal | 2018-01-31~2026-09-30 / 105월 / 2560종목 | 214,456 | [De Bondt, Thaler (1985): Does the Stock Market Overreact?](https://doi.org/10.1111/j.1540-6261.1985.tb05004.x) |
| `kr_roa_fy_v1`<br>연간 순이익/자산 | profitability | 2015-06-30~2026-09-30 / 136월 / 2956종목 | 257,854 | [Balakrishnan, Bartov, Faurel (2010): ROA reproduction](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Predictors/roaq.py); [Novy-Marx, Medhat (2025): Profitability Retrospective](https://www.nber.org/papers/w33601) |
| `kr_roe_fy_v1`<br>연간 자기자본 수익성 | profitability | 2015-06-30~2026-09-30 / 136월 / 2952종목 | 256,779 | [Haugen, Baker (1996): Commonality in the Determinants of Expected Stock Returns](https://quantitativeinvestment.com/documents/common.pdf) |
| `kr_sales_growth_fy_v1`<br>매출 성장 | investment | 2016-06-30~2026-09-30 / 124월 / 2629종목 | 209,968 | [Lakonishok, Shleifer, Vishny (1994): Contrarian Investment, Extrapolation, and Risk](https://shleifer.scholars.harvard.edu/publications/contrarian-investment-extrapolation-and-risk) |
| `kr_sales_inventory_gap_fy_v1`<br>매출과 재고의 기대 대비 차이 | fundamental_divergence | 2018-02-28~2026-09-30 / 104월 / 2239종목 | 159,868 | [Abarbanell and Bushee (1998), Abnormal Returns to a Fundamental Analysis Strategy](https://www.jstor.org/stable/248340); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_sales_receivables_gap_fy_v1`<br>매출과 채권의 기대 대비 차이 | fundamental_divergence | 2018-02-28~2026-09-30 / 104월 / 1774종목 | 114,146 | [Abarbanell and Bushee (1998), Abnormal Returns to a Fundamental Analysis Strategy](https://www.jstor.org/stable/248340); [JKP official replication documentation, pinned commit](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_sales_to_issue_cap_fy_v1`<br>연간 매출/종목시총 | value | 2015-06-30~2026-09-30 / 136월 / 2872종목 | 254,031 | [Barbee, Mukherji, Raines (1996): Do Sales–Price and Debt–Equity Explain Stock Returns Better than Book–Market and Firm Size?](https://rpc.cfainstitute.org/research/financial-analysts-journal/1996/do-salesprice-and-debtequity-explain-stock-returns-better-than-bookmarket-and-firm-size) |
| `kr_size_issue_v1`<br>기업 규모 대용: 종목 시가총액 | size | 2015-01-31~2026-09-30 / 141월 / 3160종목 | 320,056 | [Kenneth French: Fama/French 5 Factors](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html) |
| `kr_tangibility_fy_v1`<br>유형자산 비중 | quality | 2016-02-29~2026-09-30 / 128월 / 2743종목 | 250,398 | [Almeida, Campello (2007): Financial Constraints, Asset Tangibility, and Corporate Investment](https://www.nber.org/system/files/working_papers/w12087/w12087.pdf) |
| `kr_tax_expense_change_assets_fy_v1`<br>연간 법인세비용 변화 | tax_information | 2017-02-28~2026-09-30 / 116월 / 2686종목 | 201,232 | [Thomas and Zhang (2011), Tax Expense Momentum](https://doi.org/10.1111/j.1475-679X.2011.00409.x); [JKP author replication documentation](https://github.com/bkelly-lab/jkp-data/blob/666e8960ed81a664f1e9f189f92925ab2eeffcd5/documentation/documentation.tex) |
| `kr_traded_value_1m_v1`<br>평균 거래대금 | liquidity | 2015-01-31~2026-09-30 / 141월 / 3140종목 | 310,355 | [Brennan, Chordia, Subrahmanyam (1998): Alternative factor specifications](https://www.sciencedirect.com/science/article/pii/S0304405X98000282) |
| `kr_traded_value_cv_1m_v1`<br>거래대금 변동계수 | liquidity | 2015-01-31~2026-09-30 / 141월 / 3140종목 | 310,355 | [Chordia, Subrahmanyam, Anshuman (2001): Trading activity and expected stock returns](https://research.iimb.ac.in/fac_pubs/1268/) |
| `kr_turnover_1m_v1`<br>주식 회전율 | liquidity | 2015-01-31~2026-09-30 / 141월 / 3145종목 | 318,739 | [Datar, Naik, Radcliffe (1998): Liquidity and stock returns](https://www.sciencedirect.com/science/article/pii/S1386418197000049) |
| `kr_turnover_cv_1m_v1`<br>회전율 변동계수 | liquidity | 2015-01-31~2026-09-30 / 141월 / 3140종목 | 310,355 | [Chordia, Subrahmanyam, Anshuman (2001): Trading activity and expected stock returns](https://research.iimb.ac.in/fac_pubs/1268/) |
| `kr_volume_trend_reference_v1`<br>장기 거래량 추세 | trading_participation | 2015-06-30~2026-09-30 / 136월 / 2730종목 | 261,416 | [Haugen and Baker (1996), Commonality in the determinants of expected stock returns; Chen-Zimmermann VolumeTrend replication](https://doi.org/10.1016/0304-405X(95)00868-F) |
| `kr_working_capital_assets_fy_v1`<br>운전자본/자산 | quality | 2015-06-30~2026-09-30 / 136월 / 2874종목 | 257,647 | [Altman (1968): Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x) |
| `kr_wq_001_daily_monthend_v1`<br>WQ 001: 하락 변동성과 고점 시점 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3123종목 | 300,626 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_002_daily_monthend_v1`<br>WQ 002: 거래량 변화와 장중수익 순위 관계 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 305,871 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_004_daily_monthend_v1`<br>WQ 004: 저가 순위의 단기 위치 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 305,569 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_005_daily_monthend_v1`<br>WQ 005: 평균 체결가격 대비 시가·종가 괴리 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 300,166 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_006_daily_monthend_v1`<br>WQ 006: 시가와 거래량의 상관 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 305,285 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_008_daily_monthend_v1`<br>WQ 008: 가격수준 가중 단기 추세 변화 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3127종목 | 303,676 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_009_daily_monthend_v1`<br>WQ 009: 추세 연속성에 따른 반전 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3132종목 | 306,560 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_011_daily_monthend_v1`<br>WQ 011: 체결가격 괴리 범위와 거래량 변화 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3136종목 | 305,672 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_012_daily_monthend_v1`<br>WQ 012: 거래량 방향 조건부 가격변화 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3141종목 | 308,122 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_013_daily_monthend_v1`<br>WQ 013: 가격·거래량 순위 공분산 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3134종목 | 306,933 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_014_daily_monthend_v1`<br>WQ 014: 수익률 가속과 거래량 관계 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 305,285 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_019_daily_monthend_v1`<br>WQ 019: 장단기 방향의 결합 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 2923종목 | 251,485 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_020_daily_monthend_v1`<br>WQ 020: 전일 가격범위 대비 시가 갭 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3141종목 | 308,122 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_023_daily_monthend_v1`<br>WQ 023: 평균 고가 돌파 조건부 반전 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3124종목 | 302,542 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_024_daily_monthend_v1`<br>WQ 024: 장기추세 조건부 단기 반전 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 2983종목 | 261,050 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_026_daily_monthend_v1`<br>WQ 026: 거래량·고가 시계열 순위 관계 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3129종목 | 281,689 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_030_daily_monthend_v1`<br>WQ 030: 가격방향 일관성과 거래집중 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3124종목 | 302,542 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_035_daily_monthend_v1`<br>WQ 035: 거래량·가격범위·수익률의 위치 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3115종목 | 298,548 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_037_daily_monthend_v1`<br>WQ 037: 장중 압력의 지연 상관 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 2982종목 | 260,874 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_038_daily_monthend_v1`<br>WQ 038: 가격 시계열 위치와 시가 대비 종가 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3130종목 | 305,295 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_041_daily_monthend_v1`<br>WQ 041: 고저가 중심과 평균 체결가격 괴리 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3144종목 | 308,584 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_052_daily_monthend_v1`<br>WQ 052: 저점 이동과 중기 추세의 거래량 조건 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 2938종목 | 253,308 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_060_daily_monthend_v1`<br>WQ 060: 거래량 가중 가격위치와 고점 시점 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3128종목 | 305,040 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_wq_101_daily_monthend_v1`<br>WQ 101: 일중 범위로 조정한 몸통 크기 | price_volume_interaction | 2015-01-31~2026-09-30 / 141월 / 3144종목 | 309,128 | [Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission](https://arxiv.org/abs/1601.00991) |
| `kr_zero_volume_1m_v1`<br>무거래 관측일 비율 | liquidity | 2015-01-31~2026-09-30 / 141월 / 3145종목 | 318,739 | [Liu (2006): A liquidity-augmented capital asset pricing model](https://research.manchester.ac.uk/en/publications/a-liquidity-augmented-capital-asset-pricing-model/) |

## 신규 정의의 원문 대비 차이

### 매출 대비 비정상 설비투자 — `kr_abnormal_capex_fy_v1`

정확한 FY 4개 필요. DART 유형자산 취득을 CAPEX로 한정한 한국형 측정. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### AQR 방식 축소 베타 — `kr_bab_beta_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 종목별 달력 계절성 — `kr_calendar_seasonality_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 설비투자 증가율 — `kr_capex_growth_2fy_v1`

JKP capx_gr2, 정확히 두 FY 전 취득 현금유출 비교. 기존 총자산 증가율과 별개. 1년/3년 변형은 별도 등록하지 않음. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 영업현금흐름 수익성 개선 — `kr_cfo_assets_change_fy_v1`

CFM 관련 연구. JKP 연간 ocf_at_chg1을 DART KRW FY 영업현금흐름·기말총자산으로 측정. 애널리스트 기대 경직성을 측정하거나 인과를 입증하지 않음. 기존 CFO/Assets 수준과 변화는 별개 가설이며 경제적 중복은 후속 spanning 검토 대상.

### 시장 공동첨도 진단 — `kr_cokurtosis_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 시장 공동왜도 — `kr_coskewness_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 하락시장 민감도 — `kr_downside_beta_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 5개 FY 이익 안정성 — `kr_earnings_stability_5fy_v1`

최종판 연간 ROE 변동성 fallback. 5개 연속 FY 모두 필요하며 분기 60개 원형을 재현했다고 하지 않음. 총자본 ROE 사용. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### EDGE 유효 스프레드 추정 — `kr_edge_spread_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명. EDGE는 원시 OHLC의 연속성이 필요하므로 월내 인접 가격조정계수가 1e-6 초과 변화한 달은 기업행위 혼입 방지를 위해 제외.

### 외부조달 현금흐름 강도 — `kr_external_financing_fy_v1`

DART 재무활동 순현금흐름으로 정의. 발행액 단독 아님. 원문 금융현금흐름 분류와 IFRS 이자/배당 분류 차이 가능. Cohen-Lys(2006)의 발생액 통제 후 효과 약화라는 반대 근거를 보존. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 잉여현금흐름 수익률 — `kr_free_cashflow_yield_fy_v1`

JKP FCF/ME의 DART 유형자산 취득 현금유출 기반 구현. 무형자산 취득은 포함하지 않으며 전체 기업 CAPEX와 동일하지 않음. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 5년 주당 매출총이익 성장 — `kr_gross_profit_growth_per_share_5fy_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 매출총이익과 매출의 기대 대비 차이 — `kr_gross_profit_sales_gap_fy_v1`

JKP CHG_TO_EXP는 최근 두 FY 평균에 대한 비율. 채권은 매출채권 단독이 아닌 DART 기타유동채권 포함. 원문/JKP에서 개별 신호 유의성이 모두 지지된 것은 아님. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 시장모형 잔차 변동성 — `kr_idiosyncratic_volatility_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 거래대금 조건부 반전 계수 — `kr_liquidity_reversal_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 5년 이익 대비 순지급 — `kr_net_payout_profit_5fy_v1`

대체 payout 정의의 5년 합산. 순자본 변화에는 OCI·비지배지분이 섞일 수 있으므로 실제 배당/자사주 현금액으로 해석하지 않음. 첨부 Size/Quality 논의와 최종 QMJ 부록 연결. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 분할조정 대용 주식수 순발행 — `kr_net_share_issuance_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 비가격 기업규모: 유형자산 — `kr_nonprice_size_property_plant_and_equipment_v1`

첨부 AQR 20 for Twenty 16장 비가격 규모. 시장가격을 포함하지 않는 기업규모 통제이며 단독 초과수익 주장이 아님. 자본은 우선주/비지배지분 차감 전 총자본, PPE는 순장부가로 원문의 gross PPE와 다름. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 비가격 기업규모: 매출 — `kr_nonprice_size_revenue_v1`

첨부 AQR 20 for Twenty 16장 비가격 규모. 시장가격을 포함하지 않는 기업규모 통제이며 단독 초과수익 주장이 아님. 자본은 우선주/비지배지분 차감 전 총자본, PPE는 순장부가로 원문의 gross PPE와 다름. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 비가격 기업규모: 총자산 — `kr_nonprice_size_total_assets_v1`

첨부 AQR 20 for Twenty 16장 비가격 규모. 시장가격을 포함하지 않는 기업규모 통제이며 단독 초과수익 주장이 아님. 자본은 우선주/비지배지분 차감 전 총자본, PPE는 순장부가로 원문의 gross PPE와 다름. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 비가격 기업규모: 장부자본 — `kr_nonprice_size_total_equity_v1`

첨부 AQR 20 for Twenty 16장 비가격 규모. 시장가격을 포함하지 않는 기업규모 통제이며 단독 초과수익 주장이 아님. 자본은 우선주/비지배지분 차감 전 총자본, PPE는 순장부가로 원문의 gross PPE와 다름. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 이익 대비 발생액 — `kr_percent_accruals_fy_v1`

이익의 현금전환 비율 질문. 총자산으로 나눈 기존 발생액과 경제적 관련성은 있지만 동일하거나 단조변환인 산식은 아님. NI=0은 결측. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 유형자산·재고 투자 — `kr_ppe_inventory_investment_fy_v1`

원형의 gross PPE 대신 DART 순장부 PPE를 사용한 명시적 적응. 기존 재고 단독 변화/총자산 성장과 산식이 다름. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 시장정보 반영 지연 — `kr_price_delay_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### AQR 수익성 품질 종합측정 — `kr_quality_profitability_composite_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 일별 수익률 자기상관 — `kr_return_autocorrelation_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### 매출과 재고의 기대 대비 차이 — `kr_sales_inventory_gap_fy_v1`

JKP CHG_TO_EXP는 최근 두 FY 평균에 대한 비율. 채권은 매출채권 단독이 아닌 DART 기타유동채권 포함. 원문/JKP에서 개별 신호 유의성이 모두 지지된 것은 아님. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 매출과 채권의 기대 대비 차이 — `kr_sales_receivables_gap_fy_v1`

JKP CHG_TO_EXP는 최근 두 FY 평균에 대한 비율. 채권은 매출채권 단독이 아닌 DART 기타유동채권 포함. 원문/JKP에서 개별 신호 유의성이 모두 지지된 것은 아님. 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.

### 연간 법인세비용 변화 — `kr_tax_expense_change_assets_fy_v1`

JKP의 연간 tax_gr1a 측정. Thomas-Zhang 원문의 분기 전년동기 tax surprise 원식 재현 아님. DART 계속영업 법인세비용을 사용하고 현금납부세금·유효세율과 구별. 한국 수익성 미검증.

### 장기 거래량 추세 — `kr_volume_trend_reference_v1`

시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.

### WQ 001: 하락 변동성과 고점 시점 — `kr_wq_001_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 002: 거래량 변화와 장중수익 순위 관계 — `kr_wq_002_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 004: 저가 순위의 단기 위치 — `kr_wq_004_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 005: 평균 체결가격 대비 시가·종가 괴리 — `kr_wq_005_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명. VWAP는 동일 일자의 KRW 거래대금/거래량으로 계산하며 OHLC 단순평균으로 대체하지 않음. 거래량 0 또는 VWAP가 당일 저가~고가 범위 밖이면 결측 처리.

### WQ 006: 시가와 거래량의 상관 — `kr_wq_006_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 008: 가격수준 가중 단기 추세 변화 — `kr_wq_008_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 009: 추세 연속성에 따른 반전 — `kr_wq_009_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 011: 체결가격 괴리 범위와 거래량 변화 — `kr_wq_011_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명. VWAP는 동일 일자의 KRW 거래대금/거래량으로 계산하며 OHLC 단순평균으로 대체하지 않음. 거래량 0 또는 VWAP가 당일 저가~고가 범위 밖이면 결측 처리.

### WQ 012: 거래량 방향 조건부 가격변화 — `kr_wq_012_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 013: 가격·거래량 순위 공분산 — `kr_wq_013_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 014: 수익률 가속과 거래량 관계 — `kr_wq_014_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 019: 장단기 방향의 결합 — `kr_wq_019_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 020: 전일 가격범위 대비 시가 갭 — `kr_wq_020_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 023: 평균 고가 돌파 조건부 반전 — `kr_wq_023_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 024: 장기추세 조건부 단기 반전 — `kr_wq_024_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 026: 거래량·고가 시계열 순위 관계 — `kr_wq_026_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 030: 가격방향 일관성과 거래집중 — `kr_wq_030_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 035: 거래량·가격범위·수익률의 위치 — `kr_wq_035_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 037: 장중 압력의 지연 상관 — `kr_wq_037_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 038: 가격 시계열 위치와 시가 대비 종가 — `kr_wq_038_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 041: 고저가 중심과 평균 체결가격 괴리 — `kr_wq_041_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명. VWAP는 동일 일자의 KRW 거래대금/거래량으로 계산하며 OHLC 단순평균으로 대체하지 않음. 거래량 0 또는 VWAP가 당일 저가~고가 범위 밖이면 결측 처리.

### WQ 052: 저점 이동과 중기 추세의 거래량 조건 — `kr_wq_052_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 060: 거래량 가중 가격위치와 고점 시점 — `kr_wq_060_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

### WQ 101: 일중 범위로 조정한 몸통 크기 — `kr_wq_101_daily_monthend_v1`

원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.

## 발행에서 제외한 계산 후보

WorldQuant #3, #15, #18, #22, #34, #44, #55는 전체 실데이터의 독립 계산 대조에서 수치/순위 차이가 있어 격리했다. 임계값을 완화하거나 일치한 행만 골라 개수를 채우지 않았다. 수정된 EDGE는 가격조정계수 변화 월을 제외한 최종 정의만 적재했다.

## 재현 경로

활성 카탈로그는 [100개 정의](../research/phenomena/reference-catalog-100-20261003.json),
실제 소비 포인터는 [program.json](../research/phenomena/program.json)이다.
45개·47개 시점의 포인터는 `research/phenomena/program-snapshots/`에 보존했다.

활성화 후 테스트 명령:

```sh
.venv/bin/python -m pytest -q tests/test_reference_*.py tests/test_phenomenon_*.py tests/test_publish_prebuilt_references.py
```

결과: **690 passed, 23.62초**. 단위·통합 테스트 성공은 아래 실DB 전 행 검증과 별개로 기록한다.

최종 감사 증거 위치는 `output/phenomena/reference-expansion-100-20261003/final-audit/`다.
`completion.json`은 활성화 직전의 불변 감사 영수증이며, `duplicate-audit.json`과
`joint-availability.json`에 중복·교집합 결과를 보존한다. 로컬 파일만으로 DB 검증을 생략하지 않는다.

`scripts.capture_reference_daily` → `scripts.prepare_reference_diversity` / `scripts.build_reference_formulaic` / `scripts.build_reference_risk_diversity` → 발행 → `scripts.audit_reference_expansion_100` 순서다.
이번 동결 위험 지표 배치는 EDGE 사전 보완을 별도 `scripts.prepare_edge_action_filter`로 재검증했다. 과거 `risk-build` 발행 재개에는 `--exclude-reference kr_edge_spread_reference_v1`을 사용하고, EDGE는 `edge-action-filter`의 publication만 사용한다. 새 원천으로 전체 재계산할 때에는 최신 위험 빌더에 같은 제외 규칙이 내장되어 있다.

## 최종 활성화 및 실제 소비 검증

2026-10-03 **19:45:12 KST**, `ACTIVE_PUBLISHED_AND_CONSUMER_VERIFIED`를 확인했다.
활성 프로그램은 100개 정의·58개 dataset을 정확히 지정한다.

- `program_sha256`: `797c849cea0af2c076a790da68696348f925414a935250b35c3745a3c1c02289`
- `catalog_sha256`: `1521ca08ef82a2ab987bce9a4f5ccf5dff3a0489385748b70fde42f46fb6a633`
- 활성화 증거: [activation-verification.json](../output/phenomena/reference-expansion-100-20261003/final-audit/activation-verification.json)
- 실제 `load_active_references` → `reference_fields` 경로로 규모·세금 변화·비가격 규모·WQ 41·BAB 베타·EDGE·5년 주당 매출총이익 성장의 **7개 대표 지표**를 조회했다.
- 해당 dataset의 **4,245,277행 전체**를 DB와 재대조한 뒤 선택한 1,726,103값을 320,056종목-월에 연결했다. 결측 대체 없음, 레거시 fallback 없음, 알파 승인 없음.
- 전체 100개에 대한 DB 메타데이터·행수·정의·발행 시 전 행 재조회 증거 및 캐시 내용 검증은 최종 감사에서 확인했다. 실제 소비 함수를 통한 추가 재대조는 위 7개 지표가 속한 dataset 범위이며, 100개 전체의 새 수익률 연구를 실행했다는 뜻이 아니다.

활성화 직전의 `completion.json`은 불변 기록이므로 `PREPARED_NOT_ACTIVATED`를 유지한다. 최종 활성 상태는 위 별도 영수증으로 확인한다.
