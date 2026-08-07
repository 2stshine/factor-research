# Campaign·epoch·봉인 OOS 프로토콜

## 목차

- [목적](#목적)
- [상태 전이](#상태-전이)
- [시작](#시작)
- [Discovery와 성찰](#discovery와-성찰)
- [자동 기준 통과](#자동-기준-통과)
- [Gold 구현 검증](#gold-구현-검증)
- [정확한 36개월 OOS](#정확한-36개월-oos)
- [일회성 공개](#일회성-공개)
- [산출물](#산출물)

## 목적

같은 OOS 결과를 본 뒤 다음 가설을 선택하는 간접 과최적화와, 사람이 좋아 보이는 후보만
confirmation에 보내는 선택 편향을 함께 막는다. 새 campaign은 `epoch-1.4`를 적용하며 역사적
cycle과 산출물은 원래 규칙의 기록으로 보존한다. 과거 결과를 본 후보에 새 경계를 소급 적용하지
않는다.

## 상태 전이

```text
campaign OPEN
  └─ epoch OPEN → 사전등록 후보 discovery 평가 → epoch CLOSED
  └─ 필요하면 다음 epoch 반복
campaign-finalize
  ├─ 비REJECT ∩ discovery BY PASS 전체 → AWAITING_IMPLEMENTATION
  └─ 해당 후보 없음                         → CLOSED_NO_QUALIFIED
AWAITING_IMPLEMENTATION → 전 후보 SQL·hash·parity PASS → READY_FOR_CONFIRMATION
READY_FOR_CONFIRMATION → 사용자 요청·readiness PASS → REVEALED(종료)
```

- `OPEN`: 후보 생성과 discovery만 허용한다.
- epoch `CLOSED`: 해당 배치의 결과와 구조화 성찰이 확정됐다.
- `AWAITING_IMPLEMENTATION`: 자동 확인 대상은 확정됐지만 생산 계산 계약이 아직 미검증이다.
- `READY_FOR_CONFIRMATION`: 전 대상의 definition/SQL hash와 Python/SQL parity까지 확정됐다.
- `CLOSED_NO_QUALIFIED`: 자동 기준을 통과한 후보 없이 종료됐다.
- `REVEALED`: 봉인 OOS를 한 번 공개한 terminal 상태다.

## 시작

부분월은 쓰지 않는다. campaign을 시작할 때 Silver의 최신 **완료 수익률월**을
`snapshot_cutoff`로 동결하고, 그 월에 미래수익이 끝나는 직전 36개 signal월을 역사적 OOS로
역산한다. discovery는 OOS 앞에서 끝내고 두 구간 사이 한 signal월을 embargo한다. snapshot에
OOS 행이 물리적으로 있어도 discovery 입력·출력에서는 숨긴다.

예를 들어 최신 완료 수익률월이 `2026-07`이면 경계는 다음과 같다.

| 용도 | signal월 | 해당 미래수익월 |
|---|---|---|
| Discovery 마지막 | `2023-05` | `2023-06` |
| Embargo | `2023-06` | `2023-07` |
| OOS 36개월 | `2023-07~2026-06` | `2023-08~2026-07` |

`2026-08` 관측이 필요하면 마지막 수익률 마감과 비활성 종목의 경계를 확인하는 데만 쓰며 OOS
IC에는 넣지 않는다. 이 예에서는 `2026-06-30 + 45일`보다 늦은 실제 Silver 관측일이어야 하므로
8월 초의 부분월만으로는 reveal하지 않는다. discovery와 OOS의 signal·미래수익 행은 겹치지 않는다.

이 구간의 IC·수익률을 후보 정의나 선택 전에 봉인했을 때만 공식 OOS다. 이미 결과가 노출된
후보는 같은 경계를 다시 적용해도 `retrospective-only`이며 승격 근거로 쓰지 않는다. 한 번
reveal한 OOS signal·수익률 구간은 이후 campaign에서 재사용하지 않는다.

```bash
uv run python scripts/research.py campaign-start --campaign campaign-001
uv run python scripts/research.py epoch-start \
  --campaign campaign-001 --epoch epoch-001 \
  --factors factor_a factor_b factor_c
```

후보 파일을 모두 작성한 뒤 결과를 보기 전에 한 번에 사전등록한다. manifest에는 이름, family,
definition hash, `snapshot_cutoff`, discovery·embargo·OOS 경계와 ruleset을 저장한다. 소스가
바뀌거나 목록에 없는 후보를 평가하면 중단한다.

## Discovery와 성찰

```bash
uv run python scripts/research.py evaluate \
  --campaign campaign-001 --epoch epoch-001 --factor factor_a
uv run python scripts/research.py epoch-close \
  --campaign campaign-001 --epoch epoch-001
```

discovery는 manifest의 discovery 경계 안에서 T0~T3와 기존 Gold 직교성을 검사한다. campaign
전체 BY 전까지 FDR은 `PENDING`이고 최종 OOS는 계산·출력·기록하지 않는다. hard fail은
`REJECT`, 나머지도 OOS가
봉인돼 있으므로 최대 `PROVISIONAL`이다. 동결 snapshot과 discovery scope를 재현하지 못하면
최신 데이터로 대체하지 않고 중단한다.

epoch은 모든 후보가 평가돼야 닫힌다. 성찰에는 실패 유형, 신규성, family 중복, 데이터 병목과
무결성 교훈만 남긴다. 성과 수치·파라미터 수정안·봉인 OOS는 다음 epoch에 전달하지 않는다.

## 자동 기준 통과

모든 epoch을 닫은 뒤 다음 명령으로 discovery를 확정한다.

```bash
uv run python scripts/research.py campaign-finalize --campaign campaign-001
```

모든 등록 정의를 하나의 family로 묶어 HAC p값에 BY를 한 번 적용한다. p값이 없으면 `p=1`로
포함한다. 그 결과 **discovery 최종 판정이 `REJECT`가 아니고 BY가 `PASS`인 후보 전부**를
`qualified_factors`로 자동 확정한다. 사람은 후보를 추가·제외하거나 일부만 골라 확인할 수 없다.
정책 식별자는 `all_discovery_non_reject_by_pass_v1`이다.

결과와 family digest는 `multiple-testing.json`에 고정한다. 한 명도 통과하지 못하면
`CLOSED_NO_QUALIFIED`로 끝내며 성공할 때까지 epoch을 추가하지 않는다. 후보 소스나 definition
hash가 이후 달라지면 reveal은 실패한다. 통과 후보가 있으면 campaign은
`AWAITING_IMPLEMENTATION`으로 전환한다.

## Gold 구현 검증

Agent는 자동 확인 대상 **전부**에 동결된 연구 정의와 같은 query-only Gold 계산 SQL을 작성하고,
Gold 테이블에는 쓰지 않는다. 생산 manifest에는 방향 계약·`research_definition_hash`·SQL URI를
기록하고, 구현 검증 artifact에는 manifest digest와 실제 SQL SHA256을 기록한다. 일부 후보만 구현하거나 구현 단계에서 경제적 정의·파라미터·
방향을 바꿀 수 없다. SQL은 read-only 연결에서 인증 Silver allowlist만 읽고 Bronze·Gold·
`fundamental_current` 같은 현재상태 relation은 읽지 않는다.
기본 구현 위치는 형제 레포 `../TeamAlpha-data/pipeline/gold/factors/`의 SQL과
`manifest.json`이며, 생산 runner는 검증된 query를 일반 Gold upsert로 감싼다.

그 뒤 다음 명령으로 모든 binding과 parity를 검증한다.

```bash
uv run python scripts/research.py campaign-verify-implementations \
  --campaign campaign-001
```

parity는 동결 Silver snapshot의 **discovery 구간만** 사용해 Python과 SQL의 key set, raw value,
`predicted_sign`을 반영한 rank가 일치하는지 확인한다. 결과에는 snapshot digest, 비교 행 수,
key mismatch, 수치 오차와 rank mismatch를 남긴다. SQL 오류는 OOS 결과를 보지 않은 채 같은 연구
정의로 고칠 수 있지만 모든 시도와 최종 SHA256을 보존한다.

전 후보가 통과해야 `READY_FOR_CONFIRMATION`이 된다. 하나라도 누락·불일치하면
`AWAITING_IMPLEMENTATION`에 머물며 OOS를 열 수 없다. 이 단계는 생산 구현의 준비 여부만
확인하며 Gold write·승인·발행을 수행하지 않는다.

## 정확한 36개월 OOS

OOS는 **정확히 36 signal개월**이고 유효한 투자 가능 Rank IC도 정확히 36개여야 한다. 한 달이
빠지거나 뒤의 월을 덧붙여 기간을 바꾸면 실패한다. 시작·종료월은 campaign 시작 때 고정한다.

경계는 최신 완료 수익률월에서 역산해 campaign 시작 때 동결한다. 늦게 reveal해도 뒤의 월을
덧붙이지 않는다. 마지막 경계 확인월은 비활성 종목과 수익률 마감 확인에만 쓰고 IC에는 넣지
않는다.

## 일회성 공개

reveal 직전에 같은 campaign scope로 귀무 보정을 만든 뒤 공개한다.

```bash
uv run python scripts/run.py null --campaign campaign-001 --n 25
uv run python scripts/research.py campaign-reveal --campaign campaign-001
```

readiness, 전체 자동 확인 대상의 definition/SQL hash와 parity, 확정 discovery 재현과 귀무
보정을 먼저 검증한다. 복구 가능한 사전조건이 실패하면 OOS를 계산하지 않아 봉인을 소비하지
않는다. 검증이 끝나면 모든
`qualified_factors`의 OOS를 동시에 한 번 공개하고 하나의 family로 BY 보정한다. p값이 없는
후보도 `p=1`로 포함해 `NOT_TESTABLE`로 실패시킨다.

결과는 `confirmation/`에 저장하고 campaign을 `REVEALED`로 종료한다. 같은 OOS를 다시 열거나
결과를 보고 종료된 후보를 수정하지 않는다. 공개된 구간은 이후 campaign의 OOS로 재사용하지
않는다. reveal과 `PROMOTE` 판정은 Gold를 쓰지 않으며,
별도 사람 검토 없이는 어떤 팩터도 자동 발행하지 않는다.

## 산출물

```text
research/campaigns/<campaign>/
├── manifest.json
├── multiple-testing.json       # finalize 때 campaign 전체 BY·qualified 확정
├── epochs/<epoch>/
│   ├── manifest.json
│   ├── reflection.json
│   └── reflection.md
├── implementation-verification.json  # manifest binding·discovery-only parity
├── implementation-attempts/          # 실패를 포함한 append-only parity 시도
└── confirmation/               # reveal 뒤 한 번만 생성
    ├── result.json
    └── report.md
```

개별 discovery의 가설·검사·수치는 `research/runs/<cycle>/`에 저장한다. `latest.md`는 campaign
상태와 경로만 요약하며 보고서 내용을 복사하지 않는다.
