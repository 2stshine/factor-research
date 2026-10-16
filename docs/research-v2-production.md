# 일반 연구에 연결한 v2 진단

> 2026-10-02 후속 입력 감사: TTM 연속성 계산을 수정해 실제 인증 원장으로 별도 패널을
> 재생했다. 후보 입력 이력은 여전히 부족하고 운영 가격 generation도 변경돼 새 패널은
> 미활성이다. [재무 입력 복구·재검증 기록](research-v2-fundamental-repair-20261002.md) 참조.
> 구형 재무 캐시는 새 실행 시 버전 계약 검사에서 차단되며, 기존 결과 파일은 보존한다.

기존 팩터 승인과 새 설명 절차는 서로 다른 책임을 가진다. 새 `campaign-start`는
`research/v2/production-policy.json`을 기본 동결하며 기존 캠페인에 소급 적용하지 않는다.
`--legacy-diagnostics`는 새 캠페인에서만 명시적으로 이전 경로를 선택한다.

## 실제 실행 순서

1. 현재 데이터 인증·경계·시행 이력을 확인하고 새로운 단일 가설과 계산식을 정한다.
2. 후보의 `RESEARCH_SPEC.diagnostic_plan`에 경쟁 설명을 구분할 경제 결과, 추가 통제,
   최대 두 매크로 축과 대비 상태, 비용 진단 필요성을 결과 전에 선언한다.
3. 새 캠페인은 일간 위험 기반 레짐·기존 매크로 원천·코드 hash를 동결한다. KOSPI와
   KOSDAQ은 각각 따로 분석한다. 입력 범위 밖은 UNKNOWN이다.
4. 후보별 기억 검색·사용 기록을 사전등록에 결합한다. 정확한 범위의 기억이 없으면
   빈 검색이 정상이다. 다른 범위의 절차적 교훈은 별도 제안·독립 비평 ACCEPT를 요구한다.
   비어 있지 않은 기억의 사용 이유를 자동으로 지어내지 않는다.
5. 기존 엔진이 후보를 한 번 평가한다. 같은 패널과 계산된 신호를 v2로 넘긴다.
   v2 때문에 후보를 다시 계산하거나 OOS를 열지 않는다.
6. `research/campaigns/<campaign>/v2/<epoch>/<factor>`에 원본·계약·준비 상태를 고정하고
   HOST_LLM 세션을 만든다. 호스트는 아래 명령으로 실제 진단을 선택·해석한다.
7. 본 캠페인을 기존 규칙대로 마무리한다. 통과 시 SQL parity와 일회성 confirmation을
   따르며, 미통과면 OOS는 미사용이다. 진단이 좋아도 후보를 승격시키지 않는다.
8. 종료된 캠페인과 실제 종료 결정을 기록한 진단 세션에서만 검토 bundle을 만든다.
   자료 요청·추가 검사 제안으로 끝난 세션도 관측 근거가 있어야 검토 가능하며, 미수행
   검사와 `explanation_complete=false`를 보존한다. 제안만 있는 빈 세션은 교훈이 아니다.
   해석자 초안과 별도 비평자의 실제 ACCEPT를 기존 release validator로 검증한다.
9. `activate-production`으로 새 검토본을 기억 DB에 추가하고 반환된 포인터 변경안을
   확인 후 적용한다. 이전 원문·검토·기억은 보존한다.

```bash
.venv/bin/python -m scripts.research_production packet --handoff PATH
.venv/bin/python -m scripts.research_production act --handoff PATH \
  --action action.json --request-id UNIQUE --expected-revision REVISION
.venv/bin/python -m scripts.research_production status --handoff PATH
.venv/bin/python -m scripts.research_production prepare-review --handoff PATH --output NEW_RELEASE
.venv/bin/python -m scripts.research_v2_release stage --release-root NEW_RELEASE \
  --draft-file lesson.json --critic-file critic.json
.venv/bin/python -m scripts.research_v2_memory --help
```

실행 중인 호스트가 실제 선택·해석·비평을 수행한다. 모델 API 공급자나 과금 키를
추가하지 않았으며 상시 서비스가 자동으로 연구를 반복한다고 표시하지 않는다.
생성된 세션만 있고 종료 결정이 없으면 진단 대기, 독립 비평이 없으면 검토 대기다.
`REQUEST_DATA`와 `PROPOSE_TEST`는 요청·제안을 기록하고 세션을 종료한다. 자료가 실제로
확보되거나 새 검사가 실행됐다는 뜻은 아니다. 모든 필요한 검사를 시도한 뒤 미확인을
정리하려면 `STOP`의 `NEEDS_DATA`/`INCONCLUSIVE`를 사용한다. 어떤 종료든 원인 확인과
교훈 검토 완료를 자동으로 뜻하지 않는다.

## 증거와 해석의 경계

- 기본 입력·관계·통제·국면 진단은 필수다. 경제적 주장과 실행 가능성 주장을 등록하면
  해당 진단도 필수이며 자료 부족을 미검증으로 남긴다.
