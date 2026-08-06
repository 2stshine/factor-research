# factor-research

TeamAlpha의 **DQ 인증된 RDS Silver(`public`)만** 읽어 팩터를 만들고 Gold 승격 여부를 판정하는 엔진.
Bronze는 Silver 품질 대사 외에는 리서치 입력으로 사용하지 않는다.

> 현재 운영 임계값은 이 문서와 `engine/gate.py`에 공개한다. 임계값의 상세 캘리브레이션과
> 공격 분석은 `private/CALIBRATION.md`에 보존한다. 후보는 결과나 임계값에 맞춰 튜닝하지
> 않고 경제적 가설과 PIT 입력을 기준으로 사전등록한다.

## 사용

```bash
uv sync
uv run python scripts/run.py build          # 인증 Silver → PIT 패널 캐시
uv run python scripts/run.py null --n 25    # 귀무 4종×25개 = 최소 100개 보정
uv run python scripts/run.py gate           # discovery 판정; 최종 OOS는 SEALED
```

환경변수: `SILVER_DB_URL`(필수), `CACHE_DIR`(기본 `.cache`).
RDS가 SSM 터널 뒤에 있으면 `build/gate/publish` 전에 터널을 연다.

모든 팩터의 공통 평가 시작일은 `2018-03`으로 고정한다. 개발 표본은 고정 OOS 직전
1개월을 embargo하며, 평가 시작일과 OOS 시작일을 결과에 맞춰 변경하지 않는다.

## 자율 연구 campaign/epoch

새 연구는 후보별로 OOS를 반복해서 보지 않는다. campaign이 최종 OOS를 봉인하고, epoch이
결과를 보기 전에 여러 후보의 이름과 definition hash를 동결한다.

```bash
uv run python scripts/research.py context
uv run python scripts/research.py campaign-start --campaign campaign-001
uv run python scripts/research.py epoch-start \
  --campaign campaign-001 --epoch epoch-001 --factors factor_a factor_b
uv run python scripts/research.py evaluate \
  --campaign campaign-001 --epoch epoch-001 --factor factor_a
uv run python scripts/research.py epoch-close \
  --campaign campaign-001 --epoch epoch-001
uv run python scripts/research.py campaign-freeze \
  --campaign campaign-001 --factors factor_a
# 최소 24 OOS IC개월이 쌓인 뒤 한 번만 실행
uv run python scripts/research.py campaign-reveal --campaign campaign-001
```

평가할 때마다 `research/runs/cycle-NNNN-<factor>/`에 JSON과 Markdown 보고서가 생성되고,
`research/history.jsonl`과 `research/context/latest.md`가 갱신된다. 다음 루프는 반드시 이
컨텍스트를 먼저 읽는다. discovery에는 OOS 수치가 생성되지 않고 최대 `PROVISIONAL`까지만
가능하다. `research/campaigns/`에는 epoch 성찰과 봉인 상태가 저장된다. reveal은 Gold에 쓰지
않으며, 결과를 본 뒤 기존 후보 파일을 수정하거나 같은 OOS로 다시 확인할 수 없다. discovery
입력도 manifest의 data cutoff 이하로 고정하며 현재 캐시가 그 cutoff를 재현하지 못하면 중단한다.

## 왜 통계가 마지막인가

게이트를 4개 관점으로 설계하고 각각을 레드팀이 공격했다. **성공한 공격 18개 중 통계적
요행은 0개**였다. 전부 표본틀(sample frame)이 틀린 것을 수확했다:

| 공격 | 무엇을 수확했나 |
|---|---|
| NCAV 딥밸류 | 상장폐지 종착수익률이 데이터에 없음 — 시계열이 그냥 끝나 −100%가 기록 안 됨 |
| Amihud 비유동성 | 체결 불가능한 가격 |
| 거래정지 리셋 | 정지 구간의 가짜 0 수익률 |
| 배당 갭 | `adj_close` 가 배당 미반영이라 고/저배당 스프레드가 공짜로 생김 |

