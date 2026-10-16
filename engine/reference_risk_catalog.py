"""Frozen source attribution for market, friction, and AQR reference controls."""
from engine.reference_profit_growth import JKP_URL
from engine.reference_library import validate_catalog

SOURCE_TYPE='RDS_CERTIFIED_REFERENCE_RISK_DIVERSITY_V1'
SOURCE_CONTRACT='FROZEN_KRX_DART_FULL_VECTOR_SCALAR_RISK_V1'
PARITY_KIND='INDEPENDENT_VECTOR_SCALAR_FULL_RAW_INPUTS'
PIT_STATUS='PIT_ASSUMED'

# key, name, category, expression, author/title, primary link, quota, orientation
SPECS=[
('downside_beta','하락시장 민감도','asymmetric_market_risk','OLS beta on daily market returns below trailing-year market mean;252 sessions,min200 paired/min60 down',
 'Ang, Chen and Xing (2006), Downside Risk',JKP_URL,'academic',-1),
('idiosyncratic_volatility','시장모형 잔차 변동성','idiosyncratic_risk','sample std residual of OLS(stock price return~1+market price return);252 sessions,min200',
 'Ali, Hwang and Trombley (2003), Arbitrage risk and the book-to-market anomaly; JKP ivol_capm_252d',JKP_URL,'academic',-1),
('coskewness','시장 공동왜도','higher_order_market_risk','mean(OLS_residual*(m-mean(m))^2)/(sqrt(mean(residual^2))*mean((m-mean(m))^2));closed month,min15',
 'Harvey and Siddique (2000), Conditional Skewness in Asset Pricing Tests','https://doi.org/10.1111/0022-1082.00247','academic',-1),
('cokurtosis','시장 공동첨도 진단','higher_order_market_risk','mean(OLS_residual*(m-mean(m))^3)/(sqrt(mean(residual^2))*mean((m-mean(m))^2)^1.5);252 sessions,min200',
 'Dittmar (2002), Nonlinear Pricing Kernels, Kurtosis Preference, and Evidence from the Cross Section of Equity Returns','https://doi.org/10.1111/1540-6261.00425','academic',1),
('return_autocorrelation','일별 수익률 자기상관','market_friction','corr(price_return_d,price_return_d-1) within closed month,min15 valid pairs',
 'Campbell, Grossman and Wang (1993), Trading Volume and Serial Correlation in Stock Returns','https://www.nber.org/papers/w4193','academic',1),
('liquidity_reversal','거래대금 조건부 반전 계수','liquidity_resiliency','OLS coefficient gamma: (r_i,d+1-r_m,d+1)~1+r_i,d+sign(r_i,d-r_m,d)*KRW_traded_value_d/1e9;both dates inside closed month,min15',
 'Pastor and Stambaugh (2003), Liquidity Risk and Expected Stock Returns','https://doi.org/10.1086/374184','academic',-1),
('edge_spread','EDGE 유효 스프레드 추정','transaction_cost','Ardia-Guidotti-Kroencke EDGE on daily OHLC within month;max(signed_squared_estimate,0)^0.5;min15 valid sessions',
 'Ardia, Guidotti and Kroencke (2024), Efficient Estimation of Bid-Ask Spreads from Open, High, Low, and Close Prices','https://doi.org/10.1016/j.jfineco.2024.103916','academic',1),
('price_delay','시장정보 반영 지연','information_diffusion','1-R2(weekly r~1+m)/R2(weekly r~1+m+lag1..4(m));52 completed weeks,min40 common observations',
 'Hou and Moskowitz (2005), Market Frictions, Price Delay, and the Cross-Section of Expected Returns','https://doi.org/10.1093/rfs/hhi023','academic',1),
('volume_trend','장기 거래량 추세','trading_participation','OLS slope(monthly split-adjustment-proxy volume~1+calendar month)/mean(volume);past60calendar months,min30',
 'Haugen and Baker (1996), Commonality in the determinants of expected stock returns; Chen-Zimmermann VolumeTrend replication','https://doi.org/10.1016/0304-405X(95)00868-F','academic',1),
('calendar_seasonality','종목별 달력 계절성','calendar_seasonality','mean(monthly price returns at calendar lags23,35,47,59 from formation month);all4 required',
 'Heston and Sadka (2008), Seasonality in the cross-section of stock returns; JKP seas_2_5an',JKP_URL,'academic',1),
('bab_beta','AQR 방식 축소 베타','market_beta','0.6*corr(sum3daily log returns_i,m over1260)*std252(log r_i)/std252(log r_m)+0.4;min750 correlation/min120 vol',
 'Frazzini and Pedersen (2014), Betting Against Beta; attached 20 for Twenty chapter14','https://doi.org/10.1016/j.jfineco.2013.10.005','aqr',-1),
('net_share_issuance','분할조정 대용 주식수 순발행','equity_supply','-ln((shares/price_adjustment_factor)t/(shares/price_adjustment_factor)t-12 calendar months)',
 'Asness, Frazzini and Pedersen (2019), Quality minus junk, alternative payout EISS','https://d-nb.info/1174954515/34','aqr',1),
('gross_profit_growth_per_share_5fy','5년 주당 매출총이익 성장','profit_growth','(GP_t/adjusted_shares_FYt-GP_FYt-5/adjusted_shares_FYt-5)/(sales_FYt-5/adjusted_shares_FYt-5)',
 'Asness, Frazzini and Pedersen (2019), Quality minus junk, GMAR growth','https://d-nb.info/1174954515/34','aqr',1),
('quality_profitability_composite','AQR 수익성 품질 종합측정','quality_composite','zscore(rank(round(sum of zscores of ranks of GP/A,NI/E,NI/A,CFO/A,GP/Sales,-(NI-CFO)/A),12)));all6 required',
 'Asness, Frazzini and Pedersen (2019), Quality minus junk; JKP qmj_prof','https://d-nb.info/1174954515/34','aqr',1),
]

