# 한국 주식 레퍼런스 측정 확장: 문헌·정의 검토

검토일: 2026-10-03 · 활성 연구 세대: `phenomenon-research-v1`

이번 확장은 기존 7개 정의를 유지하고 **가격·거래활동 13개와 연간 재무 25개**를 더해 총 45개 측정 정의를 준비한다. 문헌 매핑 파일은 [reference-expansion-literature.json](../research/phenomena/reference-expansion-literature.json)이며, 실제 구현 ID 38개에 일대일로 연결된다. 이 문서는 문헌·정의 검토 산출물이지 Gold 발행 영수증이 아니다. 실제 적재 완료 수, 종목·기간 커버리지와 데이터 품질은 별도 계산·대조·Gold 재조회 결과로 확정한다.

**45개 측정값은 45개 독립적인 알파가 아니다.** 원형의 롱숏 팩터 수익률도 아니다. 시장·기업 현상을 기술하고, 경쟁 설명을 통제하며, 이후 별도 검증을 거쳐 전략 입력을 선택하기 위한 특성값이다. 한국 수익률을 보고 정의·방향·기간을 선정하지 않았으며 한국 수익성·거래비용 후 성과를 아직 주장하지 않는다.

## 1. 근거를 세 단계로 구분한다

| 새 정의의 근거 등급 | 개수 | 해석 |
| --- | ---: | --- |
| 수익문헌 대용 (`PUBLISHED_PREDICTOR_ADAPTATION`) | 24 | 관련 특성의 수익률 관계가 문헌에 보고됐다. 이번 한국 구현은 계정·기간·단위가 달라 원형 재현이나 국내 알파 승인을 뜻하지 않는다. |
| 통제·구성요소 (`CONTROL_COMPONENT`) | 13 | 재무 상태·위험·설명 경로를 측정하거나 복합 신호의 일부를 나타낸다. 단독 초과수익 근거를 주장하지 않는다. |
| 대체 추정량 (`ALTERNATIVE_ESTIMATOR`) | 1 | 동일 경제 특성의 다른 추정법이다. 독립 경제 개념이나 알파 개수를 늘리는 근거가 아니다. |

