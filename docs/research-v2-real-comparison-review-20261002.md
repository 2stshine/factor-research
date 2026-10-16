# 실제 여섯 사례 설명 비교 검토 — 2026-10-02

적응형 `HOST_LLM`이 `FIXED_REFERENCE`보다 좋은 설명을 만들었다는 증거는 이번 여섯 쌍에서 확인되지 않았다. 양쪽 모두 핵심 수치·상태·해석 한계를 정확하게 보존했고, 아래 기준으로 검토한 중대한 오류나 누락은 각각 발견되지 않았다. 고정 방식은 국면 표본과 경쟁 설명을 더 구체적으로 기록했다. 적응형 방식의 문장이 대체로 짧다는 사실만으로 시간·비용 효율이 높다고 판단할 수는 없다.

이는 실제 완료된 최종 설명을 읽고 내린 한정적 판단이다. 모델의 일반적인 우열이나 통계적 동등성이 입증됐다는 뜻은 아니다. 같은 사례의 두 방식은 동일한 진단 근거를 사용했고, 여섯 사례도 같은 역사 패널과 관련된 정의를 공유한다. 열두 설명은 독립 실험 열두 번이 아니다.

## 검토 대상과 판정 기준

대상은 [동결 검토 묶음](../output/research_v2_pilot/release-20261002-v1/review-bundle.json)과 그 안에 지정된 `sources/{case}/{arm}.json` 열두 개다. 모든 최종 `observations`, `unresolved`, `limitations`, 종료 사유를 읽고, 사례별 여섯 진단의 수치·상태·범위와 대조했다. 초기 소표본, 추정 가능 기간 및 경제 결과의 성숙 경계는 관련 월별 행도 확인했다. 원시 패널의 재계산·DB 조회·OOS 열람은 하지 않았다.

- 내용 결합 해시 `bundle_sha256`: `2862e689bcdd563ad862a506b534af4efb89ac28ea061a51e419d770cb30842c`
- 실제 JSON 파일 SHA-256: `b0f99d9edcc50b095a4ef7bd74ff9ae5b1263826f8581012ac82d67dd91ab5cc`
- 묶음 내용 해시, 열두 원본 파일 해시와 종료 prefix 결합이 모두 일치했다.
- 열두 세션 모두 `STOPPED`, `explanation_complete=true`, 필수 미실행 목록은 빈 배열이다. 각 최종 설명은 반환된 여섯 진단을 모두 인용했고 잘못된 인용 ID는 없었다.
- 사례별 두 방식의 진단 ID·응답 해시가 모두 같다. 총 72개 보고서 사본은 36개 고유 보고서다.

이 검토에서 **중대한 오류**는 원본과 모순되어 결론을 바꾸는 주장이다. 잘못된 부호·상태, 없는 실행 결과, 인과·실거래 수익 주장, 미계산·표본 부족을 성공 또는 무효과로 바꾸는 표현이 해당한다. **중대한 누락**은 필수 진단이나 주요 결론에 필요한 업종·비용 부재, 표본 부족, PIT 가정, 관측 범위, 경제·수익 지평 불일치를 아예 빠뜨리는 경우다. 주 결론과 한계는 남겼지만 세부 지원 정보를 줄인 경우는 별도의 **표현 완결성 차이**로 분류했다. 가중 점수나 과학적 품질 백분율은 만들지 않았다.

| 확인 항목 | FIXED_REFERENCE | HOST_LLM |
|---|---:|---:|
| 검토한 최종 설명 | 6 | 6 |
| 필수 진단이 빠진 세션 | 0 | 0 |
| 최종 관측에서 반환 진단을 인용하지 않은 세션 | 0 | 0 |
| 발견한 중대한 오류 | 0 | 0 |
| 발견한 중대한 누락 | 0 | 0 |
| 별도 기록한 국면 지원 정보의 표현 누락 | 0 | 5 |

마지막 행은 아래에 특정한 다섯 가지 표현상의 차이만 센 것이다. 전체 품질 점수도, 독립 표본의 오류율 추정도 아니다. 오류를 발견하지 못했다는 결과는 원천 자료·진단 엔진의 정확성을 원시 데이터로 인증한 결과와 다르다.

