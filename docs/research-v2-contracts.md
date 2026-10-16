# 연구 v2 구현 계약

작성일: 2026-10-01 · 상태: **제안 계약. 아래 모듈·명령·상태는 구현되었다는 뜻이 아니다.**

후속 구분: [선행 검토](research-v2-data-regime-review.md)에서 주장별 메타데이터 준비 검사, 룩백 계획기, 별도 일별 레짐 shadow를 추가했다. 아래 전체 실행·권한·기억 계약은 아직 적용하지 않았다. 특히 아래 최초 국면 후보의 확장 24개월 기준과 후속 shadow의 rolling 12개월 기준은 다른 실험 버전이다.

추가 구현: [적응형 진단 실행기](research-v2-adaptive-runtime.md)에 합성 전용 행동·예산·증거 이력과 호스트 LLM 연결을 구현했다. 실제 데이터 권한 격리·ReleaseGroup·기억 학습·운영 전환까지 구현한 것은 아니다.

[설계 개요](research-v2-design.md) · [논문 반영 근거](research-v2-paper-review.md)

## 1. 우선순위와 불변 조건

우선순위는 권한·데이터 적합성 → 재현 가능성 → 올바른 연구 판단 → 이전 가능한 교훈 → 효율이다. IC, 승인율, 기억 개수, 그래프 크기를 전체 시스템의 최적화 목표로 삼지 않는다.

다음 불변 조건은 에이전트나 효용 학습이 변경할 수 없다.

1. 단일 trial의 수식·방향·입력·변환·대상·평가 창·주된 endpoint·검정 규칙은 실행 전에 해시로 동결한다.
2. 결과를 본 뒤 변경하면 `parent_trial_id`를 가진 새 trial이다. 무효화·실패·중단도 누적 원장에 남긴다.
3. 검색·graph traversal·요약·임베딩·효용이 접근 제한을 우회하지 못한다.
4. 검증 창의 노출은 팩터·전략·프로그램을 가로질러 중앙에서 관리한다.
5. 증거 파일은 불변, 해석은 버전 관리, 조회 뷰는 재생성 가능해야 한다.
6. 원래 evidence root가 같은 여러 문서는 독립 근거가 아니다.
7. 에이전트의 해석은 결정론적 판정 결과를 수정할 수 없다.
8. 연구 승인, 독립적 증거 등급, 실제 사용 권한은 서로 다른 필드다.
9. 누락된 자료·불충분한 표본은 미산출/미확인이다. 0 또는 성공으로 대체하지 않는다.
10. legacy 기록을 비활성화해도 전역 노출·시도 원장은 초기화하지 않는다.

## 2. 프로그램·검증 창·trial의 범위

| 객체 | 책임 | 필수 식별/동결 필드 |
| --- | --- | --- |
| EvaluationWindow | 데이터 구간과 노출 상태 | signal/return bounds, dataset snapshots, exposure events, scope |
| ReleaseGroup | 같은 창을 쓰는 연구들의 공동 동결 | window IDs, program IDs, final trial IDs, selection rule, evaluator hash, memory snapshot, freeze time |
| ProgramPlan | 연구 질문과 탐색 예산 | hypothesis families, allowed development scope, trial/time/token caps, stopping rule, primary criteria |
| TrialContract | 단일 팩터·한 번의 사전등록 | definition hash, design contract, parent, available inputs, endpoint, planned diagnostics, retrieval receipt |
| Run | 동일 계약의 실행/재현 | environment/code/data hashes, actual inputs, status, artifact IDs |

Program은 개발 중 후보를 추가할 수 있지만 등록한 예산과 범위를 넘으면 새 계획 승인이 필요하다. ReleaseGroup에는 최종 검증에 들어갈 후보를 모두 동결한다. 결과가 마음에 드는 것만 공개할 수 없다.

한 EvaluationWindow의 일부 결과라도 공개되면 노출 사건을 기록한다. 같은 시점 전에 완전히 동결되고 접근이 격리된 다른 후보는 동일 그룹의 일괄 검증으로 처리할 수 있다. 이미 본 결과를 반영해 바꾼 후보는 그 창에서 독립 검증 자격이 없다. “사전등록 파일이 존재했다”는 사실만으로 독립성을 인정하지 않는다. 이후 같은 기간을 사용하는 별도 역사 재사용 ReleaseGroup은 허용한다. 공동 동결 의무가 미래의 모든 연구를 미리 등록하라는 의미는 아니다.

노출 메타데이터에는 최소 다음이 필요하다.

```text
window_id, dataset_version, market/universe,
signal_start/end, return_support_start/end,
first_global_exposure_at, exposure_event_ids, prior_program_ids,
definition_frozen_at, evaluator_frozen_at, memory_frozen_at,
used_in_this_development, scoped_blindness,
independent_evidence, confirmatory_error_control_claim
```

