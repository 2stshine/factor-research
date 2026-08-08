# factor-research

TeamAlpha의 **DQ 인증된 RDS Silver(`public`)만** 읽어 팩터를 만들고 Gold 승격 여부를 판정하는 엔진.
Bronze는 Silver 품질 대사 외에는 리서치 입력으로 사용하지 않는다.

> 현재 운영 임계값과 근거는 `engine/gate.py`와
> [좋은 주식 팩터의 판정 기준](docs/factor-promotion-criteria.md)에 공개한다.
> `private/CALIBRATION.md`는 fr-2.x Bronze 기반의 **보존용 구형 기록**으로 현재 판정에 쓰지 않는다.
> 후보는 결과나 임계값에 맞춰 튜닝하지 않고 경제적 가설과 PIT 입력을 기준으로 사전등록한다.

## 사용

```bash
uv sync
uv run python scripts/run.py build          # 인증 Silver → PIT 패널 캐시
uv run python scripts/research.py campaign-start --campaign campaign-001 --epochs 3
```

환경변수: `SILVER_DB_URL`(필수), `CACHE_DIR`(기본 `.cache`).
RDS가 SSM 터널 뒤에 있으면 Silver build·평가·SQL parity 전에 터널을 연다.

`scripts/run.py gate`와 `publish`는 전체 패널이 봉인 OOS를 우회해 노출하지 않도록
`epoch-1.5`에서 비활성화했다. 평가는 아래 campaign workflow로만 실행한다.

모든 팩터의 공통 평가 시작일은 고정한다. campaign은 현재 Silver에서 45일 비활성 판정과
closure까지 끝난 최신 36 signal개월을 hidden OOS로 먼저 떼고, 그 앞부분만 discovery로
동결한다. 따라서 기본 실행은 미래 데이터를 기다리지 않고 지금 IS와 OOS를 모두 판단할 수 있다.
명시적 `prospective_holdout`은 장기 추적이 필요할 때만 사용한다.

## 자율 연구 campaign/epoch

새 연구는 같은 후보의 OOS를 반복해서 보지 않는다. campaign이 현재 데이터의 마지막 36개월을
처음부터 숨기고, epoch이
결과를 보기 전에 여러 후보의 이름과 definition hash를 동결한다.

```bash
uv run python scripts/research.py campaign-start --campaign campaign-001 --epochs 3
uv run python scripts/research.py context  # campaign cutoff 뒤 결과를 가린 컨텍스트
uv run python scripts/research.py epoch-start \
  --campaign campaign-001 --epoch epoch-001 --factors factor_a factor_b
uv run python scripts/research.py evaluate \
  --campaign campaign-001 --epoch epoch-001 --factor factor_a
uv run python scripts/research.py epoch-close \
  --campaign campaign-001 --epoch epoch-001
uv run python scripts/research.py campaign-finalize --campaign campaign-001
# Agent가 자동 통과 후보 전부의 query-only Gold SQL과 manifest를 작성한 뒤 실행
uv run python scripts/research.py campaign-verify-implementations \
  --campaign campaign-001
# READY_FOR_CONFIRMATION에서 사용자가 요청할 때 한 번만 실행
uv run python scripts/run.py null --campaign campaign-001 --n 25
uv run python scripts/research.py campaign-reveal --campaign campaign-001
```

평가할 때마다 `research/runs/cycle-NNNN-<factor>/`에 JSON과 Markdown 보고서가 생성되고,
`research/history.jsonl`과 `research/context/latest.md`가 갱신된다. 새 campaign은 OOS 경계를
먼저 봉인한 뒤, 다음 루프가 cutoff 뒤 결과를 가린 이 컨텍스트를 읽는다. discovery에는 OOS 수치가 생성되지 않고 최대 `PROVISIONAL`까지만
가능하다. finalize는 모든 epoch 후보를 한꺼번에 BY 보정하고, 비`REJECT`이면서 통과한 후보
전부를 자동 확인 대상으로 확정한다. 후보가 있으면 `AWAITING_IMPLEMENTATION`, 없으면
`CLOSED_NO_QUALIFIED`가 된다.

