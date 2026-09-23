# 레짐 입력의 최소 배포 묶음

이 문서는 **등록된 입력의 실행 이식성**을 설명한다. 원본 데이터를 다시 수집하거나
PIT를 새로 인증하는 절차가 아니다. 기존 context·approval 바이트와 해시는 보존한다.
registry에는 새 버전의 입력만 명시적으로 추가한다. `PIT_ASSUMED`는 계속 사용자 수용 가정이며 최초 발표본 인증이 아니다.

## 배포 범위

2026-09-23 `regime_sources.json`의 기본 입력은 4개 bundle, 39개 진단 축이다.
런타임에서 필요한 output 파일은 **43개 JSON, 5,626,464 bytes (약 5.6 MB)**다.

| 묶음 (`output/regime_inputs/` 아래) | 필수 파일 | 개수 |
|---|---|---:|
| `kr-policy-pit-20260920/silver/` | `context.json`, `approval.json` | 2 |
| `kospi-assumed-20260921-v1/` | `context.json`, `approval.json` | 2 |
| `fmp-assumed-20260921-v1/` | `context.json`, 지정된 `approvals/` JSON 36개 | 37 |
| `kr-production-inflation-20260923-v1/` | `context.json`, `assumption-acceptance.json` | 2 |

registry, 입력 승인 정책, 관련 엔진/스크립트/테스트도 함께 버전 관리한다.
context 안에 월별 관측값이, approval 안에 검토 또는 가정 수용 내용이 포함되어 있어
런타임에서 raw 데이터, 원본 PDF, normalized 파일이나 API 키를 다시 읽지 않는다.
실제 팩터 연구 실행에는 이 묶음과 별개로 기존 인증 패널 등 연구 환경이 필요하다.

`.gitignore`는 output 전체를 기본 제외하고 정확한 파일명만 허용한다. 현재 허용된
output은 다음 **63개**다. 임의의 새 approval 파일도 자동으로 허용되지 않는다.

- 위 런타임 JSON 43개.
- 정책 README, KOSPI README/summary, FMP README/summary: 5개.
- `assumed-regime-layer-20260921-v1/README.md`, `snapshot.json`: 2개.
- 최초 한국 기업 coverage 요청의 `fmp_korea_coverage_all.csv`, `fmp_korea_missing.csv`,
  `fmp_korea_summary.csv`, `fmp_korea_field_completeness.csv`, `fmp_korea_coverage_report.md`: 5개.
- 기존 감사의 `pit_audit/fmp-20260920/report.md`, `pit_audit/fmp-20260921/report.md`,
  `pit_review_20260921/report.md`: 3개.
- 한국 생산·물가 파생 방향 `summary.json`: 1개.
- 실행 일자 정합성 `execution-alignment-20260923-v1/README.md`, `alignment.json`: 2개.
- 최종 최신성 `remediation-20260923-final/README.md`, `snapshot.json`: 2개.

README·summary·snapshot과 coverage/감사 보고서는 보존된 결과 설명이다. 런타임 의존성은
아니며, 보고서에 등장하는 모든 로컬 원본이 Git에 포함된다는 의미도 아니다.
이 파일들을 포함해도 외부 서비스 데이터의 재배포 권한을 새로 부여하지 않는다.

## 읽기 전용 검사

저장소 루트에서 실행한다. API, DB, campaign, 성과/OOS 파일은 읽지 않고 출력도 저장하지 않는다.

```sh
python -m scripts.check_regime_artifacts
python -m scripts.check_regime_artifacts --list-runtime
# 선택 파일을 stage한 뒤 또는 clean checkout에서:
python -m scripts.check_regime_artifacts --tracked-only
```

검사 대상은 enabled registry의 context byte SHA, 별도 approval byte SHA,
전체 source 객체와 approval의 결합 및 기존 승인/가정 수용 계약이다.
파일 누락·변조·checkout 밖을 가리키는 runtime 의존성은 실패한다.
`--tracked-only`는 registry와 모든 런타임 파일이 Git index에 존재하며 현재 바이트와
일치하는지도 검사한다. **이 명령은 stage/commit을 수행하지 않는다.**
`runtime_status=PASS`와 exit 0은 입력 묶음을 읽을 수 있다는 뜻일 뿐, 팩터 연구 실행이나
PIT 재인증·외부 근거의 진실성 검증 완료가 아니다.

## 원본 증빙은 별도 보관

기존 `evidence.uri`, `local_path`, provenance의 사용자 절대경로는 당시 원본 식별자다.
경로를 새 머신에 맞춰 치환하면 승인 hash까지 달라지므로 기존 파일을 덮어쓰지 않는다.
런타임 로더는 이 원본 경로를 역참조하지 않는다. 필요하면 별도의 복원 매핑을 만들고
기존 hash로 원본을 확인한다. 이 저장소에는 자동 원본 복원이나 전체 재감사 재현을 약속하는
다운로더가 포함되어 있지 않다.

검사 결과의 `reaudit`는 **직접 참조한 로컬 증빙 파일의 존재 여부만** 별도로 보고한다.
원본 내용/hash를 다시 읽지 않고, HTTP/S3 자료를 가져오지 않으며, 증빙의 중첩 참조까지
추적하지 않는다. 파일이 있어도 재감사 완료가 아니고, 빠져 있어도 이미 동결된 runtime
입력을 읽는 데 필요한 파일이라는 뜻은 아니다. 절대경로가 checkout 밖에 남는 수도 표시한다.

원본 financial 응답, Bronze mirror, normalized 데이터, PDF/HTML, 거대한 provenance,
기타 미허용 output은 로컬/상류 저장소에 **그대로 보존**하며 이번 커밋에서 제외한다.
ignore는 삭제가 아니다. `tmp/`, `.Rhistory`도 제외하며 `git add -f output/` 같은
일괄 강제 추가로 이 경계를 우회하지 않는다. 기존에 추적 중인 파일은 ignore만으로
제거되지 않으므로 선택 커밋의 staged 목록도 확인한다.

관련 계약: [REGIME_INPUTS.md](REGIME_INPUTS.md),
[regime_sources.json](regime_sources.json), [regime_assumption_policy.json](regime_assumption_policy.json).