과거 재사용 검증은 마지막 두 Boolean이 기본 `false`다. 기간 일부가 새로 생겼다고 전체 36개월이 새로운 것은 아니다. 데이터가 미노출인지 확인할 수 없으면 “미노출 미확인”으로 기록한다.

### 구간 생성 규칙

- 데이터 인증 manifest의 실제 가용 기간에서 시작한다. README의 날짜나 오늘 날짜로 추정하지 않는다.
- 월별 신호, 실제 미래 수익률 지원 구간, 입력 lookback을 따로 계산한다.
- 내부 개발 비교는 시간 순서의 expanding/walk-forward 블록을 계획 단계에서 고정한다. 그 결과도 개발자가 보면 개발 정보다.
- embargo/purge는 최소한 목표 수익률의 겹침과 데이터 발표·체결 지연을 반영한다. 검증 입력의 과거 lookback 자체를 전부 버릴 필요는 없지만 미래 label이 개발에 들어오면 안 된다.
- 현 프로토콜의 36 유효 OOS 월 요구를 쓸 때는 실제 유효 월과 지원 수익률을 확인한다. 전향 검증도 36개월 기준을 충족하기 전에는 같은 장기 통과 표지를 주지 않는다. 중간 관찰은 가능하지만 그것으로 정의를 바꾸면 새 동결 시점부터 평가한다.
- 미래 36개월을 기다리지 않고도 개발·연구 라이브러리·모의 전략을 진행할 수 있다. 그 증거와 사용 등급을 정확히 표시한다.

## 3. 평가와 승인 계약

초기 v2의 주된 endpoint는 고정 방향의 월별 횡단면 rank IC다. 현 `engine/gate.py`의 기준은 호환 adapter로 재사용한다. 기준 수치를 현재 성과를 보고 낮추거나 바꾸지 않는다.

기준마다 평가 목적을 구분한다.

| 검사 | 의미 | 해서는 안 되는 해석 |
| --- | --- | --- |
| 정의·SQL parity | 구현이 등록된 점수를 재현함 | 경제적 유효성을 증명함 |
| 개발 IC·안정성 | 허용된 개발 자료에서 관찰된 관계 | 미노출 자료에서 재현될 것이 보장됨 |
| 가족 단위 BY 등 보정 | 명시된 검정군의 통계적 처리 | 모든 적응적 탐색 편향이 제거됨 |
| 과거 재사용 고정 검증 | 동결된 정의의 역사적 안정성 확인 | 새로운 독립 OOS 통과 |
| 전향 검증 | 동결 후 새 자료의 관찰 | 충분한 기간·표본 없이 장기 지속성 확정 |
| 거래 구현 검증 | 주문·체결·비용·권리 계산의 적합성 | 실제 체결 또는 미래 실전 수익 보장 |

최종 후보의 선택 규칙은 점수순 임의 선택이 아니라 사전등록 기준으로 정한다. 모든 시도 수와 변형 계보는 보고한다. 적응적으로 생성된 가설에 계산한 p/q 값을 기록할 수 있지만, 그 조건에서 이론상 오류율 통제가 성립한다고 별도로 입증하지 못하면 그렇게 광고하지 않는다.

승인 필드는 다음처럼 분리한다.

```text
library_status = IN_PROGRESS | APPROVED | REJECTED
evidence_grade = HISTORICAL_REUSED | HISTORICAL_SINGLE_USE | PROSPECTIVE
prospective_status = NOT_STARTED | ACCRUING | PASS | FAIL | INCONCLUSIVE
usage_scope = RESEARCH_ONLY | PAPER_STRATEGY | LIVE_APPROVED
decision_policy_version, decision_artifact_id, decided_at
```

`library_status`는 연구 라이브러리의 판정이다. `usage_scope`의 기본값은 `RESEARCH_ONLY`다. 예전 Gold의 APPROVED를 읽는 것만으로 실전 전략에 들어갈 수 없게 downstream contract를 바꾼다. legacy 행에 새 필드가 없으면 실전 권한을 추정하지 않는다.

### `research-admission-v2` 검사 집합

이는 기존 `Verdict.PROMOTE`를 그대로 번역한 값이 아닌 새 정책이다. 초기 숫자 문턱은 `fr-3.16.0`의 해당 기준을 유지하되 검사 이름과 증거 의미를 분리한다. 실제 adapter는 아래 범주 안의 각 check ID·필수 여부·임계값을 코드의 고정 manifest로 열거해야 하며, 알 수 없는 신규 check는 조용히 무시하지 않는다.

