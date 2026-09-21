# FMP 한국 레짐 입력 PIT 심사 — 2026-09-20

## 판정

**현재 보유 FMP 원본을 그대로 사용하는 2015년 이후 역사적 PIT 승인: 0 / 37개. 모두 보류.**
자료가 쓸모없다는 뜻이나 37개 모두 값이 틀렸다는 판정은 아니다. 수집 성공·현재값 대조와
당시 이용 가능했던 값의 증명은 다르다. 보류 이유를 해결하지 않고 `pit_approved=true`로 바꾸지 않았다.

| 범위 | 계열 | 검사 행 | 역사적 PIT 승인 | 남은 핵심 조건 |
|---|---:|---:|---:|---|
| 한국 매크로 + 중국 PMI | 14 | 1,932 | 0 | 정확한 S3 snapshot 재확인, 발표시각·통계 대상월·최초 발표값 |
| FX | 6 | 18,825 | 0 | 제공자 세션/기준시각·주말 행 의미·수정 이력 |
| ETF | 4 | 11,780 | 0 | 미국 종가의 한국 기준 가용시각·기업행사 조정 버전 |
| COT | 10 | 6,110 | 0 | 실제 발표일 예외 달력·수정본 가용시각 |
| Cboe 변동성 지수 | 3 | 8,836 | 0 | 공식 현재값 차이·과거 재작성 이력·한국 의사결정 시점 정렬 |
| 전체 | 37 | 47,483 | 0 | 미승인 입력 차단 유지 |

`review-v2/decisions.json`은 **보류 심사 기록**이며 `pit-regime-approval-v1` 승인서가 아니다.
새 승인 입력·Silver/Gold 게시·캠페인 실행·레짐 성과 산출은 하지 않았다.

## 실제 검사 범위와 한계

- 417개 완료 partition의 raw/projection **834개 본문 SHA256**, 바이트 길이, 원본 행 연결,
  실제 수집시각, 선택/관측 행 47,483개를 재검사했다. 이 로컬 원본 보존 검사는 통과했다.
- FX·COT·ETF·지수 23개 45,551행은 실제 `snapshot=backfill-20260920` 로컬 원본이다.
- 매크로 14개 1,932행은 `snapshot=audit-replay-20260919`의 2015년 이후 부분이다.
  S3의 `backfill-20260920`과 계열별 건수는 같지만, **이번에 두 snapshot의 바이트 동일성을
  재증명하지 않았다.** 따라서 매크로 검사 결과를 정확한 S3 업로드본 인증으로 주장하지 않는다.
- 현재 S3는 재조회하지 않았다. FMP 추가 API 호출은 0회이며, 공개 공식 근거만 조회했다.
- Cboe 3개 지수는 모든 보유 날짜의 종가를 대조했다. 한국은행은 정책금리 105행을 현재
  공식 시행일 금리표와 대조했다. COT는 공식 발표 예외를 보유 행에 연결했다.
  나머지 계열을 공식 최초 발표값과 전수 대조했다는 의미는 아니다.
- 실제 수집시각(2026년)을 과거 발표시각으로 소급하거나, `available_at`에 임의 지연을 넣지 않았다.

## 1. Cboe: 현재 공식 종가와 74건 차이, 공식 파일에 없는 날짜 1건

| 계열 | 보유 행 | 공식값 일치 | 종가 불일치 | 공식 날짜 없음 | 최대 절대 차이 |
|---|---:|---:|---:|---:|---:|
| ^VVIX | 2,946 | 2,932 | 13 | 1 | 0.36 |
| ^VIX9D | 2,945 | 2,888 | 57 | 0 | 1.60 |
| ^VIX3M | 2,945 | 2,941 | 4 | 0 | 0.05 |
| 합계 | 8,836 | 8,761 | 74 | 1 | — |

비교 허용오차는 절댓값 0.000001이다. 공식 최신 날짜는 세 파일 모두 2026-09-18이며,
동일 기간 공식 날짜 중 FMP에 빠진 날짜는 없었다. VVIX의 추가 날짜는 **2021-11-25**다.
예를 들어 2018-12-31 VIX9D는 FMP 27.35, 현재 공식값 28.57이다.

