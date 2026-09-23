# 레짐 판독 포함 팩터 연구 결과 — campaign-20260921-001

완료일: 2026-09-22 KST. 종료 결과 해석자/사용자용 문서이며, 이후 후보 생성자가 읽는 `KNOWLEDGE.md`와 달리 상세 성과를 포함한다.

## 결론

사전등록 후보 `return_trading_activity_correlation_12m` 1개를 월 리밸런싱으로 실행했다.
자동 연구 판정은 **PROMOTE**다. 레짐 입력 38개를 동결해 Discovery 진단까지 실제 연결했다.
**Gold 적재·운영 배포·커밋·푸시는 하지 않았다.**

**순위 예측력 합격과 거래전략 수익성은 다르다.**
기존 롱온리 포트폴리오 진단은 비용 후 연율 초과수익 **-0.647%p**로 음수다.
이는 Discovery 63개월의 비용 모델 진단이지 OOS 수익률이나 실거래 수익이 아니다.
이번 결과만으로 즉시 실전 배치하거나 성과가 좋은 레짐만 선택하는 규칙을 추가하지 않는다.

| 항목 | 실제 결과 |
|---|---:|
| Discovery 평균 투자 가능 Rank IC | 0.048680 |
| 36개월 OOS 평균 Rank IC | 0.068219 |
| OOS / Discovery IC | 140.14% |
| 요구 OOS IC | 0.024340 |
| OOS BY q | 1.355591e-7 |
| 기존 Gold와 최대 월별 중앙 절대 Spearman | 0.456836 |
| gate 중립화 IC / 원본 유지율 | 0.017338 / 35.62% |
| 합성 귀무 campaign | 100개, 유형별 25개 |
| 합성 귀무 오승격 | 0 / 100 (각 유형도 0 / 25) |
| 실제 Python / SQL parity | 126,844행, 키·rank·허용 오차 밖 raw 불일치 0 |

Rank IC는 팩터 점수와 다음 달 수익률의 종목 간 순위 상관이다. 수익률 %가 아니다.
귀무 실험의 관측 오승격률 0%는 실제 오승격 가능성이 없다는 보장이 아니다.

## 동결 설계와 평가 범위

- 정의: 종목별 최근 12개 월수익률과 같은 월 `log(adv20)`의 Pearson 상관. 낮을수록 높은 점수.
- `adv20`는 직전 20거래일 평균 **거래대금**이다. 월 전체 거래량·주문 불균형·투자자 수요를 직접 측정한 값이 아니다.
- 정확히 이어지는 13개 월말 가격과 12개 유효 거래활동 관측이 필요하다. 비양수·비유한 값과 상수열은 제외하며 결측을 메우지 않는다.
- 리밸런싱: 매월. 전체 시장 유니버스와 투자 가능 조건은 기존 엔진 고정 계약을 사용한다.
- Discovery 신호월: **2018-03~2023-05, 63개월**. 수익 지원 경계 2023-06-30.
- Embargo 신호월: 2023-06.
- OOS 신호월: **2023-07~2026-06, 36개월**. 수익월 2023-08~2026-07.
- 같은 역사적 구간이 이전 연구에도 노출된 `HISTORICAL_REUSED_WINDOW`다. 후보의 일회성 확인은 완료했지만 완전히 새로운 미래 표본의 독립 검증은 아니다.
- 입력 사전점검: 전체 계산 가능 비율 95.35%, 월별 p10 94.20%.
- SQL parity는 Discovery 구간에서 수행했다. raw 최대 절대 오차 7.039e-14, 기존 atol=1e-12/rtol=1e-10 적용, rank는 정확히 일치했다.
- 정의 hash: `e0e91e564995c7a2`; 후보 SHA256: `04f41601d46bd58c6090c531de908f4cf3f4dd2b3ebad19a0e91246bc51cb4af`.
- ruleset `fr-3.16.0`, epoch protocol `epoch-1.9`. 결과에 맞춘 부호·룩백·gate 변경 없음.

## 레짐을 어떻게 읽었나