| 검사 범주 | 연구 승인 필요 여부 | 초기 처리 |
| --- | --- | --- |
| 정의·입력·인과성·결정성(T0), 표본·label 계약(T1) | 필수 | 기존 검사 유지. 현재 PIT 정책을 임의로 VERIFIED로 승격하지 않음 |
| 개발 표본·IC·투자가능 IC·ICIR(T2) | 필수 | 최소 60 유효 월 등 현 기준 유지 |
| 사전등록 중립화(T3.2), 구간·국면 안정성 | 필수 검사/진단 구분 | T3.2는 필수. 나머지는 정책에 선언한 진단으로 남기며 좋은 결과만 골라 표시하지 않음 |
| 시도 원장·가족 단위 보정(T4 관련) | 필수 수행 | 기존 수치 선별 기준은 유지. 적응적 연구에 대한 보장되지 않은 FDR 통제 주장은 금지 |
| 동결한 역사 검증 창 | 필수 | 최소 36 유효 월, `IC >= max(0.02, 0.5 × 개발 IC)` 등 호환 기준 적용. 재사용이면 그 등급을 명시 |
| 기존 라이브러리·배치 후보 중복/직교성(T5 및 batch) | 필수 | 비교 catalog를 사전 동결. legacy 기본 비교군도 명시하여 불리한 기존 후보를 사후 삭제하지 않음 |
| Python/SQL parity, 증거 bundle·독립 검토 | 필수 | 재현·근거 연결이 없으면 승인 안 함 |
| 미노출성·전향 36개월 결과 | 연구 승인과 별도 | 안 했으면 NOT_EVALUATED. 역사 검증 통과로 대신 PASS 처리 금지 |
| 실제 월초 체결·실전 사용 승인 | 연구 승인과 별도 | 전략 입력·기간·체결 계약으로 판단 |

현재 null 보정 산출물이 새 적응적 연구 전체를 검증했다고 간주하지 않는다. 재사용 가능한 평가기 수준의 검증과 v2 전체 선택 과정의 검증 범위를 분리해 기록하고, 새 전체 오류율 통제 주장은 별도 검증 전까지 하지 않는다.

필수 검사에 실패하면 탈락, 필수 자료/검사가 미완료이면 진행 중이다. 모든 필수 검사 통과 후 연구 승인이다. 초기 역사 검증 36개월을 갖출 수 없는 새 데이터 팩터는 IC 탐색·교훈 축적은 할 수 있지만 이 정책의 최종 연구 승인은 하지 않는다. 전향 36개월을 기다릴 필요가 없다는 것과 검증 표본 요구를 없애는 것은 다르다.

유효 월 수는 사전 동결한 달력 구간 안에서 판단한다. 결과를 본 뒤 부족한 표본을 채우려고 검증 창을 늘리거나 옮기지 않는다. 자료/실행 미완료와, 완료된 검사에서 후보가 기준을 충족하지 못한 경우를 구분한다. `NOT_EVALUATED`는 개별 검사의 상태이며 전향 검증 워크플로의 `NOT_STARTED`와 별개다.

`RESEARCH_ONLY` 팩터를 모의 전략으로 넘길 때도 별도 StrategyTrial의 입력 identity·기간·사용 capability가 필요하다. 승인 판정만으로 새 데이터나 다른 검증 창에 접근할 수 없다.

입력 오류가 확인된 실행은 `INVALID`로 분리하고 경제적 반증으로 세지 않는다. 해결되지 않은 자료 부족은 작업 상태 `BLOCKED`/`NOT_COMPUTED`이며 승인도 탈락도 아니다. 적절한 평가가 끝난 뒤 승인 기준 미충족은 탈락이다.

## 4. 상태 전이

| 객체 | 정상 흐름 | 예외/수정 |
| --- | --- | --- |
| Trial | DRAFT → REGISTERED → RUNNING → EVALUATED → REVIEWED → CLOSED | 실행 실패/무효 사유 기록, 수정은 새 trial |
| ReleaseGroup | PLANNED → FROZEN → EVALUATED_SEALED → RELEASED | 동결 이후 취소도 감사 기록 유지 |
| Memory revision | DRAFT → REVIEWED → ACTIVE | QUARANTINED / RETIRED, 새 revision으로 정정 |
| Publication | REQUESTED → PARITY_VERIFIED → APPROVED → PUBLISHED | 별도 사용자/권한 정책, 자동 reveal 연쇄 금지 |

ReleaseGroup의 평가기는 허용된 작업이 끝날 때까지 개별 상세 결과를 연구자에게 반환하지 않는다. 제한된 결과 코드 자체가 정보를 유출할 수 있으므로 오류 계약도 고정한다. 데이터 오류로 재실행할 때는 결과를 봤는지 기록하고, 이미 노출된 창을 다시 미노출로 복구하지 않는다.

