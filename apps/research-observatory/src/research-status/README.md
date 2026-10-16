# 공개 연구 상태의 읽기 전용 진단

이 모듈은 인증된 공개 `research-catalog.json`을 읽는다. 원장·후보 생성·DB·봉인 원문은 읽지 않는다.
현재 코드의 정의를 과거 시행에 연결하거나 역사적 정의·packet·review hash를 수정하지 않는다.

- `semantics.mjs`: UNKNOWN을 포함한 레짐 합계, 최신 일반 연구/선택 레짐 연구 분리,
  교훈 stance, campaign의 표본 재사용, 보존 자료의 표시 기준월 대조.
- `projection.mjs`: 공개 시행만의 정의 기반 coverage. 계산 코드의 CRLF·외곽 공백만
  정규화한 정확한 템플릿 hash를 사용하며 params·방향·리밸런싱은 각 시행에 남긴다.
- `annotations.json`: 정의 ID·record ID·packet hash에 결합하는 별도 주석. 현재 주석은 비어 있다.
  과거 `exploration_domain=null`을 임의로 채우지 않는다. 경제적 메커니즘·텍스트의 존재는
  경제적 원인의 입증이나 독립 차원 수가 아니다.
- `config.json`: 명시적 KST 표시 점검일. 원천 스냅샷의 시각·당시 준비도를 덮어쓰지 않는다.
  2026-10-01의 필요 완료월은 2026-09다. 기존 자료가 2026-08까지인 상태를 현재 준비로 간주하지 않는다.

```sh
node scripts/build-research-status.mjs
node scripts/check-research-semantics.mjs
node scripts/check-research-status.mjs
node scripts/check-site.mjs
```

`sync-snapshot.mjs`도 같은 생성기를 호출한다. 명시적인 날짜 인자를 주면 새 표시 점검일로
만들 수 있지만, 이것이 원천 수집·새 레짐 연구·실제 체결 검증을 수행하지는 않는다.

레짐의 12개월/3발생 구간은 기존 설명 표시 정책이다. 상태별 95% HAC 구간은 pointwise 근사이며
국면 차이 검정·동시 구간·인과 검증이 아니다. 과거 레짐 분류와 값은 그대로 보존한다.
공통 적격 종목-월 점수 행렬이 없으므로 상관·유효차원은 `NOT_COMPUTED`다.
같은 코드 변형을 묶어도 실제 시행 수와 다중검정 시행 수를 줄이지 않는다.

정성 교훈의 기존 승인된 연구 메모리 사용은 유지한다. 이 공개 진단은 원시 OOS 수치나 성과
순위를 후보 생성에 새로 공급하는 인터페이스가 아니다. 과거 구간 재사용은 새 독립 검증과 다르다.
