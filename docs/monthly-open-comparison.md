# 월말 계산 · 월초 실행 비교 v1

## 적용 범위

기존 `engine/gate.py`의 단일 팩터 승격·IC·OOS·종가 수익 결과를 **수정하지 않는 별도 구현 비교**다.
기존 `strategies/run_backtest.py`의 Ridge/QP 경로도 그대로다. 새 경로는 승인 스냅샷의 팩터를
**각각 단독으로** 사용하며 합성 팩터·최고 성과 자동 선택·주문·Gold write를 수행하지 않는다.
과거 결과를 이미 본 연구의 개발용 비교이지 새 독립 OOS가 아니다.

| 순서 | 비교 ID | 선별 | 비중 |
|---|---|---|---|
| 1 · 기준선 | q20_equal | 상위 20% | 동일가중 |
| 2 | q10_equal | 상위 10% | 동일가중 |
| 3 | q20_sqrt_cap | 상위 20% | 월말 시가총액의 제곱근에 비례 |
| 4 | q10_sqrt_cap | 상위 10% | 월말 시가총액의 제곱근에 비례 |

선별 수는 `max(1, floor(적격 종목 수 × 비율))`이다. 소표본에서 기존 gate의 최소 10종목 규칙과
다르며 과거 gate 수치의 재현을 주장하지 않는다. 방향 적용이 끝난 점수 내림차순,
동점은 안정적인 `asset_id` 오름차순이다. 점수 결측은 선별할 수 없지만 적격 분모·전체 EW
벤치마크에서는 빼지 않는다. 20%를 채울 수 없으면 중단한다. 모든 방식에 같은 월·적격 표본을 쓴다.

## 시간·회계 계약

- 신호 t: 한국시간 달력 월말 23:59:59까지 가용한 점수·적격 여부·시가총액.
- 진입: t+1의 검증된 첫 정규 세션 시가. 청산/교체: t+2의 첫 정규 세션 시가.
- 휴일·특별 개장시간은 공급된 캘린더를 쓴다. 평일 또는 매일 09:00으로 추측하지 않는다.
- 배당·분할·상폐를 대사한 **시가→다음 시가 총수익 자산가치 배수**를 별도로 공급해야 한다.
  `open × total_return_close / close`로 조정 시가를 만들지 않는다. 배당락일 진입의 배당 권리 등은
  이 모델에 입력하기 전에 원시 체결가격·기업행사 원장으로 검증해야 한다.
- 보유가치 변동 후 비중에서 다음 매수·매도 금액을 계산한다. 비용을 낸 뒤 목표비중을 맞추도록
  예산 방정식을 푼다. 초기에는 매수비용만 있고 매도세는 없다. 세금은 실제 매도대금에 적용한다.
- 매수·매도비용과 매도세는 선언된 연구 가정이다. 준비 명령은 기존 gate의 비용 가정을 복사하며
  최신 세법·실제 호가충격·운용금액별 용량을 인증하지 않는다. 세율 연도가 없으면 중단한다.
- 단위는 소수 보유가치를 허용하는 배당 재투자 모델이다. 정수 주식수·주문 큐·부분체결 모델이 아니다.
- 마지막 시점은 보유자산 평가액이다. 강제청산 비용은 포함하지 않았다고 표시한다.
- 결측 보유수익을 버리고 비중을 재정규화하거나 불리한 달을 제외하지 않는다. 실행 근거가 없으면 중단한다.

## 세 가지 성과를 함께 표시

1. 비용 후 전략 자체의 총수익·CAGR·MDD.
2. 같은 시가→시가 구간의 전체 적격 종목 동일가중 **gross TR** 대비 순초과수익.
3. 같은 구간의 사전 지정 시장 **gross TR** 대비 순초과수익.

v1 혼합시장 비교 지수는 `KRX300_TR`이다. KOSPI·KOSDAQ을 포함하지만 우량 대형주 중심이라
연구의 전체 시가총액 종목군과 정확히 일치하지 않는다는 점을 남긴다. KOSPI 전용 실험 등에서
다른 지수를 쓰려면 결과를 보기 전에 새 계획의 지수·유니버스를 함께 고정한다.
가격지수·ETF 수정종가·자체 평균을 공식 시장 TR로 대신 표시하지 않는다.

초과수익의 연환산은 월별 수익률 차이의 평균×12이며, CAGR 차이나 위험조정 alpha가 아니다.
벤치마크는 비용 전, 전략은 비용 후라는 비대칭을 명시한다. 초기 NAV=1도 MDD의 고점에 포함한다.
월별 표에는 기준선 수익과 NAV, 매수·매도별 회전율·비용, 점수 커버리지, 거래 및 보유가치도 남는다.

## 실행과 보존