월말 t에 알려졌다고 인정된 상태를 **t+1 수익**에 연결했다.
KOSPI 장기 추세는 10개월 평균 대비 종가, 단기 추세는 3개월 수익률 부호다.
장·단기 변동성은 각각 12/3개월 월수익률 표준편차를 자신의 **이전 관측만으로 구한 확장 중앙값**과 비교한다.
전체 기간 중앙값으로 과거 국면을 다시 나누지 않았다.

아래는 **Discovery 진단만**이다. 이번 경로에서 OOS 레짐별 성과는 수집하지 않았으며 재계산하지 않았다.
상위−하위는 월별 재구성한 동일가중 5분위의 차이다. 비용 전 설명용 그룹 진단이며 아래 별도 롱온리 포트폴리오와 다르다.
12개 이상의 공동 유효 월과 3개 이상의 관측 구간을 모두 가져야 설명용 표본을 충족한다.
구간 수는 독립 재현 횟수가 아니고, UNKNOWN과 결측으로 새 구간을 만들지 않는다.

### 먼저 장·단기 네 축

#### 장기 추세

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 38 | 5 | 0.0386 | 0.460 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 25 | 5 | 0.0641 | 0.281 | 설명용 표본 충족 |

#### 단기 추세

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 33 | 7 | 0.0301 | 0.009 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 30 | 7 | 0.0691 | 0.807 | 설명용 표본 충족 |

#### 장기 변동성

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 58 | 3 | 0.0510 | 0.404 | 설명용 표본 충족 |
| LOW | 5 | 2 | 0.0222 | 0.216 | 표본/구간 부족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

#### 단기 변동성

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 46 | 8 | 0.0490 | 0.412 | 설명용 표본 충족 |
| LOW | 17 | 8 | 0.0478 | 0.327 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

관측된 단기 상승/하락의 평균 IC는 각각 0.0691/0.0301이었다.
이는 환경에 따른 차이의 탐색적 관측이지, 차이의 확정적 검정이나 레짐 필터 채택 근거가 아니다.
장기 고변동성은 58개월(최장 연속 44개월), 저변동성은 5개월뿐이다.
짧은 변동성 분류의 IC는 고/저가 0.0490/0.0478로 비슷했다.
여러 축이 같은 달을 중복 사용하므로 독립 검증으로 세지 않는다.

### 큰 네 국면

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| UP_LOW | 0 | 0 | — | — | 표본/구간 부족 |
| UP_HIGH | 25 | 5 | 0.0641 | 0.281 | 설명용 표본 충족 |
| DOWN_LOW | 5 | 2 | 0.0222 | 0.216 | 표본/구간 부족 |
| DOWN_HIGH | 33 | 7 | 0.0410 | 0.497 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

상승·저변동성은 해당 표본에서 **0개월**이다. 하락·저변동성도 5개월/2구간으로 부족하다.
상승·고변동성과 하락·고변동성의 IC는 모두 양수지만, 상위−하위 월평균 차이의
설명용 95% HAC 구간은 각각 [-0.600, 1.162]%p와 [-0.066, 1.060]%p로 0을 포함한다.
따라서 “모든 국면에서 안정적으로 돈을 번다”고 결론 내리지 않는다.

## 한국 매크로와 기타 보조축

정책금리 1축 + FMP 36축의 모든 상태를 부록에 보존했다. 좋은 상태만 선별하지 않았다.
정책금리 완화 11개월/2구간, 긴축 23개월/2구간은 모두 설명용 구간 수가 부족하다.
동결 금리 29개월/5구간만 표본 조건을 충족한다.
한국 소비·기업심리, 물가, 산업생산, 경상수지, 소매판매, 무역수지, 실업률을 함께 비교했다.
무역수지 HIGH는 3개월뿐이고, CPI YOY LOW는 26개월이어도 2구간뿐이라 부족으로 남겼다.

FMP HIGH/LOW는 대개 동결된 관측값과 이전 월들의 중앙값 비교이고 UP/DOWN은 3개월 변화 부호다.
이는 공식 경기 확장/침체나 경제적으로 좋음/나쁨을 뜻하지 않는다.
선물 코드의 축은 동결 COT 등 해당 입력의 상태를 뜻하므로 원자재 현물가격 수준으로 바꿔 읽지 않는다.
CL/DX/GC/HG/J6/VX/ZB/ZN/ZQ/ZT는 각각 UNKNOWN 5개월을 남겼다.
UNKNOWN 구간에 계산된 후보 성과가 있더라도 이를 정상 레짐 효과로 해석하지 않는다.