전 후보의 Gold manifest에 SQL URI·`research_definition_hash`를 묶고, 실제 SQL SHA256은 구현
검증 artifact에 동결한다. 동결 snapshot의 discovery 구간에서 Python/SQL key·raw value·rank parity를 통과해야
`READY_FOR_CONFIRMATION`이 된다. 이 SQL은 query-only로 검증하며 Gold write·발행은 하지 않는다.
OOS reveal은 hash·parity·귀무 보정·discovery 재현을 먼저 확인하고 전 후보에 한 번만 수행한다.
마지막 OOS 수익률월 다음 달이라는 월 표지만으로는 부족하며, 비활성 종목 판정을 위해 마지막
signal 월말에서 45일이 지난 실제 Silver 관측일까지 확인한다.

이미 해당 OOS 결과를 본 후보는 같은 역사 구간으로 다시 나눠도 `retrospective-only`다. 다른
후보가 같은 달력 구간을 쓰면 `research/oos-exposures/`를 지우지 않고 manifest에
`HISTORICAL_REUSED_WINDOW`와 기존 exposure id를 남긴다. 정확한 경계 산식과 상태 계약은
[campaign·epoch 프로토콜](.agents/skills/factor-research-loop/references/epoch-protocol.md)을 따른다.

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
| T2 | 전체·투자 가능 IC 최소효과와 투자 가능 Rank ICIR | 진단 1회 | 통계 |
| T3 | 기간별·레짐·중립화 IC와 원본 대비 유지율 강건성 | IC 재계산 | 통계 |
| T4 | campaign discovery BY + 36개월 OOS 절대 IC·Discovery 대비 유지율 + OOS BY·귀무 보정 | 최다 | 통계 + 시행 원장 |
| T5 | 기존 Gold별 비교월 `>= 36`, 최대 월별 중앙 절대 Spearman `<= 0.70` | — | 신호 |

최종 confirmation 판정은 T0·T1·T2·T4·T5 중 하나라도 실패하면 `REJECT`, T3 soft fail이 하나면
`PROVISIONAL`, soft fail이 없으면 `PROMOTE`다. T3 soft fail이 둘 이상이어도 `REJECT`다.
discovery 자동 확인 대상은 OOS가 봉인되어 있으므로 soft fail이 없어도 최대 `PROVISIONAL`이다.
`PROMOTE`는 연구 판정일 뿐이며, 사람 승인 없이 Gold에 자동 발행되지 않는다.

## 유니버스 계약

**유니버스는 게이트가 고정하고 팩터가 바꿀 수 없다.** 후보가 자신에게 유리한 종목만
골라 결과를 부풀리지 못하게 하기 위해서다.

```
전체 유니버스 = KOSPI/KOSDAQ · 보통주 · SPAC/리츠 제외 · 상장 250거래일 경과
                · 시가총액과 total_return_close가 정상인 종목
투자 가능 유니버스 = 전체 유니버스 중 ADV20(최근 20거래일 일평균 거래대금) > 0
```

고정 `5억원` 문턱은 제거했다. 연구 단계에는 목표 AUM과 주문금액이 없으므로 임의 금액으로
예측 근거를 잘라내지 않고, 최근 거래가 실제로 관측된 종목만 별도 유니버스로 검사한다. 진짜
체결 가능성은 승격 뒤 목표 주문금액과 허용 거래 참여율을 정해 `종목별 주문금액 / ADV20`으로
판정해야 한다.

**상장폐지 종착수익률 3점 스트레스** — 비활성·상폐 종목의 마지막 관측에 `{0%, −50%, −100%}` 를
강제 부여하고 세 시나리오 전부에서 부호가 유지되어야 한다. 안 하면 롱레그의 최악 실현값만
표본에서 증발한다.