- 금융 결과는 가설이 지정한 Silver 계정의 미래 수준/변화만 측정한다. 모든 재무 팩터에
  자동으로 ROA를 붙이지 않는다. 미래 회계연도 실적·기대 대비 서프라이즈와도 다르다.
- 당시 업종 자료나 현금흐름 계정이 연결되지 않으면 NOT_CONNECTED다. 조직 전체에
  그 데이터가 없다고 단정하지 않는다. 자료 수집 요청은 자동 구매/적재 권한이 아니다.
- 기존 월말 백테스트 비용 자료와 실제 다음 달 시가 체결은 별개의 계약이다.
  원래 모델의 보유·회전·비용 원본을 보존해도 실전 체결을 인증하지는 않는다.
- 시장별 표본·발생 구간 부족 상태를 합친 보고서에서도 유지한다. 한 시장에서 값이
  계산됐다는 이유로 다른 시장까지 충분하다고 하지 않는다. 매크로 조합 전수탐색은 없다.
- 입력 룩백은 후보 정의마다 달라진다. TTM 원천 이력과 수식 추가 시차를 따로 기록한다.
  기존 승인 성능의 공통 평가 시작일 및 36개월 hidden OOS는 이 연결 작업으로 바꾸지 않는다.
- 그래프 검색과 효용 가중치 학습은 여전히 꺼져 있다. 제한된 비교에서 우월성이 확인되지
  않았으며, 연결 구현을 이유로 효과가 검증됐다고 선언하지 않는다.

## 복구·재현

입력 파일은 임시 형제 디렉터리에 기록·검증한 뒤 완료 경로로 옮긴다. 중단된 임시 기록은
보존하며 완료 기록으로 취급하지 않는다. 원본 평가가 이미 유효하면 진단 오류 때문에
팩터를 재평가하지 않는다. 코드·정의·기억·레짐 변경은 등록/평가 전에 차단한다.
기존 완료 파일럿은 동결된 결과를 읽는 전용 경로로 공개할 수 있지만 새 코드로 몰래
재실행하지 않는다. 사이트는 검토된 스냅샷이며 자동 갱신 서비스와 구별한다.
새 운영 세션의 `status`·`export`·검토 원본 생성도 읽기 전용 SQLite와 원래 계약·파일·
감사 해시를 검증한다. 실행 코드가 바뀌어도 보존된 결과는 조회할 수 있지만 새 진단은
차단한다. 호스트에게 전달하는 입력 진단·필요 이력 등의 전체 문맥도 원래 세션 계약과
PROMPT 해시에 포함해, 화면에 전달한 내용과 감사 기록이 달라지지 않게 한다.

등록 사전검사는 assertion 전에 당시 계산한 입력/Gold 비교 artifact를
`research/campaigns/<id>/registration-preflight/<epoch>/<hash>.json`에 추가 전용으로 저장한다.
입력 부족으로 먼저 막히면 그 입력 근거와 Gold `NOT_RUN`을 남기고 DB 조회 전 종료한다.
원본 버전·후보·코드 SHA를 기록하며, 예외 원문/URL/자격증명을 저장하지 않는다. 이 기록은
등록 승인이나 수익률 평가가 아니다. 이미 유실된 과거 실패 값을 소급 복원하지 않는다.

방법 근거는 [실제 진단 방법 결정](research-v2-method-decisions-20261002.md),
기억 범위 전이는 [기억 전이 계약](research-v2-memory-transfer.md)을 따른다.

## 도입 검증 기록 — 2026-10-02

실패 체크포인트 보완까지 포함한 최종 `.venv/bin/python -m pytest -q`: **1,976 passed**, 222.16초.
새 입력·기억·국면 연결, 기존 승인 결과 불변성, 후보 소스/계약 변경 차단, 원본 보유·비용
대조, 전달 패킷 감사 일치, 불완전 종료 검토, 코드 변경 후 읽기 전용 보존 결과 조회,
입력/Gold 사전검사 실패의 원본 보존·경로 탈출/덮어쓰기 방지를
포함한다. 이는 소프트웨어 검증이지 경제적 원인·연구 성과 개선·독립 OOS의 증명은 아니다.

실행 계획은 `research/v2/production-adoption-plan-20261002.json`에 있으며, 수익률 평가 전
운영 검토에서 발견한 보완 사항은 `research/v2/production-adoption-restart-20261002.json`에
기록했다. 원 캠페인과 코드 동결 계약을 덮어쓰지 않고 `CLOSED_ABORTED / OOS NOT_USED`로
보존했다. 수정 버전도 같은 단일 후보·계산식·방향을 사용하며, 후보 대체나 성과 기반 튜닝을
허용하지 않는다. 커밋·운영 사이트 배포·Gold 적재는 이 도입 검증에 포함하지 않는다.

수정 캠페인 `v2-production-20261002-cost-intensity-v2`의 **수익률을 보지 않은 입력 분포**는
다음과 같다. 신호월 2018-03~2023-06의 64개월이며, 전체 레짐 입력의 분류 수이지 후보별
유효 표본·독립 국면 발생 수·국면별 효과 검증 결과가 아니다.

