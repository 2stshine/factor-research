# 레짐 판독·레슨런 검토 — 2026-09-23

상태: **검토 완료 / 개선안은 미구현**. 새 연구·DB 조회·봉인 OOS 열람·과거 결과 수정 없이
코드, 합성 테스트, 공개 필터를 거친 연구 스냅샷, 기존 입력 요약을 검토했다.
KNOWLEDGE 문헌은 17건에서 23건으로 보강했다. 문헌은 국내 실증 교훈 건수에 합산하지 않는다.

## 결론

현재 레이어는 **월말 정보에 따른 시장 환경을 설명하는 보조 진단**으로 사용할 수 있다.
시점·결측·동결 경계는 잘 방어하지만, **경제 국면을 정확하게 예측한다거나 국면별 팩터 선택이
효과적이라는 검증은 아니다**. 기존 PIT_ASSUMED 수용 정책은 유지하며 추가 PIT 전수검증을
사용의 선행조건으로 되돌리지 않는다.

교훈 2건은 인과를 과장하지 않고 미확인 사항을 보존한다. 다만 검토된 연구가 너무 적어
“연구 전체에서 레슨런을 충분히 축적했다”고 평가할 수 없다.

| 확인 대상 | 관측 | 판단 |
|---|---|---|
| 공개 연구 | 177건 | 공개 스냅샷 기준; 전체 원장과 분모를 구분 |
| 검토된 교훈 / 미검토 연구 | 2건 / 175건 | 검토율 1.13%; 사실 요약을 검토 교훈으로 세지 않음 |
| 레짐 진단 연결 연구 | 1건 | 여러 연구에서 반복 확인한 결과가 아님 |
| 해당 연구의 Discovery 신호월 | 63개월, 2018-03~2023-05 | 이후 봉인 구간을 추가로 읽지 않음 |
| 상세 16국면 | 최소 지원 2개, 부족 14개 | 부족 중 5개는 미관측; UNKNOWN은 별도 |
| 매크로 37축의 명시적 75상태 | 최소 지원 68개, 부족 7개 | 같은 월의 중첩 분할이며 독립 재현 68건이 아님 |

여기서 “최소 지원”은 기존의 공동 유효 관측 12개월·상태 발생 3회 기준일 뿐이다.
경제적 정확성, 상태 간 차이의 유의성, 독립 재현, 팩터 승격을 뜻하지 않는다.

## 1. 무엇을 분류하는가

현행 `monthly-trend-vol-v2`는 다음 네 축을 만든다.

| 축 | 실제 계산 | 뜻하지 않는 것 |
|---|---|---|
| 장기 추세 | 월말 지수 / 10개월 단순평균 비교 | 다음 달 상승 예측 |
| 단기 추세 | 연속 3개월 누적수익 부호 | 이번 달에 새로 시작된 반등의 탐지 |
| 장기 변동성 | 월수익률 12개의 표본표준편차 × sqrt(12) | 일별 실현변동성 또는 절대 위험 등급 |
| 단기 변동성 | 월수익률 3개의 표본표준편차 × sqrt(12) | 일중 충격 포착 또는 안정적인 정밀 위험 추정 |

변동성 HIGH/LOW는 각 지평의 **현재 월을 제외한 과거 확장 중앙값**과 비교한다.
24개의 유효 과거 변동성 관측이 필요하며 네 축 전체는 연속 입력의 37개월째부터 가능하다.
판독 순서는 **개별 네 축 → 장기 추세×장기 변동성의 큰 4분류 → 상세 16분류**가 적절하다.

매크로·COT·변동성지수 HIGH/LOW 역시 자기 과거 수준 대비 구분이다. CPI HIGH는 물가 가속,
PMI HIGH는 50 이상 확장, 실업률 HIGH는 경기 호조라는 뜻이 아니다. FX/ETF UP/DOWN은
3개월 가격 변화이며 FX는 호가 방향도 고려해야 한다. 코드가 경제적 호재/악재 해석을
하지 않는다고 명시한 것은 적절하다 (`engine/assumed_macro_regimes.py:121`).

[기존 설계 제안](REGIME_DESIGN_REVIEW_20260921.md)의 한국 성장×물가 4분면과 일별 지수
위험 측정은 아직 미구현이다. 현행 라벨의 이름만 바꿔 회복·확장·둔화·침체라고 부르면 안 된다.

