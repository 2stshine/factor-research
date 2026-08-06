# Campaign·epoch·봉인 OOS 프로토콜

## 목차

- [목적](#목적)
- [상태 전이](#상태-전이)
- [시작](#시작)
- [Discovery](#discovery)
- [성찰](#성찰)
- [Survivor 동결](#survivor-동결)
- [최종 OOS 공개](#최종-oos-공개)
- [산출물](#산출물)

## 목적

같은 OOS 결과를 본 뒤 다음 가설을 선택하는 간접 과최적화를 막는다. 기존 cycle 1~27은 이미
OOS를 본 레거시 연구로 보존하고, 새 campaign부터 `epoch-1.2`를 적용한다.

## 상태 전이

```text
campaign OPEN
  └─ epoch OPEN → 모든 사전등록 후보 discovery 평가 → epoch CLOSED
  └─ 필요하면 다음 epoch 반복
campaign FROZEN → 최소 OOS 기간 대기 → campaign REVEALED(종료)
campaign CLOSED_NO_SURVIVOR                    (통과 후보가 없을 때 종료)
```

- `OPEN`: 후보 생성과 discovery만 허용한다.
- `CLOSED`: 해당 epoch 후보와 성찰이 확정됐다.
- `FROZEN`: survivor 이름과 definition hash가 고정됐다.
- `CLOSED_NO_SURVIVOR`: BY 판정 뒤 확인할 후보 없이 종료됐다.
- `REVEALED`: 봉인 OOS를 한 번 공개한 terminal 상태다.

## 시작

현재 월의 Silver 행은 부분월일 수 있으므로 discovery cutoff에는 마지막으로 완료된 월만 쓴다.
최신 Silver 월이 현재 월이면 직전 월을 cutoff로 두고 현재 부분월은 embargo한다. OOS는 campaign
생성 시점의 **다음 달이 가장 이른 시작**이며, 겹침 회피를 위해 더 늦은 월을 결과 전에 고정할
수 있다. Silver 적재가 오래 지연됐더라도 이미 실현된 역사 월을
새 OOS로 선언하지 않고, 마지막 완료 cutoff부터 현재 월까지를 embargo한다. 여러 campaign을
만들 수는 있지만 같은 미래 구간을 여러 번 확인하지 않도록 `OPEN`·`FROZEN` campaign의 OOS
기간은 겹칠 수 없다.

```bash
uv run python scripts/research.py campaign-start --campaign campaign-001
```

후보 파일들을 모두 작성한 뒤 결과를 보기 전에 한 번에 사전등록한다.

```bash
uv run python scripts/research.py epoch-start \
  --campaign campaign-001 --epoch epoch-001 \
  --factors factor_a factor_b factor_c
```

manifest에는 이름, family, definition hash, ruleset, data cutoff가 저장된다. 이후 소스가 바뀌거나
목록에 없는 후보를 평가하면 명령이 실패한다.

## Discovery

```bash
uv run python scripts/research.py evaluate \
  --campaign campaign-001 --epoch epoch-001 --factor factor_a
```

discovery는 알려진 Silver 데이터에서 T0~T3와 직교성을 검사한다. 후보별 보고서의 개발 IC
다중검정은 campaign을 동결하기 전까지 `PENDING`이다. 최종 OOS IC와 귀무 보정은 계산하지
않으며 결과에는 `oos_sealed`가 붙는다. hard fail은 `REJECT`, 살아남은 후보는 OOS 미확인
상태이므로 최대 `PROVISIONAL`이다.

후보 코드와 gate에는 manifest의 `data_cutoff` 이하이면서 OOS 시작 전인 행만 전달한다. 현재
캐시에서 cutoff 날짜를 정확히 재현하지 못하면 더 최신 데이터로 대신하지 않고 평가를 중단한다.

## 성찰

```bash
uv run python scripts/research.py epoch-close \
  --campaign campaign-001 --epoch epoch-001
```

모든 후보가 평가되어야 닫힌다. epoch close는 후보 결과와 구조화 성찰만 동결하며 FDR은 계속
`PENDING`이다. `reflection.json/md`에는 숫자 표를 복사하지 않고 다음만 기록한다.

- 실패 유형: 데이터·무결성, 예측력, 강건성·데이터 공백, 다중검정, 중복
- 로컬 신규성: `INDEPENDENT`, `RELATED`, `DUPLICATE`, `UNMEASURED`
- 다음 epoch에서 허용되는 구조적 학습
- 부호·룩백·산식·임계값 수정 및 OOS 열람 금지

다음 epoch를 만들기 전에 `latest.md`가 가리키는 가장 최근 `reflection.md`를 읽는다. 보고서 수치가
아니라 family 중복, 데이터 병목, 무결성 실패 같은 구조적 교훈만 새 후보 선택에 사용한다.

## Survivor 동결

모든 epoch을 닫은 뒤 campaign의 모든 등록 후보를 한 family로 묶어 discovery HAC p값에 BY
보정을 한 번 적용한다. 유효 p값이 없는 후보도 `p=1`로 family 크기에 포함한다. 결과는 campaign
루트의 `multiple-testing.json`에 family digest와 함께 고정된다. 그 뒤 최종 `REJECT`가 아닌
후보 중 사용자가 명시한 후보를 survivor로 동결한다. 선택은 봉인 OOS를 보기 전에 끝나며,
생략한 후보를 같은 campaign OOS로 나중에 다시 확인할 수 없다. epoch별로 먼저 판정하지 않으므로
뒤의 epoch 때문에 과거 판정이 조용히 달라지지 않는다.

```bash
uv run python scripts/research.py campaign-freeze \
  --campaign campaign-001 --factors factor_a factor_c
```

동결 뒤 후보 소스 해시가 달라지면 reveal이 실패한다.
통과 후보가 하나도 없으면 `--factors`를 생략한다. campaign은 `CLOSED_NO_SURVIVOR`로 끝나며,
성공할 때까지 epoch을 추가하는 optional stopping을 하지 않는다.

## 최종 OOS 공개

현재 구간은 60 signal개월로 고정되며 유효한 투자 가능 IC도 60개가 필요하다. 예를 들어
2026-09에 campaign을 만들고 완료 cutoff가 2026-08이면 가장 이른 OOS는 2026-10이다. signal
구간은 2026-10~2031-09로 고정되고 마지막 signal의 다음 달 수익률까지 필요하므로 가장 마지막
수익률 월은 2031-10이다. 2031-10이 부분월이 아님을 확인할 2031-11 관측 뒤에야 공개한다.
이 확정 월은 OOS 경계에서 사라진 종목의 45일 비활성 여부를 판정할 만큼 진행돼야 한다. 수익률
행은 2031-09까지만 쓰고, 확정 월은 월마감·비활성 판정에만 사용한다. 더 늦게 reveal해도 고정
구간 뒤의 월을 덧붙여 판정을 바꾸지 않는다.

```bash
uv run python scripts/research.py campaign-reveal --campaign campaign-001
```

readiness, survivor hash, 최신 snapshot용 귀무 보정을 모두 통과해야 한다. 동시에 공개하는
모든 survivor의 OOS p값도 하나의 family로 BY 보정한다. p값이 없는 survivor도 `p=1`로
포함하고 `NOT_TESTABLE`로 실패시킨다. 결과는
`research/campaigns/<campaign>/confirmation/`에 저장되고 campaign은 종료된다. reveal은 Gold에
쓰지 않는다. 귀무 보정 scope나 동결 discovery 재현이 실패하면 실제 survivor OOS를 계산하기
전에 중단하므로, 운영 입력을 복구한 뒤 같은 봉인을 소비하지 않고 재시도할 수 있다.

reveal 직전에는 campaign manifest와 같은 OOS 시작점으로 귀무 보정을 만든다.

```bash
uv run python scripts/run.py null --campaign campaign-001 --n 25
```

귀무 보정은 실제 discovery/OOS family 크기, Gold 신호 digest, closure 시점의 Silver panel
content digest에 결박된다. 네 귀무 생성기 각각 25개 family를 만들며, 전체 평균이 아니라 가장
나쁜 생성기의 family 오류율도 기준 이하여야 한다.

## 산출물

```text
research/campaigns/<campaign>/
├── manifest.json
├── multiple-testing.json       # freeze 때 campaign 전체 discovery BY 확정
├── epochs/<epoch>/
│   ├── manifest.json
│   ├── reflection.json
│   └── reflection.md
└── confirmation/              # reveal 뒤에만 생성
    ├── result.json
    └── report.md
```

개별 discovery의 가설·검사·수치는 기존 `research/runs/<cycle>/`에 저장한다. `latest.md`는 campaign
상태와 경로만 요약하며 보고서 내용을 복사하지 않는다.
