# 산출물 분류 축

리서치 루프의 산출물(`research/history.jsonl`, `research/runs/<cycle>/`)에 덧씌우는 라벨 체계다.
**기존 파일을 고치지 않는다.** 라벨은 `labels.jsonl`에 따로 산다.

## 왜 필요한가

`latest.md`의 시행 이력만으로는 "어느 쪽 연구를 했고 어디가 비었는지"를 계산할 수 없다.
현행 `category`는 33건 중 10건이 `other`이고, `family`는 30/33으로 거의 1:1이라
집계도 군집도 빈칸 탐지도 성립하지 않는다.

## 출처

축 1·2와 문헌 메타데이터는 **Open Source Asset Pricing**(Chen & Zimmermann)의 `SignalDoc.csv`에서 가져왔다.
2026-08-08 기준 331개 시그널.

> ⚠️ **원본 CSV는 이 레포에 넣지 않는다.** 코드가 GPL-2.0이고 데이터 파일의 배포 조건이 명시돼 있지 않다.
> 여기에는 **범주 어휘와 축 정의만** 옮긴다. 원본이 필요하면 상류 레포에서 직접 받는다.

---

## 축 1 — `cat_economic` (경제 범주)

OSAP `Cat.Economic` 전사. **37종.** 괄호 안은 OSAP 331건에서의 출현 수(우리 33건과 무관, 어휘 규모 참고용).

```
other (39)                  valuation (30)              profitability (19)
investment alt (17)         liquidity (16)              external financing (16)
composite accounting (15)   momentum (15)               investment (12)
asset composition (12)      profitability alt (11)      lead lag (11)
earnings forecast (9)       risk (9)                    volatility (9)
sales growth (9)            accruals (8)                R&D (8)
leverage (7)                volume (6)                  long term reversal (6)
default risk (6)            earnings growth (5)         short sale constraints (5)
optionrisk (4)              payout indicator (4)        recommendation (3)
investment growth (3)       informed trading (3)        ownership (3)
earnings event (2)          info proxy (2)              cash flow risk (2)
turnover (2)                size (1)                    short-term reversal (1)
market risk (1)
```

**해상도 주의** — 37종은 우리 33건을 놓기에 너무 잘다. 축 2와 교차하면 296칸이고
평균 셀 점유가 0.11건이다. **교차표 표시축으로는 축 3을 쓰고, 이 축은 드릴다운 라벨로 둔다.**

## 축 2 — `cat_data` (데이터 원천)

OSAP `Cat.Data` 전사. **8종.**

| 값 | OSAP 출현 | 우리 Silver에서 가능한가 |
|---|---:|---|
| `Accounting` | 196 | 가능 (DART 재무) |
| `Price` | 56 | 가능 (KRX 시세) |
| `Trading` | 20 | 가능 (`adv20`·`trading_value`) |
| `Other` | 13 | 경우에 따라 |
| `Analyst` | 21 | **불가** — 컨센서스 없음 |
| `Options` | 9 | **불가** |
| `13F` | 8 | **불가** — 수급 없음 |
| `Event` | 8 | 부분 (`sue_score` 한정) |

뒤 4종이 비어 있는 것은 연구를 안 해서가 아니라 **데이터가 없어서**다.
빈칸 해석 시 이 구분을 지켜야 한다.

## 축 3 — `jkp_theme` (JKP 테마) · 교차표 표시축

축 1이 37종으로 너무 잘아 집계가 안 된다. 롤업이 필요한데 **직접 묶지 않고 JKP의 배정을 쓴다**
(Jensen-Kelly-Pedersen 2023, 153 특성 → 13 테마). 출처와 라이선스는 `references.md`.

**허용값 — 정확히 13종. 이 목록은 닫혀 있다.**

| 값 | JKP 특성 수 |
|---|---:|
| `Accruals` | 6 |
| `Debt Issuance` | 7 |
| `Investment` | 22 |
| `Low Leverage` | 11 |
| `Low Risk` | 18 |
| `Momentum` | 8 |
| `Profit Growth` | 12 |
| `Profitability` | 11 |
| `Quality` | 17 |
| `Seasonality` | 12 |
| `Short-Term Reversal` | 6 |
| `Size` | 5 |
| `Value` | 18 |

값이 정해지지 않으면 **비운다.** 14번째 값을 만들지 않는다.

### ⚠️ 13테마는 교차표에 **항상 전부** 나온다

관측치가 0인 테마도 행을 지우지 않는다. **빈 행이 조용히 사라지는 것이 이 작업이 고치려는 결함
그 자체**다(`latest.md`가 `history[-30:]`로 3건을 말없이 잘라낸 것과 같은 실패).

- 렌더러는 13행을 **하드코딩된 목록**에서 시작한다. 데이터에 있는 값만 모으는 방식(`groupby`)을 쓰지 않는다.
- 0인 셀은 공백이 아니라 `0` 또는 명시적 빈칸 기호로 찍는다.
- 테스트가 이를 강제한다 — 출력 행 수 == 13.

### 직관으로 묶었으면 틀렸을 자리

