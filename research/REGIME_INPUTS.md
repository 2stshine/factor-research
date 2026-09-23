# 연구 진단에 시장·매크로 레짐 전달

## 구현된 경로

`campaign-start`의 기본 registry 또는 `--regime-context` → campaign 안의 동결 입력 → epoch 입력 hash 결합 →
`capture_discovery` → `build_diagnostics(regimes=...)` 및 매크로 축별 집계 →
`regime_comparison` → 공개 허용 후 lesson evidence → 해석/비평/교훈 저장.

레짐은 진단 전용이다. 후보 계산식·부호·gate·OOS 경계·Gold를 바꾸지 않는다.
등록 후에는 입력을 추가하거나 최신 파일로 교체하지 않는다. 입력 없는 기존 campaign은
`NOT_CONFIGURED / NO_FROZEN_PIT_REGIME_INPUT`으로 표시하며 자동으로 새 데이터를 끼워 넣지 않는다.
과거 `result.json`이나 교훈을 수정하거나 기존 후보를 재평가하지 않는다.

[월 리밸런싱 문헌 검토·다음 버전 설계 제안](REGIME_DESIGN_REVIEW_20260921.md)은 별도 문서다.
2026-09-23에 시장 큰 4국면을 기본 표시로 적용하고 한국 생산·물가 방향을 별도 입력으로 등록했다.
기존 시장 v2 공식·동결 연구는 유지하며 일별 RV63 제안은 아직 구현하지 않았다.
[실행 기록](REGIME_REMEDIATION_20260923.md)과 아래 추가 규칙을 따른다.

## 2026-09-23 방향 분류·최신성 보완

기본 registry는 **39축: 검증 정책금리 1, PIT_ASSUMED 38**이다. 추가 1축은 새 원본을 수집한 것이
아니라 기존 한국 산업생산 YoY·CPI YoY에서 파생한 `KR_PRODUCTION_INFLATION_DIRECTION`이다.
`kr-production-inflation-direction-v1`은 각 월말 가용 snapshot의 최근 세 달 평균에서 앞선 세 달 평균을
뺀 부호를 결합한다. 연속 여섯 월, 가용시각이 해당 판단월 말 이내, 가용 후 최대 육십 일 조건을 요구한다.
두 축의 양·음 조합 네 가지, 정확히 영인 축이 있으면 NEUTRAL, 미충족은 UNKNOWN이다.
가격 성과로 기간·기준을 고르지 않았다. 부모 HIGH/LOW 상태는 이 계산에 사용하지 않는다.

140개월 중 134개월을 분류했다(2015-07~2026-08). GDP 성장이나 공식 침체 분류가 아니라
생산 증가율의 모멘텀과 CPI 상승률의 방향 대리값이다. 제공자 event date를 통계 기준월로 간주하지 않으며,
기준월 미제공과 동일 발표값 재사용을 lineage에 기록한다. 최초 발표본 인증은 아니고 PIT 가정 수용을 유지한다.
새 campaign-start만 해당 context·수용서·정책 hash를 동결한다. 기존 연구에는 사후 결합하지 않는다.

[최신 입력 스냅샷](../output/regime_inputs/remediation-20260923-final/README.md)의 과거 사용 가능 축은 39,
2026-08 최신 판독 가능 축은 38이다. KOSPI 완전월은 여전히 2026-06이므로 최신 상태를 UNKNOWN/STALE로 남긴다.
과거 커버리지와 최신성, 최신 입력 상태와 과거 팩터 성과는 별도 항목이다.

```sh
python -m scripts.build_korea_macro_direction \
  --parent output/regime_inputs/fmp-assumed-20260921-v1/context.json \
  --policy research/regime_assumption_policy.json --as-of 2026-09-23 \
  --output output/regime_inputs/<new-production-inflation-version>
```

## 현재 사용 정책: PIT 가정 수용 (2026-09-21)

사용자는 추가 최초값 전수검증·PIT 영향측정 없이 가정을 명시하여 레짐 진단을 사용하도록 요청했다.
[정책](regime_assumption_policy.json)은 이 결정을 별도 기록한다. **사용 가능과 PIT 검증 완료는 다르다.**
과거 감사의 보류 기록·Bronze flags·실제 수집시각은 그대로 두고, 파생 연구 입력만
`PIT_ASSUMED / ASSUMPTION_ACCEPTED`로 연결한다. 팩터 승격 판단의 보조 진단으로 사용할 수 있으나
팩터 feature 사용 권한이나 새 합격 gate는 아니다. 이 가정만으로 추가 검증을 실행 선행조건으로 요구하지 않는다.