## 현재 판정 기준: `fr-3.10.0`

판정은 IC 효과크기·시간 강건성·다중검정·표본 무결성·기존 Gold와의 비중복을 함께 본다.
절대 포트폴리오 수익률과 비용 지표는 운용 진단이며 팩터 승격선이 아니다. 지표 정의, 모든
임계값과 근거는 [좋은 주식 팩터의 판정 기준](docs/factor-promotion-criteria.md)을 단일 설명
문서로 사용한다.

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
`fr-3.3.0`부터 T3.4 섹터 검사를 판정 기준에서 제거했다. T3.2는 시장구분·유동성과 비의도
규모 노출을 통제하되, size category에서는 가설 자체인 규모 노출을 보존한다. 따라서 현재 판정은
섹터 중립성을 보장하지 않으며, 특정 업종 쏠림은
보고서 해석과 후속 운용 검토에서 별도 한계로 취급한다. 과거 PIT 업종 이력이 확보되기 전에는
섹터 검사를 다시 활성화하지 않는다.

**기업행위**는 액면분할·병합, 유상·무상증자, 합병·분할, 배당처럼 가격이나 주식수를 기계적으로
바꾸는 사건이다. Silver에는 이미 `public.corporate_action` 테이블이 존재하지만 factor-research
월말 패널은 인증된 현금배당 이력을 PIT 기준으로 붙여 `dividend_cash_ttm`을 만든다. 증자·감자,
합병·분할, 자사주 매입·소각은 아직 월말 신호로 연결되지 않았으므로 가격조정 순발행 정의에도
이 사건들의 효과가 일부 섞일 수 있다.

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
    name="operating_roa",
    category="quality",
    predicted_sign=1,
    hypothesis="영업이익/총자산이 높은 기업은 자산을 효율적으로 사용하며 시장이 그 "
               "수익성의 지속성을 과소평가할 수 있다.",
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_assets"),
    compute=lambda d: d["operating_income_ttm"] / d["total_assets"].where(
        d["total_assets"] > 0
    ),
))
```

`gross_profitability`는 `gross_profit/total_assets` 정의이므로 현재 Silver에 없는
매출총이익을 매출액으로 대체하지 않는다. `revenue_ttm/total_assets`는 이미
`asset_turnover`이며 gross profitability가 아니다.

`hypothesis` 없이는 `Factor` 생성 자체가 예외를 던진다. 게이트가 소스의 숫자 리터럴을
스캔해 **선언되지 않은 파라미터**도 잡는다.

## 판정 안전장치와 남은 한계

- 수익률은 Silver의 인증된 KRX gross 배당재투자 `total_return_close`만 사용한다. 계약이
  `CERTIFIED`가 아니거나 결측·비양수 값이 있으면 build를 중단한다
- 과거 PIT 업종 이력이 없어 섹터 중립성은 현재 ruleset의 검증 범위가 아니다
- 비용 모델의 시장충격은 아직 AUM·참여율 함수가 아닌 보수적 추정치다
- 모든 고유 정의의 시행횟수는 `.cache/trials.sqlite3`에, 봉인 OOS 상태는
  `research/campaigns/`에 보존한다. 팀 공용 운영에서는 이 원장을 RDS 테이블로 승격해야 여러
  연구자의 시행을 합산할 수 있다
- 귀무 보정은 같은 Silver snapshot·ruleset·campaign family, Gold 신호 digest에 결박한다. 필요한
  생성 수와 오류율 기준은 [판정 기준](docs/factor-promotion-criteria.md)을 따른다
- 현재 ruleset이 `fr-3.10.0`으로 변경됐으므로 이 버전의 귀무 보정을 새로 만들기 전에는
  안전장치상 `PROMOTE`가 나오지 않는다
- `epoch-1.5`는 campaign 시작 때 분리한 36개월 OOS를 후보 family에 한 번만 공개하며, 구현 parity·campaign reveal·별도 사람 검토 전
  `publish --apply`를 차단한다
