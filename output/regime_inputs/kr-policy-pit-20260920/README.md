# 사용 가능한 한국 정책금리 레짐 입력

## 결과

한국 기준금리의 **월말 3개월 방향** 입력 1개를 범위 한정 승인하고 실제 연구 입력 경로에 등록했다.
FMP 원본 전체나 모든 37계열에 대한 승인이 아니다. 나머지 36계열의 역사적 사용 승인은 유지 보류다.

| 항목 | 결과 |
|---|---|
| 입력 ID | KR_POLICY_DIRECTION_3M |
| 승인된 월 | 2015-01 ~ 2026-08, 140개월 |
| 인상 / 변화 없음 / 인하 | 28 / 82 / 30개월 |
| FMP 원본 대조 | 정확한 S3 backfill 105행 모두 공식 금리와 일치 |
| 정제된 결정 | 103건, 중복 초과 2행은 원본을 남기고 동일 결정으로 결합 |
| 날짜 정규화 | 36행의 provider 날짜를 대응하는 공식 발표일로 정규화 |
| 공식 문서 | 2014년 워밍업 포함 결정문 115건, 연도별 공식 일정 13개 |
| 교차검증 | 금리 변경 27건을 공식 시행일 금리표와 추가 대조 |
| S3 재검증 | 매크로 141 partition, 선택 1,932행의 원본·선택본·수집시각 재검증 |
| 실제 경로 확인 | read_context → freeze_context → campaign_context, 140행 전달 성공 |
| 저장 | 로컬 불변 Silver 정제 artifact. RDS/S3 Silver 게시 아님 |
| 실제 팩터 평가 / 기존 캠페인 수정 | 없음 / 없음 |

## 무엇을 승인했나

승인 대상은 **공식 결정문과 일치하는 공표 목표금리** 및 아래 고정 월별 분류뿐이다.
원본의 정확한 발표 시각, estimate/previous, 통계 대상월 표기, 다른 매크로 수치는 승인하지 않는다.

- 판단월 t 말까지 공표된 마지막 정책 목표금리를 사용한다.
- t 말 금리 - t-3 말 금리가 양수면 `TIGHTENING`, 0이면 `UNCHANGED`, 음수면 `EASING`.
- 분류는 후보 수익률을 읽지 않고 정의했다. 최적화된 매매 신호나 금리 수준의 높고 낮음이 아니다.
- t 상태는 t+1 성과 진단에만 사용한다. 9월은 미완료 월이므로 입력에 추가하지 않았다.
- 새 결정 전까지 기존 목표금리가 유효하다는 정책 결정의 의미에 따라 유지한다.
  다른 통계의 결측값을 일반적으로 forward-fill하도록 허용한 것이 아니다.
- 2014년 공식 결정은 3개월 워밍업 근거로만 사용했다. 2014년 FMP 보유를 주장하지 않는다.

## 발표일·발표시각·수집시각을 구분한 승인 v2

공식 발표문 표제의 날짜와 결정문 본문을 대조했다. 발표문의 목표금리는 경제통계의 최신 수정값을
과거에 덮어쓴 계열이 아니라 당시 정책 결정의 기록이다. 원본 PDF·수신시각·SHA256을 보존했다.
현재 공식 아카이브의 기록을 근거로 삼았으며 2015년에 직접 수집한 암호학적 증명을 갖고 있다는 뜻은 아니다.

정확한 발표 초/분은 확인하지 못했으므로 `publication_time_verified=false`를 유지한다.
대신 **공식 발표일의 23:59:59 Asia/Seoul**을 가용시각의 보수적 상한으로 기록한다.
월별 `known_at`은 해당 월말 23:59:59로 두어 월중에 최종 월말 상태가 알려졌다고 처리하지 않는다.
이는 실제 발표시각을 날조하거나 FMP 날짜에 임의로 며칠을 더해 승인한 것이 아니다.

`pit-regime-approval-v2`는 다음에 한정된다:

- 공식 일자 검증된 정책금리, 월말 진단, 공표 목표금리라는 의미.
- `publication_date_verified=true`, `historical_availability_verified=true`.
- `revision_basis=DATED_OFFICIAL_POLICY_DECISIONS`: 승인은 이 결정 목표금리 필드만 다룬다.
- 장중 사용·팩터 feature 사용은 false. FX·ETF·통계 수정값에 이 예외를 재사용할 수 없다.
- 기존 v1의 정확한 시각 및 수정 이력 검증 요건은 변경하지 않았다.