[당시 실행 결과](../output/regime_inputs/assumed-regime-layer-20260921-v1/README.md): 2026-09-21 registry 총 **38축**.

| 입력 | 축 수 | 월별 구간·실제 판독 |
|---|---:|---|
| 기존 검증 한국 정책금리 | 1 | 2015-01~2026-08, 140개월 |
| KOSPI, PIT 가정 | 1 | 원본 완전월 2015-01~2026-06; 네 축 판독 2018-01~2026-06, 102개월 |
| FMP 매크로·FX·ETF·COT·변동성, PIT 가정 | 36 | 2015-01~2026-08 총 5,040축·월 중 4,313개 판독, 727개 UNKNOWN |

FMP는 매크로 13·FX 6·ETF 4·COT 10·변동성지수 3축이다. 가격 방향 10축은 2015-04부터,
나머지는 워밍업 후 2017-01 또는 2017-02부터 판독 가능하다. 2026-08 FMP 36축은 모두 판독됐지만
KOSPI 2026-07~08은 원본 부족으로 UNKNOWN이다. 기존 FMP 9계열은 로컬 자료가 2026년 9월
표본뿐이라 장기 입력에 포함하지 않았다. 이는 API 전체의 역사 coverage 부재 판정이 아니다.

고정된 가정·계산:

- 경제 캘린더 actual만 사용하고 provider UTC를 KST로 환산한다. 통계 기준월이 아니라 발표 가정시점으로 정렬한다.
- ETF/FX/변동성 일봉은 해당 날짜 다음 뉴욕 자정에 가용하다고 가정한다. ETF/FX는 연속 4개월의 3개월 변화 부호다.
- 매크로/COT/변동성은 현재 월을 제외한 과거 유효 월값 최소 24개의 확장 중앙값과 비교한다.
- COT는 비상업 순포지션/OI와 화요일 기준+3일 15:30 NY 가정을 쓴다. 이미 확보한 예외 일정을 반영하고 알려진 미해소 지연 구간은 제외한다.
- 노후화 상한은 매크로 60일, COT 14일, 가격/지수 7일이다. 충돌·결측·워밍업은 UNKNOWN으로 보존한다.
- 실제 receipt와 `available_at_assumed`를 분리한다. HIGH/UP은 호경기·미래 상승·인과관계를 뜻하지 않는다.

새 캠페인만 이 입력·가정·정책 hash를 동결한다. 교훈 packet과 해석/비평 단계에도 가정 표시를 전달한다.
기존 후보의 판정·OOS·Gold는 변경하지 않는다. 위 실행은 **원본의 월별 상태 판독**이며, 팩터 성과와의
레짐별 결합·새 교훈 생성은 새 캠페인이 실제 실행된 뒤 기존 공개 절차를 따른다. 운영 스케줄러나 RDS 적재는 아니다.

```sh
# 기존 로컬 원본으로 새 버전 생성: 기존 출력 디렉터리는 덮어쓰지 않는다.
python -m scripts.build_assumed_market_regime --as-of 2026-09-21 \
  --policy research/regime_assumption_policy.json --output output/regime_inputs/<new-market-version>
python -m scripts.build_assumed_fmp_regimes --as-of 2026-09-21 \
  --policy research/regime_assumption_policy.json --output output/regime_inputs/<new-fmp-version>
# source 상태만 판독; campaign 생성·팩터/OOS 평가 없이 실행한다.
python -m scripts.regime_snapshot --registry research/regime_sources.json \
  --as-of 2026-09-21 --output output/regime_inputs/<new-snapshot-version>
```

## 과거 보유·검증 기록 (위 가정 수용 전)

2026-09-20 로컬 S3 검증 증빙 세 개를 실제 검사했다.
당시 Bronze 37개 시리즈·47,483행은 보유 완료지만 역사적 PIT 승인 입력은 0개였다.
`output/regime_inputs/bronze-readiness-20260920.json`에 원래 검증 파일의 SHA256,
manifest URI, 계열 목록, PIT 차단 사유를 기록했다. 이번 검사는 실시간 S3 재조회가 아니다.

