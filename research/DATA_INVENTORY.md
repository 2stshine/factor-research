# 데이터 보유 현황

확인 기준: 기존 KRX/DART/한투/FMP 일일 항목은 2026-09-18,
추가 FMP Bronze 세 묶음은 **2026-09-20 S3 적재·재조회 검증 증빙** 기준이다.
이번 갱신은 FMP 추가 보유분 반영이며 기존 항목 전체를 재조회한 것은 아니다.
아래는 운영 증거와 현재 연구 입력 목록에서 확인한 범위다.
전체 DB의 실시간 카탈로그는 아니며, 목록에 없다는 이유만으로 미보유라고 판단하지 않는다.
최신 적재일은 실행마다 달라진다. 표의 날짜는 마지막 확인값이며 실시간 보장을 뜻하지 않는다.

후속 PIT 상태: 한국 기준금리의 공식 결정 대조 **월말 진단 입력 1개(2015-01~2026-08)**를 승인하고
새 캠페인 기본 입력에 등록했다. 로컬 Silver 정제본이며, Bronze 37계열 전체 승인이나 RDS 적재는 아니다.
상세 근거는 문서 끝의 한국 정책금리 정제 승인 항목을 참조한다.
2026-09-21 후속 검증에서는 나머지 36계열 47,378행을 검사하고 COT 전수 수치 대조,
CPI 공식 발표자료 대조, ETF 최신 종가 표본 대조를 추가했다. 결과는 문서 끝의 후속 검증 항목을 참조한다.

## 보유와 연구 연결 상태

| 데이터 | 확인된 내용·기간 | 저장·조회 경로 | 연구 입력 상태 |
|---|---|---|---|
| KRX 주가·거래·규모 | 종가·수정주가·거래대금·시가총액·주식 수. 운영 가격 인증은 2026-09-17까지 확인 | RDS `price_daily`; 연구의 인증 Silver 조회 경로 | 기존 월별 연구 패널에 가격·거래·규모 및 파생 입력 연결. 패널 자체의 동결 날짜는 KNOWLEDGE 참조 |
| 총수익 가격 | 2015-01-02~2026-09-17 총수익 계약 CERTIFIED 확인 | `price_daily.total_return_close`, `price_return_contract` | 사후 실현수익 평가 label용. 과거에 알 수 있었던 가격 feature로 간주하지 않음 |
| DART 재무 | 매출·영업이익·순이익·자산·부채·자본 및 연결된 TTM 등. 계정별 결측률은 KNOWLEDGE에 기록 | RDS `fundamental` 및 연구 Silver 조회 경로 | 기존 패널에 연결된 열만 바로 사용 가능. 모든 원계정·모든 종목·모든 기간의 완전성을 의미하지 않음 |
| 한투 투자자 수급 | 개인·기관·외국인 매수/매도/순매수 수량·금액. 역사적 관찰 2,816자산, 2015년 이후~2026-09-17의 예상 거래일 적재 확인 | S3 원본; RDS `kis_market_observation`, `kis_market_latest`, `kis_market_asof(timestamp)` | RDS 보유 완료. 현재 KNOWLEDGE의 연구 패널 입력에는 아직 미연결 |
| 한투 공매도 거래 | 공매도 체결수량·금액, 수정 전 전체 거래량, 이를 분모로 계산한 비율. 같은 종목군·기간의 예상 거래일 적재 확인 | 위 KIS 테이블·뷰의 `venue='J'`, `kind='short'` | RDS 보유 완료. 연구 패널 입력은 미연결. 공매도 **잔고**·대차잔고와 구분 |
| NXT 거래 가능 이력·상장기간 | NXT 출범일 2025-03-04~2026-09-17의 해당 종목군 상태 대조 완료. 상장폐지 반영 | S3 reference 증거, RDS `asset_listing_snapshot`, KIS manifest/checkpoint | 수집 기대 범위를 정하는 기준 자료. 곧바로 연구 feature로 등록된 것은 아님 |
| FMP 일일 데이터 | 2026-09-16까지 `fmp_daily` 인증 기록 확인 | TeamAlpha-data FMP 수집 경로 | 개별 시리즈·필드별 보유 기간과 연구 연결 여부는 별도 확인 필요. 전체 FMP 카탈로그를 보유한다고 해석하지 않음 |
| FMP 한국 매크로·중국 PMI | 한국 13개 + 중국 NBS 제조업 PMI 1개, 선별 **1,932행**. 조회 범위 `2015-01-01~2026-09-18` | S3 Bronze `macro/fmp/economic-calendar/korea-coverage-v1/snapshot=backfill-20260920/` | **Bronze 보유 완료**. PIT 미승인, Silver/Gold 미적재·연구 입력 미연결. 추가 일일 수집 운영 배포 전 |
| FMP 추가 환율·COT·ETF | 환율 5개 + COT 6개 + ETF 3개, **28,191행**. 조회 범위 `2015-01-01~2026-09-18` | S3 Bronze `regime/fmp-external/korea-external-v1/snapshot=backfill-20260920/` | **Bronze 보유 완료**. PIT 미승인, Silver/Gold 미적재·연구 입력 미연결. 추가 일일 수집 운영 배포 전 |
| FMP 대만·변동성·금리 포지션 | EWT·USDTWD + 변동성 지수 3개 + 금리 COT 4개, **17,360행**. 조회 범위 `2015-01-01~2026-09-18` | S3 Bronze `regime/fmp-external/korea-risk-v1/snapshot=backfill-20260920/` | **Bronze 보유 완료**. PIT 미승인, Silver/Gold 미적재·연구 입력 미연결. 추가 일일 수집 운영 배포 전 |

