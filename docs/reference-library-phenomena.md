# 현상 연구용 레퍼런스 라이브러리

작성: 2026-10-02. [기계 판독 카탈로그](../research/phenomena/reference-catalog.json),
[계산 엔진](../engine/reference_library.py), [검증 테스트](../tests/test_reference_library.py).

## 현재 활성 목록: 108개 레퍼런스

2026-10-04 공매도 허용 이력 반영 후 **108개·27,754,980행·66개 불변 Gold dataset**이다.
기존 공매도 2개를 과거 일별 지수 편입·개별 제한일을 반영한 v2로 교체했다.
2021-05~2023-10 비중 10,365개·변화 9,904개 종목-월을 복원했다. 구버전은 보존하고 나머지 106개는 유지했다.
신규 두 데이터셋 344,144개 값의 커밋·전 행 재조회·실제 활성 소비 경로 검증을 완료했다.
[공매도 교체 결과·결측·PIT 한계](reference-short-eligibility-20261004.md),
[활성 108개 카탈로그](../research/phenomena/reference-catalog-short-eligible-108-20261004.json),
[활성 program](../research/phenomena/program.json)을 따른다. `PIT_ASSUMED`이며 알파 승인은 아니다.

## 보존 기록: 108개 최초 확장

2026-10-03 수급·공매도·R&D·고용 후속 확장은 **108개·27,734,862행·66개 불변 Gold dataset**이었다.
기존 100개를 그대로 보존하고 수급 4개·공매도 2개·양의 R&D/매출 1개·공시 직원 순고용률 1개를 추가했다.
[신규 적재·시점·제한](reference-new-information-20261003.md),
[당시 108개 카탈로그](../research/phenomena/reference-catalog-new-information-108-20261003.json),
[교체 전 program](../research/phenomena/program-snapshots/108-before-short-eligibility-20261004.json)에 보존했다.
107개 중간 전환과 108개 최종 전환의 실제 소비 경로에서 신규 1,798,154개 값을 전부 재검증했으며 결측 대체·알파 승인은 없다.
고용 원자료 23,671건은 수집 완료했고 과거 컨센서스는 빈티지·저장 권한 미확보로 미적재다.

## 보존 기록: 100개 확장

2026-10-03 확장 완료: **100개·25,936,708행·58개 불변 Gold dataset**이다.
[전체 목록 및 적재 검증](reference-expansion-100-completion-20261003.md),
[문헌·평가 방법](reference-expansion-100-methods-20261003.md),
[100개 카탈로그](../research/phenomena/reference-catalog-100-20261003.json),
[활성 program](../research/phenomena/program.json)을 기준으로 조회한다.
기존 45개와 레거시 Gold는 보존했으며 신규 55개만 추가했다. 한국 수익성 승인과는 구별한다.
선택적 로컬 검증 캐시는 `output/phenomena/reference-expansion-100-20261003/final-audit/collection-cache`다.
연구 질문에 필요한 `reference_ids`를 명시해서 읽는다. 전체 100개를 동시에 비결측으로 요구하면
교집합이 2021-02 이후 32,127종목-월로 줄어든다. 캐시 없이도 인증 DB 소비 경로를 사용한다.

## 보존 기록: 초기 7개와 첫 확장 38개

아래 초기 목록·v1 API는 **2026-10-02의 첫 가격 전용 라이브러리 기록**이다. 초기 카탈로그 16개 중
7개가 구현됐고, 당시 미준비된 9개 원형 정의는 그대로 보존한다. 2026-10-03 확장은
초기 카탈로그와 기존 7개 definition hash를 보존한다.

