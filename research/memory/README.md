# 리서치 루프 기억층 — 작업 중

> **⚠️ 아직 작업 중이다. PR 로 제안한 상태가 아니다.** 보시는 건 환영하지만 아래 미완 항목을 감안해 주세요.

`history.jsonl` 에 쌓인 시행을 다음 루프가 읽을 컨텍스트로 바꾸는 층이다.
`research/context/latest.md` 와 `engine/` 은 **건드리지 않는다.** 옆에 얹기만 한다.

## 파일

| 파일 | 상태 |
|---|---|
| `taxonomy.md` | 축 정의 3개 · 레코드 스키마 · 반출 범위 |
| `references.md` | OSAP · JKP 인용과 라이선스 자세 |
| `labels.jsonl` | 시행별 라벨 |
| `lessons.md` | `scripts/lessons.py` 가 만드는 생성물 |
| `build_labels.py` | 라벨의 근거 표. 고치고 재실행하면 `labels.jsonl` 이 갱신된다 |
| `ab-test.md` | **컨텍스트가 행동을 바꾸는지 잰 기록.** 1차는 효과 없음 |

```bash
python scripts/lessons.py                   # lessons.md 갱신
python scripts/lessons.py --view crosstab   # 분류 교차표
python scripts/lessons.py --view before-after
```

## 미완 — 리뷰 전에 알아야 할 것

1. **42건 전부 라벨했으나 28건이 `confidence: low`** 다. 근거를 특정하지 못한 값이 하나라도 있으면 low 로 뒀다. 검토 전이다.
2. **문헌 대응이 아예 없는 3건**(`nonoperating_burden_to_assets` · `paid_in_capital_ratio` · `positive_return_share_12m`)은 축을 비웠다. OSAP 331·JKP 153 어디에도 없다.
3. **`analysis` 필드가 전부 `null`** 이다. 사람이 읽는 근거 슬롯이고 아직 안 채웠다.
4. **테스트가 `tests/` 에 없다.** 시나리오는 통과를 확인했지만 `tests/` 는 이 작업 범위 밖으로 뒀다. 필요하면 올린다.
5. **컨텍스트 효과는 2차에서 확인됐다** — 개념 중복률 무컨텍스트 83% / 나열형 33% / 지시형 17%. 다만 n=3/군이고 판정자가 설계자다. **이 층을 손대기 전에 `ab-test.md` 를 먼저 읽으라.**

## 설계 메모

- 컨텍스트로 나가는 것은 **정체성 정보와 구조적 교훈뿐**이다. 판정 결과·검사 이름·성과 수치·결과 집계는 화이트리스트가 막는다. 봉인 OOS 를 지키기 위한 제약이다.
- 분류 축은 직접 만들지 않았다. 손으로 묶은 초안을 데이터에 대보니 다섯 자리가 뒤집혀, 공개된 배정(OSAP · JKP)을 쓴다. 근거는 `references.md`.
- 교차표는 **13 테마를 항상 전부** 표시한다. 관측이 0 인 행을 지우지 않는다 — 빈 행이 조용히 사라지는 것이 이 작업이 고치려는 결함 그 자체다.
- 계보는 `variant_of` 엣지에서 유도한다. 별도 그래프 저장소를 만들지 않는다.