공개 응답보다 먼저 ExposureEvent를 durable commit한다. 전달은 idempotency key로 재시도하며, 중단으로 실제 전달 여부가 불확실하면 보수적으로 노출된 것으로 취급한다. 응답은 나갔는데 원장은 미노출로 남는 순서를 허용하지 않는다.

## 5. 역할과 실제 권한

| 역할 | 읽기 | 쓰기/실행 | 금지 |
| --- | --- | --- | --- |
| Planner | 허용된 개발 근거·기억·중복 원장 | 계획/계약 초안 | sealed 결과, 판정 규칙 변경 |
| Builder | 동결 계약·허용 입력·fixture | 격리된 단일 팩터 구현 | 임의 DB/네트워크, 결과 기반 무등록 수정 |
| Evaluator | 서명된 capability의 데이터 | 결정론적 평가·불변 산출물 | 기억/정책 수정 |
| Distiller | 실행 기록·허용 결과 | 관찰 초안 | 경제적 원인 단정, 기억 직접 수정 |
| Analyst/Skeptic | 증거 bundle·계약 | 근거 있는 해석/이견 | gate override, 임의 추가 백테스트 |
| Curator | 허용된 증거·관련 기억 | 제한된 probe, 기억 revision | hidden 결과, 정책·원자료 수정 |
| Chair | 검토 메모·예산·계약 목록 | 다음 연구 배정안 | 새 실증 주장 생성, 단일 팩터 자동 합성 |
| Publisher | 승인된 계약·parity·사용 권한 | 별도 승인된 발행 | reveal만으로 Gold 발행 |

표의 역할은 논리적 권한 구분이지 각각 상시 에이전트를 띄우라는 뜻이 아니다. 초기에는 연구자 세션, 독립 검토 세션, 배치별 curator 세션으로 운영하고 평가·검증·원장 처리는 결정론적 코드로 한다. Chair 검토는 프로그램/배치 경계에서만 수행한다. 신뢰 경계가 다른 역할은 같은 대화 context·자격증명을 공유하지 않는다.

프롬프트에 “보지 말라”고 쓰는 것은 보안 경계가 아니다. worker에는 필요한 파일만 mount하고 DB·클라우드 자격증명을 주지 않는다. 데이터 중개기가 dataset/version, 허용 열·행·기간, 작업 종류, 반환 형태, 유효시간, trial ID를 담은 capability를 확인한다. sealed 데이터는 임의 shell·SQL·네트워크로 접근할 수 없어야 한다.

실제 격리가 없고 모든 worker가 저장소·자격증명을 공유한다면 `isolation_level=LOGICAL_ONLY`로 표기하고 강한 미열람 인증을 하지 않는다. 허용 목록을 통해서만 오류·행 수·시간 정보도 반환한다. 사람이 접근한 검증 결과 역시 중앙 노출 기록에 포함한다.

Builder가 만든 코드도 신뢰된 평가기 프로세스에 직접 import하지 않는다. 허용 feature만 전달받는 별도 sandbox에서 점수를 계산하고, 출력 타입·ID·범위·결정성 검증 후 고정 schema의 점수만 trusted scoring kernel로 넘긴다. hidden label과의 결합은 이 kernel에서만 한다. feature-only sandbox에는 evaluator 자격증명·sealed 파일·임의 네트워크 접근을 주지 않는다.

## 6. 최소 데이터 모델

모든 레코드는 schema version, ID, 생성 시점, 작성 주체, content hash를 갖는다.

| 엔티티 | 핵심 내용 |
| --- | --- |
| PolicySnapshot | 인간 승인 규칙, 데이터 계약, 판정 기준, 금지 작업 |
| PaperSource | URL·버전·읽은 범위·주장 연결; 문헌은 우리 시장의 실증과 별개 |
| TrialContract / Run | 질문·정의·기간·코드·환경·실제 입력·상태 |
| Artifact | raw 결과/로그/설정의 URI·hash·생성기·접근 scope |
| Observation | 측정 사실·단위·표본·결측·불확실성·artifact 경로 |
| Claim | 주장·범위·타입·근거·반례·대안·한계·성숙도 |
| MemoryRevision | 재사용할 지침·조건·예외·검증 상태·출처·유효 버전 |
| Decision | 판정 규칙 버전·입력 근거·승인/탈락·이유 |
| RetrievalReceipt | 실제 검색 및 주입된 기억·범위·버전·제외 사유 |
| UtilityEvent | 관측된 수행 결과·기억 bundle·보상 정의·검토자 |
| ExposureEvent | 데이터/결과가 누구에게 언제 어떤 범위로 공개됐는지 |

Claim의 구체적 필드 제안:

