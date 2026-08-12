# 유명 팩터 구현 및 Silver 데이터 공백 감사

- Campaign: `campaign-20260811-001`
- Epoch: `epoch-001`
- Discovery signal 구간: `2018-03 ~ 2023-04`
- Hidden OOS: `SEALED` — 이 감사에서 계산하거나 열지 않음
- Gold write: **없음**

## 이번에 새로 사전등록한 단일 팩터

| 팩터 | 고정 정의 | 예측 방향 | 현재 Silver 적합성 |
|---|---|---:|---|
| `intermediate_momentum_12_7` | 다음 holding month를 `t`로 두고 `t-12`부터 `t-7`까지 6개 월 총수익을 복리 누적 | + | 인증된 `total_return_close`만으로 정확히 계산 가능 |
| `market_leverage` | 공시시점 PIT `total_liabilities` / 월말 `market_cap` | + | Bhandari의 noncommon-equity liabilities / market equity에 대응하며 계산 가능 |

중기 모멘텀은 단순 가격 `shift(7) / shift(12)`로 만들지 않았다. 이 레포의 signal row는
다음 달 수익을 예측하므로, 월수익을 먼저 계산해 formation month 기준 `t-12 ... t-7`의
정확히 6개 월만 사용했다. 중간 달이 하나라도 없으면 값을 만들지 않는다.

시장 레버리지는 총부채를 사용한다. 이는 이자부채만을 사용한 `net debt / market equity`와는
다르다. 후자의 이름으로 바꾸거나 해석을 섞으려면 차입금과 현금 세부 데이터가 추가로 필요하다.

