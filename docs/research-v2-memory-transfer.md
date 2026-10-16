# 새 연구에서 v2 기억을 사용하는 계약

이 문서는 코드에 구현된 기억 전달·사용 기록의 범위를 설명한다. 기억 검색 자체는
새 후보 생성, 팩터 합격, 독립 OOS, Gold 적재를 수행하지 않는다. 모델 가중치도 바꾸지 않는다.

## 두 경로

1. 원래 증거와 범위가 일치하면 검토된 원본 교훈을 검색한다.
2. 범위가 달라지면 자동 일반화하지 않는다. `transfer-template`으로 출처와 새 범위를
   묶은 제안을 만들고, 변경된 모든 차원의 이유와 전달할 절차적 주의·검사 설계·미해결
   질문을 적는다. 독립 비평자의 실제 ACCEPT가 정확한 제안 hash와 연결된 경우에만
   `transfer-review`로 승인 artifact를 만든다.

두 번째 경로도 원래 교훈의 관측 사실이 새 팩터에서 재현됐다는 뜻은 아니다.
`PROCEDURAL_ONLY_NOT_TARGET_EVIDENCE`를 붙이고, 원래 범위·사실·해석·미확인 사항·한계를
보존한다. 숫자 성과, 최적 기간·파라미터 처방, 자동 방향 뒤집기는 전달하지 않는다.
논리적 역할 분리와 파일 hash 검사이며 OS 수준 격리나 경제적 진실 인증은 아니다.

## 실행 순서

`python -m scripts.research_v2_memory --help`에서 옵션을 확인한다.

1. 동결할 팩터마다 정확한 target scope를 JSON으로 만든다. 시장, 유니버스, 기간, 지평,
   팩터 정의 hash, 가용 지연, 데이터 스냅샷, PIT 정책, 비용 모형, 프로토콜,
   레짐 정의, 작업 종류의 열두 필드를 생략 없이 적는다. 와일드카드는 허용하지 않는다.
2. 필요한 경우 `transfer-template` → 제안 작성 → `transfer-propose` → 실제 독립 비평 →
   `transfer-review`를 거친다. 프로그램은 비평자의 답을 만들어주지 않는다.
3. `campaign-context --target-scope ... --task-id ... --query ... --research-as-of ...`
   를 실행한다. 승인된 전이가 있으면 `--transfer-approval`을 전달한다.
   전체 적격 교훈은 최대 세 개, 반환 맥락은 UTF-8 기준 최대 32 KiB다. 넘으면 검색 기록을
   쓰기 전에 실패하며, 승인된 교훈이나 한계 문장을 몰래 생략·축약하지 않는다.
4. 반환된 각 `entry_id`를 사용하거나 배제한 이유를 `{"used":{},"rejected":{}}` 형태로
   채운 뒤 `campaign-usage --context ... --usage-file ... --task-id ... --key ...`로 기록한다.
   검색 영 건도 유효하지만 빈 사용 확인은 남긴다. 실제 노출이 없을 때만 호스트가 이 빈
   확인을 자동 기록할 수 있다. 내용이 있으면 사용자의 에이전트가 실제 판단해야 한다.
5. 등록 전에 `campaign-check` 또는 `require_campaign_memory_usage`로 범위, 작업 ID,
   원본 유효성, 실제 검색 영수증, 사용/배제 기록을 확인한다. 원본 무효화·격리·새 검토본에
   의한 교체가 발생하면 기존 맥락을 그대로 등록할 수 없다.

`research_as_of`는 현재 연구자가 교훈을 알 수 있었던 연구 시각이다. 과거 시장 신호일로
소급하지 않는다. 같은 과거 구간에서 교훈을 이용해 만든 후속 후보는 연구용 반복 검증이며,
배치를 바꿔도 독립 미사용 데이터가 되지 않는다.

## 다음 교훈의 활성화

기존 실제 파일럿 교훈 여섯 개는 그대로 보존한다. 새 운영 Discovery 결과의 독립 검토가
완료되면 `release_mode=PRODUCTION_DISCOVERY`인 공개 정성 번들을
`activate-production --release-root ...`에 전달할 수 있다. 기존 공개 필터가 원본·초안·
비평·시각·hash를 모두 재확인하고, 새로운 교훈을 별도 불변 claim ID로 기록한다.

명령은 `production-memory-activation.json`과 `proposed_pointer`를 만들 뿐 활성 포인터를
스스로 덮어쓰지 않는다. 호스트가 결과를 확인하고 포인터의 `additional_releases`와
`reviewed_lessons`를 반영해야 다음 검색에서 보인다. 이전 여섯 개를 바꾸거나 구형 교훈을
자동 수입하지 않는다. 추가 공개가 생겨도 이미 동결한 맥락은 보존하되 출처 무효화는 막는다.

핵심 API는 `engine/research_memory_transfer.py`에 있다. 그래프 검색과 효용 가중치는 꺼져
있으며, 사용 횟수를 인과적 유용성이나 투자 성과로 바꾸지 않는다.
