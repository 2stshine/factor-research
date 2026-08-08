# 분류 축의 출처

`taxonomy.md`의 축은 두 편의 공개 연구에서 가져왔다. **어느 쪽 데이터 파일도 이 레포에 넣지 않는다.**

---

## JKP — 축 3 (`jkp_theme`)의 출처

> Jensen, Theis Ingerslev, Bryan T. Kelly, and Lasse Heje Pedersen.
> **"Is There a Replication Crisis in Finance?"**
> *The Journal of Finance* 78, no. 5 (2023): 2465–2518.
> <https://onlinelibrary.wiley.com/doi/10.1111/jofi.13249>

- 코드·데이터: `bkelly-lab/ReplicationCrisis` (유지보수는 `bkelly-lab/jkp-data`로 이관)
- 팩터 데이터 포털: <https://jkpfactors.com>
- **라이선스 파일 없음 = 전권 유보.** README가 "코드나 데이터를 쓰면 논문을 인용하라"고 요구한다.

**무엇을 가져왔나** — `GlobalFactors/Cluster Labels.csv`가 153개 특성을 13개 테마로 배정한다. 우리는 **테마 이름 13개만** 전사했다. 배정표 자체는 복제하지 않는다.

**어떻게 썼나** — 우리 팩터를 JKP 특성 하나에 대응시키고, 그 특성의 테마를 라벨로 받는다. `labels.jsonl`의 `jkp_evidence`에 근거가 된 특성명을 남겨 추적 가능하게 한다.

**왜 이 축인가** — 손으로 묶은 분류는 검증이 안 된다. 실제로 초안에서 직접 만든 9종을 데이터에 대보니 네 곳이 뒤집혔다.

| 우리 팩터 | 직관 | JKP 배정 |
|---|---|---|
| `return_skewness_24m` | 저위험 | **Short-Term Reversal** |
| `long_term_reversal_36_12` | 반전 | **Investment** |
| `net_equity_issuance_12m` | 발행 | **Value** |
| `trading_turnover_20d` | 유동성 | **Low Risk** |

`operating_roa_volatility_36m`도 품질이 아니라 **Low Risk**다. 직관으로 묶었으면 다섯 자리가 틀렸을 것이다.

---

## OSAP — 축 1·2와 문헌 메타데이터의 출처

> Chen, Andrew Y., and Tom Zimmermann.
> **"Open Source Cross-Sectional Asset Pricing."**
> *Critical Finance Review* 11, no. 2 (2022): 207–264.

- 레포: `OpenSourceAP/CrossSection` · 코드 **GPL-2.0**
- **데이터 파일의 배포 조건은 명시돼 있지 않다.**

**무엇을 가져왔나** — `SignalDoc.csv`(331 시그널)에서 `Cat.Economic`(37종)과 `Cat.Data`(8종)의 **값 목록만** 전사했다. CSV 원본은 넣지 않는다.

**부속 필드** — 우리 팩터가 OSAP 행에 붙으면 `Authors`·`Year`·`Journal`·`GScholarCites202509`를 상속한다. `Year`가 있어야 "논문 공개 이후 알파가 줄었는가"를 물을 수 있다.

---

## 재현 방법

두 파일 모두 공개 레포에서 직접 받는다. 커밋하지 않는다.

```
OpenSourceAP/CrossSection      SignalDoc.csv
bkelly-lab/ReplicationCrisis   GlobalFactors/Cluster Labels.csv
```

## 상용 사용 전 확인할 것

둘 다 **연구 참조·인용 목적으로만** 쓴다. 제품에 포함하거나 재배포하려면 배포 조건을 먼저 확인해야 한다. OSAP 코드는 GPL-2.0이고, JKP는 라이선스가 아예 없다.