순열검정·부트스트랩·홀드아웃은 전부 *같은 표본의 재표본*이다. 표본틀이 틀리면 넷이 동시에
같은 방향으로 틀린다. NCAV 공격은 통계 검사 9개를 전부 통과했지만 SQL 한 줄
(`Dept LIKE '%관리종목%'`)이면 즉사한다.

> 통계를 먼저 돌리면 **틀린 표본 위에서 계산한 t 를 다중검정 보정**하는 셈이 된다.

## 게이트 구조

| Tier | 무엇을 보나 | 백테스트 | 성격 |
|---|---|---|---|
| T0 | 등록·결정성·타입안전 | 0회 | 결정론 |
| **T1** | **표본틀 무결성** | 0회 (SQL) | 결정론 — 공격 11/18 격추 |
| T2 | 전체·투자 가능 IC 최소요건과 투자 가능 IC 유의성 | 진단 1회 | 통계 |
| T3 | 기간별·레짐·중립화 IC 강건성 | IC 재계산 | 통계 |
| T4 | discovery BY FDR + campaign 최종 OOS·귀무 보정 | 최다 | 통계 + 시행 원장 |
| T5 | 기존 Gold 신호와 직교성 | — | 신호 |

최종 confirmation 판정은 T0·T1·T2·T4·T5 중 하나라도 실패하면 `REJECT`, T3 soft fail이 하나면
`PROVISIONAL`, soft fail이 없으면 `PROMOTE`다. T3 soft fail이 둘 이상이어도 `REJECT`다.
discovery survivor는 OOS가 봉인되어 있으므로 soft fail이 없어도 최대 `PROVISIONAL`이다.
`PROMOTE`는 연구 판정일 뿐이며, 사람 승인 없이 Gold에 자동 발행되지 않는다.

## 유니버스 계약

**유니버스는 게이트가 고정하고 팩터가 바꿀 수 없다.** 후보가 자신에게 유리한 종목만
골라 결과를 부풀리지 못하게 하기 위해서다.

```
전체 유니버스 = KOSPI/KOSDAQ · 보통주 · SPAC/리츠 제외 · 상장 250거래일 경과
                · 시가총액과 total_return_close가 정상인 종목
투자 가능 유니버스 = 전체 유니버스 중 ADV20(최근 20거래일 일평균 거래대금) >= 5억원
```

`5억원`은 모든 투자자에게 절대적인 체결 가능선이 아니라 현재 엔진의 유동성 가정이다.
소액으로는 기준 미만 종목도 살 수 있지만, 여러 종목을 반복 리밸런싱할 때 가격 충격이 커질 수
있어 별도 투자 가능 유니버스로 검사한다. 향후 목표 AUM과 허용 거래 참여율이 정해지면 이 고정
금액 대신 `종목별 주문금액 / ADV20` 방식으로 바꾸는 것이 더 적절하다.

**상장폐지 종착수익률 3점 스트레스** — 비활성·상폐 종목의 마지막 관측에 `{0%, −50%, −100%}` 를
강제 부여하고 세 시나리오 전부에서 부호가 유지되어야 한다. 안 하면 롱레그의 최악 실현값만
표본에서 증발한다.

## 현재 판정 기준: `fr-3.3.0`

절대 순알파, net IR, Deflated Sharpe, 비용 스트레스 수익률은 승격 기준이 아니다.
표본 기간과 포트폴리오 구성에 민감한 절대 수익률 컷 대신 다음을 본다.

- 전체 IC `>= 0.03`, 투자 가능 유니버스 IC `>= 0.02`
- 투자 가능 유니버스 Rank ICIR `>= 0.15` (비연율화)
- 투자 가능 IC의 HAC 단측 p값 `<= 0.10`
- 4개 비중첩 구간 중 3개 이상 IC 방향 일치, IC 레짐 집중도 `<= 0.60`
- 시장·규모·유동성 중립화 후 IC `>= 0.01` 및 p값 `<= 0.10`
- 고정 OOS 투자 가능 IC `>= 0.02` 및 p값 `<= 0.10`, IC 기준 BY FDR `<= 0.10`
- 기존 Gold 팩터와 월별 신호 순위의 중앙값 절대 Spearman 상관 `<= 0.80`

