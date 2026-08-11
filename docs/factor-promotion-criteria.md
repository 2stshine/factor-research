# 좋은 주식 팩터의 판정 기준

## 결론

이 레포의 IC는 매월 종목별 **팩터 순위**와 다음 달 **총수익률 순위**의 Spearman 상관을
구한 뒤 월별 IC를 시간축으로 평균한 값이다. horizon·유니버스·수익률 정의가 다르면 같은
숫자라도 뜻이 달라지므로 다른 문헌의 IC를 그대로 같은 통계량으로 취급하지 않는다.

`fr-3.13.0`은 다음 기준을 결과를 보기 전에 고정한다. `fr-3.12.0`의 숫자 임계값과
feature/label 역할 분리를 유지하면서, 모든 신호월 계산을 후보가 선언한 직전 룩백 창으로
물리적으로 제한한다. 최신 정정 배당을 반영한 KRX gross
배당재투자 `total_return_close`는 ex-post 실현값이므로 다음 달 forward-return·IC label에만 쓰고,
후보의 모멘텀·변동성·MAX·Amihud 등은 `adj_close` 기반 분할조정 가격수익률만 쓴다. 원시
Silver 이력은 대사용으로 보존하지만 후보 코드는 `2015-01` 이후만 읽고, 공통 평가는
`2018-03`부터 시작하며 최대 룩백은 36개월이다. 후보 계산 입력에서는 미래수익 레이블과 기존
팩터 신호와 원시 `close`를 제거하며, 역할 metadata가 다르거나 구형 `return_close`가 남으면
실패시킨다. 자산별 무제한 GroupBy 축약과 동적 SQL 필드 접근도 T0/구현 검증에서 차단한다.

배당액·배당횟수처럼 배당 자체를 쓰는 후보는 현재 비활성화한다. 최신 정정 action ledger는
ex-post label에는 적합하지만 과거 각 신호시점의 known-at vintage를 인증하지 않는다. Silver에
별도 historical-vintage 계약이 생기기 전에는 로컬 metadata로 PIT를 자체 인증하지 않는다.

| 대상 | 판정 기준 | 성격 |
|---|---:|---|
| Discovery 전체 유니버스 평균 Rank IC | `>= 0.03` | 후보선·신호 범위 hard gate |
| Discovery 투자 가능 유니버스 평균 Rank IC | `>= 0.03` | 후보선·주 효과 hard gate |
| 투자 가능 Rank ICIR | `>= 0.15` | 내부 안정성 hard gate, 비연율화 |
| 투자 가능 IC HAC p값 | 숫자 보고 후 campaign BY의 입력으로만 사용 | 진단·다중검정 입력 |
| 시장구분·유동성·비의도 규모 노출 제거 후 투자 가능 Rank IC | `>= 0.01` **그리고** 원래 투자 가능 IC의 `>= 30%` | 하나의 compound soft robustness; size category는 규모 노출 보존, HAC p는 진단 |
| Discovery 다중검정 | campaign의 모든 등록 후보에 `BY q <= 0.10` | 선택 편향 hard gate |
| 봉인 OOS | 정확한 36 signal개월에서 유효 IC 36개, `OOS IC >= max(0.02, 50% × Discovery 투자 가능 IC)`, 자동 확인 대상 전체 `BY q <= 0.10` | 최소 효과·유지율 hard gate, 일회성 confirmation |
| 기존 Gold와 신호 상관 | 각 APPROVED Gold와 비교 가능한 월 `>= 36`, 월별 절대 Spearman 중앙값의 최댓값 `<= 0.70` | 중복·비교표본 hard gate |
| 생산 구현 | 자동 확인 대상 전부의 query-only Gold SQL·definition/SQL hash·discovery-only Python/SQL key/raw/rank parity | confirmation 전 hard gate |

수익률, net IR, 회전율과 거래비용은 Gold에 **예측 신호를 등록하는 기준이 아니라** 운용 가능성
진단이다. Discovery `0.03`이나 OOS 절대선 `0.02` 하나만 넘는다고 합격하지 않으며, 데이터
무결성·기간 안정성·다중검정·봉인 OOS·기존 Gold와의 비중복까지 통과해야 한다.