## 2. 실제 표본이 뒷받침하는 범위

레짐이 연결된 공개 기록:
`campaign-20260921-001/epoch-001/return_trading_activity_correlation_12m`.

| 큰 분류 | 신호월 수 | 공동 유효 상태 발생 횟수 | 지원 상태 |
|---|---:|---:|---|
| DOWN_HIGH | 33 | 7 | 기술적 최소조건 충족 |
| UP_HIGH | 25 | 5 | 기술적 최소조건 충족 |
| DOWN_LOW | 5 | 2 | 부족 |
| UP_LOW | 0 | 0 | 관측 없음 |

63개월을 16칸으로 나누면 대부분 희귀 상태다. 유리한 칸만 뽑는 대신 모든 칸과 미관측을
남겨야 한다. 현재 해석은 이 한계를 기록하고 있다. 상태 간 성과 차이 검정이나
다중진단 보정, OOS 레짐 재현은 이번 검토에서 수행하지 않았다.

별도의 **시장 입력 요약**에서는 2015-01~2026-06 원천으로 전체 네 축 READY가
2018-01부터 102개월이다. 이 중 장기 HIGH는 90개월(88.2%), UP_LOW는 2개월이다.
이는 위 팩터의 63개월 성과 표본과 다르다. 확장 중앙값이 미래를 쓰지 않는다는 것과
상태 빈도를 50:50으로 나눈다는 것은 다르다. 비대칭 빈도 자체는 코드 오류가 아니며
이 결과를 보고 수익이 좋아지는 임계값으로 바꿀 근거도 아니다.

해당 동결 시장 원천은 2026-06까지다. 2026-07/08은 UNKNOWN이므로 이 스냅샷을
2026-09의 최신 시장판독 결과로 제시하면 안 된다. 새 입력을 확보하더라도 과거 campaign의
context를 덮어쓰지 않고 새 입력 버전으로 연결해야 한다.

## 3. 시점 처리는 대체로 적절하나 매매 시각과는 다르다

확인한 강점은 t월 판독 → t+1월 수익 연결, 현재·미래 월을 배제한 확장 기준,
미완료 월 배제, 중간 결측 시 UNKNOWN, 공개 지연의 소급 덮어쓰기 방지,
출처·규칙 hash 동결이다. PIT_ASSUMED도 검증된 최초 발표본으로 격상하지 않는다.

다만 매크로 정보 마감은 **한국 달력 월말 23:59:59**
(`engine/assumed_macro_regimes.py:148`)이고 수익률은 최종 거래일 월말 종가 사이의
수익률이다 (`engine/panel.py:348`). 금요일 마지막 거래 이후 토요일 월말 발표는
그 달 진단에 포함될 수 있지만 금요일 종가에 거래할 수는 없다.

현재의 설명용 연결을 곧바로 체결 가능한 타이밍 전략으로 쓰지 않는다. 향후 포지션에
활용할 경우 별도 버전에서 `decision_at`, 거래소 달력, 다음 실행가격, 비용을 결합해야 한다.
월말 종가로 신호를 계산하고 동일 종가 체결을 자동 가정하는 문제도 함께 구분해야 한다.

## 4. 레슨런에서 확인한 개선점

### 높은 우선순위: 검토 미완료 175건

증거 생성은 자동이지만 해석·독립 비평·저장은 호스트 에이전트의 별도 단계다
(`engine/scientist_review.py:205`, `scripts/lesson_review.py:79`, `INSTRUCTIONS.md`의 실행 책임).
이번에 기존 175건을 일괄 승인하거나 누락된 진단을 재평가로 채우지 않았다.
향후에는 종료 연구의 증거 준비, 해석, critique, save를 분리해 완료 여부를 추적하는 것이 우선이다.
기존 집계만 있는 연구는 그 제한된 증거로 교훈을 쓰고 원인 미확인은 그대로 남긴다.

### 높은 우선순위: 가격 입력 분포가 수집되지 않음

`engine/mechanism_capture.py:92`의 원시 입력 요약은 `factor.needs`만 순회한다.
최신 가격·거래활동 팩터는 `needs=()`지만 실제로 `adj_close`, `adv20`을 사용한다
(`factors/candidates/return_trading_activity_correlation_12m.py:15`, `:67`).
공개 진단의 `raw_input_profile=[]`도 확인했다. 이는 팩터 계산 오류의 증거가 아니라
**측정 품질을 설명할 진단 증거의 누락**이다.