DART 지분 공시, 업종 관측, 기업행사·배당 근거, 별도 KRX 수급·공매도 잔고 테이블은
TeamAlpha-data 스키마/문서에 정의되어 있다. 이번 확인에서는 각각의 실제 행수·기간·
연구 사용 상태를 전수 확인하지 않았으므로 보유 완료로 추가 표시하지 않았다.

## FMP 추가 Bronze 상세

세 묶음의 운영 버킷은 `soma-quant-bronze-31-159372032315-ap-northeast-2-an`이다.
위 표의 경로는 해당 버킷 기준이며, 각 경로 아래
`runs/from=2015-01-01/to=2026-09-18/manifest.json`이 전체 범위의 완료 증거다.

| 묶음 | 확보한 계열 | 행 수 |
|---|---|---:|
| 한국 매크로·중국 PMI | 한국 기준금리 결정, CPI YoY/MoM, 무역수지, 산업생산 YoY/MoM, 소매판매 MoM, 실업률, 소비자심리, 기업경기, PPI YoY/MoM, 경상수지 + 중국 NBS 제조업 PMI | 1,932 |
| 추가 환율 | `USDCNH`, `USDCNY`, `USDJPY`, `AUDUSD`, `EURUSD` | 15,690 |
| COT 선물 포지션 | `HG` 구리, `CL` WTI, `DX` 달러지수, `J6` 엔화, `GC` 금, `VX` VIX | 3,666 |
| ETF 가격 | `EWY`, `EEM`, `FXI` | 8,835 |
| 대만 ETF·환율 | `EWT`, `USDTWD` | 6,080 |
| 변동성 지수 | `^VVIX`, `^VIX3M`, `^VIX9D` | 8,836 |
| 미국 금리 COT | `ZT` 2년 국채, `ZN` 10년 국채, `ZB` 30년 국채, `ZQ` 연방기금 선물 | 2,444 |

- 매크로: 141개 월별 파티션·565개 S3 객체. 2026-09-20 **00:32 KST** 재조회 검증 완료.
  원본·선별 payload 282개의 체크섬 및 원문 일치를 검증했다.
  actual=null 1행과 동일 계열·제공시각 중복 초과 3행을 그대로 보존했다.
- 환율/COT/ETF: 168개 연도·계열 파티션·673개 S3 객체. 2026-09-20 **14:22 KST** 재조회 검증 완료.
  원본·관측 payload 336개의 체크섬과 로컬 원본과의 byte 일치를 확인했다.
  FX 주말 날짜 433행을 삭제하지 않고 품질 플래그로 남겼다.
- 대만/변동성/금리 포지션: 108개 연도·계열 파티션·433개 S3 객체.
  2026-09-20 **21:29 KST** 재조회 검증 완료. 원본·관측 payload 216개의 체크섬,
  전 행의 원문·source index·수집시각·PIT 차단 및 로컬 파일과의 byte 일치를 확인했다.
  USDTWD 주말 날짜 78행은 품질 플래그로 보존했다. 실제 수집시각은 같은 날
  **21:25:24~21:26:18 KST**이고, S3 승격 중 FMP 재호출은 0회다.
- 표의 기간은 **API 조회 범위**다. 통계 대상기간·공식 발표일 범위나 모든 거래일의 완전성을
  의미하지 않는다. 이번 매크로 스냅샷에서 CPI·경상수지의 첫 제공 날짜는 2015년 2월이며,
  COT의 최신 보유 기준일은 2026-09-15, 추가 환율·ETF의 최신 제공 날짜는 2026-09-18이다.