모든 epoch을 닫은 뒤 campaign 전체 BY를 한 번 확정한다. discovery 최종 판정이 `REJECT`가
아니고 BY를 통과한 후보는 전부 자동 확인 대상이 된다. 사람이 일부만 고르거나 빼지 않는다.
campaign은 `AWAITING_IMPLEMENTATION`에서 전 후보의 생산 구현을 검증해야
`READY_FOR_CONFIRMATION`이 된다. OOS의 `PROMOTE`도 연구 판정일 뿐이며 별도 사람 검토 없이
Gold에 자동 write·발행하지 않는다.

투자 가능 유니버스는 임의의 `ADV20 5억원` 문턱을 쓰지 않고 `ADV20 > 0`인 종목으로 정의한다.
연구 단계에는 목표 AUM이 없기 때문이다. 실제 용량은 승격 후 `주문금액 / ADV20` 참여율로 따로
검토하며, 이 기본 필터를 “아무 규모로든 쉽게 체결된다”는 보장으로 해석하지 않는다.

## Discovery 0.03과 OOS 절대선 0.02를 선택한 이유

### MSCI의 good IC를 그대로 동일 통계량이라고 보지는 않는다

학계나 실무에 모든 시장에 적용되는 Rank IC 합격선은 없다. MSCI Barra와 Kahn의 CFA Research
Foundation 출판물은 표준화된 forecast와 이후 **위험조정 잔차수익률**의 상관 문맥에서
`0.05`를 good, `0.10`을 very good 또는 great로 설명한다. MSCI 문서는 상관 방식과 horizon을
명시하지 않고 이 숫자가 시장 환경과 전략에 따라 달라진다고 직접 단서를 둔다. 따라서 이는
KRX 월별 Rank IC의 실증적 최적 컷이 아니라 실무적 등급 휴리스틱이다.

현재 레이블은 잔차수익률이 아니라 총수익률 순위이고, T3도 신호 순위를 시장구분·유동성과
비의도 규모 노출에 대해 잔차화할 뿐 미래수익률 자체를 같은 위험모형으로 잔차화하지 않는다.
따라서 MSCI의 `0.05`를 KRX 월별 Rank IC의 최종 hard gate로 직접 옮기지 않는다. 이 수치는
효과크기를 해석하는 참고점이며, 현재 시스템의 임계값은 표본 분리와 선택 절차까지 포함한
사전 고정 정책값이다.

### Discovery는 0.03에서 후보를 보존한다

Discovery `0.03`은 Gold 충분조건이나 최소 실질효과가 아니라, 개발 표본에서 다음 검증으로 보낼
가치가 있는 후보를 거르는 screening 선이다. 실제 판정에는 자기상관을 반영한 HAC와 campaign
BY를 적용하므로 IC 하나만으로 후보를 확정하지 않는다.

### OOS는 Discovery보다 더 높은 IC를 요구하지 않는다

Discovery에서 관측 성과를 기준으로 후보가 선택되면 winner's curse와 표본 변동 때문에 완전히
미노출된 OOS의 IC가 줄어드는 것이 자연스럽다. 따라서 Discovery 후보선은 `0.03`인데 OOS에서
오히려 `0.05`를 요구하던 기준은 좋은 후보를 불필요하게 탈락시킬 수 있다. `fr-3.10.0`은 정확한
36개월 OOS의 최소 효과크기를 `0.02`로 고정한다.

`0.02`는 모든 시장에 통하는 자연법칙이나 “IC 0.02면 충분하다”는 선언이 아니다. OOS에서
예측 방향과 최소 효과가 남았는지를 확인하는 하한이다. 동시에 유효 IC 36개, 자동 확인 대상
전체의 OOS BY `q <= 0.10`, 같은 snapshot·ruleset·family의 귀무 보정을 요구하므로 `0.02`만
넘는 우연한 결과는 승격되지 않는다.

### OOS는 Discovery IC의 50% 이상도 유지해야 한다