다음 프로토콜에서는 기본 시장 입력과 추가 재무 입력의 명시적 진단 의존성을 구분하고,
결측·영값·극단값·단위를 수집하는 방안을 권고한다. 범용 수집이면 실제 사용 입력과
보조 통제 입력도 구별해야 한다. 동결된 후보 정의와 기존 packet은 소급 수정하지 않는다.

### 중간 우선순위: 공통 ROA 진단과 직접 메커니즘 증거를 구별

두 검토본 모두 ROA 변화의 평균과 순위 방향 불일치, 통제 후의 대안 설명을 남긴 점이 좋다.
그러나 현재 공통 12개월 공개 ROA 변화는 일시적 수요 압력의 직접 측정이 아니다
(`engine/mechanism_capture.py:54`). 수요·기대·업종·종목별 영향 등 미수집 증거를
추가 분석한 것처럼 말할 수 없다. 가설별 관측 계획과 실제 수집된 항목의 일치 여부가 다음 과제다.

순위 검사 통과와 비용 후 구현 결과도 구별하고 있다. 최신 진단의 정확한 보유·거래비용 상세는
`execution_costs=NOT_COLLECTED`다. 비용 반영 요약이 있다는 이유로 상세 실행 검증까지
완료됐다고 표시하지 않는다.

### 중간 우선순위: episode 필드의 의미를 구별

`n_episodes`는 연속 관측 구간 수이고 `n_observed_state_episodes`는 관측된 다른 상태를
사이에 둔 발생 횟수다. 지원 판정에는 올바르게 `n_joint_usable_episodes`를 사용한다
(`engine/mechanism_diagnostics.py:332`, `:361`). UNKNOWN이 중간에 끼면 연속 구간은
늘 수 있지만 반복 발생의 증거는 늘지 않는다. UI나 교훈에서 이 필드를 “독립 재현 횟수”로
읽지 않도록 이름과 설명을 구별할 필요가 있다. 큰 4분류의 미관측 상태는 엔진 집계에
빠질 수 있으므로 현재 exporter의 별도 미관측 표시를 유지한다.

## 5. 문헌 보강이 바꾼 연구 질문

새 6건 중 4건은 원논문 관련 절, 2건은 원저자/출판사 초록 범위로 확인했다.
각 항목의 출처·관측·적용 제안·필요 입력·한계는
[문헌 원장](memory/literature.json)과 [KNOWLEDGE](KNOWLEDGE.md)에 분리해 저장했다.