```bash
python -m strategies.run_monthly_comparison prepare \
  --catalog apps/research-observatory/dist/data/gold-catalog.json \
  --decision-start 2018-03 --decision-end 2026-05 \
  --output research/strategy_comparisons/monthly-open-v1/request.json

# 입력 없이 실행하면 부족한 자료를 보고하고 exit code 2. 실제 수익은 계산하지 않는다.
python -m strategies.run_monthly_comparison run \
  --plan research/strategy_comparisons/monthly-open-v1/request.json \
  --output output/strategy-comparison/monthly-open-v1

# 신원 연결과 입력 계약이 완성된 새 계획에만 사용한다.
python -m strategies.run_monthly_comparison run \
  --plan complete-plan.json --inputs authenticated-inputs.json --output new-output-directory
```

파일·출력 폴더는 덮어쓰지 않는다. 팩터 목록·정의·비교 방식·기간·비용·시장 기준선·실행 코드의
SHA-256을 고정한다. 당시 승인됐다는 주장이 아니라, 명시한 로컬 승인 스냅샷을 고정한 것이다.
실행할 때 현재 봉인 캠페인과 미래 shadow 기간을 **입력 읽기 전에** 재검사한다.
미설정 기간·시간대 누락·상태가 불명확한 원장은 무제한으로 처리하지 않고 중단한다.
현재 코드의 보호는 새 비교 경로에 적용되며 기존 Ridge/QP 실행기의 빈틈을 모두 수정한 것은 아니다.

종목·기간을 좋은 성과에 맞춰 줄이지 않는다. 입력이 일부만 갖춰져 있어도 등록 목록의 일부를
조용히 실행하지 않는다. 정의가 연결되지 않은 팩터가 있으면 `INCOMPLETE_REQUEST_NOT_EXECUTION_PLAN`
요청서로 보존하며, 완성된 실행 사전등록이라고 부르지 않는다.

## 입력 번들 형식

`monthly-comparison-inputs-v1` JSON은 `data`, `evidence`를 가진다.

`data`에는 다음이 필요하다.

- `data_kind`: `HISTORICAL_MARKET` 또는 `SYNTHETIC_TEST`.
- `factor_bindings`: 계획과 동일한 `{factor_id, definition_hash}` 목록.
- `market_benchmark`: `market_id`, `return_type=gross_total_return`, `currency=KRW`,
  `interval=same_entry_open_to_exit_open`.
- `source_files`: `{path, sha256}` 목록. 상대 경로는 번들 폴더 기준이며 파일 해시를 확인한다.
- `scores`: `{factor_id, signal_month, asset_id, signed_score, eligible, market_cap, available_at}`.
  `available_at`은 점수·적격 여부·규모 입력 중 가장 늦은 가용시각이다. 점수의 `null`은 결측이다.
- `sessions`: `{session_month, open_at}`. 해당 월의 검증된 첫 정규 세션 한 개씩.
- `asset_windows`: `{signal_month, asset_id, entry_at, exit_at, entry_open,
  gross_total_return_multiplier, return_available_at}`. 적격 전체와 이전 보유 청산 대상이 필요하다.
- `market_windows`: 위에서 `asset_id`, `entry_open`을 제외한 동일 시간 구간의 시장 TR.

`evidence`는 `schema_version=monthly-execution-evidence-v1`, `as_of`, `data_sha256`과
`calendar_verified`, `asset_open_prices_verified`, `total_return_multipliers_verified`,
`market_total_return_verified`, `pit_inputs_verified`를 갖는다. 해시는
`run_monthly_comparison.digest(data)`와 같아야 한다. 모든 시각은 timezone-aware다.
`return_available_at`은 exit 이후이며 `as_of`와 고정 자료 마감 이하여야 한다.

이 플래그는 수집기가 외부에서 확인한 증거를 전달하는 계약이다. 해시와 시간 정합성 검사가
경제적 정확성·원천의 진실·실제 체결을 증명하지 않는다. 없는 증거를 `true`로 채우면 안 된다.
테스트 예제는 `tests/test_monthly_comparison_runner.py`에 있으며 실제 시장 성과와 명시적으로 구분한다.

## 2026-09-30 초기 준비 검사 결과 (로그인 전 기록)

- 공개 승인 스냅샷 49개 중 13개의 정의 해시가 비어 있다. 누락 목록은 요청서에 보존했다.
  이는 13개가 승인되지 않았다는 뜻이 아니라 현재 스냅샷에서 계산 정의를 연결하지 못했다는 뜻이다.
- 원시 주식 시가와 종가 총수익 기반은 존재하나, 시가 진입의 배당·기업행사 회계 입력이 없다.
- 기존 시장지수의 `total_return_close`는 초기 가격 복사본일 수 있어 시장 TR로 사용할 수 없다.
- 공식 첫 세션 개장시각 증거·공식 시장 TR 입력이 확인되지 않았다.
- 현재 DB 메타데이터 재확인은 AWS SSO 토큰 오류로 실패했다. 인증과 커버리지를 최신이라고 주장하지 않는다.
- EOD `available_at` 기본값이 다음 날 08:30인 자료는 월말 23:59 결정과 충돌할 수 있다.
  실제 입력 가용시각을 확인하거나 별도 결정시각 버전을 사전에 정해야 한다.