## 비용·노출·경제적 원인: 통과와 별도 판단

| Discovery 포트폴리오 진단 (63개월) | 결과 |
|---|---:|
| 비용 전 연율 초과수익 | 0.972%p |
| 연율 비용 차감 | 1.619%p |
| 비용 후 연율 초과수익 | -0.647%p |
| 연율 회전율 | 338.78% |
| 비용 후 정보비율 | -0.145 |

엔진의 상위 20% 동일가중 롱온리 월 리밸런싱과 고정 투자 가능 유니버스의 동일가중 벤치마크 비교다.
연율은 월평균 × 12이며 복리 CAGR이 아니다. 비용은 엔진의 수수료·시장충격·연도별 거래세 가정이다.
집계 비용 결과는 존재하지만 교훈 패킷의 `execution_costs` 상세 섹션은 NOT_COLLECTED다.
상세 비용/체결 가능성과 OOS 비용 후 포트폴리오 수익은 이번 레짐 분석에서 검증하지 않았다.

동일 완전관측 표본의 **시장구분·로그 시가총액·로그 거래대금** 통제 전/후 진단 IC는
0.048680 → 0.015169로 감소했다. 이는 gate 중립화 IC 0.017338과 다른 진단이며 혼동하지 않는다.
업종·변동성·위험요인 전체를 통제하거나 원인을 식별한 회귀가 아니다.
노출이 일부 설명할 가능성이 있지만 거래압력 반전이라는 원인은 입증되지 않았다.

경제적 결과는 이후 공개 PIT ROA의 변화에 한정된다. 순위 연관과 그룹 평균의 방향이
엇갈리는 경고가 있으므로 분모·분포·결측을 확인하지 않은 채 실적 개선이나 오류라고 단정하지 않는다.
주문흐름·컨센서스·투자자 수요 변화는 직접 관측하지 않았다.

## PIT와 미확인 범위

- 검증 입력 1축: `KR_POLICY_DIRECTION_3M`.
- 사용자 가정 수용 37축: KOSPI 1 + FMP 36. **PIT_ASSUMED**이며 최초 발표값 검증 완료를 뜻하지 않는다.
- FMP 현재 보존값을 역사적 빈티지의 근사로 사용한다. 최초값/수정 경로는 복원하지 않았다.
  가정 가용시각과 실제 2026년 수신시각을 구분해 보존했다.
- 가정 수용은 월별 레짐 보조 진단에만 적용한다. 팩터 feature나 장중 자료의 PIT 인증으로 확대하지 않는다.
- 가정 정책 SHA256: `6a853a750e748038a7c2e368a363d2c7323859a9a066162bc3e9420f9e470aed`.
- 레짐 입력 SHA256: `06878f70f4e1dc39270b2ebaa22c9db1409adb1264d021a78832f81a9c0ae3ae`.
- 시장 분류: `monthly-trend-vol-v2`, SHA256 `18c7e980b2de79094a3fb6c9f1b677b4ca702ce5d978ece9a61618e82a931fe6`.
- 입력 계약: `regime-input-contract-v1`, SHA256 `f7795aa614634978acc0b65eedb584f539e320c5e76b521b253e320a9ead7ed0`.
- 가정 수용 자체를 별도 탈락 기준으로 바꾸거나 추가 PIT 전수검증을 선행조건으로 요구하지 않았다.

| 진단 구역 | 수집 상태 |
|---|---|
| charts | AVAILABLE |
| controlled_comparison | AVAILABLE |
| economic_outcomes | PARTIAL |
| execution_costs | NOT_COLLECTED |
| input_quality | PARTIAL |
| monthly_performance | PARTIAL |
| regime_comparison | PARTIAL |
| selection_profile | AVAILABLE |

PARTIAL은 존재하는 수치를 지운다는 뜻이 아니라 원시 입력 분포·경제 결과 성숙도·비용 상세·레짐 표본 등의 한계가 남는다는 뜻이다.
후보가 선언한 별도 원시 컬럼이 없어 기초 가격/거래대금의 전체 분포 감사가 수집됐다고 말할 수 없다.
이미지 시각 검토는 수행하지 않았고 숫자표를 해석했다.

