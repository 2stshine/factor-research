# 레퍼런스 입고와 전략 선택: 별도 판정

2026-10-16 구현. 기존 Gold 108개 값과 활성 program은 변경하지 않는다.
상세 기준은 `research/phenomena/reference-evaluation-policy-v1.json`에 고정한다.

2026-10-16 후속 사용자 요청으로 **일상 전략 탐색의 기본 경로는 갱신 없는 고정 스냅샷**이다.
`python -m scripts.run_reference_snapshot run --output <새 결과 디렉터리>`를 사용한다.
[사용법·월말 가격수익과 월초 TR의 차이](reference-snapshot-strategy.md)를 참조한다.
아래 live 비교는 유지하지만 오프라인 탐색에 갱신/인증을 강제하지 않는다.

## 두 단계의 의미

| 단계 | 질문 | 판정 | 수익률 사용 |
| --- | --- | --- | --- |
| 입고 | 정의가 명확하고, 출처·시점·값·표본이 연구용으로 적절한가? | ADMITTED / NEEDS_DATA / REJECTED | 없음 |
| 전략 비교 | 입고된 입력을 어떻게 조합할 때 비용 후 도움이 되는가? | 각 모델·포트폴리오 결과와 월별 선택 이력 | 학습 구간에서만 선택·적합; 평가 구간은 비교만 |

입고 통과는 **측정값 사용 허용**이지 한국 시장 알파 승인이나 실거래 승인이 아니다.
전략에서 선택되지 않아도 Gold에서 삭제하지 않는다. 위험 통제용 지표도 독립 수익률이
좋아야 입고되는 것은 아니다. 데이터 부족은 수익성 실패와 구분한다.

## 입고 구현

`engine/reference_admission.py`, `scripts/evaluate_reference_admission.py`.

- 정확한 활성 program·catalog·definition·dataset 연결.
- 실제 DB의 전체 Gold 행과 캐시 대조. 실패 시 파일로 우회하지 않는다.
- 월말 기준일, 개별 known_at, 유한값, 종목 식별, 중복 키 검사.
- 기존 발행 기준과 같은 최소 100종목·60개 관측 월. 종목별 60개월 보장 아님.
- 동일 수식·입력·룩백·대상 정의의 중복은 별도 거절 사유.
- 상관이 높다는 이유만으로 다른 경제적 측정값을 입고 거절하지 않는다.
- PIT_ASSUMED를 명시적으로 허용하되 최초 발표값 입증으로 표현하지 않는다.
- 검증된 Gold 계산을 재평가하는 것이며 모든 수식의 원자료 재계산은 이번 절차에 포함하지 않는다.
- 전체 역사 커버리지는 현재 인벤토리 진단이다. 과거 특정 월에 알 수 있던
  커버리지로 소급하지 않으며, 전략 선택은 월별 학습 자료에서 다시 한다.

`snapshot-audit`는 동결 파일의 명시적 사전 진단 모드다. DB 연결 실패 후 자동 선택되지
않으며 `UNVERIFIED_SNAPSHOT_ONLY`만 발행한다. 이 결과는 전략 입력 허용에 사용할 수 없다.
산출물은 불변 JSON이고, dataset별 결과를 남긴다. 재실행해도 live 모드는 DB를 다시 검증한다.

```sh
.venv/bin/python -m scripts.evaluate_reference_admission \
  --cache-receipt output/phenomena/short-eligibility-20261003/activation-audit-v3/completion.json \
  --output output/phenomena/admission-selection-20261016/live-admission-v1 \
  --mode live-admission
```

## 전략 비교 구현

`engine/reference_strategy_evaluation.py`, `scripts/evaluate_reference_strategy.py`.
기존 `phenomenon_ridge`와 월초 시가 체결 엔진을 재사용한다. 신규 비교의 입력은
입고 보고서 해시와 정확한 활성 program으로 묶이며, OBSERVED 실행은 실제 Gold 값과
개별 known_at까지 다시 대조한다. 보고서만 통과한 다른 값으로 바꿔치기할 수 없다.