| 문헌 | 확인 범위 | 우리 프로젝트의 적용 제안 |
|---|---|---|
| [Daniel–Moskowitz (2016)](https://kentdaniel.net/papers/published/jfe_16.pdf) | §3–3.2, §3.4 | 사전 하락·위험 상태와 사후 반등, 양쪽 포트폴리오 노출을 구별 |
| [Stock–Watson (1989)](https://www.journals.uchicago.edu/doi/abs/10.1086/654119) | 출판사 초록 | 현재 경기 측정·경기 예측·시장 상태를 별도 대상으로 설명 |
| [Giannone–Reichlin–Small (2005)](https://www.federalreserve.gov/Pubs/feds/2005/200542/200542pap.pdf) | §2.1, §3 수정오차 한계 | 기준월과 공개시점을 분리하고 월말 정보 집합의 서로 다른 지연을 표시 |
| [Corsi (2009)](https://statmath.wu.ac.at/~hauser/LVs/FinEtricsQF/References/Corsi2009JFinEtrics_LMmodelRealizedVola.pdf) | §2 관련 정의·모형 | 월 리밸런싱과 변동성 측정 빈도를 분리; 현재 방식은 HAR-RV 아님 |
| [Newey–West (1987)](https://www.nber.org/papers/t0055) | 1986 working paper 초록·출판 정보 | 시간 의존성을 고려해도 희귀 상태·다중비교 문제가 사라지지 않음 |
| [Hansen (2005)](https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Hansen.pdf) | §1–2.1 | 비교군 전체와 기준모형을 기록; 재귀 추정에 SPA를 무조건 이식하지 않음 |

Giannone 등의 해당 working paper는 수정오차 불확실성 측정을 생략한다. 이를 근거로 FMP
최초 발표값을 인증하지 않는다. Hansen의 원형은 재귀 모수 추정 비교를 허용하지 않으므로
확장 기준을 사용하는 현행 국면에 SPA 검정을 기계적으로 붙이는 개선안은 채택하지 않았다.

## 6. 권고 순서와 완료 조건 — 이번에는 실행하지 않음

1. **연구 관측 가능성부터 보강**: 교훈 검토 상태, 원시 입력 진단, 레짐 최신성,
   상태별 개월/발생/UNKNOWN을 명확히 표시한다. 합성 테스트로 누락·미관측·오래된 원천·
   기본 가격 입력·반복 가용 관측을 확인한다. 기존 교훈을 자동 승인하지 않는다.
2. **해석의 기본 화면은 네 축과 큰 4분류**: 16분류는 보조 상세표로 유지한다.
   표본 지원·불확실성·대안 설명을 먼저 읽고 좋은 칸으로 정의나 기간을 바꾸지 않는다.
3. **한국 경제 축은 별도 새 버전 후보**: 기존 성장×물가 제안을 출발점으로 기준기간,
   수준/방향/서프라이즈, 중복 발표와 수정 선택을 명시한다. 원문이 보장한 최적 산식은 아니다.
4. **실제 레짐 활용은 별도 연구**: 진단에서 포지션 선택으로 넘어갈 때만 의사결정/체결시각,
   기준전략, 비교군 전체, 손실함수, 검증 경계를 사전 고정한다. 지금 본 결과는 새 독립 OOS가 아니다.

위 권고는 기존 팩터 승격에 추가 gate를 만들거나 PIT_ASSUMED 진단 사용을 중단하라는 뜻이 아니다.

## 7. 검증 및 재현 경계

관련 합성 테스트 **327개 통과(40.91초)**. 중복 실행을 더한 수가 아닌 아래 통합 실행 결과다.
이는 코드 계약 검사이지 경제 국면 정확도나 인과 추론의 진실 판정이 아니다.

```sh
.venv/bin/python -m pytest -q \
  tests/test_literature.py tests/test_knowledge.py tests/test_knowledge_compaction.py \
  tests/test_regimes.py tests/test_regime_context.py tests/test_regime_inputs.py \
  tests/test_regime_artifacts.py tests/test_regime_readiness.py \
  tests/test_assumed_macro_regimes.py tests/test_assumed_market_regime.py \
  tests/test_assumed_regime_inputs.py tests/test_assumed_regime_integration.py \
  tests/test_policy_regime.py tests/test_mechanism_capture.py \
  tests/test_mechanism_diagnostics.py tests/test_scientist_review.py \
  tests/test_candidate_lessons.py tests/test_lesson_portability.py tests/test_lessons.py
```

`python -m scripts.knowledge`로 생성 후 변경 전후를 대조했다. 기존 17개 문헌 항목,
KNOWLEDGE의 문헌 이외 구역, `factor_index.json`, `candidate_lessons.jsonl` 내용은 보존됐다.
새 문헌은 별도 검토자도 확인했으며, Daniel–Moskowitz의 사후 헤지 편향 직접 근거 절을
출처 위치에 추가했다. 기존의 미커밋 연구·사이트 변경은 유지했다.

읽은 공개 스냅샷은 `apps/research-observatory/dist/data/research-catalog.json`
(as_of 2026-09-23)이며 SHA-256은
`0c7f0ebdd1c5c0334b209cfb64527fbb494ba87057b0d19341836d4e2f9c75bf`다.
입력 범위는 다음 요약을 사용했으며 DB의 현재 상태를 재인증한 것은 아니다.

- `output/regime_inputs/kospi-assumed-20260921-v1/summary.json`:
  `e9825e0efaace3489401d8b9eef85163bce9b81031473041c96665260e599429`
- `output/regime_inputs/fmp-assumed-20260921-v1/summary.json`:
  `73a8b5353a537442d68e3a6de09e372f7cbb3bd38c817a9237e6e273e99cd8de`

검토에 따른 변경은 문헌 원장, 문헌 설명 렌더러와 테스트, 생성된 KNOWLEDGE, 이 보고서다.
레짐/팩터 계산·합격 기준·campaign·Gold·배포 사이트는 변경하지 않았다.
