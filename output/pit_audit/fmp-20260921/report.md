# FMP 잔여 36계열 검증 결과

검사 실행: 2026-09-20~21 KST. 대상 snapshot: 2015-01-01~2026-09-18.

**36계열 47,378행의 원본 무결성·기초 품질 검사를 실행했다. 역사적 PIT 검증 전체가 끝났다는 뜻은 아니다.**
신규 역사적 사용 승인 0개, 기존 한국 정책금리 월말 정제 입력 승인 1개 유지.
검증되지 않은 부분을 통과로 처리하거나 기존 보류 flag만 재출력하지 않았다.

| 범위 | 계열 | 보유 행 | 이번 실검사 결과 |
|---|---:|---:|---|
| COT | 10 | 6,110 | CFTC 현행 원본의 10개 필드 61,100개 값 전부 일치. 날짜 누락/추가 0 |
| 한국 CPI | 2 | 280 | 공식 발표 페이지 140건 전수 대조. 값 279 일치, 1 차이 |
| 나머지 매크로 | 11 | 1,547 | 정확한 S3 원본 검사. actual null 1행, 중복 1행. 공식 최초 발표값 전수 대조는 미완료 |
| FX | 6 | 18,825 | 핵심 OHLCV 결측·음수·범위 오류 0. 일요일 511행, 토요일 0행 |
| ETF | 4 | 11,780 | OHLCV 기초 검사 통과. 운용사 최신 종가 4/4 일치. 과거 종가 전수 대조 아님 |
| Cboe 지수 | 3 | 8,836 | 공식 현재 종가 8,761 일치, 74 차이, 공식 파일에 없는 날짜 1 |

## 원본과 검사 범위

정책금리를 포함한 37계열 47,483행, 417 partition을 재검사했다. 나머지 36계열은 47,378행이다.
매크로는 앞선 audit-replay가 아니라 전날 S3에서 받은 정확한 backfill 미러 141 partition·1,932행이다.
이번 실행에서 S3를 다시 내려받지는 않았으며 보존한 다운로드 영수증·manifest·원본·선별본의 SHA256,
바이트 수, 행 연결, 실제 수집시각을 재검증했다. 외부 23계열은 실제 업로드에 쓰인 로컬 backfill 원본이다.
FMP 추가 API 호출 0회. 공식 자료 HTTP 수집은 최대 동시 3개, 성공 원문과 수신시각·URL·hash를 보존했다.

기초 품질 PASS는 단위·세션·vintage까지 승인했다는 뜻이 아니다.
36계열 중 35개는 이 기초 검사에서 문제가 없고 산업생산 YoY 1개는 null/중복이 있다.

## COT: 수치는 통과, 발표·정정 이력은 별도