전체 IC의 HAC p값과 `투자 가능 IC / 전체 IC` 유지율은 보고서에 진단값으로 남기되
승격 판정에는 사용하지 않는다. 두 유니버스의 절대 IC 하한을 각각 적용하므로 유지율을
추가 hard gate로 두지 않으며, 실제 운용 대상인 투자 가능 IC의 유의성만 판정한다.

IC는 매월 팩터 순위와 미래수익률 순위의 Spearman 상관이다. Rank ICIR은 투자 가능 유니버스의
`월평균 Rank IC / 월별 Rank IC 표준편차`로 계산하며 연율화하지 않는다. 평균 IC가 높더라도
월별 흔들림이 지나치게 크면 0.15를 넘지 못한다. HAC는 연속된 월의 IC가 서로 독립적이지 않고
시기별 변동성도 다르다는 점을 Newey-West 방식으로 보정한다. 단측 p값은 실제 평균 IC가 0
이하라는 가정 아래 지금 같은 양의 결과가 나올 가능성을 나타내며, 팩터가 틀릴 확률 그 자체는
아니다.

비용 후 수익률·IR·회전율·미래수익 결측은 보고서에 계속 계산하지만 모두 설명·용량 검토용
진단값이다. 진단 포트폴리오를 만들 표본이 부족해도 IC 연구 판정을 중단하지 않는다.

## 단일 팩터 계약

후보 하나는 하나의 경제적 신호만 검증한다. `value rank + quality rank`,
`small rank + low-vol rank`처럼 이미 정규화된 여러 팩터 점수를 가중합하지 않는다.
여러 원천 필드가 하나의 의미 있는 비율을 만드는 것은 허용한다. 예를 들어
`영업이익 / 총자산`은 단일 영업ROA 팩터다. 게이트는 둘 이상의 횡단면 rank 결합이나
등록 팩터 컬럼 재사용을 T0에서 거부한다.

## 롱온리 진단을 유지하는 이유

표본의 43.5%가 공매도 제약 구간이다.

```
2020-03 ~ 2021-05   전면금지
2021-05 ~ 2023-11   KOSPI200·KOSDAQ150 만 부분재개 (숏 가능 종목 13~14%)
2023-11 ~ 2025-03   전면금지
2025-03 ~           재개
```

미국식 롱숏 템플릿을 그대로 쓰면 존재하지 않는 숏 유니버스를 부풀린 허구가 된다.

## 재무 데이터의 함정

**`Q4 = FY − (Q1+Q2+Q3)` 를 재무상태표 지표에 적용하면 삼성전자 2024 자산총계가 −933조**
(정답 514조)가 나오는데 **에러 없이 통과한다.** 더 나쁜 건 이 버그가
`TTM = Q1+Q2+Q3+Q4 = FY` 항등식 검사를 **100% 통과**한다는 것이다 — 데이터에 Q4 행이 없어
뺄셈으로 정의하는 순간 항등식이 정의상 참이 된다.

→ `engine/fundamentals.py` 의 **flow(5) / stock(9) 타입 태깅**만이 실제로 잡는다.

그 외:
- 분기값은 **단독 3개월**. `Q2 − Q1` 하면 안 된다
- `fs_type` CFS/OFS 공존 → 반드시 필터 (엔진이 CFS 우선 처리)
- Silver의 모든 revision을 `available_date` 순으로 재생한다. `fundamental_current`를 과거에
  붙이면 최신 정정공시가 새므로 사용하지 않는다

## 섹터 한계와 기업행위 데이터