세 모델을 동일한 종목·월·비용·시장 TR 기준으로 비교한다.

1. 학습 당시 사용 가능한 모든 입고 입력 + ridge.
2. 학습 월별 Rank IC의 절댓값 순서로 후보를 검토하고 상관 중복을 줄인 입력 + ridge.
3. 2의 입력 + 학습 자료로 적합한 일반 PCA + ridge.

선택 모델은 최대 30입력, PCA 10성분, ridge alpha 10을 사전에 고정한다.
학습 최대 60개월·최소 24개월·1,000행, 최소 한 달 간격과 결과의 실제 가용시각을
동시에 검사한다. 한 달 간격만으로 월초→월초 결과를 미리 쓰지 않는다.
결측률 최대 60%, 비상수, 상관 절댓값 0.95를 기준으로 학습 시점의 입력을 거른다.
모든 입력 모델도 학습에서 관측되지 않은 지표는 사유를 남기고 제외한다.
10개 PCA 성분을 만들 만큼 남지 않으면 해당 비교는 실패하며 몰래 차원을 바꾸지 않는다.

IC는 월별 횡단면 순위 상관을 계산한 후 월에 동일 비중을 준다. 음의 IC도 예측 정보일 수
있으므로 절댓값으로 순서를 정하고 방향은 ridge가 학습한다. 이는 **조건부 알파 검정이나
다중검정 보정 통과가 아니다**. 유용성은 전체 모델과 선택 모델의 짝지은 비용 후 결과로
검토한다. 위험·상호작용 통제는 단변량 IC가 약할 수 있어 모든 입력 모델도 함께 보존한다.
PCA는 주식 특성의 일반 PCA이며 RP-PCA나 수익률 요인 추정이라고 부르지 않는다.

각 모델에서 상위 20%/10% × 동일/시총제곱근 가중의 네 포트폴리오를 모두 실행한다.
각각 누적·연율 비용 후 수익률, 최대 낙폭, 시장 및 동일가중 대비 월평균 초과수익,
회전율, 비용을 출력한다. 결과를 보고 자동으로 우승 전략을 승인하지 않는다.
승격은 별도 검토이며 이 비교로 지식 그래프의 검토된 주장을 자동 생성하지 않는다.

```sh
.venv/bin/python -m scripts.evaluate_reference_strategy \
  --admission <live-admission의 admission.json> \
  --bundle <검토된 실제 월초 체결 및 학습 입력.json> \
  --contract <동결한 runtime contract.json> \
  --cache-receipt output/phenomena/short-eligibility-20261003/activation-audit-v3/completion.json \
  --registered-at <시간대가 포함된 연구 실행시각> \
  --output <새로운 결과 디렉터리>
```

수익률 입력·공식 첫 거래 세션·기업행위·시장 TR 자료가 없으면 실제 성과는 계산하지 않는다.
합성 테스트를 실제 한국 주식 성과로 보여주거나 월말 종가 수익률로 조용히 대체하지 않는다.
과거 연구에서 노출된 구간은 `HISTORICAL_REUSE`로 표시한다. 새로운 독립 OOS가 아니다.

## 적용한 근거와 한계

- [scikit-learn 데이터 누출 지침](https://scikit-learn.org/stable/common_pitfalls):
  전처리·선택을 학습 자료 안에서만 적합하는 원칙. 이것이 특정 임계값의 최적성을 보장하지는 않는다.
- [Gu, Kelly, Xiu, Empirical Asset Pricing via Machine Learning](https://doi.org/10.1093/rfs/hhaa009):
  예측 모델의 시간 분리 평가를 참고한다. 이 구현은 해당 논문의 전체 모형·실증 재현이 아니다.
- 입고 100종목·60개월은 기존 라이브러리의 운영 기준을 유지한 것. 30입력·10성분·0.95상관 등은
  논문이 보장한 보편적 최적값이 아니라 결과를 보기 전에 고정한 초기 비교 예산이다.