차이의 원인이 FMP 오류인지, 공식 사후 수정인지, 종가 정의/시점 차이인지는 아직 확정하지 않았다.
공식값으로 덮어쓰면 오히려 사후 정보를 주입할 수 있어 원본을 변경하지 않았다.
일치한 8,761행도 그 사실만으로 최초 공개 vintage가 증명되지는 않는다.
Cboe 정책은 정정 시 EOD 값을 소급 변경할 수 있다고 명시한다.

근거: [공식 지수 이력](https://www.cboe.com/tradable_products/vix/vix_historical_data),
[공식 재작성 정책 3.3](https://cdn.cboe.com/resources/indices/governance/Cboe_Index_Policies_Practices.pdf).
공식 CSV 및 정책 원문은 `evidence/`에 URL·수신시각·SHA256과 함께 보존했다.

## 2. COT: 기준일 + 3일은 안전한 PIT 규칙이 아님

2025년 공식 예외 일정 13개 기준일을 10개 보유 계열에 연결했다.
**130개 관측**에서 단순 +3일 규칙이 공식 발표 일정보다 앞서며,
그중 **90개 관측은 +3일로 계산한 달의 월말 이후로 공개 일정이 넘어간다.**
이는 90개의 서로 다른 달이라는 뜻이 아니라 계열별 관측 수다.

예: 포지션 기준일 2025-09-30 → 단순 추정 2025-10-03 → 공식 새 발표 일정 2025-11-19.
추정값이 47일 빠르다. 한국시간으로 변환하지 않은 미국 공지 날짜 비교이며, 승인용 timestamp가 아니다.

2025-12-09 수정 공지를 사용했다. 이전 11월 공지는 일부 후속 공개 일정이 달라 그대로 쓰지 않았다.
이번 목록은 **확인한 반례**이지 2015년 이후 모든 예외/실제 공개시각을 완성한 달력이 아니다.
공식 일정 자체도 의도된 공개일이므로 각 최초 발표본의 값·실제 게시 이력 검증을 대체하지 않는다.

근거: [CFTC 공식 특별공지](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm),
[기준일과 발표일을 구분하는 공식 이력 안내](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/index.htm).
적용한 예외가 저장된 공식 공지에 실제 존재하는지도 코드로 검사했다.

## 3. 한국 정책금리: 가장 먼저 정제할 후보지만 아직 원본 승인 아님

105행을 현재 한국은행 기준금리 시행일 표와 비교했다. manifest에 적힌 UTC를 가정해
KST로 변환했을 때 104행이 시행 중 금리와 일치한다. 이 변환은 **민감도 검사이며 타임존 인증이 아니다.**

나머지 1행은 2020-03-16의 0.75%다. 한국은행 표에서는 2020-03-17부터 시행된다.
이는 발표일과 시행일의 차이로 설명될 수 있으므로 단순한 값 오류로 판정하지 않는다.
한국은행은 [2020년 3월 긴급 결정 기자간담회](https://www.bok.or.kr/portal/bbs/B0000169/view.do?depth=201295&menuNo=201295&nttId=10057043&oldMenuNo=201151&programType=multiCont&relate=Y)에서
인하 결정을 설명한다. [시행일 표](https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643)를 발표 timestamp 대신 쓰면 안 된다.

2026-04-10과 2026-07-16에는 각각 동일 timestamp 두 행이 있으나 event 대상월이 서로 다르다.
금리 actual은 같아도 원본 payload는 다르므로 `drop_duplicates`로 조용히 삭제하지 않았다.
발표일/시행일 분리, 공식 결정 문서 연결, 중복 해소 및 정확한 S3 원본 binding 후
**월말 정책금리**처럼 범위를 좁힌 별도 정제 입력으로 심사할 수 있다.
원본의 모든 event timestamp나 estimate/previous까지 함께 승인하는 것은 아니다.

## 4. 다른 매크로·FX·ETF

- 산업생산 YoY 2026-03-30 23:00:00에 값이 -2.2인 행과 actual=null인 행이 함께 있다.
  previous도 6.8과 7.1로 다르다. 최초 발표/수정/대상월 관계가 해결되지 않았다.
- 경제 캘린더의 날짜, 통계 대상월, actual의 vintage를 별도로 확인해야 한다.
  `previous`를 당시 이미 알고 있던 값으로 간주하지 않는다. 달력 수집 건수의 충실함은 PIT 증명이 아니다.
- FX 6개 계열의 제공자 날짜상 주말 행은 합계 **511행**이다. UTC 일요일과 거래 세션의 관계를
  모르는 상태에서 오류라고 단정하거나 한국 일자에 그대로 정렬하지 않았다.
- ETF 4개는 기업행사 조정 정의와 그 버전의 가용시각을 검증하지 못했다.
  오늘 받은 장기 수정주가 전체를 당시 이용 가능했던 입력으로 자동 승인하지 않는다.

## 계열별 결론

모든 행의 역사적 승인 상태는 `DEFERRED`다. 코드형 상세 사유, 날짜, 중복 payload와
수집시각은 `review-v2/decisions.json` 및 `review-v2/audit.json`에 있다.

| 구분 | 계열 |
|---|---|
| 한국 정책금리 | KR_POLICY_RATE |
| 한국 가격 | KR_CPI_YOY, KR_CPI_MOM, KR_PPI_YOY, KR_PPI_MOM |
| 한국 실물·대외 | KR_TRADE_BALANCE, KR_CURRENT_ACCOUNT, KR_INDUSTRIAL_PRODUCTION_YOY, KR_INDUSTRIAL_PRODUCTION_MOM, KR_RETAIL_SALES_MOM |
| 한국 고용·심리 | KR_UNEMPLOYMENT_RATE, KR_CONSUMER_CONFIDENCE, KR_BUSINESS_CONFIDENCE |
| 중국 | CN_NBS_MANUFACTURING_PMI |
| 환율 | USDCNH, USDCNY, USDJPY, AUDUSD, EURUSD, USDTWD |
| ETF | EWY, EEM, FXI, EWT |
| 포지션 | HG, CL, DX, J6, GC, VX, ZT, ZN, ZB, ZQ |
| 변동성 | ^VVIX, ^VIX3M, ^VIX9D |

## 재승인 조건 및 우선순위

1. **KR_POLICY_RATE 월말 계열**: 정확한 Bronze snapshot 확보 → 공식 결정 발표 문서/date 연결 →
   발표/시행 분리 및 중복 명시적 처리 → 시각 증거 또는 별도 허용된 가용시각 계약으로 심사.
2. **Cboe 지수**: 74건 차이 및 추가 날짜 해소 → 정정 공지·당시 EOD vintage 확보 →
   미국 세션과 한국 신호월 경계 정렬. 일치하는 행만 골라도 vintage 검사가 생략되지는 않는다.
3. **COT**: 전체 기간 실제 공개/수정 달력과 최초 발표 값 확보. reference date join 금지.
4. **다른 매크로**: 최초 보도자료 또는 vintage archive와 reference period를 매칭.
   시차를 넉넉히 주는 것만으로 revision look-ahead가 해결되지 않는다.
5. **FX·ETF**: 제공자 세션·조정 계약과 필요한 역사적 버전 확인.

엄격한 역사적 PIT 승인이 아닌 revised-history 연구용 proxy를 허용하려면 별도 정책 변경으로
구분해야 한다. 이번 심사에서 그 기준을 낮추거나 현재 연구 계약을 우회하지 않았다.

## 재현과 보호 검사

```sh
.venv/bin/python -m scripts.fmp_pit_audit \
  --data-root /Users/mac/Documents/GitHub/TeamAlpha-data/data \
  --evidence-dir output/pit_audit/fmp-20260920/evidence \
  --output /absolute/path/to/new-audit-directory

.venv/bin/python -m pytest tests/test_fmp_pit_audit.py tests/test_regime_inputs.py -q
```

감사 결과는 덮어쓰지 않는다. 재실행은 새 출력 디렉터리를 사용한다.
검사 테스트와 기존 레짐 입력 계약 테스트 **25개 통과**.
해시 변조·공식 날짜 중복·현재값 일치와 PIT 증명의 혼동·발표일/시행일 혼동·중복/null 보존,
미승인 입력 및 OOS/embargo 경계 보호를 확인했다. 단위 테스트는 실자료 승인이 아니다.
`factor-research-loop` 스킬의 연구 경계에 따라 후보 성과·봉인 OOS·기존 캠페인/교훈은 열거나 변경하지 않았다.