Silver에 과거 시점별 업종분류 이력이 없고 현재 업종을 과거에 복사하면 미래정보가 새므로,
`fr-3.3.0`부터 T3.4 섹터 검사를 판정 기준에서 제거했다. T3.2는 모든 후보에 동일하게
시장·규모·유동성만 통제한다. 따라서 현재 판정은 섹터 중립성을 보장하지 않으며, 특정 업종 쏠림은
보고서 해석과 후속 운용 검토에서 별도 한계로 취급한다. 과거 PIT 업종 이력이 확보되기 전에는
섹터 검사를 다시 활성화하지 않는다.

**기업행위**는 액면분할·병합, 유상·무상증자, 합병·분할, 배당처럼 가격이나 주식수를 기계적으로
바꾸는 사건이다. Silver에는 이미 `public.corporate_action` 테이블이 존재하지만 factor-research
월말 패널은 아직 이를 붙이지 않는다. 따라서 `net_equity_issuance_12m`처럼 시가총액과 총수익
변화를 이용한 proxy는 실제 증자뿐 아니라 합병·분할·큰 배당 효과가 섞일 수 있다. 기업행위
보강은 이 이벤트를 PIT 기준으로 패널에 연결해 신호의 경제적 원인을 구분하는 별도 작업이다.

## 한국시장에서 확인된 사실

| 사실 | 함의 |
|---|---|
| **모멘텀 부호가 반대** (6-1 t = −2.57) | 미국식 팩터를 이식하면 정확히 반대로 베팅한다 |
| IC 와 롱온리 수익은 다를 수 있다 | 수익률은 승격 컷이 아니라 별도 진단으로 해석한다 |
| 회전율이 높으면 구현 부담이 커진다 | IC 승격 뒤 용량·비용 검토에서 별도로 다룬다 |
| KOSDAQ 소형주가 통계를 지배 | 전체 유니버스 IC 는 투자불가 종목의 통계일 수 있다 |

## 팩터 등록

```python
from engine.factors import REGISTRY, Factor

REGISTRY.add(Factor(
    name="gross_profitability",
    category="quality",
    predicted_sign=1,
    hypothesis="매출총이익/총자산은 순이익보다 회계 조작에 덜 노출돼 이익의 질을 "
               "더 잘 반영한다(Novy-Marx 2013). 한국은 계열사 내부거래로 영업이익이 "
               "왜곡될 수 있어 총자산 대비 정규화가 특히 유효할 것.",
    params={"lookback_quarters": 4},
    rebalance_months=3,
    needs=("revenue_ttm", "total_assets"),
    compute=lambda d: d["revenue_ttm"] / d["total_assets"],
))
```

`hypothesis` 없이는 `Factor` 생성 자체가 예외를 던진다. 게이트가 소스의 숫자 리터럴을
스캔해 **선언되지 않은 파라미터**도 잡는다.

## 판정 안전장치와 남은 한계

- 수익률은 Silver `total_return_close`만 사용하며 결측·비양수 값이 있으면 build를 중단한다
- 과거 PIT 업종 이력이 없어 섹터 중립성은 현재 ruleset의 검증 범위가 아니다
- 비용 모델의 시장충격은 아직 AUM·참여율 함수가 아닌 보수적 추정치다
- 모든 고유 정의의 시행횟수는 `.cache/trials.sqlite3`에, 봉인 OOS 상태는
  `research/campaigns/`에 보존한다. 팀 공용 운영에서는 이 원장을 RDS 테이블로 승격해야 여러
  연구자의 시행을 합산할 수 있다
- 동일 Silver cutoff·ruleset으로 만든 귀무 팩터가 100개 미만이거나 전체 게이트 위양성률이
  10%를 넘으면 T4.4가 실패한다. `build` 뒤 `null --n 25` 이상을 먼저 실행한다
- 현재 ruleset이 `fr-3.3.0`으로 변경됐으므로 이 버전의 귀무 보정을 새로 만들기 전에는
  안전장치상 `PROMOTE`가 나오지 않는다
- epoch-1.0에서는 campaign reveal과 별도 사람 검토 전 `publish --apply`를 차단한다