## 사례별 판단

각 원본 링크의 `/terminal_decision/payload`가 실제 검토한 최종 설명이다. 표의 진단 ID는 동일 묶음의 `evidence` 항목을 식별하며, 모든 사례의 여섯 근거 ID와 개별 arm 판정은 [구조화 검토 기록](../research/v2/real-comparison-review-20261002.json)에 있다.

| 사례와 최종 설명 | 두 방식 모두 보존한 핵심 | 비교 판단 |
|---|---|---|
| `asset_growth_12m` · [고정](../output/research_v2_pilot/release-20261002-v1/sources/asset_growth_12m/FIXED_REFERENCE.json) / [적응형](../output/research_v2_pilot/release-20261002-v1/sources/asset_growth_12m/HOST_LLM.json) | 불확실한 무통제 관계, 동일 표본 통제 뒤 방향 변화, ROA **변화**와의 관측 연관성, 경제·수익 지평 차이, 비용 미계산 | 양쪽 중대 지적 없음. 고정은 초기 작은 횡단면·국면 발생구간·설명을 구분할 관측을 더 자세히 적었다. 적응형은 발생구간 수 생략(P01). |
| `current_assets_growth_12m` · [고정](../output/research_v2_pilot/release-20261002-v1/sources/current_assets_growth_12m/FIXED_REFERENCE.json) / [적응형](../output/research_v2_pilot/release-20261002-v1/sources/current_assets_growth_12m/HOST_LLM.json) | 통제 전후 관계와 감소분 모두 불확실하여 통제가 원인을 설명했다고 단정하지 않음. 미래 ROA **변화**와 앞선 수익의 매개를 구분 | 양쪽 중대 지적 없음. 적응형의 발생구간 수 생략(P02) 외에 주요 결론은 일치한다. |
| `net_roa` · [고정](../output/research_v2_pilot/release-20261002-v1/sources/net_roa/FIXED_REFERENCE.json) / [적응형](../output/research_v2_pilot/release-20261002-v1/sources/net_roa/HOST_LLM.json) | 통제 후 남는 관측 연관성과 불확실한 분위 차이, 미래 ROA **수준**과 개선의 구분, 지평·표본 선택 한계 | 양쪽 중대 지적 없음. 고정은 지속성 대 공동노출·선택 설명의 근거와 구별 관측을 명시하고, 규모·유동성만의 감소분 불확실성도 남겼다. 적응형은 이를 축약하고 발생구간 수 생략(P03). |
| `operating_roa` · [고정](../output/research_v2_pilot/release-20261002-v1/sources/operating_roa/FIXED_REFERENCE.json) / [적응형](../output/research_v2_pilot/release-20261002-v1/sources/operating_roa/HOST_LLM.json) | 통제 뒤 감소와 잔여 관계, 미래 ROA **수준**, 매개 미확인, 경제 표본 선택 및 비용 부재 | 양쪽 중대 지적 없음. 고정은 수익성 지속과 동반 노출이 공존할 수 있다는 대안 비교를 더 구체적으로 제공한다. 적응형은 발생구간 수 생략(P04). |
| `price_momentum_12_3` · [고정](../output/research_v2_pilot/release-20261002-v1/sources/price_momentum_12_3/FIXED_REFERENCE.json) / [적응형](../output/research_v2_pilot/release-20261002-v1/sources/price_momentum_12_3/HOST_LLM.json) | 통제 후 단순 약화가 아니라 위쪽 이동임을 정확히 설명. 잔여 관계와 국면 대비는 불확실. 경제·비용 진단은 모두 미계산 | 양쪽 중대 지적 없음. 두 방식 모두 네 국면의 개월·발생구간 수를 보존했다. 적응형 우위는 확인되지 않았다. |
| `price_momentum_6_1` · [고정](../output/research_v2_pilot/release-20261002-v1/sources/price_momentum_6_1/FIXED_REFERENCE.json) / [적응형](../output/research_v2_pilot/release-20261002-v1/sources/price_momentum_6_1/HOST_LLM.json) | 원래 음의 관계가 동일 표본 통제 뒤 영에 가까워짐, 넓은 구간, 업종·경제·비용 근거 부족. 부호 반전이나 알파 승인을 처방하지 않음 | 양쪽 중대 지적 없음. 고정은 네 국면과 각 지원 상태를 모두 설명한다. 적응형은 사전 대비의 두 국면만 상세하게 적어 나머지 둘을 생략(P05). |

