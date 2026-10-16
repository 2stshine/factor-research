# 2026-10-16 메인 통합 범위

이번 통합은 기존 개발 결과를 보존하는 코드 통합이다. 새로운 현상 연구, 전략 승인,
Gold 재적재, 데이터 갱신, 웹사이트 배포를 직접 수행하는 작업이 아니다.
TeamAlpha-data는 메인 병합으로 기존 GitHub Actions 배포 워크플로가 자동 실행된다.

## 포함

- 현상 중심 세대 전환, 레거시 보관 manifest와 실행 경계.
- 현상·경쟁 설명·예측·근거·독립 검토·지식 그래프 실행 틀.
- 108개 레퍼런스 정의와 Gold 입고/전략 선택 분리.
- 동결 스냅샷의 선택·PCA·릿지, 거래금액 비용 및 시기별 세금·슬리피지 진단.
- 기존 연구 v2, 월초 실행 입력 준비, 대시보드 소스와 공개용 정적 산출물.
- TeamAlpha-data의 별도 reference Gold 및 역사 공시 원천 계약.

## 공개하지 않고 로컬 보존

원시 output, parquet/pickle 패널, 비밀키, 레거시 opaque object는 기존 ignore를 유지한다.
아래 새 파일도 공개 Git에서 제외하며 삭제·내용 수정하지 않는다.

- `research/v2/new-sales-original-2015-quarter-upper-bound-20261002.json`
- `research/v2/historical-financial-identity-source-20261002.json`
- `research/v2/historical-financial-fy-receipt-reference-20261002.json`
- `research/v2/dart-parser-v2-source-shape-audit-20261002.json`
- `research/campaigns/v2-e2e-20261002-sales-acceleration/manifest.json`
- `research/campaigns/v2-production-20261002-cost-intensity/manifest.json`
- `research/campaigns/v2-production-20261002-cost-intensity-v2/manifest.json`

첫 네 파일은 종목별 추출 원천·재무 값·문서 발췌이고, 마지막 세 manifest는 공급자 시장·매크로
시계열을 내장한다. 따라서 새 clone은 해당 과거 실행을 재생할 모든 자료를 포함하지 않는다.
문서의 로컬 산출물 경로는 공개 다운로드 링크나 새 clone의 실행 준비 완료 보장이 아니다.

## 통합 중 보완

역사 재무 overlay의 기존 회귀 검사가 다른 매출 원장을 허용하는 문제를 발견했다.
월별 재생 값만 비교하면 결측 뒤의 원장 변경을 놓칠 수 있으므로 원래 부모 계약의
전체 원장 정체성도 일치해야 한다. 인코딩만 다른 경우에도 자동 허용하지 않으며,
별도 부모 계약 재작성·검증 없이는 실패한다. 기존 동결 결과·DB·가격수익률은 수정하지 않았다.

TeamAlpha-data의 두 `020_*.sql` 파일은 서로 독립적인 기존 적용 이력이다.
마이그레이션 실행기는 번호가 아닌 전체 파일명과 내용 해시로 식별하므로 이름을 변경하지 않았다.

실제 입고 상태와 탐색 성과는 [입고 보고서](reference-admission-status-20261016.md)와
[스냅샷 전략 기록](reference-snapshot-strategy.md)을 따른다. 과거 완료 문서의
당시 미커밋/미배포 기록은 역사적 사실로 보존한다.