## 실행·검토 기록

- 정상 Discovery 1회, 종료된 OOS 확인 1회. 후보·기준 변경이나 결과 기반 재시도 없음.
- 최초 Discovery의 연결 실패는 유효 결과 생성 전이었다. 동일 동결 후보로 재개했다.
- 최초 확인 명령의 자동 게시 경로를 발견해 OOS 계산 전 Gold 입력 조회에서 중단했다.
  `--no-publish` 옵션을 추가·검증하고 같은 후보로 확인을 완료했다.
- 완료 로그: `Gold publication: SKIPPED (--no-publish); Gold write 없음`.
- 최종 SSM 터널과 이 실행에만 건 idle-sleep 방지는 종료했다.
- 후보/SQL/manifest 관련 합성 검사 78개, 별도 후보·레짐 관련 묶음 97개, 연구 불변식/기억 121개,
  게시 분리 회귀 17개, scientist/교훈/게시 분리 마무리 묶음 49개 통과. 묶음 사이 중복이 있어 합산하지 않는다.
- 실제 해석자 → 새 컨텍스트의 독립 비평자 검토 완료: **ACCEPT**, 6개 점검 통과.
  `lesson_review save`의 증거·초안 hash 검증을 통과해 교훈을 저장했고 `KNOWLEDGE.md` 반영을 확인했다.
  별도 보고서 QA도 원본의 국면 154개 행과 수치·표본 수준 일치를 확인했다.
- 저장한 일반 교훈: 가격과 명목 거래활동의 동행성이 수익 순위와 이어져도 일시 수요나 실적 변화의
  원인이 확인된 것은 아니다. 동반 노출·결측·경제적 결과·비용 후 구현을 나눠 판단하고,
  국면의 표본 부족과 사용자 수용 가정을 보존한다. 순위 검사 통과와 비용 후 수익성은 별개다.
  후보 부호·기간·레짐 필터를 바꾸는 처방이나 새 실험은 실행하지 않았다.

## 근거 파일

- [일회성 확인 보고서](confirmation/report.md)
- [일회성 확인 JSON](confirmation/result.json)
- [SQL parity 증거](implementation-verification.json)
- [동결 campaign](manifest.json)
- [검토된 교훈 초안](lesson-review-draft.json)
- [독립 비평 ACCEPT](lesson-review-critique.json)
- [갱신된 연구 기억](../../KNOWLEDGE.md)
- [종료 해석 전용 증거 패킷](../../memory/lesson_evidence/c693ab9aa04b2028ff35e1640ae5e5e9202ae8e933ad63bf5910e73fa7846aeb.json)
- [Discovery 원본](../../runs/cycle-0230-return_trading_activity_correlation_12m/result.json)
- [후보 정의](../../../factors/candidates/return_trading_activity_correlation_12m.py)
- [비용 진단 단위/정의](../../../engine/gate.py) — `backtest` 함수.
- 실행한 절차: 프로젝트 `factor-research-loop` 스킬. 동결 후보·일회성 확인·가정 표시·진단용 레짐·별도 비평을 유지했다.

## 부록 A. 장단기 조합과 세부 16개 상태

### trend_phase

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN_CONFIRMED | 29 | 7 | 0.0263 | 0.125 | 설명용 표본 충족 |
| DOWN_REBOUND | 9 | 5 | 0.0780 | 1.540 | 표본/구간 부족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP_CONFIRMED | 21 | 4 | 0.0653 | 0.493 | 설명용 표본 충족 |
| UP_PULLBACK | 4 | 4 | 0.0576 | -0.831 | 표본/구간 부족 |

### volatility_phase

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH_BOTH | 44 | 8 | 0.0510 | 0.428 | 설명용 표본 충족 |
| LONG_HIGH_ONLY | 14 | 7 | 0.0508 | 0.329 | 설명용 표본 충족 |
| LOW_BOTH | 3 | 2 | 0.0339 | 0.316 | 표본/구간 부족 |
| SHORT_HIGH_ONLY | 2 | 1 | 0.0046 | 0.065 | 표본/구간 부족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