절대선만 쓰면 Discovery IC가 `0.08`이었던 후보도 OOS에서 `0.02`만 남으면 통과한다. 이는 신호의
75%가 사라진 결과를 같은 방식으로 승인하는 문제를 만든다. 반대로 유지율만 쓰면 아주 작은
Discovery IC가 아주 작은 OOS IC로 이어져도 통과할 수 있다. 그래서 두 조건을 함께 사용한다.

```text
필요 OOS IC = max(0.02, 0.50 × Discovery 투자 가능 IC)
```

예를 들어 Discovery IC가 `0.03`이면 OOS는 최소 `0.02`, Discovery IC가 `0.06`이면 최소
`0.03`이어야 한다. 분모는 T2를 통과한 투자 가능 IC라 `0.03` 이상이고, OOS와 같은 방향·같은
유니버스 정의를 사용한다. `50%`는 winner's curse에 따른 축소는 허용하되 신호가 대부분
사라진 경우는 막는 내부 재현성 guardrail이며 보편적 자연상수는 아니다.

### T3 중립화는 절대값과 30% 유지율을 함께 본다

중립화 IC `0.01`만 보면 원래 IC가 매우 강한 후보가 공통 노출 제거 후 대부분 사라져도 통과할
수 있다. 반대로 비율만 보면 잔존 IC 자체가 너무 작을 수 있다. 따라서 같은 투자 가능 표본에서
`중립화 IC >= 0.01`과 `중립화 IC / 원래 투자 가능 IC >= 0.30`을 하나의 compound soft
robustness 검사로 묶는다. 실패가 이 검사 하나뿐이면 `PROVISIONAL`이며 즉시 Gold 승인하지 않는다.

### T5는 기존 Gold와의 최대 중복을 0.70으로 제한한다

후보와 각 APPROVED Gold의 횡단면 Spearman 상관을 월별로 계산하고, 각 Gold별 절대 상관의
중앙값 중 최댓값을 본다. `0.70` 이하는 관련된 경제적 가족을 허용하면서도 사실상 같은 순위를
재포장한 후보를 막기 위한 라이브러리 구성 guardrail이다. 한 달 상관을 안정적인 중복 검사로
오인하지 않도록 각 Gold마다 최소 36개의 비교월을 요구한다. APPROVED Gold 자체가 없을 때만
비교 없이 통과한다.

| 월평균 Rank IC | 이 레포의 해석 |
|---:|---|
| `< 0.01` | 효과가 매우 작음 |
| `0.01 ~ 0.02` | 약한 신호; OOS 최소 효과선 미달 |
| `0.02 ~ 0.03` | OOS 최소 효과선은 충족 가능하나 discovery 후보선 미달 |
| `0.03 ~ 0.05` | discovery 후보 구간; OOS에서는 shrinkage를 허용 |
| `0.05 ~ 0.10` | 강한 효과 구간; 나머지 gate 확인 필수 |
| `>= 0.10` | 매우 강함; 미래정보·누수·표본 오류를 우선 재점검 |

작은 IC도 독립적인 투자기회가 충분하면 경제적 가치가 생길 수 있다는 것이 fundamental law의
핵심이다. 다만 종목 수 자체가 독립 breadth는 아니며 상관, 제약, 비용 때문에 실현 성과는 그
이론적 상한보다 낮다.

### 데이터 기반 검토는 sanity check로만 썼다

구형 `fr-3.2.0` 합성 귀무 100개에서 투자 가능 IC 95백분위는 `0.0052`, 최대는 `0.0078`이었다.
Discovery `0.03`이 그보다 충분히 크다는 점만 확인했다. ruleset과 OOS 구조가 다른 레거시 결과이므로 이
분포에 맞춰 임계값을 튜닝하거나 통계적 보장으로 사용하지 않는다.

### OOS 36개월은 효과크기와 시간 안정성을 함께 확인한다

