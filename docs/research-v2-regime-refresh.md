# 연구 v2 시장지수 갱신과 월 완료 계약

2026-10-01에 기존 S3 Bronze의 KOSPI/KOSDAQ 일별 원본을 로컬에 연결하고 새 shadow를 실행했다.
일별 63/21 수익률, 10개월 추세, 이전 12개월 위험 기준은 변경하지 않았다.
팩터 수익·봉인 결과·DB는 읽지 않았고 활성 registry와 기존 캠페인은 변경하지 않았다.

## 실제 갱신

원본은 기존 버킷 `soma-quant-bronze-31-159372032315-ap-northeast-2-an`의
`index/krxapi/date=2026-07-*`, `2026-08-*`, `2026-09-*`에 있는
`kospi.parquet`와 `kosdaq.parquet`만 사용했다. provider API 재호출은 0회다.

| 검사 | 결과 |
|---|---:|
| 내려받아 대조한 원본 | 124개 |
| 로컬에 없어서 추가한 파일 | 100개 |
| 이미 존재하며 SHA가 동일한 파일 | 24개 |
| 기존 내용과 충돌·덮어쓴 파일 | 0개 |
| 시장별 7/8/9월 관측일 | 22 / 20 / 20일 |
| 최신 원본 거래일 | 2026-09-30 |

기존 `daily_full._download_keys`와 같은 boto3 bucket/key 전송 방식을 사용하되,
새 artifact 디렉터리에 먼저 받은 뒤 로컬 대상은 exclusive create로 추가했다.
기존 파일은 SHA를 비교하고 다른 경우 보존하도록 했다. 다운로드 전후 S3 ETag·크기를 대조했다.
수신 시작·완료 시각, S3 LastModified·ETag·version ID, byte 수, 원본/로컬 SHA와 경로는
[retrieval-manifest.json](../output/research_v2_preflight/regime-refresh-20261001-v1/retrieval-manifest.json)에 있다.
실제 이번 수신 시각과 S3 변경시각은 역사적 최초 공개시각으로 사용하지 않는다.

## 9월 완료 여부

기본 compiler가 사용하는 `monthly_rows`는 후속 월의 원본 거래일이 있어야 직전 월을 완료로
취급한다. 10월 1일 S3 prefix는 비어 있었다. 따라서 새 데이터로 기본 실행한
[conservative 결과](../output/research_v2_preflight/regime-refresh-20261001-v1/shadow-conservative.json)는
8월까지 계산하고 9월을 UNKNOWN으로 남긴다. 이는 원본이 9월 30일까지 없다는 뜻이 아니다.

shadow compiler에만 선택적 `--completion-contract`를 추가했다. 기존 upstream 수집 경로가 쓰는
`exchange_calendars` 4.13.2의 XKRX 달력에서 **2026년 9월** 예상 거래일 20개를 별도 생성했다.
두 시장 원본과 로컬 달력에 각각 정확히 같은 20일이 있는지 확인했다. 이 버전의 달력 구현 SHA,
package 버전, 예상 날짜, 실제 원본 대조는 [calendar-evidence.json](../output/research_v2_preflight/regime-refresh-20261001-v1/calendar-evidence.json)에 동결했다.
[completion-contract.json](../output/research_v2_preflight/regime-refresh-20261001-v1/completion-contract.json)은
그 evidence SHA와 두 시장·완료월을 결합한다.

옵션은 기본적으로 제외된 바로 다음 한 달에만 적용되며 부분월·미래월, 시장 불일치,
evidence 변조, 중복 날짜, 누락/추가 거래일, 가격 관측일 자체로 만든 달력을 거부한다.
`monthly_rows` 전역 동작과 `engine/regime_shadow.py`는 변경하지 않았다.

이것은 **버전이 명시된 라이브러리 달력에 근거한 9월 완료 판단**이다. 전체 역사 거래일 달력의
거래소 인증이나 원본 최초 빈티지 검증을 뜻하지 않는다. `calendar_verified=false`,
`PIT_UNKNOWN`, `EXPERIMENTAL_SHADOW_NOT_APPROVED`를 유지한다. 역사적 가용시각은 기존
일별 관측일 KST 종료 가정이며 실제 receipt와 구분한다. 기존에 수용한 매크로 PIT 가정을
재검증하라는 조건을 추가하지 않았다.

7월까지 라이브러리 달력을 기계적으로 확대하면 7월 17일을 예상 거래일로 포함하는 차이가 있다.
[KRX의 제헌절 운영 공지](https://strn.krx.co.kr/corebbs5/BHPSTRN0401/view?bbsSeq=146)는 그날의 휴일을 명시한다.
이 차이는 [calendar-limitations.json](../output/research_v2_preflight/regime-refresh-20261001-v1/calendar-limitations.json)에
기록했고, 라이브러리·과거 로컬 달력·공식은 수정하지 않았다. 9월 한 달의 정확한 대조를
전체 과거 달력 인증으로 확장해서 해석하지 않는다.

## 결과와 검증

[명시적 완료 계약 적용 결과](../output/research_v2_preflight/regime-refresh-20261001-v1/shadow-completed.json)의
141개월 중 시장별 126개월이 READY_SHADOW이고 초기 15개월은 UNKNOWN이다.
9월은 KOSPI UP_HIGH, KOSDAQ DOWN_HIGH다. 연율화 RV63은 각각 약 67.55%, 53.37%이며
이는 입력 기반 연속 위험 진단이다. HIGH/LOW는 이전 12개월 대비 상대 구분이고 미래 수익 판단이 아니다.

기존 artifact의 2015-01~2026-06 **138개월**은 각 시장에서 값·입력 hash까지 그대로였다.
이번 기본 실행과 완료 계약 실행은 9월 전 **140개월**이 완전히 일치한다.
공식 hash도 기존 결과와 같다. 로컬 파일과 별도 내려받은 원본의 SHA 대조 248건을 통과했다.
[verification.json](../output/research_v2_preflight/regime-refresh-20261001-v1/verification.json)에 모든 artifact·compiler·engine hash와
검사 결과를 남겼다. `tests/test_regime_shadow.py`의 기존 14개 및 새 11개, 총 **25개 테스트가 통과**했다.

활성 연구 국면 채택이나 실데이터 팩터 실행까지 완료됐다는 결과가 아니다.
다음 단계는 해당 실험 방법·가용시각·달력 범위를 새 진단 입력 계약에 결합하는 것이다.
기존 캠페인의 국면이나 판정 결과를 덮어쓰지 않는다.

## 재현

`--data-dir`는 **data 루트**다. 내부에서 `index/krxapi`를 붙이므로 그 하위 경로를 전달하지 않는다.
출력 파일은 존재하지 않는 새 경로를 사용한다.

```sh
.venv/bin/python -m scripts.research_regime_shadow \
  --data-dir /Users/mac/Documents/GitHub/TeamAlpha-data/data \
  --as-of 2026-10-01 \
  --completion-contract output/research_v2_preflight/regime-refresh-20261001-v1/completion-contract.json \
  --output output/research_v2_preflight/regime-refresh-reproduction.json

.venv/bin/python -m pytest tests/test_regime_shadow.py -q
```

선택 옵션을 빼면 보수적 8월 완료 경로를 재현한다. artifact 디렉터리의 `refresh.py`,
`calendar_evidence.py`, `verify.py`는 이번 유한한 작업의 재현 소스이며 기존 artifact를
덮어쓰지 않도록 설계했다. 새 실행에는 새로운 디렉터리를 사용해야 한다.