```text
claim_id, revision, statement_ko,
type = OBSERVATION | INTERPRETATION | HYPOTHESIS | PROCEDURE,
scope = { market, universe, period, horizon, feature_definition,
          information_lag, data_snapshot, pit_policy,
          cost_model, protocol_version, regime_definition },
artifact_refs, evidence_root_ids, dependency_groups,
supports, challenges, rival_explanations, limitations,
measurement_validity, diagnostic_coverage, evidence_stage,
review_state, available_at, valid_from, valid_to,
supersedes, retirement_reason
```

`confidence` 하나로 모든 품질을 표현하지 않는다. 실행 완결성, 측정 타당성, 적용 범위, 표본 의존성, 독립 검증 여부, 기억의 유용성은 별도다. 과학적 근거가 약한 관찰도 정확히 범위를 붙이면 개발 참고 자료로 남길 수 있지만 일반적인 지시나 확립된 법칙으로 승격하지 않는다.

### edge 의미와 근거 중복

`produced`, `derived_from`, `supports`, `weakens`, `contradicts`, `limited_by`, `used_in`, `supersedes`, `related_to`를 구분한다. 지지·반박은 비교 가능한 estimand·scope일 때만 붙인다. 서로 다른 기간·대상의 결과 차이는 자동 모순이 아니다.

증거 root는 원실행·입력 snapshot·평가 프로토콜에 연결한다. 같은 자료의 seed 변경·LLM 재요약·재현 실행은 별도 관찰일 수 있으나 독립 시장 표본으로 세지 않는다. 부분적으로 겹치는 종목·기간도 overlap을 기록한다. source cycle과 근거 없는 support edge는 검증기가 거부한다.

## 7. 시점 일관성과 기억 검색

두 가지 as-of를 별도로 전달한다.

| 시계 | 제약 |
| --- | --- |
| market_as_of | 신호에 사용할 데이터가 판단 시각까지 공개·가용했는가? |
| research_as_of | 교훈·증거·평가 결과가 연구자가 기억을 읽는 시점에 허용됐는가? |

기억의 `available_at`은 적어도 근거 공개 시점, 검토 승인 시점, 해당 revision 생성 시점 중 가장 늦은 값이다. 요약·임베딩·효용 snapshot도 같은 의존성 제약을 따른다. 문서의 관측 대상 연도가 과거라는 이유로 그 기억을 과거에 사용 가능했던 것으로 표시하지 않는다.

검색 순서:

1. `namespace + capability + research_as_of + data/protocol scope`로 대상 제한.
2. 정확한 ID/키워드, BM25, 의미 검색으로 후보 생성.
3. 조건이 맞는 연결을 최대 2 hop 탐색하고 각 hop에서 권한 재검사.
4. 연결된 반례·한계·수정본을 함께 선택. 근거가 없으면 만들지 않음.
5. 원래 증거가 같은 중복을 줄이고 작은 context bundle 생성.
6. 원문·요약·출처·scope·토큰 수·hash가 포함된 receipt를 동결.

초기값은 후보 20, 교훈 최대 3, 약 1,500~2,000 토큰이다. 안전 규칙은 별도 고정 context다. 적용 범위·반례를 잘라 숫자만 맞추지 말고 필요하면 항목 수를 줄인다. 요약도 출처를 보존한 별도 버전이어야 한다.

접근 불가 항목은 검색 결과뿐 아니라 유사도·개수·효용 집계·오류 메시지로도 유출하지 않는다. 인덱스와 효용은 허용 scope별로 생성하거나, 비간섭을 검증한 필터링 방식을 사용한다. graph-only 경로도 동일 검사 대상이다.

```text
RetrievalReceipt:
  task_id, query_hash, research_as_of, capability_id,
  corpus_snapshot_hash, embedding_version, ranker_version,
  utility_snapshot_id, candidate_ids_within_allowed_scope,
  injected_memory_revision_ids, included_counterevidence,
  exclusion_reason_codes, rendered_context_hash, actual_tokens
```

receipt는 읽기 기록이지 사고의 인과적 기여 증명은 아니다. 연구자는 이후 사용/거부 이유를 덧붙일 수 있지만 원래 주입 기록을 변경할 수 없다.

## 8. 기억 작성·검증·은퇴

한 trial의 사실 요약 → 교훈 후보 → 독립 검토 → 제한된 확인 → 활성화/보류 순서다. distiller가 보는 수치 자체를 숨길 필요는 없지만 최종 승인·실패라는 이야기 틀에 맞춰 사실을 왜곡하지 않도록 역할을 분리한다.

항상 수행하는 검사: schema, 해시, 출처 존재, 시점, capability, 의존성, 주장과 인용 내용의 일치. 추가 환경 확인은 기본 최대 3회·120초로 제한한다. 호출·행·바이트·비용 상한과 timeout을 계약에 포함한다.

