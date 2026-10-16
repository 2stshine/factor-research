# 새 연구의 정성 교훈 계보 — 선택적 사전등록 v1

기존 `research/INSTRUCTIONS.md`가 허용하는 공개 정성 교훈·pass/fail 학습을 보존한다.
어떤 메모리의 어떤 교훈 검토본을 참고했다고 선언했는지를 **앞으로 등록할 후보에만** 남긴다.
원시 OOS 수치나 성과 순위를 새 후보 입력으로 제공하지 않으며 기존 후보·epoch·packet·review를
소급 수정하지 않는다. 선언이 없는 과거 기록은 `NOT_RECORDED`다.

## 새 후보를 작성하고 등록할 때의 순서

1. 기존 승인된 경로로 갱신된 `research/KNOWLEDGE.md`를 읽을 때 다음 캡처 명령을 실행한다.
   이 명령은 기존 파일을 그대로 보관하고 현재 공개·검토 상태를 읽기 전용으로 인증한다.
   메모리를 갱신하거나 새 실험을 만들지 않는다.

   ```sh
   python -m scripts.knowledge_lineage --root research capture
   ```

   내용 주소 방식의 `research/memory/knowledge_snapshots/<capture_id>.json`을 새로 보존한다.
   파일에는 정확한 기존 메모리 바이트, 도구가 기록한 시각, 당시 공개 검토본의 ID·review/packet
   hash가 들어간다. CLI 출력은 식별자와 상태뿐이며 지식 원문/성과 payload는 출력하지 않는다.
   이 로컬 보관 파일은 공개 사이트 번들에 넣지 않는다. 현재 메모리가 인증된 lesson projection과
   다르면 실패한다. 기존 갱신 흐름으로 먼저 해결하며 오래된 내용을 자동으로 인증하지 않는다.
2. **새 후보**의 단일 top-level literal `RESEARCH_SPEC`에 `knowledge_lineage`를 넣는다.
   구조는 [schema](knowledge-lineage.schema.json)에 고정돼 있다. 캡처 출력의
   `knowledge_snapshot_hash`, `captured_at`을 각각 해당 필드와 `snapshot_captured_at`에 사용한다.
   `declared_at`은 실제 선언 시각이다. 실제 참고한 ID만 `referenced_lesson_record_ids`와
   `lesson_references`에 같은 순서로 적는다. 각 참조의 `review_hash`/`packet_sha256`도 캡처 당시
   버전을 사용한다. 참조가 없다는 빈 배열 선언과 필드 자체 미기록은 다르다.
3. 사용자가 새 연구 등록을 시작할 때 기존 명령에 선택 플래그를 추가한다.

   ```sh
   python -m scripts.research epoch-start --campaign CAMPAIGN --epoch NEW_EPOCH \
     --factors NEW_FACTOR --knowledge-capture CAPTURE_SHA256
   ```

   기존 입력 적격성·Gold 상관 사전검사는 그대로 수행한다. opt-in의 잘못된 선언은 trial DB
   초기화보다 먼저 거부하고, epoch 쓰기 직전에 다시 인증한다. 후보 소스 SHA, 실제 loader가
   만든 Factor/compute, literal 선언, snapshot, 당시 공개 검토본과 현재 검토본을 결합한다.
   캡처 ≤ 선언 ≤ 실제 epoch `created_at`이어야 한다. 캡처 이후에 공개·검토된 새 교훈,
   바뀐 review/packet, 다른 계산 파일, 중복 선언이나 실행/인과관계 주장은 거부한다.
4. 등록 결과의 선택적 `knowledge_lineage` 블록은 `RECORDED_AT_REGISTRATION`이다.
   후보별 definition/strategy/declaration hash와 capture ID를 묶는다. 등록 후에는 후보 파일과
   캡처를 바꾸지 않는다. 다음 명령은 당시 결합된 식별자만 읽는다.

   ```sh
   python -m scripts.knowledge_lineage --root research audit \
     --campaign CAMPAIGN --epoch NEW_EPOCH --factor NEW_FACTOR
   ```

   audit는 오늘의 후보·메모리·review를 과거 참조에 대신 붙이지 않는다. 당시 캡처가 없거나
   손상됐다면 실패한다. 새 플래그/선언이 없는 기존 등록 경로는 추가 필드나 인증 읽기 없이
   기존 형식을 유지한다. 선언을 넣었는데 플래그를 빼면 조용히 무시하지 않고 거부한다.

이 문서의 명령은 **향후 사용법**이다. 구현·합성 테스트 중 실제 후보/campaign/epoch를 등록하거나
연구를 실행하지 않았다. 선택하지 않으면 미래 연구도 미기록으로 남는다. 자동 강제·참조 추천·
지식 주입·과거 그래프 보충 기능은 아니다.

## 무엇을 증명하고, 무엇을 증명하지 않는가

관계는 `DECLARED_QUALITATIVE_LESSON_USE`와 `DECLARED_COMPARISON_REFERENCE`만 허용한다.
자유 텍스트·성과 숫자·추가 필드는 받지 않는다. 교훈 사용 선언은 실증적 지지, 메커니즘 입증,
실제로 제안 실험을 실행했다는 뜻이 아니다. 사람/에이전트가 정말 읽었는지도 이 해시로 증명할 수 없다.