def definitions():
    ds=[]
    for key,name,family,formula,title,url,bucket,orientation in SPECS:
        ds.append(dict(id=f'kr_{key}_reference_v1',name_ko=name,family=family,formula=formula,
            object_type='STOCK_CHARACTERISTIC',role='MEASUREMENT_CONTROL',alpha_approved=False,orientation=orientation,
            required_columns=['EXACT_FROZEN_KRX_DAILY_AND_WHERE_REQUIRED_DART_FY_FEATURES'],
            lookback={'basis':'PAST_ONLY_DECLARED_DAILY_WEEKLY_CALENDAR_OR_EXACT_FY_WINDOWS'},
            sources=[{'title':title,'url':url,'review_scope':'정의 및 공식 복제 문서; 원형/한국 측정 차이 별도 명시'}],
            quota_bucket=bucket,evidence_tier='LITERATURE_RELATED_MEASUREMENT_NOT_KOREAN_ALPHA',
            adaptation='시장수익은 전일 시총 가중 KRX 보통주 가격수익률 대용이며 공식 지수 TR/무위험 초과수익 아님. 배당 제외·공통주 범위·시장 구성 차이가 있음. 한국 예측성과 미검증. 고차 공동모멘트와 자기상관은 경쟁설명 진단이며 원 논문 SDF/완성 전략 복제가 아님. PS는 개별 유동성 수준 gamma이며 aggregate liquidity-risk beta 아님. 주식수·거래량 조정에는 KRX adj_close/close 대용을 사용하므로 순수 분할 외 권리 조정이 섞일 수 있음. FY 주당 값은 보통주 issue 주식수와 연결 총액을 연결하는 적응이며 모든 종류주 합산 주당액 아님. 수익성 composite는 문헌 고정 가중으로 기존 측정치를 요약하며 독립 알파 추가를 뜻하지 않음. PIT_ASSUMED, 첫 빈티지 미증명.',
            readiness={'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}))
    for definition in ds:
        if definition['id']=='kr_edge_spread_reference_v1':
            definition['formula']+='; exclude closed months crossing any adjacent price-adjustment-factor change>1e-6'
            definition['adaptation']+=' EDGE는 원시 OHLC의 연속성이 필요하므로 월내 인접 가격조정계수가 1e-6 초과 변화한 달은 기업행위 혼입 방지를 위해 제외.'
    validate_catalog(ds)
    return ds