- 세계 경제캘린더 전체 원본 254,037행은 매크로 `raw/` 증빙에 들어 있다.
  이 숫자를 허용 목록의 관측 수로 세거나, 포함된 미국·중국 통계를 연구 입력으로 자동 승인하지 않는다.
- 세 묶음 모두 `pit_approved=false`, `publication_time_verified=false`,
  `revision_history_verified=false`, `silver_publish_allowed=false`다.
  외부 레짐 두 묶음은 추가로 `historical_backtest_allowed=false`이며,
  모든 관측의 미검증 `released_at`·`available_at`·`vintage`는 null이다.
- 기준일과 실제 API 수집시각을 분리했다. COT 기준일에 임의의 발표시각을 붙이지 않았고,
  S3로 옮길 때 실제 수집시각을 업로드 시각이나 과거 날짜로 바꾸지 않았다.
  **Bronze 보유 완료는 과거 PIT 인증·백테스트 사용 승인·연구 패널 연결 완료가 아니다.**
- 일일 연결 코드는 있으나 추가 수집기의 운영 배포는 아직 하지 않았다.
  기존 `fmp_daily` 인증 기록과 별개다. 항셍·닛케이225·TIP·RSP 등 나머지 조사 후보는
  이번 적재분에 없다. VVIX·VIX3M·VIX9D는 위 risk 묶음에 보유 완료로 반영했다.

## 한투 데이터 상세

- 수급 시장: KRX `J`, NXT `NX`, 통합 `UN`. NXT는 2025-03-04 이후 실제 대상 날짜에만 해당한다.
  공식 비대상 날짜의 통합 수급은 KRX 원본으로 구성하며 도출 근거를 기록한다.
- 공매도는 KRX 거래 기준이다. NXT/통합 공매도나 공매도 잔고를 이번 적재 범위에 포함하지 않는다.
- 금액은 Silver에서 원 단위로 정규화한다. 한투 수급 원본의 백만원 단위와 혼동하지 않는다.
- 모든 자산이 2015년부터 존재한다는 뜻은 아니다. 상장 전·폐지 후와 거래소 비대상 날짜를
  구분한 기대치로 검증한다. 과거 제외·상장폐지 종목도 역사적 종목군에서 유지한다.
- 종목군 원천은 **2026-08-10 기준 연구 export의 역사적 합집합 2,816자산**이다.
  이후 실제 데이터 적재일과 export 기준일은 다르다. 연구 종목군을 새로 발행하면
  manifest/reference seed도 맞춰 갱신해야 하며 신규 편입을 자동 추측하지 않는다.
- 9월 14~17일 추가 적재: 예상·실제 32,115행 일치.
- 로그인 없는 일일 경로 시험: 9월 11·14·15·16·17일 예상·실제 **40,148행** 일치,
  누락·초과·중복·비율 오류 0건. 이는 내부 검증이며 전 종목·전 기간 KRX 외부 값 대조를 뜻하지 않는다.

## 일일 운영

2026-09-18 활성화 확인. AWS 일일 파이프라인은 화~토 08:30 Asia/Seoul에 시작하며,
선행 인증 데이터가 준비된 뒤 한투 수집·RDS 게시를 실행한다. 최근 5거래일을 재조회하고,
중단 시 마지막 성공일 이후 누락 구간도 포함한다. 40일 초과 중단은 별도 복구가 필요하다.

`KIS_FLOWS_ENABLED=1`, `KIS_DAILY_MODE=PROVIDER_TRUST`. 사용자가 한투 시장 구분을
신뢰하기로 선택한 정책이다. KRX 브라우저 로그인·LLM·로컬 PC 상시 실행 없이 운영한다.
NXT 공개 자료와 필요한 한투 상장폐지 메타데이터는 코드가 조회한다. 수량·금액 계산,
원거래량 분모, J+NX와 UN 대조, 날짜·식별자·누락 검사는 유지한다.
2026-09-18 확인 당시 활성화 이후 첫 예약 실행은 2026-09-19 08:30 예정이었다.
이번 FMP 인벤토리 갱신에서는 그 이후 한투 예약 실행 성공 여부를 재조회하지 않았다.
실제 시험 실행 및 설정 활성화와 구분한다.

## 시점·인증 구분

아래는 **한투 데이터의 시점 계약**이다. 추가 FMP Bronze에 이 가용시각 정책을 적용하지 않는다.