캡처 시각은 로컬 도구의 현재 시각이며 독립 타임스탬프 기관의 증명이 아니다. 파일 mtime이나
사용자 지정 과거 시각은 사용하지 않는다. 현재 인증에서 확인한 lesson 버전을 캡처에 묶으며,
과거 review의 최초 작성일을 만들어 내지 않는다. 연구 담당자의 기존 저장소 쓰기 권한을 막는
보안 장치가 아니라 실수·변경·시점 불일치를 발견하는 재현성 계약이다.

정확한 renderer 재현은 lesson projection 결합을 확인한다. 기존 renderer가 가져오는 입력/context
문구 전체를 새로 내용 심사하는 것은 아니다. 따라서 `snapshot_content_safety_audited=false`를
유지하고 캡처 원문을 새 candidate feed로 내보내지 않는다. 원래 정성 학습도 적응적 과거 연구이며,
참조를 남겨도 독립 OOS가 새로 생기지 않는다. `independent_evidence=false`,
`follow_up_executed=false`를 유지한다.

## 검토자용 별도 검사와 검증

기존 `scripts.check_knowledge_lineage`는 선언 JSON과 보존 메모리의 읽기 전용 검사로 계속 제공한다.
그 상태 `VALID_DECLARATION_NOT_REGISTRATION`은 실제 epoch 등록과 다르다. 새 통합 경로는
`engine/knowledge_registration.py` → `engine/epochs.py:start_epoch` 및
`scripts/research.py:cmd_epoch_start`에서만 선택적으로 연결한다.

`tests/test_knowledge_registration.py`는 실제 candidate loader를 사용하는 합성 파일과 임시
research root로 캡처·사전등록·재실행·과거 audit를 검증한다. 미공개/미존재/stale 참조, 캡처 후
공개된 참조, 시점 역전, 변조, 다른 Factor 출처, preflight 사이 검토 변경, invalid CLI의 DB 전
차단을 검사한다. 기존 등록·메모리·계보 검증 회귀를 함께 실행한다. 실제 시장 성과 검증은 아니다.

## 공개된 연구지도까지 이어지는 경로

새 연구가 원래 절차에 따라 공개된 뒤 기존 `export_research_catalog.py`가 release·결과물·
packet 재구축 인증을 먼저 완료한다. 이후 `registered_lineage.py`가 **선택적으로** 보존된
등록과 frozen result의 선언 hash·definition hash·strategy SHA를 대조한다. 당시 capture와
등록을 오늘의 소스 파일이나 새 KNOWLEDGE로 대체하지 않는다.

참조 대상도 현재 공개·검토된 기록이어야 한다. 캡처와 같은 `safe()` 처리 후 review의 Python
canonical hash 및 packet hash를 두 번째 순회에서 대조한다. 참조 대상이 비공개·미검토·변경된
경우 해당 참조의 ID나 원문을 공개하지 않고 보류 건수와 이유만 남긴다. 이 과정은 기존 공개
연구를 탈락시키지 않으며 선택 계보만 `WITHHELD`로 보류한다.

공개 출력에서는 raw `research_spec.knowledge_lineage`를 복사본에서 제거하고 인증된
`registered_lineage` 투영만 제공한다. 원본 payload/packet은 바꾸지 않는다. 투영에는
식별자·hash·시각·허용된 관계만 들어가며 capture 원문·로컬 경로·원시 OOS를 추가하지 않는다.
**이 투영과 전체 연구 카탈로그는 검토자용이다. 새 후보 생성 feed에 넣지 않는다.**

지도 생성의 `registered-lineage.mjs`는 이 투영과 공개 양 끝점만 사용한다.

- 교훈 활용 선언: 앞 **교훈 → 새 가설**. 읽기나 인과 영향의 입증은 아니다.
- 비교 참조 선언: **선언한 가설 ↔ 비교 대상 가설**. 선언 주체는 등록 참조에 보존하며 비교 수행·지지 관계와 다르다.
- 같은 관계의 원문 인용과 등록 선언이 모두 있으면 선 한 개에 두 출처를 보존한다.
- 앞 검토의 `PROPOSED_NOT_RUN` 질문은 실행된 질문으로 바뀌지 않는다.
- 새로운 연구가 아직 미공개이거나 지도 포함 조건을 충족하지 않으면 선도 표시하지 않는다.

계보 없는 과거 catalog에는 `null`이나 새 0 카운터를 추가하지 않는다. 같은 `as_of`와 직렬화로
현재 177건 catalog 및 graph JSON의 바이트 불변을 확인했다. UI는 없음을 `NOT_RECORDED`로
설명한다. 이 기능 추가로 실제 신규 연구·참조·등록 기록이 생긴 것은 아니다.

합성 검증은 `tests/test_registered_lineage_export.py`, `check-registered-lineage.mjs`,
`check-lineage-browser.cjs`에 있다. 등록·결과물 불일치, 캡처 누락/변조, sealed 조기 제외,
현재 review/packet 변경, 빈 명시 참조, raw 선언 단독, 중복 선, 관계 구분 및 키보드 상세를
검증한다. 미래 fixture는 테스트 메모리/임시 디렉터리에만 존재하며 공개 번들에 저장하지 않는다.
