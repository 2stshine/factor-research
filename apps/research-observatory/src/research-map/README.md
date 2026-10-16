# 연구 지도 / shared-coordinate network v2

기존 연구 관측소의 정식 `#map` 경로. 정적인 검토용 스냅샷이며 실시간 지식망이나 다음 후보 생성 입력이 아니다.

## 선택한 구조와 이유

- 이전 주제 개요 + 단일 사례 상세는 모든 연구를 한 공간에서 연결해 보려는 요구를 충족하지 못했다.
- 순수 유사도 force graph는 닮음과 실제 영향을 혼동하기 쉽고 위치가 흔들린다. lesson_key만 병합하면 현재 거의 모든 사례가 고립된다. 기존 compactor의 엄격한 동등성을 느슨하게 바꾸지 않는다.
- **선택: canonical evidence graph 위의 단일 좌표공간.** 공개 가설·교훈·질문을 항상 유지하고 category로 안정적인 배치를 정한다. 노드는 직접 옮길 수 있다. 관측·대안설명·한계는 선택 상세에서 원문 그대로 펼친다. 배치는 확신·지지·인과를 뜻하지 않는다.

공개 cycle 54–230의 177개 사례 × 가설/교훈/미실행 질문 = 531개 핵심 노드. cycle 50–53의 비공개 내용은 읽거나 노출하지 않는다. 카탈로그 전체 withheld26 집계는 보존한다. 검색·선택·관계 필터도 핵심 노드를 제거하지 않는다.

| 유형 | 건수 | 생성 근거와 해석 |
| --- | ---: | --- |
| 동일 사례 가설→교훈 | 177 | 검토 기록 구조. 원가설 성공 아님 |
| 교훈→제안 질문 | 177 | 모두 PROPOSED_NOT_RUN. 실행 연결 없음 |
| 명시적 교훈 활용 | 1 | 229 교훈→230 가설의 data_notes 인용. 229 후속 실험 실행 아님 |
| 명시적 비교·참조 | 33쌍 / 37필드 인용 | 공개 hypothesis/expected_relationship/mechanism/data_notes/falsification의 factor-name 정확 매칭. 수행된 비교·지지·인과 아님 |
| 동일 코드 조건 변형 | 64쌍 / 14그룹 / 45사례 | frozen source의 줄바꿈·외곽 공백만 정규화. params·predicted_sign 차이 보존. 독립 재현 아님 |
| 편집상 같은 category | 172 | 같은 분류의 시간상 이웃, 기본 해제. 과학적 관계 아님 |

총624개 표시 관계 중 편집선172개는 기본 해제. 실제 교훈 영향 기록에 연결된 사례는2개이며 나머지175개를 억지 계보로 연결하지 않는다. 외부/미공개 팩터 언급은 원문 상세에 남지만 실행된 경계 노드를 만들지 않는다. 원시 ledger 전체 참조 카운트와 공개 5필드 범위의 수치는 다를 수 있다.

노드 drag/drop은 표시 위치만 바꾼다. 배경 pan, 휠/두 손가락 확대, 노드·선 클릭 상세, 방향키/Enter, 검색 이웃 강조, 관계 필터, 전체보기·위치 리셋을 지원한다. 선택은 다른 연구를 숨기지 않는다. 확대 수준에 따라 cycle/이름을 표시하며 위치 변경은 원본이나 디스크에 저장하지 않는다.

## 근거 계약

자동 추출: case / hypothesis / observation / explanation / lesson / limitation / follow-up / evidence / assessment / window. 주제만 EDITORIAL_TYPED_RULE이며 about은 실증 지지를 뜻하지 않는다.