## 국면과 미계산 상태에 대한 세부 검토

네 재무 사례에서 `DOWN_LOW`는 11개월·6발생구간이며 `INSUFFICIENT_SUPPORT`다. 양쪽 모두 이를 정확히 남겼고 효과 부재로 해석하지 않았다. 적응형의 P01~P04는 이 상태를 숨긴 오류가 아니라 개월 수 옆에 발생구간 수를 함께 적지 않은 누락이다. 고정 방식은 모두 표시했다. 해당 근거는 `asset_growth_12m/regime_interaction/d772e862b657d5819f0d`, `current_assets_growth_12m/regime_interaction/f6023f0f4a5925f7a9bd`, `net_roa/regime_interaction/5f02c473cfc524fda83a`, `operating_roa/regime_interaction/e6c6ddabb91dda210707`이다.

두 모멘텀 사례의 `DOWN_LOW`는 12개월·7발생구간으로 `DESCRIPTIVE`다. 네 재무 사례의 표본 부족을 여기에 잘못 복사한 설명은 없었다. `price_momentum_6_1` 적응형은 `DOWN_LOW`와 `UP_HIGH`(14개월·5발생구간)를 최종 문장에서 생략했지만, 사전 지정한 대비와 불확실성은 정확했다(P05, `price_momentum_6_1/regime_interaction/c56c9768b52975b9b5b8`). 발생구간 수를 추가하더라도 독립 재현 횟수로 사용할 수 없다.

모든 설명은 역사적 업종 분류 부재와 실행비용 `NOT_COMPUTED`를 남겼다. 비용 진단의 공통 누락 자료는 `same_window_holdings_and_cost_measurement`이며, 매월 새로 만든 분위 차이를 인증된 보유·체결·순수익으로 서술하지 않았다. 모멘텀 두 사례의 `economic_link`도 `hypothesis_aligned_economic_outcome` 부재로 `NOT_COMPUTED`이며 경제적 실패와 구분했다. 이 상태는 각 사례의 `controls`, `execution_cost`, `economic_link` 근거에 직접 연결된다.

열두 설명 모두 관측 통제와 인과 식별을 구분한다. 재무 네 사례의 12개월 경제 결과와 1개월 수익 간 지평 불일치도 보존한다. `POLICY_BOUND`와 해시 결합을 역사적 최초 발표본 인증으로 바꾸지 않으며, 국면 `PIT_ASSUMED`, 기술적 HAC 구간 및 반복 열람의 한계를 명시한다. 기계적인 `mechanism_identified=false`뿐 아니라 실제 문장에서도 인과·매개가 확인됐다는 주장을 찾지 못했다.

## 비교의 적용 범위

이 묶음만으로 적응적 진단 선택의 과정상 우열은 판단할 수 없다. 전체 행동 이력·프롬프트·모델 출처를 검토한 것이 아니고, 경과 시간·토큰·금전 비용 측정도 없다. 별도 원장에서 쓰는 비용 수치가 있다면 **명목 예산 단위**라고 표시해야 하며 초·시간·원·달러로 읽으면 안 된다. 거래 실행비용 미계산과 연구 작업 예산도 서로 다른 항목이다.

현재 뒷받침되는 판단은 “두 방식이 같은 근거에서 핵심 결론과 제한을 보존했고, 고정 설명이 일부 근거 지원과 경쟁 설명을 더 상세하게 남겼다”이다. 적응형 우위를 증명하거나 고정 방식의 일반적 우위를 확정하려면 이번 설명의 길이나 중복 근거 수를 성과 점수로 바꾸는 방식은 적합하지 않다.

이 문서는 종료된 Discovery 설명의 비교 기록이다. 원본 수정, 진단 재실행, OOS 확인, release stage, 기억 게시, Gold 적재를 하지 않았으며, 별도 release 초안에 대한 `ACCEPT` 비평 영수증을 대신하지 않는다.