### regime_detail

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| LT_DOWN_ST_DOWN_LV_HIGH_SV_HIGH | 22 | 8 | 0.0287 | 0.119 | 설명용 표본 충족 |
| LT_DOWN_ST_DOWN_LV_HIGH_SV_LOW | 3 | 2 | 0.0162 | -0.082 | 표본/구간 부족 |
| LT_DOWN_ST_DOWN_LV_LOW_SV_HIGH | 2 | 1 | 0.0046 | 0.065 | 표본/구간 부족 |
| LT_DOWN_ST_DOWN_LV_LOW_SV_LOW | 2 | 2 | 0.0368 | 0.562 | 표본/구간 부족 |
| LT_DOWN_ST_UP_LV_HIGH_SV_HIGH | 6 | 3 | 0.0768 | 1.403 | 표본/구간 부족 |
| LT_DOWN_ST_UP_LV_HIGH_SV_LOW | 2 | 2 | 0.1065 | 2.811 | 표본/구간 부족 |
| LT_DOWN_ST_UP_LV_LOW_SV_HIGH | 0 | 0 | — | — | 표본/구간 부족 |
| LT_DOWN_ST_UP_LV_LOW_SV_LOW | 1 | 1 | 0.0283 | -0.175 | 표본/구간 부족 |
| LT_UP_ST_DOWN_LV_HIGH_SV_HIGH | 3 | 3 | 0.0713 | -0.437 | 표본/구간 부족 |
| LT_UP_ST_DOWN_LV_HIGH_SV_LOW | 1 | 1 | 0.0167 | -2.012 | 표본/구간 부족 |
| LT_UP_ST_DOWN_LV_LOW_SV_HIGH | 0 | 0 | — | — | 표본/구간 부족 |
| LT_UP_ST_DOWN_LV_LOW_SV_LOW | 0 | 0 | — | — | 표본/구간 부족 |
| LT_UP_ST_UP_LV_HIGH_SV_HIGH | 13 | 6 | 0.0722 | 0.701 | 설명용 표본 충족 |
| LT_UP_ST_UP_LV_HIGH_SV_LOW | 8 | 3 | 0.0540 | 0.155 | 표본/구간 부족 |
| LT_UP_ST_UP_LV_LOW_SV_HIGH | 0 | 0 | — | — | 표본/구간 부족 |
| LT_UP_ST_UP_LV_LOW_SV_LOW | 0 | 0 | — | — | 표본/구간 부족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

## 부록 B. 모든 매크로 상태

각 축은 동일한 Discovery 63개월에 연결됐다. 각 표의 UNKNOWN도 원본 그대로 보존한다.
구간 충족은 기술적 표본 조건이지 독립 실증, 인과 검증, 다중검정 보정된 유의성 또는 추가 승격 gate가 아니다.

### FMP_ASSUMED_AUDUSD

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 38 | 12 | 0.0344 | 0.106 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 25 | 11 | 0.0704 | 0.819 | 설명용 표본 충족 |

Source ID: `fmp-assumed-AUDUSD-63620d24f99c030d-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_CL

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 32 | 5 | 0.0444 | -0.058 | 설명용 표본 충족 |
| LOW | 26 | 5 | 0.0443 | 0.646 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-CL-d0f587ca0b2d1eeb-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_CN_NBS_MANUFACTURING_PMI

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 25 | 4 | 0.0603 | 0.330 | 설명용 표본 충족 |
| LOW | 38 | 4 | 0.0410 | 0.428 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-CN_NBS_MANUFACTURING_PMI-480c5213b5e61b1f-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_DX

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 30 | 5 | 0.0291 | 0.004 | 설명용 표본 충족 |
| LOW | 28 | 6 | 0.0607 | 0.530 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-DX-a685a1ded9d5f53e-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_EEM

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 36 | 5 | 0.0358 | 0.277 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 27 | 6 | 0.0658 | 0.539 | 설명용 표본 충족 |

Source ID: `fmp-assumed-EEM-aefd218ac3bbb6e2-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_EURUSD

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 38 | 9 | 0.0337 | 0.084 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 25 | 10 | 0.0714 | 0.853 | 설명용 표본 충족 |