- evidence 정체성은 packet SHA-256 + evidence ID. 과학적 edge는 record ID, 원문 JSON pointer, packet hash, evidence ID를 가진다.
- 지지·제약은 explanations.supporting_evidence/opposing_evidence를 그대로 사용한다. cited_by는 인용일 뿐 지지 판정이 아니다. 같은 기록 내 항목선은 구조선이며 메커니즘 입증이 아니다.
- SUPPORTS/UNCERTAIN은 general_lesson에 대한 검토 입장이다. 현재 62/115개이며 CONTRADICTS는 0개. 서로 다른 가설의 mechanism 판정을 합쳐 하나의 가설에 대한 투표로 표시하지 않는다.
- cycle0229→0230은 data_notes에 앞 lesson_key가 정확히 명시돼 있어 methodology_reference로 연결했다. 자산 성장 연구가 일시 수요를 입증했다는 의미가 아니다.
- 정확한 signal window를 공유하는 사례는 같은 window node로 묶고, 같은 phase의 달력 겹침을 별도로 기록한다. 개월·사례·패킷 개수를 독립 재현 횟수로 환산하지 않는다. 달력 일치는 행 단위 표본 동일성이나 동일 데이터 vintage를 증명하지 않는다.
- follow-up은 원문 PROPOSED_NOT_RUN. 필요한 입력의 현재 가용성을 조사하거나 연구를 실행하지 않았다. 외부 문헌 언급은 원문의 가설 맥락에 보존하며 로컬 검증 증거로 승격하지 않았다.
- historical raw_input_profile은 당시 미수집. 이후 raw-input-profile-v2 수정은 과거 packet을 소급 변경하지 않는다. REGIME_LESSON_REVIEW_20260923.md / REGIME_REMEDIATION_20260923.md 참조.

## 현재 coverage

2026-09-23 카탈로그: ledger203, released177, REVIEWED_CURRENT177, campaigns25, unique lesson_key177, withheld26. 3,907 nodes / 5,126 edges. 177개 입력 품질 중 NOT_COLLECTED175/PARTIAL2; regime monthly1. mechanism assessment 4종은 모든 사례에 있으나 상세 reason 문장이 없는 경우 없는 것으로 표시한다.
탐색 기간 2018-03~2023-04의 175개와 2018-03~2023-05의 2개는 서로 겹친다. OOS/탐색 지표를 구분한다. 최신 사례의 비용 후 -0.65%p는 탐색 구간 연환산 초과수익이며 OOS 수익이 아니다.

## 생성과 배포 범위

`node scripts/build-research-map.mjs`는 기존 인증 catalog 뒤의 projection이다. 원본 인증을 대체하지 않는다. sealed/pending/stale row는 제외, review packet binding·unknown evidence·중복 identity는 검사한다. `sync-snapshot.mjs`가 JSON 패키징 후 호출한다.

보존 소스: 이 디렉터리의 projection.mjs / network.mjs / network-view.js / themes.json / snapshot.json / view.js / view.css. dist만 편집하지 않는다. 기존 app.js의 연결부는 정적 앱과 같은 위치에 최소 추가했다. source revision을 갱신하지 않으면 링크는 명시된 이전 원본 커밋을 가리킨다.

이미 공개된 사이트 https://teamalpha-research-observatory.vercel.app/ 의 두 catalog JSON과 로컬 파일이 바이트 단위로 같음을 확인했다. 새 공개 데이터 원천 없음: 지도는 그 catalog의 부분 재배열, 출처 ID, 편집 주제와 달력 비교만 추가한다. 숨겨진 ledger/봉인값/로컬 credential은 포함하지 않는다. reviewer-only란 연구 해석 용도 제한이다. 이 목적을 candidate-generation feed로 바꾸지 않는다.

이 v2 변경은 로컬 전용이며 기존 Vercel 공개판과 별개다. 이번 작업에서는 커밋·푸시·배포하지 않았다. 새 승인 없이 이전 배포 승인을 재사용하지 않는다.

## 검증

`node scripts/check-research-map.mjs`: 결정론적 재생성, 모든 source pointer와 ID, dangling/unknown evidence, sealed/stale 누출 방지, packet binding, identity 중복, 정확한 원문 지지·제약 개수, 임의 lesson conflict 0, 기간 재사용, 177×6 상세 상태, 빈 검색, 과거 profile 불변.
`node scripts/check-site.mjs`: 8개 페이지(월초 실행 비교 포함), 177개 기존 연구 상세, 49개 승인 팩터, 90개 레짐 보기 및 기존 한국어·최신순·단위·민감정보 회귀 검사.

`node scripts/check-network.mjs`: 531개 공개 ID, 모든 typed edge 출처, 실제 교훈 활용, 코드/조건 차이, 177개 미실행 질문, 허구 실행·지지·반증 0.

`PLAYWRIGHT_MODULE=/path/to/playwright OBSERVATORY_PREVIEW_URL=http://127.0.0.1:4320 node scripts/check-network-browser.cjs`: 독립 브라우저에서 실제 마우스/터치 인터랙션 및 기존7개 페이지 회귀. 브라우저 실행 가능한 환경과 Playwright가 필요하다. 출력 위치는 `OBSERVATORY_EVIDENCE_DIR`로 지정한다.
