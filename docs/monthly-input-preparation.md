# 월초 비교 입력 준비 v1 — 로컬 초안

`strategies/monthly_input_preparation.py`는 원천 자료가 준비된 뒤 사용할 **순수 계산·검사 모듈**이다.
`scripts/prepare_monthly_inputs.py`는 동결 계획과 자료 해시를 먼저 확인하여 로컬 초안을 만든다.
DB 조회·쓰기, 자료 수집, Gold 계산, 백테스트 실행, 사이트 배포를 하지 않는다.

현재 구현은 **실제 시장 성과 0/196** 상태를 바꾸지 않는다. 49개 팩터 × 4개 방식의 실행기와
동결 계획은 그대로이며, 이 모듈의 출력은 기존 실행기가 받는 입력 번들이 아니다.
자료를 모두 공급해도 `execution_certified=false`, `real_performance_computed=false`다.
원천 대사와 독립 검토를 거친 최종 번들 변환은 아직 구현하지 않았다.

## 기존 코드 재사용과 새 구현의 경계

| 기존 구현 | 사용할 수 있는 근거 | 이번 구현에서 대체하지 않는 것 |
| --- | --- | --- |
| `engine/dividends.py` | 인증된 배당 이력·계약 확인, 공시 가용시점 적용. 기존 fixture로 늦은 공시가 과거 신호에 들어가지 않음을 재검증 | 해당 인증을 생략하거나 사후 배당 결과를 당시 알려진 신호로 사용하지 않음 |
| 인접 `TeamAlpha-data/pipeline/silver/total_returns.py` | 정정·철회 공시의 canonical event 선택, 배당락일·상장 episode·주식/현금 단위 대사 | 기존 계산은 종가 TR. 시가 TR로 직접 복사하거나 `open × total_return_close / close`로 변환하지 않음 |
| `engine/panel.py:forward_returns` | 과거 연구의 terminal 손실 시나리오 | 기본 -50%를 실제 상폐 정산대금으로 사용하지 않음 |
| `strategies/run_monthly_comparison.py:load_plan` | 동결 구현·계획 해시 및 현재 봉인/shadow 기간 검사 | 새 준비 명령에서도 원천 manifest를 읽기 전에 실행. 기존 보호 로직과 동결 파일은 수정하지 않음 |

## 계산되는 구성요소

### 당시 가용한 점수

`prepare_pit_scores`는 월말 한국시간 23:59:59까지 실제 가용한 후보 중 최신 `as_of_date`의
이미 방향이 적용된 점수를 고른다. 점수·유니버스·시총 각각의 모든 원천 의존성과 가용시각을
호출자가 검토해 공급해야 한다. Gold의 날짜나 DB 적재시각만으로 인증할 수 없다.
유니버스 적격성은 점수 존재 여부와 독립적으로 공급하며, 점수가 없는 종목도 `null`로 남긴다.
이 함수는 오래된 점수의 허용 기간, 원천 정정 이력의 완전성 또는 실제 eligibility를 결정하지 않는다.
이 부분은 49개 정의별 원천 연결·검토와 최종 번들 검증에 남아 있다.

### 원시 주식수로 계산한 시가→시가 총수익 초안

`compute_open_window`는 검토된 완전한 일별 세션·원시 가격·기업행사 원장을 입력받는다.
시가에 1주를 매수한 뒤 주식수와 현금 권리를 추적한다.

- 진입일 배당락·분할은 진입 시가에 이미 반영된 단위다. 진입일 배당 권리를 추가하지 않는다.
- 보유 중 현금배당은 배당락일 종가에 세전 재투자한다. 배당락일이 최종 청산일이면 시가와
  배당 미수금으로 평가하여 청산 이후 종가를 사용하지 않는다.
- 분할·병합·무상주식은 기존 1주당 새 주식수로 반영한다. 같은 날 배당과 분할은 모두
  **행사 전 원시 주식 단위**로 정규화된 증거가 있어야 한다.
- 빈 행사 목록은 “행사 없음”의 증거가 아니다. 상장 episode별 완전성 확인이 필요하다.
- 상폐·합병·유상증자·분사·거래정지, 결측/0 시가, 모호한 행사 중복, 검증되지 않은 재투자
  종가가 있으면 해당 구간을 실패로 남긴다. 종목이나 달을 빼서 통과시키지 않는다.

