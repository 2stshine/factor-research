---
name: factor-research-loop
description: factor-research 저장소의 현상·팩터 연구, 레퍼런스 측정, 근거·교훈 검토와 연구 문서화에 사용한다. 활성 연구 세대를 먼저 확인해 현상 중심 그래프 연구와 보존된 단일 팩터 campaign을 구분한다. 데이터 시점·반대 근거·검토/발행 권한을 보존하며 기존 연구나 Gold를 새 세대에 자동 승계하지 않는다.
---

# 연구 세대를 먼저 선택한다

레포 루트의 `research/active-generation.json`과 `research/INSTRUCTIONS.md` 상단의
현재 경로 안내를 먼저 확인한다. 새 작업에 과거 campaign 규칙이나 기억을 자동 적용하지 않는다.

- `phenomenon-research-v1`: `research/phenomena/INSTRUCTIONS.md`를 읽는다.
  실행·입력 연결이 필요하면 `docs/phenomenon-research.md`, 레퍼런스 정의가 필요하면
  `docs/reference-library-phenomena.md`를 읽고 실제 활성 graph/program을 사용한다.
  아래 레거시 `KNOWLEDGE.md`·과거 성과·교훈은 새 가설의 입력으로 자동 읽지 않는다.
  레퍼런스 측정, 실증 주장, 전략 검사, 수익성 승인은 별개다.
- `reference-factor-v3`: `research/v3/INSTRUCTIONS.md`를 읽는다.
- 사용자가 특정 과거 campaign을 명시적으로 재개/검토하라고 하면 해당 보존 계약을 사용하고,
  아래 레거시 절차를 따른다. 새 활성 세대를 묵시적으로 변경하지 않는다.
- 포인터가 없거나 알 수 없는 세대면 기본값을 추측하지 말고 로컬 세대 manifest와 요청 범위를 확인한다.

## 레거시 팩터 campaign: 두 층의 컨텍스트

레포 루트 기준 두 파일을 사용하되 현재 작업에 필요한 구역을 읽는다.

1. `research/INSTRUCTIONS.md`의 **읽는 방법·공통 원칙**을 먼저 읽고, 현재 단계 구역을 읽는다.
   후보 생성 / 실행과 재개 / 최종 검증과 적재 / 결과 정리 중 해당 구역을 선택한다.
   단계 전환 전에 다음 구역을 읽고, 재개·대화 요약·지침 수정 후에는 다시 확인한다.
2. 후보를 만들 때 `research/KNOWLEDGE.md`에서 인증 입력·등록 정의·시행 정체성·공개 가능한 기억을 확인한다.
   다른 단계에서는 해당 campaign의 필요한 상태만 확인하고 봉인 결과를 읽지 않는다.

기존 context/latest.md와 memory/lessons.md는 생성용 호환 artifact이며 함께 읽지 않는다.
지식이 없거나 오래됐으면 지침에 따라 갱신하고, 원시 결과로 봉인 필터를 우회하지 않는다.
이 스킬 자체는 캠페인 실행이나 Gold 적재 권한을 추가하지 않는다.