```text
ProbeContract:
  claim_id, uncertainty, allowed_artifacts_or_queries,
  capability_id, expected_check, stop_rule,
  max_calls, max_rows, max_bytes, max_seconds, cost_cap
```

새로운 경제적 검정을 probe로 숨길 수 없다. 허용되지 않은 결과가 필요하면 “새 실험 필요”로 넘긴다. timeout은 미확인이며 검증 성공이 아니다. false claim은 정정하거나 은퇴시킨다. 원증거 무효화·구조적 오류가 확인되면 의존한 활성 기억·파생 요약을 우선 QUARANTINED로 전이하고 색인·효용·cache의 사용도 차단한다. 재검토 후에만 다시 활성화한다. 이미 주입된 실행과 미발행 판정에도 재검토 표시를 붙인다. 과거 원자료·receipt는 삭제하지 않는다.

정책 문구는 기억으로부터 승격할 수 없다. retrieved text 안의 도구 호출 명령·권한 변경 요구는 신뢰하지 않는 내용으로 처리한다.

## 9. 효용 기록과 활성화 조건

초기 검색 점수에는 효용을 쓰지 않는다(`utility_weight=0`). 도입 이후에도 관련성·권한·조건 적합성의 최소 기준을 통과한 기억 사이에서만 효용을 반영한다. 검증된 절차 규칙과 의무적 경고는 점수로 제거하지 않는다.

효용 키는 최소 `memory_revision × task_class × model_version × reward_policy_version × protocol_version`이다. 모델·환경·기억 의미가 바뀌면 과거 효용을 무조건 이어받지 않는다.

보상 rubric은 다음을 구분한다.

- 적절하게 답함 / 적절히 반증함 / 필요한 정보를 요청함 / 근거 부족으로 적절히 판단 유보함.
- 근거 없는 주장 / 권한 위반 / 필요한 검사를 생략함 / 불필요하게 판단을 회피함.
- 데이터 장애·시스템 장애로 관찰할 수 없음: 보상 업데이트 대상 제외.

LLM 자기평가만 사용하지 않는다. 결정론적 검사와 블라인드 검토 표본을 결합한다. 모든 기억에 같은 최종 점수를 나누어 주면 `Q_observed` 즉 공동 사용의 관측 효용이다. 인과적 기여나 사실의 신뢰도가 아니다. `Q_incremental`은 별도의 통제 비교가 있을 때만 기록한다.

UtilityEvent는 `retrieval_receipt_id`, 실제 주입된 memory revision, episode/outcome ID, 보상 근거 artifact와 공개시각·권한 scope를 필수로 가진다. 검색 후보였지만 주입되지 않은 기억에는 보상을 주지 않는다. episode별 idempotency key로 중복 업데이트를 차단한다. Q snapshot의 가용 시점은 보상을 만든 결과의 허용 공개 시점까지 상속한다.

`Q_incremental`은 초기 비활성이다. 활성화하려면 포함/제외 개입, 독립 세션, 같은 과제·모델·도구·예산, 동결 snapshot, 비교 중 학습 금지를 사전에 고정해야 한다. 안전 규칙은 제외 대상이 아니다. 측정값은 해당 bundle·순서·토큰 예산 아래의 조건부 증분효과이며 기억의 보편적 기여가 아니다.

EMA 업데이트 계수나 관련성/효용 혼합 비율은 논문 값을 그대로 채택하지 않는다. 개발용 절차 과제에서 정한 뒤 최종 평가 전에 고정한다. 배치 중 utility를 바꿔 다른 trial에 누출하지 않는다.

효용 순위를 켜는 조건은 안전 검사 통과, 고정 평가에서의 품질/비용 이점, 오류·회피 증가 없음이다. 작은 파일럿에서 높게 나온 숫자 하나로 활성화하지 않는다. 증거가 부족하면 계속 deterministic retrieval을 쓴다.

## 10. 월초 체결·국면 계약의 구체화

### 월초 체결 후보 계약

- 시장 관측 cutoff: 해당 월의 마지막 실제 거래일 종료까지의 관측값.
- decision cutoff: 다음 검증된 거래 세션 시가 시각보다 사전 고정한 버퍼만큼 이전. 초기 후보 버퍼는 10분이며 실제 주문 가능성 검증 전에는 체결 보장이 아니다.
- 입력 조건: `observation_at <= market_cutoff`와 `available_at <= decision_cutoff`를 모두 만족. 월말 이후 공개된 새 회계/매크로 관측을 넣을지는 별도 계약 없이는 허용하지 않는다.
- 보유 구간: 해당 세션 시가부터 다음 리밸런싱 세션 시가까지. 수익률·벤치마크·배당 권리의 창을 일치시킨다.
- 필수 입력이 늦으면 월을 조용히 제외하거나 가격을 소급 적용하지 않는다. `NOT_COMPUTED_INPUT_LATE`로 전체 비교의 미산출 상태를 명시한다. 지연 체결 대안은 별도 사전 규칙으로 검증한다.
- 거래정지·주문 불가능 종목의 잔존 포지션, 현금, 비용, corporate action, delisting을 사전등록한다. 해당 계약이 없으면 실제 체결 성과로 표시하지 않는다.

