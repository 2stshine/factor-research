# 현상 중심 연구 프레임워크

## 무엇이 바뀌었나

연구 단위가 “팩터 하나의 합격/탈락”에서 **현상 질문과 경쟁 설명을 구분하는 연구**로 바뀐다.
레퍼런스 팩터는 유명하다는 이유로 수익성을 승인하는 대상이 아니라 현상을 측정하고
규모·모멘텀·유동성 같은 대안 설명을 통제하는 공통 도구다. 전략 생성은 지식 축적과 분리한다.

흐름: 질문 → 경쟁 설명 → 관측 가능한 예측 → 자료 확인 → 검사 선택·실행 → 독립 검토 → 범위가 명시된 지식 → 전략 명세·검증.

| 계층 | 저장하는 것 | 하지 않는 것 |
|---|---|---|
| 데이터 탐색 | 요구사항, 실제 검색 기록, 원천/권한/PIT 검토, 원본 해시, 검증된 스냅샷 | 다운로드 성공을 PIT 승인으로 간주 |
| 레퍼런스 | 논문 정의, 국내 적용 차이, 입력 계약, 검증된 측정치 | 유명한 팩터를 수익성 승인으로 간주 |
| 연구 그래프 | 질문·경쟁 가설·예측·AND 논증·실험·관측·검토 주장·반론 | 그래프 연결을 시장 인과관계로 간주 |
| 연구 실행 | 선택 이유, 고정 입력, 검사별 결과, 전체 예산, 종료 이유 | 마음에 드는 결과만 남기기 |
| 전략 실행 | 지식 스냅샷, 사전 명세, 월초 체결 모형, 비용, 모든 비교 변형 | 자동 매매/alpha 승격 |

## 논문을 어떻게 적용했나