월별 IC 표준편차가 `0.07`이면 36개월 평균의 단순 IID 표준오차는 약 `0.0117`이다. 그래서
`0.02`라는 효과크기 하한만으로 통계적 확인을 주장할 수 없다. 실제 IC는 시간에 따라 변하고
월별 자기상관도 있을 수 있으므로 HAC p값과 자동 확인 대상 전체의 BY를 함께 적용한다. 즉
`0.02`와 50% 유지율은 효과의 크기와 재현성, BY와 귀무 보정은 선택 편향과 우연을 통제하는
서로 다른 안전장치다.

봉인 OOS는 정확히 36 signal개월이고 유효 IC도 정확히 36개여야 한다. 시작·종료월은 campaign
생성 시 45일 비활성 판정과 closure가 끝난 최신 수익률월에서 역산해 고정하며 뒤의 월을 덧붙이지 않는다.
마지막 경계 확인월은 수익률 마감과 비활성 종목 확인에만 쓰고 IC에는 넣지 않는다. 36개월은
3년의 시간 강건성과 discovery 표본 보존 사이의 사전 고정 정책 절충이며, 복합 규칙의 검정력이
특정 값이라는 뜻은 아니다. 실제 판정력은 family 크기와 자기상관에 따라 달라진다. 정확한 월
산식은 [campaign·epoch 프로토콜](../.agents/skills/factor-research-loop/references/epoch-protocol.md)에만 둔다.

역사 구간도 후보 정의·선택 전에 결과 접근을 막았다면 OOS가 될 수 있다. 반대로 후보가 그
구간의 IC나 수익률에 이미 노출됐다면 같은 날짜를 다시 나눠도 공식 confirmation이 아니다.
이 결과는 `retrospective-only`로 표시하고 승격 근거로 쓰지 않는다. 한 번 reveal한 구간도 다른
candidate campaign에 재사용할 수는 있지만, `HISTORICAL_REUSED_WINDOW`와 기존 exposure id를
남겨 program-wide 독립성이 낮다는 사실을 승격 검토자가 볼 수 있게 한다.

## ICIR, HAC p값, BY q값의 역할

- `Rank ICIR = 월평균 Rank IC / 월별 Rank IC 표준편차`다. `0.15`는 문헌의 보편적 컷이 아니라
  월별 변동성이 지나치게 큰 신호를 막는 내부 guardrail이다. 단순히 `sqrt(12)`를 곱한 값을
  실제 포트폴리오 IR로 해석하지 않는다.
- HAC p값은 월별 IC의 이분산성과 자기상관을 Newey–West 장기분산으로 보정한다. p값은 “팩터가
  틀릴 확률”이 아니라 평균 IC가 0 이하라는 귀무가설 아래 현재와 같거나 더 극단적인 검정통계량이
  나올 확률이다.
- BY q값은 campaign에서 여러 후보를 시도한 사실을 반영한다. 같은 HAC p값에 `q <= 0.10`을
  요구하면 원시 `p <= 0.10`은 자동으로 포함되므로 별도 p hard gate는 두지 않는다.
- `q=0.10`은 선택된 팩터 하나가 90% 확률로 참이라는 뜻이 아니다. discovery에서 허용할
  false-discovery 비율이며, 최종 근거는 별도의 봉인 OOS다.

Discovery BY는 epoch마다 확정하지 않는다. 모든 epoch을 닫은 뒤 **campaign 전체 등록 후보를
한 family로 묶어 finalize 시점에 한 번만** 계산한다. 그래야 뒤에 후보가 추가됐다는 이유로 과거
판정이 조용히 바뀌지 않는다. 비REJECT이면서 BY를 통과한 후보 전부를 자동 확인 대상으로 삼아
수동 선택 자유도를 없앤다. 다만 같은 개발 데이터를 본 성찰로 다음 epoch을 만드는 과정은
적응적 연구이므로 discovery q값만을 순수한 확인 검정으로 과장하지 않는다. 자동 확인 대상과
definition/SQL hash와 구현 parity를 확정한 뒤 봉인 OOS를 한 번만 공개한다.

T4 귀무 보정은 같은 Silver snapshot·ruleset·campaign family로 네 생성기 각각 25개, 총 100개
family를 요구한다. 네 생성기 중 최악의 family 오류율도 `10%` 이하여야 한다. 보정 결과는 closure
Silver panel content digest와 기존 Gold 신호 digest에 결박하며 입력이 바뀌면 다시 만든다.