이는 기존 월말→월말 연구 수익률과 다른 정의다. 기존 결과를 새로운 월초 체결 결과로 이름만 바꾸지 않는다.

### 4국면 후보의 정확한 정의

정식 구현 전 데이터 검증 대상인 제안이다. 계약 ID를 새로 부여하고 기존 국면 버전을 덮어쓰지 않는다.

1. 시장별 인증된 일별 가격지수 종가 `P_d`를 사용한다. 휴장일을 수익률 0으로 채우지 않는다. 소스·지수 유형·시점을 manifest에 기록한다.
2. 월말 수준 `M_t`는 그 월 마지막 유효 거래일의 값. `trend_up = M_t >= mean(M_t ... M_(t-9))`이며 유효한 연속 10개월을 요구한다.
3. 일별 로그 수익률 `log(P_d/P_(d-1))`의 최근 63개 유효 연속 거래일 표본 표준편차(ddof=1)에 `sqrt(252)`를 곱해 `vol_t`를 만든다. 필요한 종가 64개와 실제 거래 달력의 완전성을 확인한다.
4. 기준은 현재 월 이전의 유효 `vol` 월 값들의 expanding median이다. 최소 24개 과거 월을 요구하고 현재 월을 기준 계산에서 제외한다.
5. `vol_high = vol_t > prior_median`. 동률은 LOW로 처리. 추세와 조합해 UP_LOW / UP_HIGH / DOWN_LOW / DOWN_HIGH, 입력 부족은 UNKNOWN.
6. 값·기준·기준 표본 수·입력 마지막 날짜·available_at을 함께 저장한다. 해당 월 이후 수익률과 연결하며 같은 월 수익률의 사후 원인으로 쓰지 않는다.

국면의 빈도 균등을 목표로 임계값을 바꾸지 않는다. 판독 변화·축의 분포·전환율·시점 누출을 먼저 검사한다. 충분한 일별 자료가 없으면 이 후보를 미구현으로 남긴다. 매크로 축은 별도 정의·PIT 정책을 유지하고 모든 조합을 교차해 유리한 구간을 찾지 않는다.

## 11. 저장·동시성·재시작

초기 단일 writer 구성:

- SQLite WAL 이벤트 원장: 현재 상태의 권위 있는 변경 이력.
- 내용 해시 기반 artifact 저장소: write-once 원자료·계약·결과.
- 관계형 claim/edge 및 검색 색인: 이벤트·artifact에서 재생성 가능한 읽기 모델.
- JSON/CSV/사이트 snapshot: 내보내기이며 원장이 아님.

먼저 임시 artifact를 완성하고 해시 확인 후 최종 경로로 원자적 이동한다. 그 뒤 이벤트 트랜잭션에서 참조를 commit한다. 고아 파일은 가비지 수집 정책으로 따로 처리하고, commit되지 않은 실행을 성공으로 표시하지 않는다.

writer는 idempotency key와 expected revision을 확인한다. 동시 curator 충돌은 재검토로 보내며 마지막 쓰기 우선으로 덮어쓰지 않는다. 실행 cache는 코드·데이터·정의·정책·기간·기억 snapshot의 정확한 hash 조합을 사용한다. 다른 권한의 결과를 cache로 재사용하지 않는다.

오류 후 재시작은 남은 단계부터 하되 해시가 달라지면 새 실행으로 취급한다. 동일 trial의 기계적 재현 실행은 새 가설을 발견한 것으로 세지 않는다.

## 12. 구현 파일 제안과 기존 코드 연결

아래 새 파일 이름은 설계용 제안이며 아직 존재/동작한다고 가정하지 않는다.

| 제안 파일 | 책임 | 재사용할 현재 기반 |
| --- | --- | --- |
| `engine/research_program.py` | 계획·예산·ReleaseGroup | epochs/boundaries/trials |
| `engine/access_scope.py` | capability·시점·전역 노출 | boundaries + 노출 메타데이터 |
| `engine/evidence_graph.py` | typed evidence·의존성·뷰 | knowledge_lineage, scientist_review |
| `engine/memory_store.py` | 불변 이벤트·revision | 현재 memory 파일의 보관/이관 adapter |
| `engine/memory_retrieval.py` | scope 검색·반례·receipt | knowledge_registration 확장 |
| `engine/memory_grounding.py` | 검토·허용 probe·은퇴 | evidence/critic 검토 계약 |
| `engine/memory_utility.py` | 관측 효용·오프라인 비교 | 신규, 초기 shadow mode |
| `scripts/research_v2.py` | 분리된 plan/run/review/freeze/release 흐름 | 기존 CLI를 호환 adapter로 감쌈 |