[CFTC Legacy Futures Only 공식 API](https://publicreporting.cftc.gov/resource/6dca-aqww.json)에서
계약 코드와 포지션 기준일로 결합했다. 계약 코드의 leading zero를 보존하고 Futures-and-Options와 섞지 않았다.
각 계약 611행을 공식 count 쿼리와 대조해 응답 잘림을 검사했다.
open interest, noncommercial long/short/spread, commercial long/short,
total reportable long/short, nonreportable long/short를 모두 비교했다.
양쪽 포지션 합계와 open interest의 회계적 항등식도 전수 통과했다.

현재 CFTC 파일과 100% 일치하는 것은 긍정적인 결과다. 다만 기준일은 발표일이 아니다.
전날 확인한 공식 지연 일정 13개 기준일 × 10계열 = 130행은 +3일 규칙의 반례이며,
그중 90행은 월말을 넘긴다. 실제 발표·정정 달력과 최초 발표본 검증은 남아 있다.
[CFTC 특별공지](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm).

## 한국 CPI: 2015-01~2026-08 공식 발표 140건

MoM 139/140, YoY 140/140이 현재 보존된 공식 발표 페이지의 headline과 일치한다.
문장에 '변동이 없음'이라고 적힌 경우에만 0으로 읽고, 결측을 0으로 바꾸지 않았다.
headline CPI와 근원·생활물가를 분리했다. 값이 다른 1건을 임의 수정하지 않았다.

1. **2017-09 대상월**: 공식 PDF의 보도일시는 2017-09-28 08:00 KST.
   FMP는 2017-10-02 08:00 KST에 해당하는 UTC timestamp다. 4일 늦고 판단월이 달라진다.
   MoM·YoY 두 행 모두 해당한다. [공식 발표](https://mods.go.kr/board.es?mid=a10301040100&bid=213&act=view&list_no=363448).
2. **2024-04 MoM**: FMP 0.0%, 현재 공식 PDF 요약·본문 0.1%다.
   웹페이지 headline도 0.1%지만 하위 설명에는 '전체 변동 없음'이 남아 있다.
   FMP 오류인지 공식 정정 전 값인지 확정할 근거가 부족하므로 불일치로 기록했다.
   [공식 발표](https://mods.go.kr/board.es?mid=a10301040100&bid=213&act=view&list_no=430714).
3. **2026-01 대상월**: 웹 게시일 2026-03-06을 최초 발표일로 쓰면 안 된다.
   PDF 표지는 2026-02-03 08:00이며 FMP 날짜와 일치한다. 사이트에는 일부 자료를
   2026-03-06 08:00에 변경 게시했다는 공지가 있다. headline 값은 현재 FMP와 같지만
   처음 발표한 버전과 동일하다는 전수 보장은 아니다.
   [공식 수정 공지](https://mods.go.kr/board.es?mid=a10301040100&bid=213&act=view&list_no=443358).

PDF로 게시일/보도일 차이를 해소한 후 날짜 일치는 278/280, 나머지 2행은 2017-09분이다.
3개 PDF의 해당 표지/요약을 렌더링해 확인했다. 모든 140 PDF를 검사한 것은 아니다.
FMP 문서의 UTC를 한국시간으로 바꾸면 CPI 두 계열 각각 18행의 달이 바뀐다.
원시 UTC 날짜의 월을 그대로 신호월로 쓰는 결합은 안전하지 않다.

## FX·ETF: 확인한 부분과 확인하지 못한 부분

[FMP 공식 FAQ](https://site.financialmodelingprep.com/it/faqs?code=marketPerformance)는 경제 캘린더를 UTC,
FX를 EST로 설명하고 일요일 개장도 명시한다. 따라서 FX 511개 일요일 행을 단순 오류로 분류하지 않는다.
다만 EST 고정 오프셋과 실제 뉴욕 DST/일봉 경계의 정확한 계약, 동일 fixing의 독립 값은 아직 검증하지 못했다.

ETF는 [EWY](https://www.ishares.com/us/products/239681/ishares-msci-south-korea-capped-etf),
[EEM](https://www.ishares.com/us/products/239637/EEM),
[FXI](https://www.ishares.com/us/products/239536/),
[EWT](https://www.ishares.com/us/products/239686/EWT)의 운용사 최신 Closing Price를 확인했다.
2026-09-18 값은 각각 181.31, 67.03, 34.32, 111.64 USD로 모두 FMP와 일치한다.
운용사 장기 XLS의 Historical 시트는 NAV per Share다. NAV와 거래소 종가를 비교해 오류율을 만들지 않았다.
보유 11,780개 ETF 날짜는 모두 운용사 NAV 날짜에도 있다. 반대 방향의 추가 NAV 날짜
2024-03-29와 2024-03-31은 각각 [거래소 휴장일](https://ir.theice.com/press/news-details/2023/NYSE-Group-Announces-2024-2025-and-2026-Holiday-and-Early-Closings-Calendar/default.aspx),
일요일이므로 FMP 종가 누락으로 판정하지 않는다.

FMP close는 split 조정 가격이며 배당 포함 총수익 가격과 다르다.
[EWT 2016년 역분할 공시](https://www.sec.gov/Archives/edgar/data/1100663/000119312516737785/d231942d497.htm)도 확인했다.
향후 분할의 동일 배율은 수익률/가격비율에서 상쇄될 수 있으므로 조정주가라는 이유만으로 모든 파생값을
불합격 처리하지 않는다. 하지만 그 불변성이 임의 가격정정·배당 처리까지 해결하는 것은 아니며,
이번에는 과거 종가 정정 이력과 파생 입력 계약을 승인하지 않았다.
각 ETF의 미국 날짜 98개는 다음 한국 날짜로 옮기면 월이 바뀐다. 같은 날짜 월말 결합을 승인하지 않았다.

## 나머지 매크로와 Cboe

산업생산 YoY의 2026-03-30 23:00 두 행은 actual=-2.2/null, previous=6.8/7.1로 서로 다르다.
둘을 무조건 합치거나 null만 삭제하지 않았다. 심리지수의 FMP unit='%'도 지수 수준과 구별해야 한다.
중국 PMI와 다른 한국 통계 11계열의 최초 발표자료 전수 대조는 아직 하지 못했다.

Cboe 기존 공식 CSV의 hash를 확인한 뒤 전수 비교를 다시 실행했다.
VVIX 13차이+추가 1날짜(2021-11-25), VIX9D 57차이, VIX3M 4차이다.
현재 공식값과 같은 행도 최초 공개 vintage 증명과는 다르며, 원본을 최신 공식값으로 덮어쓰지 않았다.

## 계열별 검사 상태

PASS/기초 품질/현재값 일치/최신일 표본을 구분한다. 이 표는 PIT 승인서가 아니다.

| 계열 | 보유 행 | 기초 품질 | 독립 수치 대조 |
|---|---:|---|---|
| AUDUSD | 3,133 | PASS | NOT_PERFORMED |
| CL | 611 | PASS | PASS |
| CN_NBS_MANUFACTURING_PMI | 141 | PASS | NOT_PERFORMED |
| DX | 611 | PASS | PASS |
| EEM | 2,945 | PASS | LATEST_CLOSE_SAMPLE_PASS |
| EURUSD | 3,119 | PASS | NOT_PERFORMED |
| EWT | 2,945 | PASS | LATEST_CLOSE_SAMPLE_PASS |
| EWY | 2,945 | PASS | LATEST_CLOSE_SAMPLE_PASS |
| FXI | 2,945 | PASS | LATEST_CLOSE_SAMPLE_PASS |
| GC | 611 | PASS | PASS |
| HG | 611 | PASS | PASS |
| J6 | 611 | PASS | PASS |
| KR_BUSINESS_CONFIDENCE | 140 | PASS | NOT_PERFORMED |
| KR_CONSUMER_CONFIDENCE | 140 | PASS | NOT_PERFORMED |
| KR_CPI_MOM | 140 | PASS | DISCREPANCY |
| KR_CPI_YOY | 140 | PASS | PASS_DATED_PAGE_VALUES |
| KR_CURRENT_ACCOUNT | 140 | PASS | NOT_PERFORMED |
| KR_INDUSTRIAL_PRODUCTION_MOM | 140 | PASS | NOT_PERFORMED |
| KR_INDUSTRIAL_PRODUCTION_YOY | 141 | ISSUES_FOUND | NOT_PERFORMED |
| KR_PPI_MOM | 141 | PASS | NOT_PERFORMED |
| KR_PPI_YOY | 141 | PASS | NOT_PERFORMED |
| KR_RETAIL_SALES_MOM | 141 | PASS | NOT_PERFORMED |
| KR_TRADE_BALANCE | 141 | PASS | NOT_PERFORMED |
| KR_UNEMPLOYMENT_RATE | 141 | PASS | NOT_PERFORMED |
| USDCNH | 3,162 | PASS | NOT_PERFORMED |
| USDCNY | 3,134 | PASS | NOT_PERFORMED |
| USDJPY | 3,142 | PASS | NOT_PERFORMED |
| USDTWD | 3,135 | PASS | NOT_PERFORMED |
| VX | 611 | PASS | PASS |
| ZB | 611 | PASS | PASS |
| ZN | 611 | PASS | PASS |
| ZQ | 611 | PASS | PASS |
| ZT | 611 | PASS | PASS |
| ^VIX3M | 2,945 | PASS | DISCREPANCY |
| ^VIX9D | 2,945 | PASS | DISCREPANCY |
| ^VVIX | 2,946 | PASS | DISCREPANCY |

## 재현 및 남은 일

`verification.json`이 최종 종합본이며 `audit.json`은 CPI/ETF 후속 대조 전 중간 검사본이다.
`cpi-comparison-v2.json`은 웹 게시일 기준 비교이고, 종합본은 PDF로 해소한 날짜를 별도 보존한다.
초기 CPI 파서 결과는 덮어쓰지 않았으며 최종 검사는 '변동이 없음'을 처리한 v2다.

```sh
# 신규 빈 출력 디렉터리 지정. 실패한 연간 ZIP 대신 공식 Socrata API를 사용한다.
python -m scripts.verify_fmp_remaining --fetch-cot-api --output NEW_OUTPUT
python -m scripts.verify_fmp_remaining --audit --output NEW_OUTPUT
python -m scripts.verify_fmp_cpi_releases --collect --reparse --compare --output NEW_OUTPUT
# ETF 페이지/다운로드 및 CPI 예외 PDF 원문은 URL/영수증과 함께 보존되어 있다.
python -m scripts.verify_fmp_etf_sources --output EXISTING_EVIDENCE_OUTPUT
python -m scripts.finalize_fmp_validation --output EXISTING_EVIDENCE_OUTPUT
```

수치 검증을 통과한 COT는 발표/정정 달력 검증으로, CPI는 위 예외와 최초 발표 버전 복원으로 이어질 수 있다.
FX·ETF는 미완료인 독립 역사 값/시점 검사를 진행해야 한다. 새 승인을 허위 발급하거나 기준을 완화하지 않았다.
기존 원본, 승인 registry, 캠페인, 후보, OOS, Silver/Gold DB는 변경하지 않았다.
`factor-research-loop`의 연구 경계, `spreadsheets`의 원본/결측 보존 및 독립 대조,
`pdf`의 렌더링 검증 절차를 적용했다. 검증 단위 테스트와 기존 입력 보호 테스트 69개 통과.