## 좋은 팩터가 갖춰야 할 것

1. **가설**: 결과를 보기 전에 경제적 메커니즘, 방향, 반증 조건이 고정돼 있다.
2. **무결성**: 인증된 Silver PIT만 사용하고 미래 공시, 생존편향, 종착수익 누수가 없다.
3. **Discovery 후보선**: 동일한 1개월 horizon에서 전체와 투자 가능 Rank IC가 각각 `0.03` 이상이다.
4. **안정성**: 개발 표본 60개월 이상, Rank ICIR, 네 비중첩 구간, 레짐 집중도를 함께 본다.
5. **공통노출 이후 잔존성**: 중립화 IC가 `0.01` 이상이고 원래 투자 가능 IC의 `30%` 이상 남는다.
   size category에서는 가설 자체인 규모 노출을 보존한다.
6. **선택 편향 통제**: 성공·실패를 포함한 campaign 전체 후보의 HAC p값을 BY 보정한다.
7. **진짜 OOS**: 미노출 역사 구간에서 전 후보를 정확한 36개월 동안 한 번만 확인하고, 유효 IC 36개·`max(0.02, Discovery IC의 50%)`·OOS BY를 함께 요구한다.
8. **구현 동등성**: 전 후보의 query-only Gold SQL을 연구 정의와 hash로 묶고 discovery 구간의 key·raw value·rank parity를 통과한다.
9. **신규성·운용성**: Gold별 비교월이 36개월 이상이고 최대 월별 중앙 절대 상관이 `0.70` 이하며, 통과 후 비용·용량·회전율을 따로 검토한다.

## 참고 문헌

- Grinold (1989), [The Fundamental Law of Active Management](https://doi.org/10.1515/9781400829408-021)
- Kahn, CFA Institute Research Foundation (2018), [The Future of Investment Management](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/book/rf-publication/2018/future-of-investment-management-kahn.pdf)
- MSCI Barra, [Converting Scores into Alphas](https://www.msci.com/documents/10199/1645561/PI_Converting_Scores_Into_Alphas.pdf/7adf1f42-10aa-40eb-9e8c-ecc11eeba2d4)
- Heinen and Valdesogo (2020), [The Spearman rank correlation of the bivariate Student t and scale mixtures of normal distributions](https://www.sciencedirect.com/science/article/pii/S0047259X20302311)
- Ding and Sun (2022), [The Statistics of Time Varying Cross-Sectional Information Coefficients](https://link.springer.com/article/10.1057/s41260-022-00295-9)
- Quantopian, [Alphalens IC implementation and documentation](https://quantopian.github.io/alphalens/alphalens.html)
- Newey and West (1987), [Heteroskedasticity and Autocorrelation Consistent Covariance Matrix](https://www.nber.org/papers/t0055)
- Harvey, Liu, and Zhu (2016), [... and the Cross-Section of Expected Returns](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824)
- Benjamini and Yekutieli (2001), [The Control of the False Discovery Rate under Dependency](https://doi.org/10.1214/aos/1013699998)
- Ramdas et al. (2018), [SAFFRON: an Adaptive Algorithm for Online Control of the False Discovery Rate](https://proceedings.mlr.press/v80/ramdas18a.html)
- White (2000), [A Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152)
- Hou, Xue, and Zhang (2020), [Replicating Anomalies](https://academic.oup.com/rfs/article/33/5/2019/5236964)
- McLean and Pontiff (2016), [Does Academic Research Destroy Stock Return Predictability?](https://doi.org/10.1111/jofi.12365)
- Jensen, Kelly, and Pedersen (2023), [Is There a Replication Crisis in Finance?](https://doi.org/10.1111/jofi.13249)
- Novy-Marx and Velikov (2016), [A Taxonomy of Anomalies and Their Trading Costs](https://doi.org/10.1093/rfs/hhv063)
- Arnott, Harvey, and Markowitz (2019), [A Backtesting Protocol in the Era of Machine Learning](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275654)