근거: [Novy-Marx (2012)](https://doi.org/10.1016/j.jfineco.2011.05.003),
[Bhandari (1988)](https://doi.org/10.1111/j.1540-6261.1988.tb03952.x).

## Discovery 실행 결과

| 팩터 | 판정 | 투자가능 Rank IC | Rank ICIR | BY q | 가장 강한 기존 관계 |
|---|---|---:|---:|---:|---|
| `intermediate_momentum_12_7` | REJECT | 0.0054 | 0.0580 | 0.5067 | `mom_12_1`, Spearman 0.693 |
| `market_leverage` | PROVISIONAL | 0.0476 | 0.4699 | 0.0021 | `value_sp`, Spearman 0.812 |

중기 모멘텀은 데이터·결정성·커버리지는 통과했지만 전체 IC, 투자 가능 IC, Rank ICIR이
모두 최소요건보다 낮았다. 문헌의 미국 결과를 현재 한국 discovery 구간에서 재현하지 못했다.

시장 레버리지는 IC·기간·중립화 강건성과 discovery BY를 통과했다. 다만 등록된 전체 후보
중에서는 `value_sp`와 0.812로 중복 판정을 받았다. 현재 APPROVED Gold 네 팩터와의 최대
상관은 0.099로 낮았지만, 아래 asset identity 문제 때문에 Gold SQL parity는 통과하지 못했다.
OOS는 계속 봉인되어 있다.

## P0 무결성 차단: 캐시와 현재 RDS의 asset identity 불일치

SQL/Python parity에서 Python 125,776행과 SQL 125,737행 중 같은 `(asset_id, as_of_date)`로
비교할 수 있었던 행은 4,401개뿐이었다. 산식을 고치기 전에 2023-04 종목 단면을 직접 대사한
결과는 다음과 같다.

- 캐시 종목: 2,588개
- 현재 RDS에 같은 `asset_id`가 존재: 2,588개
- 같은 `asset_id`가 같은 KRX ticker를 뜻함: **0개 (0.0%)**
- 예: 캐시 `asset_id=647`은 `000020`, 현재 RDS의 `asset_id=647`은 과거 ticker `9275`이고
  현재 `000020`은 `asset_id=2812`

즉 `.cache/panel.pkl` 생성 뒤 RDS의 종목 ID namespace가 전면 재키되었다. 캐시 내부에서 가격과
재무가 함께 정렬돼 discovery 통계는 계산됐지만, 현재 Gold FK가 뜻하는 종목과 키가 다르므로
이 결과를 Gold 승인 근거로 사용할 수 없다. ticker로 억지 변환해 parity를 통과시키지 않는다.

필요한 해결은 다음 순서다.

1. 현재 RDS에서 인증 패널 캐시를 다시 구축한다.
2. cache metadata와 campaign manifest에 asset-identity mapping digest를 추가한다.
3. campaign 시작·평가·Gold parity 때 live mapping digest가 다르면 즉시 중단한다.
4. 이번 campaign은 `implementation-attempts/attempt-001.json`의 실패 증거와 함께 보존하고,
   데이터 identity 변경으로 무효화된 연구를 재실행하는 명시적 protocol migration을 만든다.

## 이미 구현되어 새 후보를 만들지 않은 유명 계열

현재 레지스트리에는 규모, B/M·E/P·S/P 가치, ROE·ROA·영업이익률, 12-1 모멘텀,
단기·장기 반전, 저변동성·시장베타·MAX, SUE, 자산증가, 순주식발행, Amihud 비유동성,
52주 고점, 계절성 등이 이미 있다. 이름만 다른 변형을 더 만들면 독립적인 연구가 아니라
시도 횟수만 늘어나므로 이번 epoch에서는 제외했다.

## 유명 원형을 정확히 만들기 위해 부족한 데이터

| 만들고 싶은 원형 | 현재 막는 공백 | 필요한 Silver PIT 입력 |
|---|---|---|
| Gross profitability, FF operating profitability | 매출과 영업이익은 있지만 gross profit, COGS, SG&A, 이자비용이 없음 | `gross_profit`, `cost_of_revenue`, `selling_general_admin_expense`, `interest_expense`와 공시 `available_at` |
| Cash-flow-to-price, Sloan/Hribar–Collins accruals, FCF yield | KRX 표준 materializer가 현금흐름표 세부 항목을 만들지 않음 | `operating_cash_flow`, `cash_and_equivalents`, `depreciation_amortization`, `capital_expenditure`, `change_in_working_capital` |
| EBITDA/EV, net-debt yield, 상세 레버리지 | 총부채만 있고 이자부채·리스부채·현금 분해가 없음 | 단기차입금, 유동성 장기부채, 장기차입금, 사채, 리스부채, 현금 |
| q-factor 분기 ROE, earnings-increase streak | 최신 단독분기 이익과 직전 분기 common book equity가 연구 패널에 없음 | standalone 분기 `net_income`, common-equity 구성, 정확한 회계기간·정정·가용시점 |
| 정확한 idiosyncratic volatility·residual momentum | 공식 한국 일별 요인과 무위험수익률이 없음 | 일별 MKT·SMB·HML 또는 사전 인증된 요인, 일별 risk-free, 일별 종목 총수익 |
| 정확한 downside beta·coskewness | 내부 주식 시총가중 proxy만 있고 공식 시장 총수익·risk-free가 없음 | broad-market 일별 총수익지수, 일별 risk-free, 동일 거래일 정렬 계약 |
| Liu LM12·정석 turnover·bid-ask liquidity | 거래 없는 날과 누락 행을 구분할 캘린더, PIT 주식수·유동주식수, 호가가 없음 | 시장 거래일, 거래정지 상태, 일별 volume, PIT shares/free-float, bid/ask |
| 산업 모멘텀·산업 중립 팩터 | KOSPI/KOSDAQ 시장구분만 있고 과거 업종 이력이 없음 | 업종 taxonomy와 `effective_from/to`, `available_at`, revision 이력 |
| 애널리스트 revision·dispersion | 원천과 테이블이 없음 | forecast period/horizon, estimate, analyst count, dispersion, `as_of_at/available_at` |
| Short interest·대차 제약 | 원천과 테이블이 없음 | 공매도·대차 잔고/거래량, free float, 공개시점 |
| 기관보유·ownership breadth | 원천과 테이블이 없음 | holder별 지분, 보고기간, filing/revision, `available_at` |
| Net payout·shareholder yield | 배당 live lineage가 불변 스냅샷을 재현하지 못하고 자사주 매입·소각도 없음 | append-only 기업행위 membership, 재인증 배당, 자사주 매입·소각·발행 |
| 원자재 노출 주식 팩터 | 연속선물의 과거 vintage·롤/총수익 계약과 기업별 노출 매핑이 없음 | PIT 원자재 vintage, 롤·담보수익 계약, 생산자/소비자 기업 노출 이력 |

정확한 IVOL 원형은 직전 1개월의 **일별** 종목 초과수익을 일별 FF3에 회귀한 잔차
변동성이다. 36개월 월수익과 내부 시장 하나로 비슷하게 계산하면 다른 팩터이므로 후보로
등록하지 않았다. Downside beta와 Liu LM12도 같은 이유로 현재 집계 컬럼을 억지로
대체하지 않았다. 근거: [Ang et al. (2006)](https://doi.org/10.1111/j.1540-6261.2006.00836.x),
[Ang, Chen and Xing (2006)](https://doi.org/10.1093/rfs/hhj035),
[Liu (2006)](https://doi.org/10.1016/j.jfineco.2005.10.001).

## 실제 원천 부재와 연결 공백의 구분

- `price_daily`에는 OHLC·거래량·VWAP가 있으나 현재 factor-research 월 패널이 전부 노출하지
  않는다. 이는 원천 부재가 아니라 materializer/계약 연결 공백이다.
- 재무 long 테이블은 확장할 수 있지만 현재 KRX parser가 14개 표준계정만 보존한다. 전체
  OpenDART 계정을 PIT 정정 이력과 함께 백필·표준화해야 한다.
- KOSPI200·KOSDAQ150 가격지수는 있으나 배당 포함 총수익 계약이 아니다. 정확한 시장요인에
  그대로 쓰면 안 된다.
- 배당 캐시의 값 존재는 live lineage 인증과 같지 않다. append-only 스냅샷 membership을
  복구하고 총수익 계약을 다시 인증하기 전에는 신규 배당 팩터를 승격 근거로 삼지 않는다.

## 보강 우선순위

1. **현재 RDS asset identity로 패널 재구축 + mapping digest 계약**
2. 배당·기업행위 append-only lineage 복구와 총수익 재인증
3. 전 종목 OpenDART 전체재무제표 계정 백필·PIT 표준화
4. PIT 업종분류 이력
5. 공식 broad-market 일별 총수익과 일별 무위험수익률
6. 시장 거래일·거래정지·PIT 유동주식수·호가 및 공매도/대차
7. 애널리스트·기관보유 이력
8. 원자재 PIT vintage·롤/총수익 계약과 기업 노출 매핑

원칙은 단순하다. 필요한 PIT 입력이 없으면 비슷한 현재 컬럼으로 유명 팩터 이름만 재현하지
않고, 해당 후보를 차단한 뒤 정확히 어떤 데이터가 필요한지 기록한다.