Bronze에 `pit_approved=false`인 자료를 이 어댑터가 true로 바꾸지 않는다.
발표/수정 이력 검증 없이 가정 시각을 검증 시각으로 표시하거나 실제 수집시각을 소급하지 않는다.
아래 후속 정제 승인 전까지는 입력이 차단됐다. **코드 연결 완료와 실데이터 레짐 분석 완료는 다르다**. 새 FMP 자료로 국면별 성과나
경제적 교훈을 실제 산출했다고 주장하지 않는다.

## 입력 계약

`engine.regime_inputs.read_context`는 `diagnostic-regime-input-v1` JSON의 `contexts`를 읽는다.
각 항목은 `source`, `approval_file`, `approval_sha256`을 가진다. approval_file은 입력 파일
기준 상대경로 또는 절대경로다. 범용 자동 PIT 인증 CLI는 없다. 공식 한국 정책금리 검증/정제 경로와
사용자 정책을 요구하는 별도 가정 입력 생성 경로를 구분한다.

`source` 공통 필드:

- `context_id`: 중복 없는 계열/축 식별자.
- `source_id`: 출처와 데이터 버전의 식별자.
- `kind`: `market_index` 또는 `macro_state`.
- `rows`: 사전에 PIT 검증되었거나 아래 별도 가정 수용 계약을 통과한 월별 입력. 미래 성과를 보고 정한 국면은 허용하지 않는다.
- market_index: `official_market_index=true`, `market_id`, 그리고 각 행의
  `month`, 양수 `close`, `known_at`. 공식 지수 하나만 지원하며 ETF로 대신하지 않는다.
- macro_state: 사전 고정 `states` 목록과 `classification_rules`(버전·계산식·임계값 등),
  각 행의 `month`, `state`, `known_at`. 이는 별도 검증/산출된 상태를 전달하는 계약이며,
  이 코드가 원시 매크로 값으로 임계값을 최적화하거나 새로운 국면을 생성하지 않는다.

`month`는 판단 대상 월이다. 특히 매크로 통계 대상월과 혼동하지 않는다.
v1 `known_at`은 한국 판단 달력으로 정규화하고 검증한 최종 입력의 실제 공개시각이다.
timezone-naive 한국 달력 날짜/시각만 허용하며, raw FX 날짜에서 타임존을 추측하지 않는다.
월말까지 알려지지 않은 값은 UNKNOWN으로 남긴다. 다음 달에 공개됐다는 이유로 그 전 달을
다시 판독하지 않는다. 엄격 검증 경로에서 통계 기준일·발표일·수정 버전 해소는 상류 PIT 검증의 책임이다.
가정 경로의 `known_at`은 검증 공개시각이 아니라 명시된 월말 가용성 모델의 판단시각이다.

별도 approval 파일에는 다음이 필요하다:

- `schema_version=pit-regime-approval-v1`, `status=APPROVED`, `source_layer=SILVER`,
  `purpose=DIAGNOSTIC_ONLY`.
- `source_id` 및 전체 source 객체의 `source_sha256`.
- `pit_approved`, `publication_time_verified`, `revision_history_verified`,
  `historical_backtest_allowed`가 모두 명시적 true.
- 담당 `reviewer`, timezone 있는 실제 `reviewed_at`, 비어 있지 않은 근거
  `evidence` 목록(각각 `uri`, `sha256`).

이 파일은 상류에서 실제 검토 후 발급한 진술이다. 해시 대조는 데이터와 검토의 결합을 확인할 뿐,
진술 자체의 경제적 정확성이나 외부 인증기관의 전자서명을 검증하지 않는다.
Boolean·가짜 근거를 직접 채워 인증을 우회하면 안 된다. 현재 Bronze 검증 보고서는 이 승인이 아니다.

별도 가정 수용서는 `schema_version=pit-regime-assumption-v1`, `status=ASSUMPTION_ACCEPTED`,
`source_layer=DERIVED_RESEARCH_CONTEXT`, `purpose=DIAGNOSTIC_ONLY`를 사용한다.
PIT/발표/수정 검증 flags는 false, `historical_backtest_allowed=true`는 **가정 하의 진단 사용**만 뜻한다.
source의 `pit_status=PIT_ASSUMED`, `known_at_semantics=ASSUMED_HISTORICAL_AVAILABILITY`,
비어 있지 않은 assumptions·월별 scope와 사용자 정책 원문/hash·출처 근거/hash를 결합한다.
`factor_feature_allowed=false`, `intraday_allowed=false`를 유지한다. 검증 v1/v2 계약은 완화하지 않는다.

