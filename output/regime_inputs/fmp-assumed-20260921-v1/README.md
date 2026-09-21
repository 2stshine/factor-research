# 가정 기반 FMP 월말 레짐 입력

**PIT_ASSUMED — 역사적 PIT 검증 완료가 아닌 사용자가 수용한 가정 기반 진단 자료.**

원본 actual/close/COT 포지션을 사용하되, 과거 최초값·정정 이력은 복원되지 않았다는 한계를 유지한다.
실제 수집시각은 보존하며 별도 assumed 가용시각을 계산한다. 기존 source/approval/DB/campaign은 수정하지 않는다.

- 경제 캘린더: provider UTC→KST, 기준월이 아니라 가용 시점의 최신 actual 사용.
- ETF/FX: provider 날짜 다음 뉴욕 자정 가용 가정, 연속 4개월 월말값의 3개월 변화 부호.
- 매크로/COT/변동성지수: 현재 월을 제외한 과거 유효월말 최소 24개 중앙값 대비 HIGH/LOW.
- COT: 비상업 순포지션/OI; 일반 화요일+3일 15:30 NY 가정, 보존된 지연 예외는 별도 적용.
- 알려진 미복원 COT 지연/비정규 기준일은 제외한다. 주별 자료는 발표 후 경과뿐 아니라 포지션 기준일 이후 14일도 적용한다.
- stale 제한: 월간 60일, COT 14일, 가격/지수 7일. 결측·상충·워밍업은 UNKNOWN으로 보존한다.
- 월 t 판독은 t+1 진단용이다. HIGH/UP이 경기 호조·미래 상승을 뜻하지 않는다.
- 동일 시각 값 충돌은 UNKNOWN; 숫자 1개와 null 중복이면 숫자를 사용하되 양쪽 원본 연결을 보존한다.