새 [확장 카탈로그](../research/phenomena/reference-catalog-expansion-20261003.json)는
**기존 7개 + 추가 가격·거래활동 13개 + 연간 재무 25개 = 45개 측정 정의**다.
[문헌 연결](../research/phenomena/reference-expansion-literature.json)과
[정의 검토 문서](reference-expansion-literature-20261003.md)에 원형과 국내 적응식·근거 등급을 남겼다.
2026-10-03 확인 기준 신규 38개·9,865,877행은 outer transaction 커밋과 그룹별 전 행 대조를
완료했다. 기존 현상 연구 레퍼런스 7개·2,119,881행을 합쳐 **45개·11,985,758행·14개 불변 dataset**이다.
이는 독립 알파 수나 한국에서 수익성이 확인된 수가 아니다.
[확장 적재 완료 보고서](reference-expansion-completion-20261003.md)에 수치와 검증 범위를 기록한다.
전체 14개 dataset·11,985,758행 재조회 후 collection 활성 프로그램 v2 전환을 완료했다.
이전 program 원문을 보존하고 CAS 일치를 확인했으며, 전환 후 collection manifest 검증에서
45개 측정치·14개 dataset을 확인했다. 실제 사용 목록은
[활성 program](../research/phenomena/program.json)과 실행 영수증으로 확인한다.
당시 45개 전환의 `program_sha256`은 `0b94e084e73bd5d5c20761e0a8a46b34a69bb69ce09fd4d8639bbb56dad5de54`다. 현재 활성 해시는 최상단 후속 확장과 program을 따른다.

이번 적재는 **2026-09 월말 기준 일회성 스냅샷**이며 일일 갱신 배포가 아니다.
`PIT_ASSUMED`로 취급하고 최초 발표 빈티지는 독립 입증하지 못했다. 측정치별 시작일과 종목별
유효 history는 서로 다르다. 측정 재현성 검증은 알파 승인이 아니며 기존 레거시 연구·Gold는 보존한다.

| 경로 | 원천·구현 | 현재 문서의 의미 |
| --- | --- | --- |
| 초기 v1 | 인증 KRX 가격, `reference_library.py`, 기존 7개 | 기존 1개 dataset·2,119,881행과 정의 그대로 보존·재사용 |
| 확장 v2 | 인증 KRX 가격 + 정확 계정 DART FY as-of, `reference_library_v2.py` | 신규 38개·13개 dataset·9,865,877행 커밋 및 그룹별 전 행 대조 완료 |
| 활성 조회 | program-v1 단일 dataset 또는 program-v2 collection | 명시된 dataset만 검증해 읽음. 최신·레거시 fallback 없음 |

## 사용 목적

새 연구의 출발점은 팩터가 아니라 시장 현상과 경쟁 가설이다. 레퍼런스는 규모·추세·위험·유동성·회계 특성을
측정하고, 관측된 관계가 기존 설명과 겹치는지 비교하기 위한 도구다. 유명하거나 논문에서 지지를 받은 정의를
선정했지만 한국 시장의 우수 순위라고 주장하지 않는다. 한국 성과를 보고 목록·방향·기간을 고르지 않았다.

**라이브러리 등재, 측정 검증, 알파 승인, 전략 승인은 별개다.** 모두 `MEASUREMENT_CONTROL`,
`alpha_approved=false`로 등록한다. 단독 수익이 약해도 정확히 측정된 통제 변수는 남길 수 있다.
기존 Gold 값이나 승인 상태는 가져오지 않는다. 이 엔진 자체는 DB 조회·적재·수익률 평가를 하지 않는다.
실제 적재 여부와 행 수는 별도 발행기의 실행 영수증이 source of truth다.

## 초기 v1 선정 목록과 구현 범위

