# 새 레퍼런스 팩터 연구 경로

활성 세대는 `research/active-generation.json`과 그 해시로 묶인 manifest가 정한다.
기존 `factors/candidates`, `research/campaigns`, `research/v2`, Gold 전체 APPROVED 목록은
레거시다. 새로운 세대에 자동 수입하지 않는다.

먼저 `docs/research-v3-design.md`, `docs/research-v3-transition.md`,
`docs/research-v3-reference-library.md`를 읽는다. 이 문서는 실제 캠페인 실행 계약이 아니라
전환 안내다. 준비되지 않은 adapter/판정/발행 단계를 실행 가능한 것으로 해석하지 않는다.

## 유지할 규칙

- 단일 팩터 연구는 가설·정의·데이터 버전·비교 레퍼런스·진단 예산을 먼저 동결한다.
- 기존 검증·교훈의 출처/불확실성/독립 비평 규칙은 유지한다. 수치 선택과 설명을 분리한다.
- 전략에서만 여러 팩터 결합을 허용한다. 단일 팩터 정의 내부의 몰래 합성을 허용하지 않는다.
- 이미 노출된 기간·실패한 시행·기존 가설 정체성을 보존한다. 새 세대가 새 OOS를 만들지 않는다.
- 레퍼런스 통제 사용, 독립 알파, 전략 선택, 실제 발행은 서로 다른 질문이다.
- 원천 인증, 자료 readiness, 실험 판정이 불완전하면 상태를 그대로 적고 승인/적재했다고 하지 않는다.
- PCA/선택/전처리/릿지의 모든 fit은 허용된 과거 fold에서만 한다. 미래 feature/label,
  전체 기간 상관 선택, 무작위 종목-월 CV, 최종 테스트를 본 튜닝을 금지한다.
- 숫자 성과를 높이기 위한 자동 후보 대체·반복 OOS·Gold 게시·배포는 없다.

## 현재 사용 가능한 것

세대/보관 도구와 합성 수치 baseline만 사용 가능하다. 실제 reference 등록 및 v3 trial runner,
선택 실험·실행형 label·신규 Gold 발행은 아직 운영 연결 전이다. 초기 문헌 카탈로그는 승인 목록이 아니다.
이 단계에서 `scripts.research.py campaign-start`를 호출해 새 v3 연구가 시작됐다고 하지 않는다.