| Series | Kind | Records | Months | States | First classified |
|---|---|---:|---:|---|---|
| AUDUSD | fx | 3133 | 140 | {'UNKNOWN': 3, 'UP': 67, 'DOWN': 70} | 2015-04 |
| CL | cot | 611 | 140 | {'UNKNOWN': 31, 'HIGH': 45, 'LOW': 64} | 2017-01 |
| CN_NBS_MANUFACTURING_PMI | macro | 141 | 140 | {'UNKNOWN': 24, 'HIGH': 47, 'LOW': 69} | 2017-01 |
| DX | cot | 611 | 140 | {'UNKNOWN': 31, 'HIGH': 39, 'LOW': 70} | 2017-01 |
| EEM | etf | 2945 | 140 | {'UNKNOWN': 3, 'UP': 82, 'DOWN': 55} | 2015-04 |
| EURUSD | fx | 3119 | 140 | {'UNKNOWN': 3, 'DOWN': 73, 'UP': 64} | 2015-04 |
| EWT | etf | 2945 | 140 | {'UNKNOWN': 3, 'UP': 85, 'DOWN': 52} | 2015-04 |
| EWY | etf | 2945 | 140 | {'UNKNOWN': 3, 'UP': 79, 'DOWN': 58} | 2015-04 |
| FXI | etf | 2945 | 140 | {'UNKNOWN': 3, 'UP': 69, 'DOWN': 68} | 2015-04 |
| GC | cot | 611 | 140 | {'UNKNOWN': 31, 'LOW': 36, 'HIGH': 73} | 2017-01 |
| HG | cot | 611 | 140 | {'UNKNOWN': 31, 'HIGH': 73, 'LOW': 36} | 2017-01 |
| J6 | cot | 611 | 140 | {'UNKNOWN': 31, 'LOW': 63, 'HIGH': 46} | 2017-01 |
| KR_BUSINESS_CONFIDENCE | macro | 140 | 140 | {'UNKNOWN': 24, 'HIGH': 54, 'LOW': 62} | 2017-01 |
| KR_CONSUMER_CONFIDENCE | macro | 140 | 140 | {'UNKNOWN': 24, 'LOW': 59, 'HIGH': 57} | 2017-01 |
| KR_CPI_MOM | macro | 140 | 140 | {'UNKNOWN': 25, 'HIGH': 65, 'LOW': 50} | 2017-02 |
| KR_CPI_YOY | macro | 140 | 140 | {'UNKNOWN': 25, 'HIGH': 87, 'LOW': 28} | 2017-02 |
| KR_CURRENT_ACCOUNT | macro | 140 | 140 | {'UNKNOWN': 25, 'LOW': 69, 'HIGH': 46} | 2017-02 |
| KR_INDUSTRIAL_PRODUCTION_MOM | macro | 140 | 140 | {'UNKNOWN': 24, 'HIGH': 58, 'LOW': 58} | 2017-01 |
| KR_INDUSTRIAL_PRODUCTION_YOY | macro | 141 | 140 | {'UNKNOWN': 24, 'HIGH': 66, 'LOW': 50} | 2017-01 |
| KR_PPI_MOM | macro | 141 | 140 | {'UNKNOWN': 24, 'HIGH': 67, 'LOW': 49} | 2017-01 |
| KR_PPI_YOY | macro | 141 | 140 | {'UNKNOWN': 24, 'HIGH': 82, 'LOW': 34} | 2017-01 |
| KR_RETAIL_SALES_MOM | macro | 141 | 140 | {'UNKNOWN': 24, 'LOW': 67, 'HIGH': 49} | 2017-01 |
| KR_TRADE_BALANCE | macro | 141 | 140 | {'UNKNOWN': 24, 'LOW': 85, 'HIGH': 31} | 2017-01 |
| KR_UNEMPLOYMENT_RATE | macro | 141 | 140 | {'UNKNOWN': 24, 'LOW': 80, 'HIGH': 36} | 2017-01 |
| USDCNH | fx | 3162 | 140 | {'UNKNOWN': 3, 'DOWN': 74, 'UP': 63} | 2015-04 |
| USDCNY | fx | 3134 | 140 | {'UNKNOWN': 3, 'DOWN': 68, 'UP': 69} | 2015-04 |
| USDJPY | fx | 3142 | 140 | {'UNKNOWN': 3, 'UP': 85, 'DOWN': 52} | 2015-04 |
| USDTWD | fx | 3135 | 140 | {'UNKNOWN': 3, 'DOWN': 68, 'UP': 69} | 2015-04 |
| VX | cot | 611 | 140 | {'UNKNOWN': 31, 'LOW': 56, 'HIGH': 53} | 2017-01 |
| ZB | cot | 611 | 140 | {'UNKNOWN': 31, 'LOW': 74, 'HIGH': 35} | 2017-01 |
| ZN | cot | 611 | 140 | {'UNKNOWN': 31, 'LOW': 83, 'HIGH': 26} | 2017-01 |
| ZQ | cot | 611 | 140 | {'UNKNOWN': 31, 'HIGH': 62, 'LOW': 47} | 2017-01 |
| ZT | cot | 611 | 140 | {'UNKNOWN': 31, 'LOW': 88, 'HIGH': 21} | 2017-01 |
| ^VIX3M | index | 2945 | 140 | {'UNKNOWN': 24, 'LOW': 45, 'HIGH': 71} | 2017-01 |
| ^VIX9D | index | 2945 | 140 | {'UNKNOWN': 24, 'LOW': 51, 'HIGH': 65} | 2017-01 |
| ^VVIX | index | 2946 | 140 | {'UNKNOWN': 24, 'HIGH': 71, 'LOW': 45} | 2017-01 |

컨텍스트 36개. raw 정책금리 105행은 기존 검증 정제축으로 대체하여 중복 생성하지 않는다.
기존 FMP 9계열의 로컬 자료는 2026년 9월 표본뿐이라 이번 완료월 범위에서 제외한다. 추가 수집하지 않았다.
수용서 schema는 pit-regime-assumption-v1이며 검증 PIT 승인과 구별한다. 분류 룰은 팩터 성과 없이 고정했다.