| 분류 | 레퍼런스 | 측정 정의 | 이 모듈의 상태 |
|---|---|---|---|
| 규모 | 종목 시가총액 | 시가총액의 자연로그 | 구현; 입력 인증 필요 |
| 추세 | 12–2 가격 모멘텀 | `P(t-1)/P(t-12)-1` | 구현; 연속 월 경로 필요 |
| 반전 | 1개월 가격 반전 | 직전 월 수익의 반대 방향 | 구현; 인접 달 필요 |
| 위험 | 저변동성 | 최근 252개 관측 행의 일수익 표본 표준편차 | 구현; 유효 수익 200개 이상 |
| 유동성 | Amihud | 월간 평균 `abs(일수익)/원화 거래대금` | 구현; 유효 일수 15개 이상 |
| 추세 | 52주 고점 근접도 | 현재가/252개 관측 행 고점 | 구현; 가격 252개 필요 |
| 복권 선호 | MAX | 이전 한 달 최대 일수익 | 구현; 유효 일수 15개 이상 |
| 가치 | 장부가/시가 | 보통주 장부가치/대응 기업 시가 | 계정·기업 대응 미준비 |
| 가치 | 이익수익률 | 정의에 맞는 연간 이익/기업 시가 | 이익 계정·기간 미준비 |
| 수익성 | 매출총이익/자산 | `(매출-매출원가)/자산` | 매출원가·동일 기간 미준비 |
| 수익성 | 영업 수익성 | 매출−원가−판관비−이자비용/장부가 | 구성 계정·범위 미준비 |
| 투자 | 자산 성장 | 연속 두 결산기의 자산 성장률 | 결산기 쌍 원장 미준비 |
| 품질 | 발생액 | Sloan balance-sheet 발생액/평균 자산 | 계정 쌍·부호·기간 미준비 |
| 위험 | 저베타/BAB | 원형 추정·축소·베타조정 참고 | 시장·RF·공분산 계약 미준비 |
| 품질 | QMJ | 버전별 구성요소·표준화 참고 | 구성요소·버전 구현 미준비 |
| 시장 | 시장 초과수익 | 시장 TR−동일 기간 원화 RF | 별도 공통 수익률 스키마 필요 |

일간 집계 값은 열 이름만 믿지 않는다. 아래 원천 추정식·단위·관측 수 계약이 인증된 adapter로 전달돼야 한다.
252일은 현재 Silver SQL의 **관측 행 252개**다. 거래정지·누락으로 달력 기간이 길어질 수 있으며,
252일 고점은 정확한 52 달력주 정의와 다르다. 최소 일수는 문헌에서 한국 최적값으로 입증한 값이 아니라
이번 구현에서 성과 평가 전에 고정한 측정 정책이다.

## 원형과 국내 적용을 구분한다

French의 규모·가치·수익성·투자 팩터는 명시한 정렬과 비중을 적용한 포트폴리오 **수익률**이다.
이 라이브러리의 시가총액·가격 지표는 개별 종목 **특성값**이다. `-log(시가총액)`은 SMB 수익이 아니다.
시장 초과수익은 모든 종목에 공통인 관측이며 횡단면 종목 순위가 아니다.
[공식 Fama–French 정의](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html).

모멘텀은 다음 보유 월 직전 한 달을 제외한 11개 월수익을 연결한다. 이번 적용은 배당을 포함하지 않는
가격 지표이며, 누락된 월을 배열의 행 이동으로 건너뛰지 않는다. 단기 반전도 별도 정의다.
[Mom](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html),
[단기 반전](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_st_rev_factor.html).