특히 2020-03-16 발표문은 2020-03-17 시행을 명시한다. 공표 목표금리는 16일에 알려진 결정이며,
그날 이미 시행 중인 금리라고 표현하지 않는다. `ANNOUNCED_POLICY_TARGET`이라는 별도 의미를 유지한다.
2017-11-30처럼 월말 당일에 공표한 변경도 당일 종료 후 월말 판단에는 포함된다.
대표적인 두 문서는 PDF 렌더링으로 표제 날짜와 목표금리·시행일을 육안 확인했다.

## 실제 사용 경로

`research/regime_sources.json`에 이 입력의 SHA256을 등록했다.
앞으로 `scripts.research campaign-start`를 실행할 때 기본으로 읽고 새 캠페인 안에 복사·동결한다.
등록 파일 또는 context/approval가 바뀌면 해시 검증으로 차단하며 조용히 입력을 생략하지 않는다.
이미 생성된 캠페인에는 소급 삽입하지 않는다. OOS·embargo 구간 제외도 기존대로 적용된다.

특정 새 캠페인에서 제외하려면 `--no-regime-context`, 다른 승인 입력을 지정하려면
`--regime-context /absolute/path/context.json`을 사용한다. 둘은 동시에 지정할 수 없다.

시장지수는 아직 별도 승인 입력이 없으므로 시장 추세·변동성 부분은 미수집 상태다.
한국 정책금리 축만 사용 가능하며 전체 진단이 모두 AVAILABLE이라고 표시하지 않는다.
승인 종료 월 이후 새 관측은 자동 생성하지 않는다. 새 공식 결정 대조와 새 버전 심사가 필요하다.

## 파일

- `silver/context.json`: 실제 입력.
- `silver/approval.json`: 출처·범위·시점 정책·검토자·전체 source hash에 묶인 승인서.
- `silver/resolved_decisions.json`: 공식 결정과 모든 해당 FMP 원본행의 대응표. 중복·원래 시각도 보존.
- `silver/checks.json`: 실측 검증 수치.
- `silver/wiring_check.json`: 실제 어댑터 전달 검사. 캠페인 생성이나 팩터 평가가 아님.
- `official/decisions-v2.json`: 전체 공식 발표문 색인, 원문 URL·날짜·목표금리·해시.
- `official/calendar-YYYY.html`, `official/decisions/`: 공식 근거 원문과 수신 기록.
- `bronze_policy.json`, `bronze_mirror/`: 정확한 S3 원본의 읽기 전용 로컬 사본과 검증 기록.

원래 Bronze·과거 검사 보고서·보류 원장은 바꾸지 않았다. 이 정제 버전이 좁은 범위의 후속 승인이다.
공식 출처는 [한국은행 연도별 결정 자료](https://www.bok.or.kr/portal/singl/crncyPolicyDrcMtg/listYear.do?menuNo=200755&mtgSe=A)와
[한국은행 기준금리 시행일 이력](https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643)이며,
각 PDF의 정확한 URL과 해시는 색인 및 승인서에 기록했다.

## 검증 결과

- 정책 정제·입력 승인·진단 연결 관련 테스트 108개, epoch·교훈·연구 불변조건 회귀 테스트 160개:
  **합계 268개 통과**.
- 실제 registry → context → approval → 공식 근거의 해시를 다시 확인했다.
- 실제 승인 입력에 별도의 테스트 경계(data cutoff 2023-06-30, OOS 시작 2023-07)를 적용했을 때
  2023-05까지 101개월만 남고 이후 39개월이 제외됨을 확인했다. 실제 캠페인/OOS를 읽은 검사가 아니다.
- 원래 S3 Bronze manifest의 `pit_approved=false`가 그대로 유지되는 것을 확인했다.
- 전체 시장 레짐·팩터 성과는 산출하지 않았다. 이 검사는 승인된 금리 축의 실제 전달 가능성을 확인한다.

## 재현

```sh
# 읽기 전용 S3 원본 확보. AWS role credentials는 메모리에서만 사용한다.
.venv/bin/python -m scripts.prepare_bok_policy --fetch-s3 --output NEW_DIRECTORY

# pypdf가 있는 bundled Python으로 공식 기록 수집/추출.
BUNDLED_PYTHON -m scripts.prepare_bok_policy --fetch-bok --output NEW_DIRECTORY

# 모든 근거 검증 후 이 고정 snapshot 범위의 승인/정제 artifact 생성.
.venv/bin/python -m scripts.curate_bok_policy --input NEW_DIRECTORY \
  --rate-history output/pit_audit/fmp-20260920/evidence/bok_rates.html \
  --reviewer REVIEWER_NAME
```

기존 Silver 디렉터리는 덮어쓰지 않는다. FMP API 추가 호출은 없으며 키를 코드에 넣지 않았다.
공식 PDF를 새로 작성하거나 수정하지 않았다. `factor-research-loop`의 봉인 경계와
PDF 스킬의 원문 추출·시각 확인을 적용했다.