이는 **배당락일 총수익 재투자 규약**이며 배당 지급일까지의 현금 운용·실제 체결·호가충격을
모사하지 않는다. 현재 v1은 연속 거래와 단순 현금/주식 행사만 처리한다. 비지원 사례가 실제
적격군·이전 보유에 하나라도 있으면 전체 196개 실행 준비를 완료할 수 없다.

## 준비 manifest 인터페이스

JSON 루트의 `schema_version`은 `monthly-preparation-source-v1`, `data_kind`는
`HISTORICAL_MARKET` 또는 `SYNTHETIC_TEST`다. 테스트 값을 시장 자료로 바꿔 표시하면 안 된다.

| 필드 | 필수 내용 |
| --- | --- |
| `source_files[]` | `path`, `sha256`. 상대 경로는 manifest 디렉터리 기준. 실제 파일과 해시가 맞아야 함 |
| `availability_sources` | 원천 ID별 `status=VERIFIED_SOURCE_AVAILABILITY`, timezone-aware `available_at`, `evidence_ref`, `availability_basis` |
| `score_candidates[]` | `factor_id`, 동결 `definition_hash`, `asset_id`, `as_of_date`, `signed_score`(또는 null), `input_refs[]`, `dependency_coverage=COMPLETE_REVIEWED` |
| `universe[]` | `signal_month`, `asset_id`, boolean `eligible`, `market_cap`, `universe_refs[]`, `cap_refs[]`, `dependency_coverage=COMPLETE_REVIEWED` |
| `asset_paths[]` | `signal_month`, `prices[]`, `events[]`, `coverage` |
| `calendar` | `status=VERIFIED_OFFICIAL_SESSIONS`, `source_refs[]`, `sessions[]`의 `session_month`·정확한 `open_at` |
| `market` | `status=VERIFIED_OFFICIAL_TOTAL_RETURN`, `source_refs[]`, `market_id=KRX300_TR`, `return_type=gross_total_return`, `currency=KRW`, `interval=same_entry_open_to_exit_open`, `windows[]` |

허용 가용시각 근거는 `OFFICIAL_PUBLICATION`, `VERIFIED_VENDOR_RELEASE`,
`EXCHANGE_OBSERVATION`, `CANONICAL_ANNOUNCEMENT_PLUS_ONE_DAY`다. 이것은 증거 분류이지
표시 문자열만으로 인증되는 자격이 아니다. 마지막 분류도 기존 배당 계약을 검증한 경우만 쓴다.
현재 CLI는 파일 해시를 확인하지만 `evidence_ref`를 실제 원문으로 해석·인증하는 adapter는 없다.

`asset_paths[].coverage` 필드:

- `asset_id`, `listing_episode_id`, `status=REVIEWED_COMPLETE`, `evidence_refs[]`
- 정렬된 완전한 `session_dates[]`, `raw_share_basis=RAW_UNADJUSTED`,
  `event_cash_basis=PRE_EVENT_RAW_SHARE`

각 `prices[]` 행은 `date`, 같은 `asset_id`·`listing_episode_id`, 원시 `open`, `source_ref`,
`open_status=VERIFIED_TRADABLE`이 필요하다. 배당을 재투자하는 날에는 원시 `close`와
`close_status=VERIFIED_TRADABLE`도 필요하다. 양수 가격만으로 거래 가능성을 인증하지 않는다.

각 `events[]` 행은 고유 `economic_event_id`, 같은 `asset_id`·`listing_episode_id`, `ex_date`,
`source_ref`, `canonical=true`, `resolution_status=VERIFIED`가 필요하다.
`type=CASH_DIVIDEND`이면 `cash_per_pre_action_share`, `SPLIT`/`REVERSE_SPLIT`/`BONUS_SHARES`이면
`new_shares_per_old_share`가 필요하다. 원본 receipt를 직접 합산하거나 조정 DPS를 넣지 않는다.

각 `market.windows[]` 행은 `signal_month`, `entry_at`, `exit_at`, `return_available_at`,
`gross_total_return_multiplier`다. 공급된 공식 첫 세션과 진입·청산시각이 정확히 일치해야 한다.
외부 인터페이스 검사만으로 전체 계획의 99개월 완전성·자료 경계·시장지수 방법론이 인증되지는 않는다.