Amihud는 주식 수가 아닌 거래 **금액**을 분모로 사용한다. 원형의 연간 달러 비율을 월간 원화 비율로
바꿨으므로 같은 이름의 완전 재현이라 하지 않는다. 높은 비유동성과 높은 거래비용은 양립한다.
[Amihud 원문](https://archive.nyu.edu/jspui/bitstream/2451/27420/2/S-AM-00-10.pdf).

고점 근접도와 월간 최대 일수익은 서로 다른 가격 특성이다. MAX 방향은 논문의 이전 한 달 최대 일수익과
후속 수익의 음의 관계에서 가져왔으나 국내 결론은 아니다.
[George–Hwang](https://doi.org/10.1111/j.1540-6261.2004.00695.x),
[Bali–Cakici–Whitelaw](https://pages.stern.nyu.edu/~rwhitela/papers/max%20jfe11.pdf).

매출총이익/자산은 영업이익/자산과 다르며, 발생액도 순이익 하나로 계산할 수 없다. 계정·동일 기간·CFS/OFS·
최초 가용일·정정 이력이 준비되지 않으면 계산하지 않는다. 월별로 반복되는 자산 값을 12행 이동해 두 FY로
간주하지 않는다. 저베타·저변동성·BAB도 같은 정의가 아니며 QMJ에 보유 계정을 임의로 섞지 않는다.
[Novy-Marx](https://mysimon.rochester.edu/novy-marx/research/OSoV.pdf),
[Sloan](https://www.cuhk.edu.hk/acy2/workshop/June2009Wasley/1996TAR%29.pdf),
[BAB](https://pages.stern.nyu.edu/~afrazzin/pdf/Betting%20Against%20Beta%20-%20Frazzini%20and%20Pedersen.pdf),
[QMJ](https://www.aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly).

문헌 검토는 위 측정 정의·구성 규칙과 관련 절을 대상으로 했다. 모든 논문을 전부 읽었다거나 한국 실증을
재현했다고 주장하지 않는다. 카탈로그는 각 URL과 검토 범위를 보존한다.

## 초기 v1 입력·출력 API

`calculate_reference_panel(panel, input_attestation=..., definitions=None, as_of=None)`는
`ReferenceLibraryResult(values, validation, blocked)`를 반환한다.

입력 필수 열:

- `asset_id`: 시점에 맞는 안정 식별자. 계산은 ticker가 아닌 이 값으로 묶는다.
- `stock_code`: `005930`, `0037T0` 같은 6자리 영숫자 문자열(`^[0-9A-Z]{6}$`).
  leading zero와 원문 대문자를 정확히 보존하며, 정수의 임의 zero-padding·소문자 자동변환·비ASCII 문자를 허용하지 않는다.
  코드 형태만으로 보통주 여부를 추론하지 않고 상위 adapter의 역사적 종목 유형 인증을 요구한다.
- `date`: KST 달력 월말을 나타내는 timezone-naive 자정 날짜.
- `known_at`: timezone-aware 원천 가용시각. 해당 KST 월말 정보 마감을 넘을 수 없다.
- `market`: KOSPI 또는 KOSDAQ. 인증 대상은 보통주다.
- 계산에 필요한 숫자형 feature와 관측 수. `FEATURE_CONTRACTS`, `FEATURE_UNITS` 상수로 정확히 지정한다.

`fwd_*`, `total_return_close`, 인증 없는 재무 열을 포함한 임의 열은 입력 스키마에서 거부한다.
입력 adapter는 source-only 열을 투영해야 한다. 원본 panel의 자의적인 attrs 선언만으로 인증된 자료가 되지 않는다.

attestation에는 `status=CERTIFIED`, `source_version`, `source_contract`, `evidence_sha256`,
`input_sha256`, `identity_contract=HISTORICAL_ASSET_ID`, `scope=KRX_COMMON_STOCK`, `units`,
`feature_contracts`를 넣는다. `input_panel_digest`는 전체 입력을 검증하고 행 순서와 무관한 내용 해시를 계산한다.
이 JSON이 진짜 원천 증거에 연결됐는지 확인하는 책임은 인증 adapter·publisher에 있으며 이 함수의
자기신고만으로 외부 데이터의 신뢰성을 보장하지 않는다.

출력은 `(reference_id, asset_id, date)` 단위다. `value`는 원 측정값, `oriented_value`는 문헌 방향을
한 번 적용한 값이다. 횡단면 순위·winsorization·합성은 수행하지 않는다. 정의 해시, 입력 해시, 원천 버전과
원천 가용시각을 유지한다. `validation`은 구현 코드 해시, reference별 전체/유효/결측 수와 날짜 범위를 담는다.

입력 단위·추정식·열이 부족하면 해당 reference는 `blocked`에 이유를 남기며 나머지 적격 정의는 계산한다.
잘못된 시점·identity·내용 해시는 전체 호출을 거절한다. 비수치 문자열은 거절하고, 개별 NaN/무한대·잘못된
분모·관측 수 부족은 값을 만들지 않는다. 0행은 `NO_VALID_ROWS`이지 측정 승인이나 적재 완료가 아니다.

## 검증 범위

독립적인 닫힌식 기대값으로 7개 구현을 검사한다. 미래 feature 변조, 누락 달, ticker 재사용, leading zero·신규 영숫자 코드,
무한대/음수/0 분모, 관측 수 경계, 미래 known-at, 자료·계정·범위 인증 누락, 레이블 열 차단을 테스트한다.
이 테스트는 소프트웨어 정확성 검사이며 실제 원천 SQL과의 대사·커버리지·Gold 적재 검증은 별도 실행 단계다.

새 연구는 사용할 reference ID·정의 해시·자료 버전을 사전에 고정한다. 이후 더 좋은 지표를 찾았더라도
완료된 연구의 비교 집합을 덮어쓰지 않는다. library의 문헌 방향·룩백을 한국 수익률을 보고 바꾸지 않는다.

## 활성 Gold 조회와 선택적 로컬 스냅샷

`engine.phenomenon_references.load_active_references(conn, repo_root, snapshot_path=None, reference_ids=None)`는
활성 세대·프로그램·카탈로그 해시가 지정한 정확한 Gold dataset만 조회한다. 기본값은 DB의 모든 원시 행을
읽어 publication과 대조한다. 최신 dataset 자동 선택, 레거시 Gold, 파일만으로의 오프라인 대체는 없다.

대규모 자료를 SSM으로 매번 전송하지 않으려면, 생성 시 동결한 **정확한 parquet 파일 경로**를
`snapshot_path`에 명시할 수 있다. 이것은 네트워크 전송 캐시일 뿐 신뢰 근거가 아니다.
매 호출마다 DB의 불변 metadata로 로컬 전체 행·정의·값 해시를 검증하고, 같은 트랜잭션에서
DB **전 행**의 PostgreSQL binary chunk hash와 비교한다. DB 연결 실패·dataset 부재·값 변경·스키마 불일치는
오류이며 로컬 파일로 fallback하지 않는다. 표본 일치만으로 통과시키지 않는다.

일반 파일이며 symlink가 아닌 `.parquet`만 허용한다. 정확한 Gold 7열 또는 라이브러리 출력 11열만 허용하고,
후자의 원천 버전·입력 해시도 DB와 대조한다. 반환은 `reference_id`, `definition_hash`, `asset_id`,
`stock_code`, `date`, `known_at`, `value` 7열이며 raw value의 방향을 다시 적용하지 않는다.
`reference_fields(...)`는 선택한 지표들의 outer union과 각각의 known-at를 제공하며, 결측은 그대로 남긴다.
편입 universe·거래일·총수익률·전략 승인에 관한 판단은 이 측정 조회와 별도로 검토해야 한다.

CLI: `python -m scripts.reference_library readback --dataset-id <정확한 dataset SHA256> --snapshot-path <동결한 values.parquet>`.
`--snapshot-path`는 `readback`에서만 허용한다. 생략하면 기존 DB 원시 행 전체 조회를 사용한다.

## 확장 v2: 가격 + DART FY 입력

`engine/reference_library_v2.py`는 `ALL_COLUMNS`의 정확한 feature-only 스키마만 받는다.
미래 수익·TR label·옛 팩터 열은 허용하지 않는다. 숫자형·유한값·분모·관측 수·역사적 asset identity·
월말 cutoff를 검사하고, 0개 유효값은 `NO_VALID_ROWS`로 남긴다. 단위와 추정식은
`FEATURE_UNITS`·`FEATURE_CONTRACTS` 사전과 정확히 일치해야 한다.

재무 어댑터 `engine/reference_financial_inputs.py`는 월말에 가용한 DART FY filing을 연결한다.
KRW, 정확 계정, CFS/OFS, filing/revision, 가용시각을 기록한다. 전년은 월별 행 shift가 아니라
동일 전년 결산기·동일 회계범위로 대응한다. 최신 FY의 최대 경과일은 550일이며, 누락·오래된 값·
불일치 계정은 사유와 함께 결측으로 남긴다. 현재 총자본/종목시총과 광의의 매출·기타 채권 등은
원형과 다른 새 ID로 등록하며 canonical B/M·순수 매출채권으로 가장하지 않는다.

자산·부채·자본이 모두 유효한 공시에서 `abs(자산−부채−자본) > max(1원, abs(자산)×10⁻⁶)`이면
해당 FY 묶음은 불확실 격리한다. 현재·전년 모두 적용하고 공시 메타와 시점은 보존한다.
반올림 가능성이 있으므로 원천 오류 확정으로 표시하지 않으며, 음수 자본 자체를 오류로 취급하지 않는다.

새 원천 유형은 `RDS_CERTIFIED_KRX_DART_FY_REFERENCE_V2`, 계약은
`KRX_PRICE_AND_EXACT_DART_FY_ASOF_V2`다. 다음 한계를 강제한다.

- `pit_status=PIT_ASSUMED_ACCEPTED_VINTAGE_NOT_FIRST_RELEASE_PROOF`
- `first_vintage_independently_verified=false`

as-of 연결·DQ 인증·해시가 있어도 최초 발표값의 독립 입증은 아니다. 가격과 재무 capture도 서로
별도의 불변 snapshot이며 공통 DB 빈티지로 가장하지 않는다. 초기 가격 전용 source-v1는 정확한
기존 7개 정의에만 허용해 재무 측정값의 출처로 재라벨할 수 없게 한다.

계산 API는 `calculate_one(panel, reference_id, attestation=...)`이며 `(values, summary)`를 반환한다.
`validated=True`는 발행기가 전체 입력을 이미 검증한 뒤 사용하는 **신뢰된 내부 성능 경로**다.
외부 호출자가 검증을 생략하는 용도로 사용하지 않는다. 측정 검증은 alpha 승인이 아니다.

## 확장 발행과 program-v2 collection

실행기는 `scripts/publish_reference_expansion.py`다. 순서는 완성된 capture의 `prepare` →
`calculate` → 그룹별 `publish-group`(실제 쓰기는 `--apply`) → `activation-plan`이다.
수익률 대신 사전 고정한 데이터 기준(새 정의별 100종목 이상·전체 관측 월 60개 이상)을 적용한다.
이는 모든 종목이 60개월 history를 갖거나 독립 경제 개념이 30개임을 뜻하지 않는다.

원천 수집은 `python -m scripts.reference_expansion fetch-price`와 `fetch-financial`로 실행한다.
각각 새로운 `--output` 경로와 월말 `--end`를 지정한다. 가격은 2015-01-01, 재무는
2013-01-01부터 요청하는 것이 기본이며, 실제 최초 보유일·가용일은 원천 manifest에 기록된다.
`python -m scripts.audit_reference_price_expansion --source <가격 경로>`의 원자료 표본 대조가
통과해야 `prepare --price-source ... --financial-source ... --output ...`를 진행할 수 있다.
부분 capture는 재사용하지 않으며, 완료된 원천은 재다운로드 없이 새 build에 재연결할 수 있다.
어댑터 의미가 바뀌면 이전 build의 입력을 그대로 발행하지 않고 새로운 경로에 다시 계산한다.

기존 7개의 원 dataset은 그대로 재사용한다. 새로운 발행은 **그룹당 최대 3개 정의**로 나눠
메모리·전송량을 제한한다. 각 그룹은 입력·정의·코드 해시, 전체 SQLite 공식 대조,
사전 고정 PostgreSQL 표본 공식 대조, Gold 전 행 binary readback, outer transaction commit을 기록한다.
완료 checkpoint를 재사용할 때도 실제 DB를 재조회한다. 전 그룹 commit과 재조회 뒤에만 활성화 제안을 만든다.
제안 파일 생성 자체가 활성 program 교체나 적재 완료 보고를 대신하지 않는다.

활성 program이 `phenomenon-program-v2`이면 같은 공개 API가
`engine.phenomenon_reference_collection.load_reference_collection`으로 분기한다.

```python
values, metadata = load_active_references(
    conn, repo_root,
    reference_ids=["kr_roa_fy_v1", "kr_momentum_12_2_price_v1"],
    snapshot_path=collection_cache_directory,
)
```

이 예제는 해당 ID들이 활성 program에 실제 등록된 뒤 사용할 수 있다. v2의 `snapshot_path`는
단일 파일이 아니라 `<dataset_id>.parquet` 파일들이 들어 있는 명시적 캐시 디렉터리다.
선택한 지표가 속한 **각 dataset 전 행**을 DB와 대조한 다음 선택 열만 반환한다. v1의 단일 파일
캐시 방식은 그대로 유지한다. 누락 그룹·잘못된 해시·DB 연결 실패를 파일로 우회하지 않는다.

collection metadata의 `dataset_id`는 **collection manifest 해시**이지 Gold 단일 dataset 키가 아니다.
`dataset_kind=REFERENCE_COLLECTION_NOT_A_GOLD_DATASET`, `reference_datasets`, `source_versions`를
함께 보존한다. `reference_fields`는 선택값과 개별 known-at를 outer union으로 연결하고 결측을 남긴다.
전략 universe·세션·수익률·실거래 승인은 만들지 않는다.
