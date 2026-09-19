# 데이터 보유 현황

확인 기준: 2026-09-18. 아래는 운영 증거와 현재 연구 입력 목록에서 확인한 범위다.
전체 DB의 실시간 카탈로그는 아니며, 목록에 없다는 이유만으로 미보유라고 판단하지 않는다.
최신 적재일은 실행마다 달라진다. 표의 날짜는 마지막 확인값이며 실시간 보장을 뜻하지 않는다.

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

DART 지분 공시, 업종 관측, 기업행사·배당 근거, 별도 KRX 수급·공매도 잔고 테이블은
TeamAlpha-data 스키마/문서에 정의되어 있다. 이번 확인에서는 각각의 실제 행수·기간·
연구 사용 상태를 전수 확인하지 않았으므로 보유 완료로 추가 표시하지 않았다.

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
활성화 이후 첫 예약 실행은 2026-09-19 08:30 예정이며, 이 문서 작성 시 그 실행 성공까지
확인한 것은 아니다. 실제 시험 실행 및 설정 활성화와 구분한다.

## 시점·인증 구분

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