Source ID: `fmp-assumed-EURUSD-1951d347ee56f89e-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_EWT

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 30 | 10 | 0.0402 | 0.381 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 33 | 11 | 0.0564 | 0.397 | 설명용 표본 충족 |

Source ID: `fmp-assumed-EWT-7d496bc8002b0314-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_EWY

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 36 | 6 | 0.0293 | -0.020 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 27 | 7 | 0.0745 | 0.935 | 설명용 표본 충족 |

Source ID: `fmp-assumed-EWY-4c3aedeed7a98035-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_FXI

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 40 | 7 | 0.0403 | 0.293 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 23 | 7 | 0.0633 | 0.557 | 설명용 표본 충족 |

Source ID: `fmp-assumed-FXI-56822b0a3ce1a868-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_GC

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 35 | 4 | 0.0387 | -0.016 | 설명용 표본 충족 |
| LOW | 23 | 4 | 0.0529 | 0.674 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-GC-4823d239d7244363-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_HG

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 31 | 6 | 0.0525 | 0.329 | 설명용 표본 충족 |
| LOW | 27 | 6 | 0.0350 | 0.176 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-HG-3e89b9679a52bb94-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_J6

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 26 | 5 | 0.0588 | 0.551 | 설명용 표본 충족 |
| LOW | 32 | 5 | 0.0326 | 0.019 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-J6-93d7328f4fba90c8-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_BUSINESS_CONFIDENCE

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 33 | 4 | 0.0500 | 0.360 | 설명용 표본 충족 |
| LOW | 30 | 4 | 0.0472 | 0.422 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_BUSINESS_CONFIDENCE-6d70b2ae47a53b64-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_CONSUMER_CONFIDENCE

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 20 | 3 | 0.0468 | 0.283 | 설명용 표본 충족 |
| LOW | 43 | 3 | 0.0496 | 0.438 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_CONSUMER_CONFIDENCE-3e0e2d97232e74f9-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_CPI_MOM

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 37 | 13 | 0.0520 | 0.436 | 설명용 표본 충족 |
| LOW | 26 | 13 | 0.0440 | 0.322 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_CPI_MOM-554fafc7dfd2c62c-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_CPI_YOY

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 37 | 3 | 0.0506 | 0.663 | 설명용 표본 충족 |
| LOW | 26 | 2 | 0.0459 | -0.001 | 표본/구간 부족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_CPI_YOY-4afd7ea30809fb7d-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_CURRENT_ACCOUNT

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 19 | 7 | 0.0454 | 0.241 | 설명용 표본 충족 |
| LOW | 44 | 8 | 0.0501 | 0.453 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_CURRENT_ACCOUNT-abb9e5799b234fdc-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_INDUSTRIAL_PRODUCTION_MOM

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 31 | 18 | 0.0444 | 0.173 | 설명용 표본 충족 |
| LOW | 32 | 18 | 0.0528 | 0.599 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_INDUSTRIAL_PRODUCTION_MOM-9380554d288bf1a8-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_INDUSTRIAL_PRODUCTION_YOY

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 34 | 11 | 0.0507 | 0.630 | 설명용 표본 충족 |
| LOW | 29 | 12 | 0.0463 | 0.107 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_INDUSTRIAL_PRODUCTION_YOY-d0e9fb2b50fa5377-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_PPI_MOM

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 39 | 11 | 0.0563 | 0.526 | 설명용 표본 충족 |
| LOW | 24 | 11 | 0.0364 | 0.167 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_PPI_MOM-18055c65c5c4b7a5-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_PPI_YOY

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 44 | 4 | 0.0479 | 0.538 | 설명용 표본 충족 |
| LOW | 19 | 3 | 0.0504 | 0.044 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_PPI_YOY-0832ff0d71d217d7-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_RETAIL_SALES_MOM

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 27 | 14 | 0.0489 | 0.154 | 설명용 표본 충족 |
| LOW | 36 | 14 | 0.0485 | 0.566 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_RETAIL_SALES_MOM-2ca3bf023e3939d3-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_TRADE_BALANCE

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 3 | 3 | 0.0190 | 0.155 | 표본/구간 부족 |
| LOW | 60 | 4 | 0.0502 | 0.401 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_TRADE_BALANCE-bbd449fc45d5d091-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_KR_UNEMPLOYMENT_RATE

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 30 | 7 | 0.0505 | 0.218 | 설명용 표본 충족 |
| LOW | 33 | 8 | 0.0470 | 0.544 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-KR_UNEMPLOYMENT_RATE-ab06392f6aa6f538-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_USDCNH

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 32 | 7 | 0.0495 | 0.205 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 31 | 7 | 0.0478 | 0.579 | 설명용 표본 충족 |