## 사용과 시점 보호

```sh
# 새 캠페인 시작이 이미 승인된 경우에만 기존 campaign-start 옵션에 추가한다.
python -m scripts.research campaign-start --campaign <new-id> \
  --regime-context /absolute/path/to/reviewed-context.json
```

입력은 campaign 생성 시 내부 JSON으로 복사·hash 동결하며 이후 외부 파일을 다시 읽지 않는다.
Discovery data cutoff와 OOS 시작으로 계산한 마지막 신호월까지만 저장한다.
워밍업용 과거 지수 이력은 남기지만 OOS/embargo 관측은 값 계산 전에 제외한다.
epoch는 이 hash를 다시 결합해 등록 후 입력 변경을 거절한다.

시장 지수는 기존 `monthly-trend-vol-v2`의 장·단기 네 축을 그대로 계산한다.
매크로 상태는 모든 설정 축·모든 상태·UNKNOWN을 보존하며 가장 성과가 좋은 구간을 고르지 않는다.
개월 수·서로 다른 상태를 사이에 둔 발생 구간 수와 표본 부족을 함께 보고한다.
시장 입력만 없거나 일부 매크로가 UNKNOWN이면 PARTIAL/NOT_COLLECTED를 유지한다.
두 종류 모두 t월 말 상태와 t+1 수익을 연결한다. 미래 수익을 t월 레짐에 넣지 않는다.

종료 후 기존 공개 필터를 통과한 `regime_comparison`만 교훈 해석자에게 전달된다.
`regime-input-contract-v1` hash가 시장/매크로 출처·분류 정의를 교훈에 결합하여 서로 다른 기준을
같은 교훈으로 합치지 않는다. 기존 prepare → 해석 → critique → save 절차를 유지한다.

## 검증

`tests/test_regime_inputs.py`는 합성 자료로 실제 capture 호출부터 lesson packet까지 전달을 확인한다.
PIT 미승인·Bronze layer·승인 파일/입력 hash 불일치, 입력 교체, 늦은 발표, 월 누락,
OOS/embargo 차단, 다른 진단의 수치 불변성도 검사한다. 합성 테스트는 실자료 인증이나 연구 실행이 아니다.

Bronze 보유 증빙은 연구 결과를 열지 않고 다음과 같이 점검한다:

```sh
python -m scripts.regime_inputs \
  --bronze-verification /absolute/path/to/verification.json \
  --output /absolute/path/to/new-readiness.json
```

`--bronze-verification`은 여러 번 지정할 수 있고 출력은 덮어쓰지 않는다.
S3 보유 검증 성공을 PIT 승인으로 해석하지 않으며, RDS/Gold write·새 평가·OOS 공개를 하지 않는다.

## 사용 가능한 후속 정제 입력: 한국 정책금리

[정제 결과와 근거](../output/regime_inputs/kr-policy-pit-20260920/README.md).
`KR_POLICY_DIRECTION_3M`은 2015-01~2026-08 **140개월**의 월말 금리 방향이다.
정확한 S3 FMP 105행을 한국은행 공식 결정 103건과 대조했고 모든 actual이 일치했다.
공식 날짜로 36행을 정규화하고 중복 2행의 연결 근거를 남겼다. 2014년 워밍업을 포함해 공식 PDF 115건,
공식 시행일 표의 변경 27건을 확인했다. 이는 원래 FMP 계열 전체가 아닌 정제된 월말 입력 1개의 승인이다.

별도 `pit-regime-approval-v2`는 **공식 정책 결정의 날짜 단위 증거**만 허용한다.
`publication_time_verified=false`를 유지하고 `publication_date_verified=true`,
`historical_availability_verified=true`, `availability_basis=OFFICIAL_POLICY_PUBLICATION_DAY_END_KST`를
요구한다. 날짜의 종료시각을 보수적 가용 상한으로 쓰며 월별 known_at은 해당 월말 종료로 한정한다.
`revision_basis=DATED_OFFICIAL_POLICY_DECISIONS`, macro_type=policy_rate,
value_semantics=ANNOUNCED_POLICY_TARGET, MONTH_END 빈도와 장중/팩터 feature 금지를 함께 검사한다.
따라서 일반 경제통계·FX·ETF에 임의 지연을 붙여 승인하는 우회 경로가 아니다. v1 계약은 그대로다.