발행은 별도 경로로 남기고 release의 기본 후속 동작으로 넣지 않는다. 기존 INSTRUCTIONS/SKILL은 구현·테스트·전환 승인 전에는 변경하지 않는다. 저장소의 진행 중 변경과 새 구현의 충돌은 적용 단계에서 다시 확인한다.

## 13. 검증 계획과 완료 조건

| 테스트 | 통과 조건 |
| --- | --- |
| 숨긴 결과 canary | SQL·파일·검색·graph·효용·오류 출력 어느 경로로도 노출 안 됨 |
| 과거 시점 재생 | 당시 허용되지 않았던 기억·요약·Q 업데이트가 결과를 바꾸지 않음 |
| cold start | legacy lesson/embedding/Q/파생 요약이 기본 검색에 0개 포함 |
| 반례 검색 | 관련된 허용 반례가 존재하면 장점만 있는 문맥으로 누락되지 않음 |
| 증거 중복 | 동일 결과의 여러 요약이 독립 증거 개수를 늘리지 않음 |
| 교훈 정정 | 새 검색은 수정본·경고 사용, 과거 receipt는 원래 버전 유지 |
| scope drift | 시장·스키마·프로토콜 불일치에서 자동 일반화하지 않음 |
| 예산·권한 | probe 상한 초과 차단, 미등록 백테스트 실행 차단 |
| 동시성·복구 | 중복 실행·curator 경합·중간 종료에도 불변 원장 일관성 |
| 전역 검증 창 | 다른 팩터/전략에서 먼저 본 창을 독립 OOS로 재승격 못함 |
| 판정·발행 | LLM이나 release가 Gold/실전 권한을 자동 변경 못함 |
| 평가기 코드 격리 | 악성/오류 factor 코드가 scoring kernel의 label·자격증명에 접근 못함 |
| 공개 중 종료 | 응답 전후 중단·재시도에도 실제 노출 창이 미노출로 남지 않음 |
| 월초 체결 | 늦은 입력·기업행동·상폐·불일치 benchmark 창을 성공으로 보고하지 않음 |

기억 비교는 B0~B4 구성을 단계적으로 평가한다. 초기 과제 은행 제안은 6개 절차 영역, 총 48개 과제, 개발 24/최종 24다. 서로 비슷한 원인·fixture 계열은 같은 쪽에 배치해 변형 복사를 통한 누출을 막는다. 이 수는 검정력을 보장하는 수치가 아니라 구축 예산이며, 불확실성이 크면 결론을 유보한다.

각 구성은 분리된 저장소, 동일 모델·도구·전체 비용 한도를 사용한다. 공통 정책·문헌 접근·데이터 계약·성과 없는 정의/시도 색인은 동일하게 제공한다. 고정 평가에서는 memory corpus/ranker를 동결한 테스트와, 과제 순서에 따라 학습하는 online 테스트를 분리한다. online 테스트는 구성별로 같은 사전 고정 순서를 쓰고 매 반복 처음 상태에서 시작한다. 순서·난수의 반복은 변동성을 보지만 동일 과제의 반복을 독립 과제로 세지 않는다.

online 과제는 `응답·점수 봉인 → 허용 피드백 공개 → 다음 과제용 기억/Q 갱신` 순서를 지킨다. evaluator의 정답·숨긴 판정 근거를 curator에 제공할지 사전 고정한다. oracle 정답 학습 조건과 실제 운영 가능한 피드백 조건은 분리해 보고한다. 반복 초기화에는 대화 context·도구 cache·이전 반복의 학습 산출물도 포함한다.

절차 과제의 안전성과 품질이 확인된 다음 6개 팩터 trial로 통합 흐름을 확인한다. 3개 가설 계열의 2개 비교는 사전에 정하고 동일한 기대 독립성을 주장하지 않는다. 이 파일럿은 승인 팩터 개수나 기억 학습 효과를 통계적으로 확증하는 실험이 아니다.

최종 평가를 열기 전에 측정 지표·판정 규칙·비용 집계를 고정한다. 치명적 누출은 무조건 실패다. 나머지는 품질 저하 없이 비용이 줄거나, 같은 예산에서 의미 있는 품질 이점이 있는지 불확실성과 함께 판단한다. 단순 구성보다 이점이 확인되지 않은 기능은 도입하지 않는다.