| 시장 | 상승·저위험 | 상승·고위험 | 하락·저위험 | 하락·고위험 | 미분류 |
|---|---:|---:|---:|---:|---:|
| KOSPI | 17 | 9 | 11 | 27 | 0 |
| KOSDAQ | 20 | 11 | 10 | 23 | 0 |

동결 원본의 `PIT_ASSUMED`, `historical_pit_verified=false`, `calendar_verified=false`는
그대로다. 이 표로 역사적 최초 발표본·실제 가용시각을 검증했다고 주장하지 않는다.

### 실제 신규 후보 실행 결과

`operating_cost_intensity`의 같은 동결 Discovery 입력 검사에서 coverage는 **91.97%**,
월별 coverage 하위 십분위는 **90.19%**로 PASS였다. 원래 승인 기억을 독립 검토한 절차적
전이 한 건을 실제 검색·읽기·사용 기록에 연결했다. 후보 정의와 방향·기간은 바꾸지 않았다.

그러나 `epoch-start`의 **Gold 신호 상관 사전검사에서 FAIL**했고, 캠페인을
`CLOSED_ABORTED / OOS NOT_USED`로 닫았다. 이 검사는 매월 공통 유효 종목이 최소 30개인
비교를 사용해 비교 월 36개월 이상 및 월별 절대 Spearman 중앙값 0.70 이하를 요구한다.
당시 CLI는 assertion 실패 전에 상세 artifact를 보존하지 않았으므로, 이번 메시지만으로
상관 초과·비교 월 부족·둘 다를 구분할 수 없다. 구체 상관값이나 상대 팩터를 추정하지 않는다.
확인 가능한 사실은 `research/v2/production-cost-intensity-preflight-failure-20261002.json`에
남겼으며, 이후 실패도 상세 원본을 남기도록 CLI를 보완했다. 이 보완으로 당시 유실된
구체 수치가 복구됐다는 뜻은 아니며 실제 후보를 다시 실행하지 않았다.

따라서 이번 **신규 후보 등록·수익률 평가·실데이터 운영 진단 세션·신규 실증 교훈은 모두
0건**이다. 기존 여섯 파일럿과 코드/합성 회귀 검증을 신규 연구의 전 과정 실증 완료로 세지 않는다.
전체 연결 코드의 도입과, 이 새 경로로 끝까지 완료된 새로운 실증 연구는 다른 상태다.
후보 대체·임계값 완화·Gold 적재·커밋은 하지 않았다.

느린 부분은 진단 에이전트가 아니라 기존 승인값 대조였다. 읽기 전용 통계에서
`gold.factor_value`는 약 2.37억 행·41GB, APPROVED는 49개였다. 소규모 synthetic key의
`EXPLAIN`에서는 기본키 역방향 Index Scan과 LIMIT 1을 사용했다(ANALYZE 미실행).
타깃 자산·월마다 승인 팩터 수만큼 인덱스/테이블 페이지를 읽는 구조가 긴 IO 대기와
부합한다. 명백한 전체 스캔 오류는 확인되지 않았으며 DB·인덱스·승인값은 수정하지 않았다.

### 로컬 대시보드 검증

`output/research-dashboard-source/production-v2-20261002-final-audit.json`과 배치 파일의
바이트가 일치한다. 생성 기록 2건·등록 전 중단 2건·등록 후보/진단/새 해석 0건을 표시한다.
기존 여섯 파일럿 JSON 해시 `dee7dd18c48f35728d77f78faac3c0d21455f0fd65f008e57110e3246a574d6c`는
그대로 유지했다. Node 정적 검사와 실제 Chrome 데스크톱/모바일 검증을 통과했고,
1180/768/390px에서 페이지 가로 넘침이나 JavaScript 오류가 없었다.
근거는 `output/production-v2-ui/production-browser-verification.json`과 같은 폴더의 화면이다.
로컬 확인 URL은 `http://127.0.0.1:4173/#research-v2`이며 운영 Vercel에는 배포하지 않았다.

### 추가 실데이터 E2E 검증 — 2026-10-02 05시 KST

[후속 검증 보고서](research-v2-e2e-validation-20261002.md)에 과거 실패의 읽기 전용
재측정과 새 단일 후보 검증을 기록했다. 비용집약도는 현재 Gold 49개 모두 64개월 비교가
가능했고, `current_asset_turnover` 0.706418 및 `revenue_to_noncurrent_assets` 0.794530의
월별 절대 Spearman 중앙값으로 중복 기준을 초과했다. 이는 과거 유실 원본의 복구가 아니라
동일 후보/Discovery 입력에 대한 **새 측정**이다.

새 매출 성장가속도 후보는 전체 coverage 66.43%지만 월별 하위 십분위 0%로 입력 단계에서
막혔다. Silver 초기 분기 이력 부족과 별개로 TTM 분기 연속성 결함을 합성 입력에서 재현했다.
실제 데이터 영향과 수정은 미완료다. 새 캠페인은 등록·수익률 평가 없이 중단했고,
신규 운영 진단·실증 교훈은 여전히 0건이다. 기존 동결 입력·Gold·활성 기억은 변경하지 않았다.