`research/regime_sources.json`의 승인 context/hash를 **새 campaign-start의 기본 입력**으로 로드한다.
명시적 `--regime-context`는 기본 입력을 대체하고, `--no-regime-context`는 해당 새 캠페인에서만 제외한다.
등록 artifact 손상/누락은 오류이며 무시하지 않는다. 기존 캠페인은 동결 입력을 유지한다.
로컬 불변 Silver artifact이며 RDS 적재·시장지수 승인·실제 팩터 평가를 의미하지 않는다.
나머지 36계열의 역사적 PIT 검증 승인은 여전히 없지만 위 별도 가정 경로로 진단 사용이 가능하다.
현재 동결 범위 이후 관측은 새 버전으로 생성·등록해야 하며 기존 캠페인에는 소급하지 않는다.

## 2026-09-20 실원본 PIT 심사 후속

[실원본 심사 보고서](../output/pit_audit/fmp-20260920/report.md) 및
`output/pit_audit/fmp-20260920/review-v2/decisions.json`에 37계열의 보류 판정을 기록했다.
당시 47,483행 로컬 보존 검사와 공식 소스 대조를 수행했으며 역사적 승인 입력은 0개였다.
23계열은 실제 backfill 로컬 원본, 14계열은 앞선 macro replay이므로 후자는 S3 동일본 인증이 아니다.
Cboe 현재 종가 74건 차이·공식 날짜 없는 1건, COT +3일 가정의 발표 지연 반례를 확인했다.
당시 원본의 flags와 기존 campaign을 변경하지 않았다. 이 보류 기록은 승인 파일이 아니며,
위 한국 정책금리 정제 승인은 이후 별도로 발행한 범위 한정 승인이다.

## 2026-09-21 잔여 입력 검증

[후속 검증](../output/pit_audit/fmp-20260921/report.md)은 기초 품질·현재 공식값 일치·역사적 PIT를 구분한다.
COT 10계열의 61,100개 핵심 값은 CFTC 현행 이력과 모두 일치했다.
CPI 공식 발표 140건에서 280개 값 중 279개 일치, 1개 차이 및 발표/수정 시점 예외를 확인했다.
ETF 최신일 종가 4개는 운용사와 일치하나 장기 NAV를 과거 종가 대조로 대체하지 않았다.
FX와 나머지 매크로의 공식 최초값 전수 검증은 미완료다.
이 결과는 별도 감사 증빙이며 승인 계약이나 등록 입력을 변경하지 않는다.

## 2026-09-21 전체 입력 PIT 재검토와 완성 사전검사

[현재 입력·후보 통합 감사](../output/pit_review_20260921/report.md)는 DART·KRX·FMP·KIS를 구분한다.
로컬 DART 최초본 누락 표본 및 KRX 현재 명칭의 과거 적용 차이를 확인했고, live RDS 전체 인증은
연결 제한으로 완료하지 못했다. 기존 한국 정책금리 월말 진단 1개 승인 외 신규 승인은 없다.

`scripts.regime_readiness --manifest <review-scope.json> --registry <registry.json>
--output <new-output.json> --require-complete`는 필수 검토 목록을 자동 축소하지 않고,
근거 해시·승인 범위·가용 월·UNKNOWN·워밍업을 검사한다. 하나라도 미완료면 exit 2다.
검토 목록 및 결과는 입력 준비도이지 원문 빈티지의 자동 인증이 아니다. 이 과거 전수검증 목록을
가정 수용으로 임의 축소하지 않는다. 기본 strict 모드에서 가정은 검증 승인으로 세지 않는다.
명시적 `--allow-assumed`는 수용된 입력을 `READY_ASSUMED`로 구분하며 다른 차단 사유를 면제하지 않는다.
새 운영 입력은 위 snapshot으로 별도 확인한다. 레짐 연결 완성과 전 원본의 PIT 인증 완료를 혼동하지 않는다.