Source ID: `fmp-assumed-USDCNH-d0419c3e7536d468-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_USDCNY

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 30 | 7 | 0.0547 | 0.416 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 33 | 7 | 0.0432 | 0.364 | 설명용 표본 충족 |

Source ID: `fmp-assumed-USDCNY-bb9a6dfc0d387898-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_USDJPY

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 23 | 5 | 0.0501 | 0.338 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 40 | 5 | 0.0479 | 0.418 | 설명용 표본 충족 |

Source ID: `fmp-assumed-USDJPY-cf47e3577d11b514-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_USDTWD

분류: `TRAILING_3_MONTH_CHANGE_SIGN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| DOWN | 33 | 12 | 0.0660 | 0.758 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |
| UP | 30 | 11 | 0.0296 | -0.017 | 설명용 표본 충족 |

Source ID: `fmp-assumed-USDTWD-87d74b1655a0450f-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_VIX3M

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 52 | 6 | 0.0467 | 0.322 | 설명용 표본 충족 |
| LOW | 11 | 5 | 0.0581 | 0.707 | 표본/구간 부족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-^VIX3M-2bf8dddc04f9b8d4-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_VIX9D

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 48 | 8 | 0.0459 | 0.390 | 설명용 표본 충족 |
| LOW | 15 | 7 | 0.0577 | 0.385 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-^VIX9D-050c70250c3bca73-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_VVIX

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 42 | 6 | 0.0373 | -0.054 | 설명용 표본 충족 |
| LOW | 21 | 6 | 0.0714 | 1.275 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `fmp-assumed-^VVIX-4710cc3b14bf6627-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_VX

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 19 | 11 | 0.0393 | 0.179 | 설명용 표본 충족 |
| LOW | 39 | 10 | 0.0468 | 0.296 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-VX-e22a211139333352-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_ZB

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 8 | 5 | 0.0410 | 0.345 | 표본/구간 부족 |
| LOW | 50 | 4 | 0.0449 | 0.244 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-ZB-dc906dde144d181e-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_ZN

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 18 | 2 | 0.0617 | 0.193 | 표본/구간 부족 |
| LOW | 40 | 3 | 0.0365 | 0.287 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-ZN-d2dc80fd780a2cda-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_ZQ

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 41 | 6 | 0.0505 | 0.488 | 설명용 표본 충족 |
| LOW | 17 | 6 | 0.0296 | -0.299 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-ZQ-863a514809277075-assumed-fmp-monthly-diagnostics-v1`.

### FMP_ASSUMED_ZT

분류: `EXPANDING_PRIOR_MONTH_MEDIAN`; 입력: `PIT_ASSUMED`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| HIGH | 20 | 8 | 0.0379 | 0.203 | 설명용 표본 충족 |
| LOW | 38 | 9 | 0.0478 | 0.287 | 설명용 표본 충족 |
| UNKNOWN | 5 | 0 | 0.0988 | 1.914 | UNKNOWN |

Source ID: `fmp-assumed-ZT-3536e15c941dbc75-assumed-fmp-monthly-diagnostics-v1`.

### KR_POLICY_DIRECTION_3M

분류: `동결 정책금리 방향 계약`; 입력: `VERIFIED 정책결정 월말 계약`.

| 상태 | 유효 월 | 관측 구간 | 평균 Rank IC | 상위−하위 월평균 (%p) | 표본 판정 |
|---|---:|---:|---:|---:|---|
| EASING | 11 | 2 | 0.0145 | -0.999 | 표본/구간 부족 |
| TIGHTENING | 23 | 2 | 0.0521 | 0.964 | 표본/구간 부족 |
| UNCHANGED | 29 | 5 | 0.0589 | 0.460 | 설명용 표본 충족 |
| UNKNOWN | 0 | 0 | — | — | UNKNOWN |

Source ID: `bok-fmp-announced-target-monthend-201501-202608-v1`.