문헌에 등장한다는 사실만으로 단독 예측변수가 되지는 않는다. 따라서 CFO/자산은 Piotroski의 현금 창출 관련 정보와 연결하되, Ball 등의 **현금 기반 영업수익성** 전체 공식과 같다고 표시하지 않는다. 유동비율, 부채비율, 이익잉여금/자산, 유형자산 비중도 재무 통제로 구분한다. [Piotroski (2000)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455), [Ball 등 저자 연구 목록](https://jlinnainmaa.com/publications.html)

원문·저자 소속기관의 초록과 변수 정의, 공식 데이터 정의, 저자 공개 재현 코드를 우선 사용했다. **모든 논문 전문을 처음부터 끝까지 읽었다는 의미는 아니다.** 접근 실패·초록만 검토한 경우는 JSON의 `review_scope`에 명시했다. 2차 요약의 수익률 숫자를 한국 성과처럼 가져오지 않았다.

재현 문헌의 큰 그림도 반영했다. Jensen·Kelly·Pedersen은 많은 측정값을 경제적 주제별로 묶어 해석하며, Chen·Zimmermann은 원 연구가 직접 검정한 예측변수와 간접·위약 성격 변수를 구분한다. 본 목록 역시 비슷한 수식을 모두 독립 발견으로 세지 않는다. [Jensen·Kelly·Pedersen (2023)](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13249), [Chen·Zimmermann 연구 문서](https://www.federalreserve.gov/econres/feds/files/2021-037pap.pdf)

## 2. 가격·거래활동 추가 13개

방향은 관측값을 정렬할 때 사전 고정한 방향이다. 통제·대체 추정량의 방향은 **수익률이 좋다는 예측이 아니다**. 예컨대 낮은 명목 주가는 복권형 주식 특성을 진단하기 위한 방향이다.

| 구현 ID | 한국어 명칭 | 정렬 선호 | 근거 구분 | 직접 참고 |
| --- | --- | --- | --- | --- |
| `kr_turnover_1m_v1` | 주식 회전율 | 낮음 | 수익문헌 대용 | [Datar, Naik, Radcliffe (1998)](https://www.sciencedirect.com/science/article/pii/S1386418197000049) |
| `kr_turnover_cv_1m_v1` | 회전율 변동계수 | 낮음 | 수익문헌 대용 | [Chordia, Subrahmanyam, Anshuman (2001)](https://research.iimb.ac.in/fac_pubs/1268/) |
| `kr_traded_value_1m_v1` | 평균 거래대금 | 낮음 | 수익문헌 대용 | [Brennan, Chordia, Subrahmanyam (1998)](https://www.sciencedirect.com/science/article/pii/S0304405X98000282) |
| `kr_traded_value_cv_1m_v1` | 거래대금 변동계수 | 낮음 | 수익문헌 대용 | [Chordia, Subrahmanyam, Anshuman (2001)](https://research.iimb.ac.in/fac_pubs/1268/) |
| `kr_zero_volume_1m_v1` | 무거래 관측일 비율 | 높음 | 수익문헌 대용 | [Liu (2006)](https://research.manchester.ac.uk/en/publications/a-liquidity-augmented-capital-asset-pricing-model/) |
| `kr_downside_risk_252d_v1` | 하방 반편차 | 낮음 | 통제·구성요소 | [Bawa, Lindenberg (1977)](https://www.sciencedirect.com/science/article/pii/0304405X77900174) |
| `kr_return_skew_252d_v1` | 일수익 왜도 | 낮음 | 수익문헌 대용 | [Bali, Engle, Murray](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Predictors/ReturnSkew.py) |
| `kr_parkinson_1m_v1` | 고저가 범위 분산 | 낮음 | 대체 추정량 | [Parkinson (1980)](https://www.cmegroup.com/trading/fx/files/michael_parkinson.pdf) |
| `kr_overnight_momentum_1m_v1` | 장외 구간 가격 지속성 | 높음 | 수익문헌 대용 | [Lou, Polk, Skouras (2019)](https://www.fmg.ac.uk/pwc/publications/academic-journals/tug-war-overnight-versus-intraday-expected-returns) |
| `kr_intraday_momentum_1m_v1` | 장중 구간 가격 지속성 | 높음 | 수익문헌 대용 | [Lou, Polk, Skouras (2019)](https://www.fmg.ac.uk/pwc/publications/academic-journals/tug-war-overnight-versus-intraday-expected-returns) |
| `kr_information_discreteness_12_2_v1` | 정보 불연속성 | 낮음 | 수익문헌 대용 | [Da, Gurun, Warachka (2014)](https://www.umitgurun.com/work/Frog.pdf) |
| `kr_nominal_price_v1` | 명목 주가 | 낮음 | 통제·구성요소 | [Kumar (2009)](https://doi.org/10.1111/j.1540-6261.2009.01483.x) |
| `kr_reversal_36_13_price_v1` | 장기 가격 반전 | 낮음 | 수익문헌 대용 | [De Bondt, Thaler (1985)](https://doi.org/10.1111/j.1540-6261.1985.tb05004.x) |

원형과의 주요 차이는 다음과 같다.

- 회전율과 거래대금 변동계수는 **당월 일별 관측값**으로 계산한다. Chordia 등의 장기간 월별 변동성 정의와 다르므로 동일 원형으로 부르지 않는다.
- 무거래 관측일 비율은 Liu의 무거래일·회전율을 결합한 유동성 측정값 전체가 아니다. 존재하지 않는 거래일을 0거래일로 보간하지 않는다.
- 하방 반편차는 시장 하락 시 민감도를 나타내는 **downside beta가 아니다**.
- 왜도는 252개 과거 관측행을 사용한다. 재현 문헌의 짧은 추정창과 다르며 극단값·관측 수에 민감하다.
- Parkinson은 `mean(log(high/low)^2 / (4 log 2))`인 **분산**이다. 표준편차도, 연율화된 변동성도 아니다.
- 장외·장중은 각 1개월 기하 누적 가격수익률이다. 장외 일별 gross는 `(open/close) × (adj_close/prev_adj_close)`로 당일 조정계수를 일관되게 적용한다. 배당 포함 총수익이 아니다. 모든 관측 세션이 유효해야 하며 최소 15개를 요구한다.
- 정보 불연속성은 과거 모멘텀의 부호와 상승·하락 일수 구성의 결합이다. 원 논문의 조건부 모멘텀 해석을 지켜야 하며 무조건적인 단독 신호로 읽지 않는다.
- 장기 반전은 36개월 전~12개월 전 가격 변화로 최근 12개월을 건너뛴다. 원형의 기간·포트폴리오 구성과 차이가 있다.
- 모두 거래소 공식 세션 달력 대신 현재 어댑터의 **관측행 기반 창**이다. 결측·거래정지·상장기간 차이는 커버리지 진단에 따로 남겨야 한다.

원 논문과 국내 적응식의 차이는 각 JSON 정의의 `adaptation` 및 구현 공식에 보존한다.

## 3. 연간 재무 추가 25개

`FY`는 실제로 이용 가능했던 연간 회계 기간을 뜻한다. 현재 값을 과거에 단순히 복사하는 것이 아니며, 분기 자료를 혼합해 임의의 TTM을 만들지도 않는다. 아래 “정렬 선호”는 한국 성과로 최적화한 부호가 아니다.

| 구현 ID | 한국어 명칭 | 정렬 선호 | 근거 구분 | 직접 참고 |
| --- | --- | --- | --- | --- |
| `kr_equity_to_issue_cap_fy_v1` | 총자본/보통주 종목시총 대용 | 높음 | 수익문헌 대용 | [Kenneth French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/variable_definitions.html) |
| `kr_earnings_to_issue_cap_fy_v1` | 연간 순이익/종목시총 | 높음 | 수익문헌 대용 | [Kenneth French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/variable_definitions.html) |
| `kr_sales_to_issue_cap_fy_v1` | 연간 매출/종목시총 | 높음 | 수익문헌 대용 | [Barbee, Mukherji, Raines (1996)](https://rpc.cfainstitute.org/research/financial-analysts-journal/1996/do-salesprice-and-debtequity-explain-stock-returns-better-than-bookmarket-and-firm-size) |
| `kr_cfo_to_issue_cap_fy_v1` | 영업현금흐름/종목시총 | 높음 | 수익문헌 대용 | [Desai, Rajgopal, Venkatachalam (2004)](https://business.columbia.edu/sites/default/files-efs/pubfiles/12921/desai%20rajgopal%20venkatachalam.pdf) |
| `kr_gross_profit_assets_fy_v1` | 매출총이익/자산 | 높음 | 수익문헌 대용 | [Novy-Marx (2013)](https://www.nber.org/papers/w15940) |
| `kr_operating_profit_assets_fy_v1` | 연간 영업이익/자산 | 높음 | 수익문헌 대용 | [Ball, Gerakos, Linnainmaa, Nikolaev (2016)](https://jlinnainmaa.com/publications.html) |
| `kr_roa_fy_v1` | 연간 순이익/자산 | 높음 | 수익문헌 대용 | [Balakrishnan, Bartov, Faurel (2010)](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Predictors/roaq.py) |
| `kr_roe_fy_v1` | 연간 자기자본 수익성 | 높음 | 수익문헌 대용 | [Haugen, Baker (1996)](https://quantitativeinvestment.com/documents/common.pdf) |
| `kr_cfo_assets_fy_v1` | 영업현금흐름/자산 | 높음 | 통제·구성요소 | [Ball, Gerakos, Linnainmaa, Nikolaev (2016)](https://jlinnainmaa.com/publications.html) |
| `kr_gross_margin_fy_v1` | 매출총이익률 | 높음 | 통제·구성요소 | [Soliman (2008)](https://doi.org/10.2308/accr.2008.83.3.823) |
| `kr_operating_margin_fy_v1` | 영업이익률 | 높음 | 통제·구성요소 | [Soliman (2008)](https://doi.org/10.2308/accr.2008.83.3.823) |
| `kr_net_margin_fy_v1` | 순이익률 | 높음 | 통제·구성요소 | [Soliman (2008)](https://doi.org/10.2308/accr.2008.83.3.823) |
| `kr_liabilities_assets_fy_v1` | 총부채 비율 | 낮음 | 통제·구성요소 | [Piotroski (2000)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455) |
| `kr_current_ratio_fy_v1` | 유동비율 | 높음 | 통제·구성요소 | [Piotroski (2000)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455) |
| `kr_cash_assets_fy_v1` | 현금/자산 | 높음 | 수익문헌 대용 | [Palazzo (2012)](https://www.sciencedirect.com/science/article/pii/S0304405X11002856) |
| `kr_retained_earnings_assets_fy_v1` | 이익잉여금/자산 | 높음 | 통제·구성요소 | [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x) |
| `kr_tangibility_fy_v1` | 유형자산 비중 | 높음 | 통제·구성요소 | [Almeida, Campello (2007)](https://www.nber.org/system/files/working_papers/w12087/w12087.pdf) |
| `kr_working_capital_assets_fy_v1` | 운전자본/자산 | 높음 | 통제·구성요소 | [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x) |
| `kr_cashflow_accruals_fy_v1` | 현금흐름 방식 발생액 | 낮음 | 수익문헌 대용 | [Desai, Rajgopal, Venkatachalam (2004)](https://business.columbia.edu/sites/default/files-efs/pubfiles/12921/desai%20rajgopal%20venkatachalam.pdf) |
| `kr_asset_growth_fy_v1` | 총자산 성장 | 낮음 | 수익문헌 대용 | [Cooper, Gulen, Schill (2008)](https://doi.org/10.1111/j.1540-6261.2008.01370.x) |
| `kr_sales_growth_fy_v1` | 매출 성장 | 낮음 | 수익문헌 대용 | [Lakonishok, Shleifer, Vishny (1994)](https://shleifer.scholars.harvard.edu/publications/contrarian-investment-extrapolation-and-risk) |
| `kr_equity_growth_fy_v1` | 장부 총자본 성장 | 낮음 | 통제·구성요소 | [Bradshaw, Richardson, Sloan (2006)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=904226) |
| `kr_inventory_investment_fy_v1` | 재고 증가/전기자산 | 낮음 | 수익문헌 대용 | [Thomas, Zhang (2002)](https://github.com/OpenSourceAP/CrossSection/blob/8db892442c2c3a3779b0f1eac4370d3655be15a1/Signals/pyCode/Predictors/ChInv.py) |
| `kr_receivables_investment_fy_v1` | 매출·기타 유동채권 증가/전기자산 | 낮음 | 통제·구성요소 | [Richardson, Sloan, Soliman, Tuna (2005)](https://doi.org/10.1016/j.jacceco.2005.04.005) |
| `kr_asset_turnover_change_fy_v1` | 총자산 회전율 변화 | 높음 | 수익문헌 대용 | [Soliman (2008)](https://doi.org/10.2308/accr.2008.83.3.823) |

### 가치와 수익성

총자본/종목시총, 순이익/종목시총, 매출/종목시총, CFO/종목시총은 서로 다른 현금·회계 규모에 대한 가격을 측정한다. 순이익과 현금흐름의 차이 자체가 경쟁 설명을 구분하는 데 도움이 된다. 매출/가격은 Barbee 등의 직접 근거를 사용하지만, 해당 연구의 미국 표본 결과를 한국으로 이전해 성과 수치를 주장하지 않는다. [Barbee·Mukherji·Raines (1996)](https://rpc.cfainstitute.org/research/financial-analysts-journal/1996/do-salesprice-and-debtequity-explain-stock-returns-better-than-bookmarket-and-firm-size)

다만 **연결 총자본 ÷ 한 보통주 종목 시총은 canonical common book-to-market이 아니다.** 비지배지분·우선주·복수 종류주가 있으면 법인 회계범위와 가격 분모 범위가 다르다. 따라서 명칭에 총자본·종목시총 대용을 표시하며, 정확한 보통주 귀속 자본과 법인 전체 보통주 시총 매핑을 확보하기 전까지 HML 구성변수와 동일하다고 부르지 않는다. [French 변수 정의](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/variable_definitions.html)

매출총이익/자산은 매출총이익률과 다르다. 전자는 자산을 얼마나 생산적으로 쓰는지를, 후자는 매출에서 남기는 몫을 본다. Novy-Marx 원형과의 분모·정보가용성·시장 차이를 기록한다. 연간 순이익/기말자산도 분기 이익/전기자산 원형과 다른 정의다. [Novy-Marx (2013)](https://www.nber.org/papers/w15940)

### 투자·발생액·재무건전성

자산 성장, 매출 성장, 재고 증가는 기업 확대와 미래 기대의 관계를 서로 다른 각도에서 측정한다. 총자본 성장은 배당·증자·자사주·손익이 섞이므로 순주식발행 효과의 정확한 대용이 아니다. 부호 -1은 보수적 성장 진단을 위한 고정 방향이며 검증된 독립 주식발행 알파로 표시하지 않는다. [Cooper·Gulen·Schill (2008)](https://doi.org/10.1111/j.1540-6261.2008.01370.x)

매출·기타 유동채권은 원천 필드가 `trade_and_other_current_receivables`이므로 **순수 매출채권이 아니다**. 광의의 채권 증가/전기자산 통제지표로 분류하며 매출채권 품질 논문의 정확한 복제라 하지 않는다. CFO 기반 발생액의 분모는 현재 구현에서 기말자산이다. 재고 증가의 분모는 전기자산이므로 평균자산 원형과 차이가 있다.

운전자본/자산과 이익잉여금/자산은 Altman의 재무건전성 구성요소다. 파산분류에 유용하다는 것과 주식 초과수익이 크다는 것은 별개다. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x)

유형자산/자산은 담보성·재무제약과 투자의 설명에 쓰는 통제다. 금융회사처럼 계정 의미가 다른 업종에서는 동일한 방향을 일반화하지 않는다. [Almeida·Campello](https://www.nber.org/system/files/working_papers/w12087/w12087.pdf)

## 4. “30개 이상”을 중복 독립 팩터라고 해석하지 않는다

| 관계 | 연구에서의 처리 |
| --- | --- |
| 발생액/자산 = 순이익/자산 − CFO/자산 | 동일 회계 범위·기간·분모라면 정확한 선형 관계다. 셋을 독립 증거로 세지 않는다. |
| 수익/자산 = 수익/매출 × 매출/자산 | 마진과 자산 회전의 경제적 경로를 구분하는 데 활용한다. |
| 일별 장외 gross × 장중 gross = 조정종가 gross | 같은 세션을 쓴 월별 곱도 전체 가격 변화와 연결된다. 분해 연구이지 무조건적인 두 독립 알파가 아니다. |
| Parkinson 분산과 종가 기반 변동성 | 동일 전체 위험의 다른 추정량이다. |
| 회전율·거래대금·Amihud·무거래 | 서로 다른 유동성 면을 보지만 규모·거래활동과 공통 성분이 많다. |
| 여러 가치비율 | 공통 시총 분모가 있으므로 다중 검정과 공선성을 통제한다. |

목표는 서로 다른 질문을 측정할 도구를 확보하는 것이다. “효과가 규모 때문인지, 수익성인지, 투자 확대인지, 유동성인지”를 구분할 수 있어야 한다. 이후 차원 축소·상관 기반 선택·릿지 적합은 **학습 기간 안에서만** 하고, 미래 성과를 보고 편한 정의를 고르는 경로와 분리한다.

## 5. 실제 적재에 필요한 확인

문헌 적합성 → 원천·시점 적합성 → 독립 계산 대조 → 실제 Gold 발행·재조회 순으로 확인한다. 어느 하나만으로 나머지를 대체하지 않는다.

1. 인증된 원천 가격·정확한 회계 계정과 asset identity를 사용한다. 종목 코드의 선행 0과 영문 혼합 코드를 보존한다.
2. 재무는 FY 기간, KRW 등 통화, CFS/OFS, 원천 filing·known-at·수집 시점·정정 버전을 기록한다. 전년 비교는 동일 전년 결산기 및 회계 범위를 요구한다.
3. 분모는 정의에 맞게 양수인지, 값은 finite인지 확인한다. 결측을 0으로 대체하지 않고, 데이터 없음과 경제적으로 0인 값을 구분한다.
4. 최초 발표값이 증명되지 않는 최신 정정 자료는 이를 명시한다. 인증 또는 lag를 적용했다는 사실만으로 최초 발표값 PIT를 증명하지 않는다.
5. 가격의 조정 방식과 일별 관측 수를 검증한다. 회계 입력의 한 종목 표본 존재만으로 전시장 커버리지를 추정하지 않는다.
6. 정의별 비결측 행 수·종목 수·최초/최신 날짜·누락 사유를 산출한다. 정의가 있어도 유효값 0개이면 실제 완료 개수에 포함하지 않는다.
7. SQL/독립 구현 계산 일치, 유효성 검사, definition/source/code hash와 실제 Gold 저장 데이터 대조를 통과한 발행 영수증을 남긴다.

이 목록은 종목을 매매 가능하다고 승인하거나, 기존 레거시 Gold의 알파 승인을 승계하지 않는다. 시장 공통 요인 수익률, 거래가능 universe, 다음 거래일 체결·총수익·비용 계약은 전략 단계에서 별도로 결합해야 한다.

## 6. 이번 숫자에 넣지 않은 후속 후보

| 후보 | 별도 확보·검증이 필요한 이유 |
| --- | --- |
| 정확한 보통주 B/M, French OP, HML/RMW/CMA 수익률 | 지분 귀속·비지배지분·우선주·이자비용·SG&A·정렬 및 포트폴리오 계약이 필요하다. |
| 완전한 Piotroski F-score | 9개 구성요소 모두의 동일 회계범위·시점과 신주발행 항목이 필요하다. |
| 순영업자산(NOA), 투자율·설비투자 성장 | 운영/재무 자산·부채 분리와 일관된 capex 계정이 필요하다. |
| 순지급수익률·순주식발행 | 배당·자사주·증자·분할 조정 및 법인 범위가 필요하다. |
| 시장 beta·특이변동성 | 인증된 시장 수익률과 정렬된 거래일/총수익 계약이 필요하다. |
| 기업가치/EBITDA | 총부채를 이자부채로 대신하지 않는 EV 구성과 EBITDA 계정 계약이 필요하다. |

계정을 추측해 채우거나 기간만 바꾸어 수를 늘리지 않는다. 이미 가진 Bronze 원본이 있는지, adapter가 아직 없는지, 검증 가능한 빈티지가 없는지는 각각 별도 상태로 남긴다.

## 7. 재현 가능한 문헌 연결

Open Source Asset Pricing 문서는 커밋 `8db892442c2c3a3779b0f1eac4370d3655be15a1`에 고정했다. [SignalDoc.csv](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/8db892442c2c3a3779b0f1eac4370d3655be15a1/SignalDoc.csv)의 SHA-256은 `f6c055120bad7afe97c16e23e0f49bce0982269026605a955e8064bd661cf415`이다. 이 메타데이터와 공개 계산 정의만 참고했고, 봉인된 한국 OOS·기존 후보 결과·옛 알파 성과를 읽지 않았다.

최종 기계 판독 파일은 실제 코드의 추가 가격 13개 및 재무 25개 ID와 방향이 일치하도록 검증한다. 문헌 변경은 계산 결과를 본 뒤 공식·기간을 바꾸기 위한 허가가 아니다. 현재 발행 영수증과 활성 program 포인터가 무엇을 실제 사용할 수 있는지 결정한다.
