# v3 전환 상태와 보존 경계

2026-10-02 · 사용자의 새 연구 방향에 따른 전환. 상세 설계는 [v3 설계](research-v3-design.md).

## 실제 전환 결과

상태: **새 기본 세대·보존·차단·합성 baseline 완료, 실자료 연구 연결 전**.
실행 영수증은 [transition-receipt-20261002.json](../research/v3/transition-receipt-20261002.json)이다.

- factor-research 2,341개 + TeamAlpha-data 289개 = **2,630개 파일 / 111,252,659 bytes** 보관·해시 검증.
  기존 campaign 314개 파일은 원본과 보관본 SHA가 모두 같다.
- 원본 캐시·raw output은 지우지 않았지만 별도 복사하지 않았다. 67개 비복사 참조와 비밀정보
  필터 한계를 manifest에 남겼다. 보관 객체는 로컬 전용이며 Git/대시보드에 게시하지 않는다.
- Gold 메타데이터 197건(기존 APPROVED 49건) 읽기 전용 인벤토리 확보. 전환 후 메타데이터
  digest도 동일하다. 전체 값 행을 덤프하거나 대사한 것은 아니며 이 작업의 Gold 쓰기는 0이다.
- `reference-factor-v3` 활성화, 신규 승인 0개. 이전 Gold 자동 fallback·직접 이름 지정·일간 캐시·
  발행/갱신 우회를 차단했다. `--legacy`도 Gold 쓰기를 복구하지 않는다.
- 문헌 참조 10개 정의 카탈로그를 작성했다. 가격 계열 4개 PENDING / 추가 계약 필요 6개 BLOCKED.
  문헌 목록과 실제 재현·승인을 분리했다.
- 최종 변경 대상 **185개 테스트 통과**. 전체 회귀는 **2,607개 통과 / 기존 알려진 원장 동일성
  문제 1개 실패**다. 마지막 좁은 guard 수정은 최종 대상 테스트에서 다시 검증했다.
- 합성 데이터에서 12개월 × 8종목 = **96개 예측**을 실행했다. 실제 팩터 성과·전략 수익은 측정하지 않았다.

커밋·푸시·웹사이트 배포는 하지 않았다.

## 이전 실행에서 보존할 것

수집·패널 갱신 프로세스는 새 구조 요청에 맞춰 중단했다. 작업별 체크포인트와 원본은 지우지 않았다.
일반 SSM 터널이나 다른 작업의 프로세스는 종료하지 않았다.

- DART 원문 수집: `output/dart-historical-statement-corpus-20261002-v1`에 중간 원문·시도 기록 보존.
  완료 run이 없는 중단본이다. 잔여 lock은 미완료 표시로 보존하며 정상 완료·PIT 인증이라고 부르지 않는다.
- 가격 패널 갱신: `.cache/research-v2-20261002-current-price-parent`의 미완료 계약 보존.
  완성된 새 패널로 사용하지 않는다.
- 이미 완료된 추가 스키마 설치: `research/v2/dart-historical-source-schema-20261002.json`.
  `fundamental_document_dataset/revenue`와 보호 trigger를 설치했지만 원본 관측값 삽입 0,
  기존 테이블 행 수정 0, Gold write 0이다. 새 전환을 이유로 스키마를 삭제하지 않는다.
- 레거시 추가 매출 overlay builder: 원장 값이 달라도 기존 feature가 결측이면 부모 패널 재현 비교를
  통과할 수 있다는 독립 감사 반례가 남아 있다. `test_historical_overlay_independent_audit.py`의
  원장 동일성 테스트를 통과하기 전 새 입력으로 승인하지 않는다. 이 문제는 v3 전환의 회귀 오류가 아니다.
- 기존 단일 매출 성장가속도 후보의 수식·부호·기간·실패 기록·봉인 결과는 변경하지 않았다.
  이 후보를 새 레퍼런스 라이브러리로 자동 승계하거나 계속 평가하지 않는다.

## 현재 도입 범위

| 부분 | 의미 |
|---|---|
| 로컬 보관본 | Git HEAD가 아니라 수정·미추적 파일을 포함한 현재 working bytes를 내용 해시로 보존 |
| 제외 항목 | 비밀정보 의심 파일, 캐시·raw output·생성 dist, 용량 초과 등은 원위치 참조만 보존; 완전 백업이라고 하지 않음 |
| 새 활성 세대 | `research/active-generation.json`이 가리키는 빈 라이브러리에서 시작 |
| 기존 Gold | 원본 값/상태를 그대로 두고 새 세대에서 제외; 물리적 DB 이동·전체 값 덤프는 아님 |
| 신규 수치 baseline | 시간순 내부 검증·PCA/no-PCA·릿지, 합성 검증 전용 CLI |
| 미도입 | 인증 실자료 adapter, 새 레퍼런스 실제 재현/승인, 기존 진단의 v3 운영 연결, 전략 실행·새 Gold publisher |

아직 새 팩터의 실증 성능이나 새 전략 수익률을 만든 상태가 아니다. 초기 라이브러리 0개는
의도한 안전 상태이며 기존 Gold로 채우지 않는다. 독립 교훈 검토 절차는 유지하되 실제 v3 trial을
진행하지 않았으므로 새 실증 교훈도 없다.

## 운영 순서

1. `python -m scripts.research_generation active --repo-root /Users/mac/Documents/GitHub/factor-research`
   로 새 세대·승인 exact set을 확인한다.
2. [문헌 카탈로그](research-v3-reference-library.md)의 입력 준비 상태를 인증 데이터와 연결한다.
3. 새 reference 정의와 사용 역할을 동결하고 실제 커버리지·시점·SQL 대사를 끝낸다.
4. 새 trial adapter에서 레퍼런스 대비 진단과 기존 packet/act → 독립 교훈 검토를 연결한다.
5. 라이브러리 선정에 사용한 기간까지 포함해 전략의 개발/검증 경계를 동결한다.
6. 실제 월초 체결 입력이 준비된 후 selection/차원 축소/릿지/비중 구성 전체를 평가한다.

`--legacy`는 이전 연구 CLI를 명시적으로 선택하는 표시이며 새 Gold 발행 권한이 아니다.
로컬 코드 가드는 운영 DB의 외부 계정 권한을 바꾸지 않으므로 다른 클라이언트까지 잠갔다고
보고하지 않는다. 향후 운영 전환에서는 새 namespace와 DB 역할 권한도 검증해야 한다.