- [POPPER, ICML 2025](https://proceedings.mlr.press/v267/huang25n.html): 가설을 검사 가능한 함의로 나누고 다음 실험을 선택하는 방향.
  논문의 검정 보장을 금융 자료에 자동 이식하지 않았다. 현재 그래프 연산은 서술통계이며
  금융 의존성·적응적 반복 검정까지 보장하는 유의확률을 출력하지 않는다.
- [Argument Interchange Format](https://www.mit.edu/~irahwan/docs/KER2006.pdf): 여러 전제를 함께 필요로 하는
  별도 논증 노드와 반론 관계. 단순한 “A→B” 간선으로 연역의 전제를 생략하지 않는다.
- [Nanopublication](https://nanopub.net/guidelines/working_draft/), [W3C PROV-O](https://www.w3.org/TR/prov-o/):
  주장·출처·검토/발행 정보를 구분하고 파생 관계를 기록한다. PROV 파생 관계는 경제적 원인이 아니다.
- [SciAgents](https://arxiv.org/html/2409.05556v1): 지식 구조를 가설 생성에 활용하는 발상.
  생성된 문장과 실제 관측의 상태를 엄격히 분리한다.
- [Stateful Discovery](https://arxiv.org/html/2606.11851v2): 지속 상태와 연구 전선, 개별 가설 검사를 분리하는
  구조를 참고한다. 해당 논문의 평가가 우리 시장의 초과수익을 보장한다는 의미는 아니다.

이 구현은 위 연구를 목적에 맞게 조합한 설계다. 논문 시스템을 그대로 복제하거나 같은 성능을
재현했다는 주장은 하지 않는다. 레퍼런스 공식의 1차 출처는 각 catalog 항목에 별도 기록한다.

## 그래프가 보존하는 구분

- `hypothesis`: 아직 검증하지 않은 설명.
- `prediction`: 설명이 맞으면 어떤 관측이 있어야 하는가.
- `argument`: **모든 전제 + 가정 + 추론 규칙**으로 제안한 결론. 자체로 실증 근거가 아니다.
- `source`: 시점과 역할이 명확한 고정 입력.
- `test_plan / test_run / evidence`: 해보기로 한 것, 실제 실행한 것, 실제 관측값을 구분.
- `claim`: 독립 검토한 제한적 결론. 동일 질문의 반대 관측도 반드시 다룬다.
- `strategy`: 특정 지식 스냅샷을 사용한 별도 연구 설계.

새 근거가 붙으면 과거 주장은 `REVIEW_REQUIRED`가 된다. 원천 무효화는 하위 의존성으로 전파한다.
정정 시에는 새 원천·새 검토를 추가한다. 무효화된 근거는 `EXCLUDED_INVALID`로 이유를 남기며
계속 보이지만 새 전략의 필수 전제로 삼지 않는다. 단순히 불리한 근거는 제외할 수 없다.

## 데이터가 없는 경우

`engine/research_data_sources.py`는 예산이 있는 데이터 요구사항을 만든다.
내부 카탈로그 검색은 직접 실행하고, 외부 검색은 호스트 에이전트가 실제 웹 검색 도구를 사용한 뒤
검색어·결과를 기록한다. 이 CLI 자체에 검색 모델이나 상시 스케줄러가 내장된 것은 아니다.

공개 HTTPS CSV/JSON은 원천과 다운로드 허용 범위를 검토한 후 제한된 크기·시간으로 가져온다.
사설 IP/인증 URL/위험한 리다이렉트를 차단하며, 데이터에 들어 있는 지시를 실행하지 않는다.
로컬 원본은 사전 등록한 정확한 해시로 캡처한다. 원본은 로컬 Bronze-equivalent이며
TeamAlpha Bronze DB에 게시했다는 의미가 아니다.

원본을 확보한 다음 스키마·범위·숫자·known_at·명시한 날짜/종목 커버리지를 검사한다.
공급자 특유의 중첩 JSON이나 발표일 추출은 별도 검토된 정규화 adapter가 필요하다.
`phenomenon_inputs`는 이미 정규화된 행만 가져오며, 관측일을 발표일로 바꾸지 않는다.
원천 이용 승인 철회와 해시 변조는 후속 실행 때 다시 확인한다.

자료를 못 찾으면 `NO_EVIDENCE`로 종료하거나 연결된 새 요구사항을 만든다.
대체변수, 범위 축소, 새 유료 원천은 묵시적으로 선택하지 않는다.

## 두 종류의 시간

| 시간 | 의미 |
|---|---|
| observation_at | 현상을 측정한 시점 |
| feature_known_at | 당시 의사결정자가 입력을 알 수 있었던 시점 |
| decision_at | 시장 판단 시점 |
| outcome_known_at | 이후 결과를 평가자가 볼 수 있게 된 시점 |
| 연구 known_at | 현재 연구가 해당 자료·판단을 기록한 시점 |

`feature_known_at ≤ decision_at`, `outcome_known_at ≤ 연구 known_at`을 각각 검사한다.
지금 검증한 자료를 과거에 연구자가 승인했던 것처럼 역산하지 않는다.
`PIT_ASSUMED`는 사전 허용·표시할 수 있지만 최초 발표값이 검증됐다는 표현은 금지한다.

## 실행 방법

```bash
# 새 활성 연구 graph는 비어 있는 별도 디렉터리로 시작한다.
.venv/bin/python -m scripts.phenomena --root research/phenomena/active-graph \
  init --actors research/phenomena/actors.json

# 질문/가설/검사 등의 구체적 JSON action을 생성한 뒤 전달한다.
.venv/bin/python -m scripts.phenomena --root research/phenomena/active-graph act --input action.json
.venv/bin/python -m scripts.phenomena --root research/phenomena/active-graph packet --study-id STUDY_ID
.venv/bin/python -m scripts.phenomena --root research/phenomena/active-graph search --query '유동성'

# 안전한 전체 소프트웨어 실행; 매번 새 output 디렉터리 사용.
.venv/bin/python -m scripts.phenomenon_demo --output output/phenomena/my-demo

# 데이터 탐색의 단계별 명령/옵션
.venv/bin/python -m scripts.research_data_sources --help

# 실제 인증 가격 입력 → 독립 SQL 대조. 기본은 Gold 쓰기 없는 dry-run.
.venv/bin/python -m scripts.reference_library build --output output/phenomena/reference-build
# 완료된 입력 스냅샷을 다시 검증하고 새 Gold namespace에만 게시.
.venv/bin/python -m scripts.reference_library publish --output output/phenomena/reference-build --apply
```

호스트는 `packet`을 읽고 다음 검사 또는 자료 탐색을 제안한다. executor는 허용 연산만 실행한다.
`choose`는 미리 적은 우선순위와 예산을 검증하는 결정론적 선택기이며,
자체 학습한 정보가치 추정이나 내장 LLM이 아니다. 독립 reviewer는 반대 근거와 한계를 검토한다.
CLI action schema의 실행 가능한 예시는 `scripts/phenomenon_demo.py`와 각 테스트에 있다.

지식 검색은 현재 사용할 수 있는 독립 검토 주장만 대상으로 하며 합성 결과는 기본 제외한다.
질문·가설·주장의 어휘와 명시한 유니버스로 찾고 수익률순으로 정렬하지 않는다.
검색 결과에는 주장만 아니라 반대 근거·한계·의존성과 전체 지식 스냅샷을 같이 붙인다.
지금은 결정론적 검색이며 embedding/GraphRAG의 성능을 검증했다는 뜻은 아니다.

## 레퍼런스 라이브러리와 Gold

[정의·계산·차이·제약](reference-library-phenomena.md)의 최초 v1 기록은 가격 기반 7개와
입력 미준비 9개를 구분한다. 2026-10-03 확장은 별도의 고정 카탈로그에 기존 7개와 신규 38개,
총 45개 측정치를 정의했다. DART FY의 실제 가용 공시를 연결하는 신규 재무 adapter를 사용하며,
기존 차단 정의를 이름만 바꿔 승인하거나 한국 수익률을 보고 항목을 골라내지 않는다.
[문헌 및 원형과의 차이](reference-expansion-literature-20261003.md)를 함께 읽는다.

2026-10-03 신규 38개·9,865,877행의 커밋·그룹별 전 행 대조를 완료했다.
기존 현상 연구 레퍼런스 7개·2,119,881행을 보존·결합해 **45개·11,985,758행·14개 불변 dataset**이다.
[확장 적재 완료 보고서](reference-expansion-completion-20261003.md)를 참고한다.
전체 14개 dataset·11,985,758행 재조회 후 collection 활성 프로그램 v2 전환을 완료했다.
실제 활성 항목은 [program.json](../research/phenomena/program.json)에 명시된 dataset 목록으로만 결정한다.
이번 적재는 **2026-09 월말 기준 일회성 스냅샷**이며 일일 갱신 배포가 아니다.
`PIT_ASSUMED`이고 최초 발표 빈티지는 독립 미입증이다. 적재·SQL 대조는 측정 검증이지
알파 승인이 아니며, 모든 종목에 동일한 길이의 history가 있음을 보장하지 않는다.

새 테이블은 `gold.reference_definition`, `gold.reference_dataset`, `gold.reference_value`다.
기존 `gold.factor`와 기존 Gold 팩터 값은 수정하지 않는다. 불변 dataset마다 입력·정의·코드·SQL
대조·값 해시를 묶고 전체 read-back을 검사한다. 업데이트·삭제·TRUNCATE를 막는다.
특권 DB 소유자나 파일 전체를 수정할 수 있는 공격자까지 막는 보안 시스템은 아니다.

신호는 raw 측정값이다. 방향은 catalog에 별도로 기록하며, 사이즈는 issue 시총 기준 등
원 논문의 포트폴리오 수익률/기업 집계와 다른 부분을 표시한다. 총수익 지수나 legacy 승인
팩터를 계산 입력으로 은밀히 대체하지 않는다.

## 검증 범위와 남는 경계

- 합성 E2E는 분기·회계·시점·무효화가 맞게 작동하는지 검사한다. 실제 시장 가설을 확인하지 않는다.
- 레퍼런스 계산/SQL parity는 측정 재현성이지 경제적 효과나 초과수익의 확인이 아니다.
- confirmation에는 별도 프로토콜·표본·노출 원장이 필요하다. 이름을 바꿔 같은 자료를 새 OOS로 쓸 수 없다.
- 월초 시가 백테스트는 실제 체결 보증이 아니다. 주문/호가·종목별 시장충격/최종 청산 등의 한계는
  런타임 결과에 표시된다. 실제 배포·매매에는 별도 승인과 운영 연결이 필요하다.
- 현재 허용 연산은 서술통계 세 가지다. 업종 내 비교·블록 부트스트랩·패널 회귀 등 새 검사는
  계약과 테스트를 추가한 후 연산 registry에 올려야 하며, 아직 실행되지 않은 것으로 표시한다.
- 코드·데이터 접근·예산이 통제된 연구 틀을 완성하는 것과, 모든 가능한 데이터를 확보하거나
  모든 경제 현상을 설명하는 것은 다른 완료 조건이다.

## 선택·차원 축소·릿지의 실제 연결

`engine/phenomenon_ridge.py`가 `TRAIN_ONLY_RIDGE` 전략을 월별로 실행한다.
학습 feature와 수익 label을 별도 배열로 고정한다. 각 월말에 **이미 종료됐고 결과도 알려진**
open-to-open 구간만 학습에 포함한다. 학습 구간의 결측률·분산을 점검하고 사전에 정한
순서에서 상관이 중복되는 특징을 제거한다. 그 안에서 결측 대체·표준화·선택적 PCA·릿지를 적합한다.

수익률은 릿지의 학습 목표에 반영된다. 선택은 현재 수익률 순위가 아니라 학습 자료의
커버리지/분산/중복 기준이다. alpha·PCA 차원·학습 길이·최소 표본을 결과를 보기 전에 고정하며,
검증 수익이 가장 좋은 설정을 자동 탐색하지 않는다. no-PCA 릿지 예측도 함께 보존한다.
시장 설명력이 높거나 독립 alpha라는 결론은 이 회계/시점 검사만으로 내리지 않는다.

## 입력 회복과 식별자 검토

실제 2026-10-02 가격 추출은 모든 44묶음이 끝난 뒤 숫자 전용 ticker 검사에서 중단됐다.
실행 로그의 완료를 명시적으로 검토하고 전체 체크포인트 해시·query·기간·종목 묶음을 묶어
`scripts/recover_reference_build.py`로 입력을 회복했다. 부분 추출을 자동으로 완료로 간주하지 않는다.
원래 조회 당시의 최대 source date는 저장되지 않아 재구성하지 않았으며, 실제 요청 종료일과
월별 원본은 보존했다. 회복 자체는 SQL parity나 Gold 적재 승인이 아니다.

종목코드는 숫자로 변환하지 않는 6자리 대문자 ASCII 영숫자 문자열이다.
보통주로 분류돼 있으면서 비영(非0) 접미사를 가진 두 항목은 원천 분류 검토 대상으로 격리했다.
원천 `public.asset`은 수정하지 않았다. DQ 인증과 수치 재현은 최초 발표 vintage의 독립 확인이
아니며, 기존에 수용한 가격 feature 계약과 관측일 종료 시각 가정을 명시한다.

세대 전환의 `apply=False`는 새 불변 manifest를 준비하지만 활성 포인터를 바꾸지는 않는다.
실제 전환은 이전 포인터 해시를 지정한 compare-and-swap으로 하며 이전 바이트를 보존한다.