## 실행과 검증

저장소 루트에서, 새로운 출력 경로로 실행한다.

```bash
.venv/bin/python3 -B -m scripts.prepare_monthly_inputs \
  --plan research/strategy_comparisons/monthly-open-current-20260930/plan.json \
  --output /tmp/monthly-input-draft.json
```

자료가 있으면 `--sources /path/to/reviewed-preparation-sources.json`을 추가한다.
출력은 `monthly-input-preparation-v1`이며 상태는 항상
`DRAFT_COMPONENTS_NOT_EXECUTION_CERTIFIED`, 종료 코드는 2다. 기존 파일은 덮어쓰지 않는다.
CLI는 가능한 구성요소와 실패 사유를 함께 저장한다. 일부 구성요소의 성공은 전체 실행 허가가 아니다.
이 결과를 `run_monthly_comparison --inputs`에 주면 스키마 불일치로 거부된다.

검증 예제는 `tests/test_monthly_input_preparation.py`에 있다. 합성 자료와 기존 배당 fixture로
진입/청산 배당 권리, 분할, PIT 경계, 비지원 행사 차단, 파일 변조, 봉인 기간 선검사,
초안의 실행기 입력 거부를 확인한다. **이 테스트 결과는 실제 투자 성과가 아니다.**

## 실제 자료 준비 상태 — 2026-10-01 KST

- 기존 읽기 전용 DB 경로에서 동결된 49개 정의의 신원이 모두 일치했다.
  99개월 × 49개 = 4,851개 factor-month에 Gold 값이 있다. PIT 인증은 별도다.
- 로컬 캐시에서 월초 후보일 100개와 원시 시가 263,301행을 준비했다.
  0/결측 11,578행을 보존했으며 `execution_certified=false`다.
- 기존 Bronze의 요청 구간 KRX/KOSPI/KOSDAQ 파일 6,102개, 지수명 조합 131개를 조사했다.
  명시적 TR/NTR/총수익/순수익/total-return 이름은 0개였다. 명칭 조사이므로 모든 보유 위치에
  TR이 없다는 증거는 아니다. 원문 필드의 `OPNPRC_IDX` 존재만으로 TR 시가를 입증하지 않는다.
- 공식 개장시각 100개와 같은 구간의 KRX300 gross TR 99개는 아직 없다.
  기존 파일/사용권 확인을 기다리며 새 수집·구독·credential은 만들지 않았다.

남은 구현은 ① 49개 정의의 원천 의존성·역사적 universe/cap를 연결하는 읽기 전용 PIT exporter,
② 원시 시가와 asset/listing identity·DQ·canonical 행사를 연결하는 adapter,
③ 실제 비지원 행사에 대한 정산 회계, ④ 공식 캘린더/시장 TR의 검증·최종 번들 대사다.
이번 모듈은 ①·②의 검증된 출력이 들어올 인터페이스와 단순 사건 회계를 제공한다.
외부 자료만 생기면 바로 196개 성과가 나오는 상태라고 표현하지 않는다.


### 최종 시점 용어

동결 계획의 마지막 신호 2026-05는 2026-06 첫 개장에 진입해 2026-07 첫 개장에 평가한다.
`last_exit_liquidation=false`이므로 마지막 평가에서 강제 청산 매도·청산 비용은 넣지 않는다.
본문의 exit/청산 경계는 수익 구간의 끝이며 실제 매도가 실행됐다는 뜻이 아니다.

### 신호월별 주식 경로 대사 보강

초안에서도 각 `asset_paths[].signal_month=t`의 첫 날짜는 t+1월, 마지막 날짜는 t+2월이어야 한다.
계획 전체 구간 안에 있다는 이유만으로 다른 월의 시가 경로를 같은 신호 수익률에 붙이지 않는다.
검토된 공식 세션 캘린더가 함께 주어지면 두 날짜를 해당 월의 정확한 첫 개장일과도 대조한다.
다른 달·같은 달 종료·같은 달의 잘못된 일자·부족하거나 중복된 공식 세션은 출력 이전에 거부한다.
캘린더가 없으면 월 정렬만 확인하며 공식 개장시각 blocker와 `execution_certified=false`를 유지한다.
일별 시가와 날짜 대사만으로 09:00 실체결이나 최초 print 시각을 입증하지 않는다.