`trade_date`는 거래일, `first_observed_at`은 실제 수집 시각이다.
`research_available_at`은 다음 달력일 08:30 KST라는 정책 가정이며 제공자의 실제 공개시각
보장이 아니다. 과거 소급 수집에는 `historical_revision_risk=true`를 보존한다.

`kis_market_latest`는 최신 정정값 조회이고 과거 시점에 알 수 있던 값만 반환하는 뷰가 아니다.
`kis_market_asof(timestamp)`는 실제 관측·정책 가용시각을 적용한다. 따라서 지금 받은
2015년 자료가 엄격한 2015년 시점 조회에 나타나지 않을 수 있다.
수집·Silver 내부 검사 통과, KRX 외부 대조, 연구 PIT 입력 연결·사용 승인은 서로 다른 상태다.

## 근거와 관련 문서

- [연구 지침](INSTRUCTIONS.md), [현재 동결 패널의 사용 가능 입력](KNOWLEDGE.md#available-strategy-inputs)
- [TeamAlpha-data 한투 운영 문서](https://github.com/danielhO9/TeamAlpha-data/blob/main/docs/kis-market-flows.md)
- [일일 수집·provider trust 변경 PR 11](https://github.com/danielhO9/TeamAlpha-data/pull/11), [기준 자료 범위 보완 PR 12](https://github.com/danielhO9/TeamAlpha-data/pull/12)
- 운영 재현 증거: 이 작업 workspace의 `outputs/kis-daily-20260918/progress.json`,
  `outputs/kis-provider-daily-20260918/progress.json`, `activation.json` 및
  `outputs/kis-status-20260918/inspection.json`. 실행 ID·S3 증거 위치는 각 파일에 기록되어 있다.
- [FMP 매크로 적재 문서](/Users/mac/Documents/GitHub/TeamAlpha-data/docs/fmp-macro-bronze.md),
  [S3 재조회 검증 증빙](/Users/mac/Documents/GitHub/TeamAlpha-data/data/audits/fmp-macro-s3-20260920/verification.json).
- [FMP 환율·COT·ETF 적재 문서](/Users/mac/Documents/GitHub/TeamAlpha-data/docs/fmp-external-bronze.md),
  [S3 재조회 검증 증빙](/Users/mac/Documents/GitHub/TeamAlpha-data/data/audits/fmp-external-load-20260920/s3_verification.json).
- [FMP 대만·변동성·금리 포지션 적재 문서](/Users/mac/Documents/GitHub/TeamAlpha-data/docs/fmp-risk-bronze.md),
  [S3 재조회 검증 증빙](/Users/mac/Documents/GitHub/TeamAlpha-data/data/audits/fmp-risk-load-20260920/s3_verification.json).
  FMP 링크는 같은 로컬 workspace의 TeamAlpha-data 파일이며, S3 위치는 각 증빙의 `manifest_uri`에도 있다.

### FMP PIT 심사 후속 (2026-09-20)

[실원본 심사 보고서](../output/pit_audit/fmp-20260920/report.md): 37계열 47,483행을 로컬 검사했으며
역사적 PIT 승인은 0개다. 23계열은 실제 backfill 원본, macro 14계열은 앞선 audit replay를 사용했고
이번에 S3 동일본을 재인증하지 않았다. Cboe 현재 공식 종가와 74건 차이 및 추가 날짜 1건,
COT 발표 예외를 반영하지 않을 때 90개 관측이 월말을 넘는 사례가 확인됐다.
Bronze 보존 검사 통과와 역사적 사용 승인을 구분한다. 원본·Silver/Gold·기존 연구 입력은 변경하지 않았다.

### 한국 정책금리 월말 정제 승인 (동일 날짜의 후속 작업)

위 0개 판정 후 [정제 입력 1개를 승인](../output/regime_inputs/kr-policy-pit-20260920/README.md)했다.
정확한 S3 매크로 141 partition·1,932행을 재검증했고, 정책금리 105행을 공식 결정 103건과 대조했다.
actual은 모두 일치, 날짜 36행 정규화, 중복 2행은 원본 연결을 보존하여 해소했다.
2014년 워밍업 포함 한국은행 결정문 115건과 금리 변경 27건의 근거를 확보했다.

`KR_POLICY_DIRECTION_3M`: 2015-01~2026-08 140개월, 월말 공표 목표금리의 3개월 변화 부호로 분류.
공식 발표일 종료를 보수적 가용시각 상한으로 쓰는 **월말 진단 전용** 승인이다.
원본 FMP 시각·estimate/previous·장중 사용·팩터 feature는 승인하지 않았다.
`research/regime_sources.json`에 등록되어 새 캠페인에서 기본 동결하며 기존 캠페인은 바꾸지 않는다.
저장은 로컬 불변 Silver artifact(`output/regime_inputs/kr-policy-pit-20260920/silver/context.json`)이며
RDS/S3 Silver 적재는 아니다. 나머지 36계열과 공식 시장지수 입력은 여전히 별도 심사가 필요하다.

### 잔여 FMP 36계열 실검증 (2026-09-21)

[종합 검증 보고서](../output/pit_audit/fmp-20260921/report.md),
[기계 판독 결과](../output/pit_audit/fmp-20260921/verification.json).
정책금리 포함 37계열 47,483행의 원본 무결성 및 기초 품질을 재검사했다.
매크로는 정확한 S3 backfill 미러를 사용했다. 이번 실행에서 S3를 새로 다운로드한 것은 아니다.

- COT 10계열 6,110행의 10개 핵심 필드 **61,100개 값 전부 CFTC 현행 공식 이력과 일치**.
  실제 발표·정정 달력과 최초 vintage 승인은 별도이며, 수치 대조 통과를 PIT 승인으로 바꾸지 않았다.
- CPI MoM/YoY는 공식 월별 발표 페이지 140건·280개 값 중 **279개 일치, 1개 차이**.
  2017-09분 FMP 날짜가 공식 발표보다 4일 늦고, 2026-01분 페이지에는 3월 수정 공지가 있다.
  PDF 표지로 2026-01분의 원래 발표시점(2월 3일)을 게시일과 구분했다.
  2024-04 MoM은 FMP 0.0%, 현재 공식 PDF 0.1%로 정정 전후/오류 여부 추가 확인이 필요하다.
- ETF 4계열의 2026-09-18 종가는 운용사 공시값과 모두 일치. 장기 운용사 XLS는 NAV이므로
  과거 종가 전수 대조로 주장하지 않는다. FX 6계열 511개 주말 행은 모두 일요일이다.
- 나머지 매크로 11계열의 최초 발표자료 전수 대조, FX 동일 fixing 값 및 ETF 역사 종가 대조는 미완료.
  기존 Cboe 현재 공식값 차이 74개와 추가 날짜 1개는 재확인했다.

새 PIT 승인 0개, 기존 정책금리 월말 진단 입력 승인 1개 유지. 원본·registry·기존 캠페인·OOS·DB는 변경하지 않았다.

### 사용자 PIT 가정 수용·실제 레짐 연결 (2026-09-21 후속)

위는 검증 당시의 기록이다. 이후 사용자가 추가 PIT 전수검증·영향측정 없이 레짐 진단에 사용하도록
요청하여 [별도 가정 정책](regime_assumption_policy.json)을 만들고 **새 캠페인 기본 입력 38축**을 연결했다.
원본의 검증 flags·실제 수집시각·기존 캠페인은 변경하지 않았다. 파생 로컬 artifact이며 RDS/Gold 적재가 아니다.

- 기존 검증 한국 정책금리 1축: 2015-01~2026-08, 140개월.
- `PIT_ASSUMED` FMP 36축: 매크로 13·FX 6·ETF 4·COT 10·변동성지수 3.
  47,378행 원본 연결을 보존. 2015-01~2026-08 5,040축·월 중 4,313개 판독, 727개 UNKNOWN.
  2026-08 36축 모두 판독. 가격 방향은 2015-04, 나머지 축은 2017-01/02부터 워밍업 완료.
- `PIT_ASSUMED` KOSPI 1축: 로컬 완전월 2015-01~2026-06 138개.
  장·단기 추세/변동성 네 축 판독은 2018-01~2026-06 102개월. 2026-07~08은 UNKNOWN.
- 기존 FMP 9계열은 로컬 2026년 9월 표본(18개 manifest)뿐이어서 이번 장기 입력에서 제외했다.
  API 자체의 장기 coverage 부재를 주장하지 않는다.

검증되지 않은 최초 vintage와 가용시각은 가정으로 표시한다. 실제 receipt·raw hash와 가정시각을 분리하고
월 t 상태를 t+1 진단에만 연결한다. 추가 팩터 실행·OOS 열람·기존 교훈 덮어쓰기는 하지 않았다.

[레짐 정책과 재현 명령](REGIME_INPUTS.md),
[38축 실제 판독 결과](../output/regime_inputs/assumed-regime-layer-20260921-v1/README.md),
[FMP 입력](../output/regime_inputs/fmp-assumed-20260921-v1/README.md),
[KOSPI 입력](../output/regime_inputs/kospi-assumed-20260921-v1/README.md).
