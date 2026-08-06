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
OOS를 본 레거시 연구로 보존하고, 새 연구부터 `epoch-1.0`을 적용한다.

## 상태 전이

```text
campaign OPEN
  └─ epoch OPEN → 모든 사전등록 후보 discovery 평가 → epoch CLOSED
  └─ 필요하면 다음 epoch 반복
campaign FROZEN → 최소 OOS 기간 대기 → campaign REVEALED(종료)
```

- `OPEN`: 후보 생성과 discovery만 허용한다.
- `CLOSED`: 해당 epoch 후보와 성찰이 확정됐다.
- `FROZEN`: survivor 이름과 definition hash가 고정됐다.
- `REVEALED`: 봉인 OOS를 한 번 공개한 terminal 상태다.

## 시작

현재 Silver cutoff 다음 달을 기본 OOS 시작으로 campaign을 만든다.

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

discovery는 알려진 Silver 데이터에서 T0~T3, 개발 IC 다중검정, 직교성을 검사한다. 최종 OOS IC와
귀무 보정은 계산하지 않으며 결과에는 `oos_sealed`가 붙는다. hard fail은 `REJECT`, 살아남은
후보는 OOS 미확인 상태이므로 최대 `PROVISIONAL`이다.

후보 코드와 gate에는 manifest의 `data_cutoff` 이하이면서 OOS 시작 전인 행만 전달한다. 현재
캐시에서 cutoff 날짜를 정확히 재현하지 못하면 더 최신 데이터로 대신하지 않고 평가를 중단한다.

## 성찰

```bash
uv run python scripts/research.py epoch-close \
  --campaign campaign-001 --epoch epoch-001
```

모든 후보가 평가되어야 닫힌다. `reflection.json/md`에는 숫자 표를 복사하지 않고 다음만 기록한다.

- 실패 유형: 데이터·무결성, 예측력, 강건성·데이터 공백, 다중검정, 중복
- 로컬 신규성: `INDEPENDENT`, `RELATED`, `DUPLICATE`, `UNMEASURED`
- 다음 epoch에서 허용되는 구조적 학습
- 부호·룩백·산식·임계값 수정 및 OOS 열람 금지

다음 epoch를 만들기 전에 `latest.md`가 가리키는 가장 최근 `reflection.md`를 읽는다. 보고서 수치가
아니라 family 중복, 데이터 병목, 무결성 실패 같은 구조적 교훈만 새 후보 선택에 사용한다.

## Survivor 동결

모든 epoch을 닫은 뒤 discovery `REJECT`가 아닌 후보만 동결한다.

```bash
uv run python scripts/research.py campaign-freeze \
  --campaign campaign-001 --factors factor_a factor_c
```

동결 뒤 후보 소스 해시가 달라지면 reveal이 실패한다.

## 최종 OOS 공개

현재 최소 기간은 24 IC개월이다. 예를 들어 cutoff가 2026-08이고 OOS가 2026-09에 시작하면,
마지막 signal의 다음 달 수익률까지 필요하므로 가장 이른 데이터 월은 2028-09다.

```bash
uv run python scripts/research.py campaign-reveal --campaign campaign-001
```

readiness, survivor hash, 최신 snapshot용 귀무 보정을 모두 통과해야 한다. 결과는
`research/campaigns/<campaign>/confirmation/`에 저장되고 campaign은 종료된다. reveal은 Gold에
쓰지 않는다.

reveal 직전에는 campaign manifest와 같은 OOS 시작점으로 귀무 보정을 만든다.

```bash
uv run python scripts/run.py null --n 25 --oos-start 2026-09
```

## 산출물

```text
research/campaigns/<campaign>/
├── manifest.json
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