초안에서 손으로 만든 9종을 데이터에 대보니 다섯 자리가 뒤집혔다. JKP를 쓰는 이유다.

| 우리 팩터 | 직관 | JKP |
|---|---|---|
| `return_skewness_24m` | 저위험 | **Short-Term Reversal** |
| `long_term_reversal_36_12` | 반전 | **Investment** |
| `net_equity_issuance_12m` | 발행 | **Value** |
| `trading_turnover_20d` | 유동성 | **Low Risk** |
| `operating_roa_volatility_36m` | 품질 | **Low Risk** |

## 문헌 메타데이터 (축이 아니라 부속 필드)

우리 팩터를 OSAP 행에 붙이면 아래를 상속한다. 붙지 않으면 전부 비운다.

| 필드 | OSAP 컬럼 |
|---|---|
| `osap_acronym` | `Acronym` |
| `paper_authors` | `Authors` |
| `paper_year` | `Year` |
| `paper_journal` | `Journal` |
| `paper_cites` | `GScholarCites202509` |

`paper_year`가 있어야 "논문 공개 이후 알파가 줄었는가"를 물을 수 있다. 이 필드가 그 축의 전제다.

---

## 레코드 스키마 (`labels.jsonl`, 한 줄 = 한 사이클)

```
cycle_id          research/history.jsonl 의 cycle_id. 조인 키
factor            팩터명
ruleset_version   history.jsonl 에서 그대로. 룰셋이 다른 레코드끼리 비교하지 않는다

cat_economic      축 1 값 또는 null (OSAP Cat.Economic 37종)
cat_data          축 2 값 또는 null (OSAP Cat.Data 8종)
jkp_theme         축 3 값 또는 null (JKP 13종)
jkp_evidence      근거가 된 JKP 특성명 (예: "rvol_21d"). 추적용

osap_acronym      매칭된 OSAP Acronym 또는 null
paper_authors     ↓ osap_acronym 이 있을 때만
paper_year
paper_journal
paper_cites

variant_of        다른 팩터의 변형이면 그 팩터명, 아니면 null. 단일 부모만. 순환 금지
analysis          해당 사이클에 대한 2~3문장. 수치·파라미터 수정안을 쓰지 않는다
confidence        high | low.  근거를 특정 못 한 값이 하나라도 있으면 low
evidence          근거 위치 (예: "runs/cycle-0031/report.md ## Mechanism")
```

**`analysis`는 컨텍스트로 나가지 않는다.** 자유서술이라 누출 통제가 불가능하다. 사람이 읽는 근거다.

## 라벨링 규칙

1. 근거는 `runs/<cycle>/report.md` 와 `factors/candidates/<name>.py` 의 `RESEARCH_SPEC` 뿐이다.
2. 근거 문장을 특정할 수 없으면 **비운다.** 지어내지 않는다.
3. 값이 하나라도 비면 `confidence: low`.
4. `ruleset_version`이 다른 레코드끼리 결과를 비교하지 않는다. 33건은 4개 룰셋(fr-2.0.0 / fr-3.1.0 / fr-3.2.0 / fr-3.5.0)에 걸쳐 있고 현행 게이트는 그보다 뒤다.

## 컨텍스트로 나가는 것

`lessons.md` 생성기는 아래만 내보낸다.

- **정체성** — `cycle_id`, `factor`, `family`, `ruleset_version`, 축 1·2·3 값, `variant_of`
- **엔진 지시** — `reflection.json` 의 `permitted_next_actions` · `forbidden_actions` 원문

앞은 평가 **이전**에 정해지는 정보고, 뒤는 엔진이 다음 epoch 에 넘기려고 만든 공인 통로다.

**내보내지 않는 것** — `verdict`, `failed_checks`, `strongest_relationship`, 결과 집계와 빈도,
성과 수치, 파라미터 수정안, `analysis`, 그리고 **평가에서 파생된 라벨 일체**
(`outcome` · `novelty` · `duplicates`).

> **왜 뒤쪽 셋이 여기 있나** — 처음에는 "범주형이라 안전하다"고 보고 반출 목록에 넣었다.
> 틀렸다. `engine/epochs.py` 의 `_failure_bucket` 은 `failed_tiers` 의 **순함수**라
> `DATA_OR_INTEGRITY` 하나로 "T0/T1 에서 REJECT" 가 복원된다. `novelty` 도
> `strongest_relationship.abs_median_spearman` 을 임계값으로 3분할한 값이고,
> `latest.md` 는 봉인 행의 그 열을 `-` 로 가린다. **이름이 범주형인 것과 결과가 아닌 것은 다르다.**

봉인 판정은 우리가 정하지 않는다. `engine.research.exposed_after_cutoff` 를 그대로 부르고
reflection 의 `oos_status` 를 함께 본다. 진행 중 campaign 도 `--context-cutoff` 인자도 없으면
경계를 모르는 상태이므로 **전량 봉인**으로 닫는다.

등록 팩터의 축별 개수는 예외로 허용한다. 결과가 아니라 등록 사실의 요약이다.