기본 요청의 마지막 신호를 2026-05로 둔 이유는 다음 달 시가→그다음 달 시가 평가의 마지막
시점이 2026-07이기 때문이다. 이미 공개된 최근 팩터 결과의 수익 지원월 안에서 개발 비교를
설계한 것이며, 이 기간을 새 독립 OOS로 부르지 않는다.

따라서 이 버전은 계산·기간 차단·입력검사·보고 구현과 합성 검증까지다. 실제 시장 비교는
누락 신원·입력 계약이 완성된 뒤 별도 새 계획으로 실행해야 한다. 기존 결과·승격·대시보드는 그대로다.

### 로컬 근거

- `TeamAlpha-data/sql/schema.sql`: 주식 원시 OHLC와 조정 종가.
- `TeamAlpha-data/pipeline/silver/prices.py`: 지수 가격·TR placeholder·가용시각 처리.
- `TeamAlpha-data/pipeline/silver/total_return.py`: 기업행사·배당 총수익 계약.
- `engine/monthly_execution_timing.py`: 월말 판단과 다음 세션 시각의 구분.
- `scripts/audit_monthly_execution_timing.py`: 기존 자료는 날짜 정렬 점검이지 체결 인증이 아님.

## 2026-09-30 로그인 후: 현재 승인 버전으로 새 등록

사용자가 현재 APPROVED 버전으로 별도 비교하는 것을 승인했다. 기존 요청서와 과거 연구·승격
결과는 변경하지 않았다. 새 폴더는 `research/strategy_comparisons/monthly-open-current-20260930/`이다.

- `catalog.json`: 2026-09-30 20:01:13 KST 읽기 전용 DB 확인. 49개 전부 일별 정의,
  버전·방향·정의 해시·SQL 구현 해시 확보. 이전 36개의 정의 해시는 변경됐으며 13개는 과거 해시가 없었다.
- `plan.json`: 49개 × 4개 고정 방식 = 196개 비교 등록. 이전 계획과 같은 판단월
  2018-03~2026-05를 사용하며 수익 지원은 2026-07까지다. 현재 봉인 shadow와 겹치지 않는다.
- `input-audit.json`: 주식 KRX `total_return_close`만 CERTIFIED,
  2015-01-02~2026-09-29. 이는 시가→시가 총수익 인증이 아니다.
- Gold 값은 이미 방향이 적용된 값이다. 부호를 다시 곱하지 않는다. `factor_value`에는 별도
  `available_at`이 없어 월말 score·유니버스·시총의 원천 가용시각 결합이 필요하다.
- 검증된 첫 정규 세션 시각, 시가 진입의 배당 권리·기업행사·상폐 회계,
  같은 시간 구간의 KRX300 TR이 미연결이다. 실제 시장 비교 0/196, 수익률은 미산출이다.
- KRX는 [KRX300 TR을 포함한 총수익지수](https://index.krx.co.kr/contents/MKD/03/0306/03060600/MKD03060600.jsp)를
  안내하지만, 지수 존재와 현재 보유한 실행 입력은 별개다. 종가 가격지수·ETF로 대체하지 않았다.

계획 SHA-256: `e0ecbceda1d3f0ab7c2f2c8da7f44a6f55bd0a7a6a9b889bb7d85016d37992f1`.
실행 준비 검사의 실제 종료 코드는 2 (`BLOCKED_MISSING_EXECUTION_INPUTS`)였다.
`output/strategy-comparison/monthly-open-current-20260930/`에 저장했다.
사이트는 `#comparison`에 준비 상태를 공개하며 과거 IC/OOS를 새 버전에 복사하지 않는다.

다음 순서는 원천 가용시각 결합 → 개장시각·기업행사 원장 대사 → 공식 시장 TR의 같은 구간
입력 확보 → 입력 번들 검증 → 49개 전체 실행이다. 이 자료가 없는데 검증 플래그만 true로
설정하거나 임의 수익률을 생성하지 않는다. 현재 집합의 과거 적용은 개발 비교이지 독립 OOS가 아니다.

### 사이트 배포 확인

- 운영 URL: https://teamalpha-research-observatory.vercel.app/#comparison
- Vercel 배포: `FGTxRYDSbHd1gGTpc2oPNipr4Nbo` (2026-09-30).
- 공개 정적 allowlist만 별도 staging에서 업로드. 로컬의 미배포 `dist/research-map/`,
  인증정보, 연구 원본, 주식별 패널은 제외했다. 배포 전 해당 research-map URL은 404였다.
- index/app/comparison/term-help/새 JSON의 익명 HTTP 200 및 로컬 SHA 일치를 확인했다.
- 147개 Python 테스트 통과. 7개 화면, 177개 연구 상세, 49개 과거 팩터 상세,
  최신 49개 정의·196개 계획·0개 성과 표시 및 공개 경계 검사를 통과했다.
- 운영 브라우저에서 새 페이지, 검색, 용어 도움말 및 JS 오류 없음 확인.
  증빙: `output/strategy-comparison/monthly-open-current-20260930/deployed-page.jpg`.
- commit/push나 Gold/DB write는 하지 않았다. 실제 성과 비교는 미완료다.
