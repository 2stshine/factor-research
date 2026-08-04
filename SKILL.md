---
name: factor-research
description: 한국 주식 팩터를 발굴하고 Gold 승격 여부를 판정한다. 팩터 아이디어를 가설과 함께 등록하고, 결정론적 게이트로 검증한다. "팩터 만들어줘", "이 아이디어 검증해줘", "Gold에 뭘 넣을지" 같은 요청에 사용.
---

# 팩터 리서치

Silver(RDS `public`)를 읽어 팩터를 만들고 Gold 승격을 판정한다.

## 네 역할과 게이트의 역할

**너는 가설을 만든다. 게이트가 판정한다. 이 경계를 넘지 마라.**

- ✅ 경제적 메커니즘을 생각하고 팩터를 정의한다
- ✅ 결과를 해석하고 왜 실패했는지 설명한다
- ❌ **판정 기준을 추측하거나 역산하려 하지 않는다**
- ❌ **게이트를 통과하도록 팩터를 조정하지 않는다**

마지막 두 개가 중요한 이유: 임계값을 겨냥해 최적화하면 게이트가 목적함수가 되고,
그 순간 게이트는 아무것도 검증하지 못한다. 임계값은 이 문서에 **의도적으로 없다.**
`engine/gate.py` 를 열어보고 싶은 충동이 들면, 그게 바로 하지 말아야 할 일이다.

게이트는 매 실행마다 합성 귀무 팩터를 몰래 섞어 자기 위양성률을 측정한다.
기준을 겨냥한 최적화가 시작되면 그 수치가 즉시 튀어 탐지된다.

## 한 사이클

```bash
python scripts/run.py build     # 패널 캐시 (최초 1회, ~10분)
python scripts/run.py gate      # 등록 팩터 전체 판정
python scripts/run.py null      # 게이트 자체 위양성률 재측정
```

새 팩터는 `factors/` 에 등록한다:

```python
from engine.factors import REGISTRY, Factor

REGISTRY.add(Factor(
    name="gross_profitability",
    category="quality",
    predicted_sign=1,
    hypothesis=(
        "매출총이익/총자산은 순이익보다 회계적 조작에 덜 노출된 수익성 지표라 "
        "이익의 질을 더 잘 반영한다(Novy-Marx 2013). 한국은 재벌 계열사 간 "
        "내부거래로 영업이익이 왜곡될 수 있어 총자산 대비 정규화가 특히 유효할 것."
    ),
    params={"lookback_quarters": 4},
    rebalance_months=3,
    needs=("revenue_ttm", "total_assets"),
    compute=lambda d: d["revenue_ttm"] / d["total_assets"],
))
```

**`hypothesis` 없이는 `Factor` 생성 자체가 예외를 던진다.** 사후 합리화를 막기 위해서다.
가설은 "왜 이게 초과수익을 낼 것인가"에 대한 **경제적 메커니즘**이어야 한다.
"IC가 높을 것 같아서"는 가설이 아니다.

## 좋은 가설을 만드는 법

**데이터에서 시작하지 말고 메커니즘에서 시작하라.** 컬럼을 조합해 무엇이 나오나 보는 건
데이터 마이닝이다. 대신 이렇게 묻는다 — *어떤 시장 참여자가 어떤 실수를 반복하는가?
왜 그 실수가 차익거래로 사라지지 않는가?*

한국 시장에서 실제로 확인된 것들:

| 사실 | 함의 |
|---|---|
| **모멘텀 부호가 반대** (6-1 t=−2.57) | 미국식 팩터를 이식하면 정확히 반대로 베팅한다 |
| 개인 비중이 높다 | 과잉반응·처분효과 계열 가설이 유효할 수 있다 |
| 공매도가 표본의 43.5% 구간에서 제약 | 고평가 해소가 느리다 → 숏 쪽 알파는 실현 불가 |
| 지주·재벌 구조 | 밸류 팩터가 지주회사 할인을 줍는 경우가 많다 |
| KOSDAQ 소형주가 통계를 지배 | 전체 유니버스 IC 는 투자불가 종목의 통계일 수 있다 |

## 사용 가능한 데이터

`build` 후 패널에 있는 컬럼:

```
가격    adj_close(배당 미반영), Close, market_cap, amount, adv20, Market, Stocks
재무    total_assets, current_assets, noncurrent_assets, total_liabilities,
        current_liabilities, noncurrent_liabilities, total_equity, capital_stock,
        retained_earnings, revenue, operating_income, pretax_income, net_income,
        comprehensive_income   (+ flow 지표는 _ttm 접미사)
메타    in_universe, is_distress, age_days, ym, trade_date
미래    fwd_opt / fwd_mid / fwd_pess  (상장폐지 종착수익률 3점 시나리오)
```

**없는 것**: 현금흐름표·감가상각비·배당·섹터 라벨·컨센서스·수급.
→ Accruals, FCF, EV/EBITDA, 배당수익률, 섹터 중립화는 현재 불가능하다.

## 재무 데이터의 함정 (반드시 지킬 것)

- **분기값은 단독 3개월**이다. `Q2 − Q1` 하면 안 된다. TTM 은 `_ttm` 컬럼을 쓴다
- **stock 지표(자산·부채·자본)에 Q4 역산이나 4분기 합산을 하지 마라.** 엔진이 이미
  타입을 분리해뒀지만 팩터에서 직접 하면 조용히 틀린다
- `fwd_mid`(−50% 종착) 를 기본으로 쓴다. 게이트가 3점 스트레스를 자동 수행한다
- 유니버스를 팩터 정의 안에서 마스킹하지 마라 — 게이트가 고정한다

## 결과 해석

```
✅ PROMOTE      Gold 적재 (단, 사람 서명 필요)
⚠️  PROVISIONAL  관찰 목록. 리스크 3% 상한, 2분기 후 자동 만료
❌ REJECT       폐기
```

**실패했을 때 임계값을 물어보지 말고 실패 검사의 이름을 보고 메커니즘을 다시 생각하라.**

- `투자가능 IC 유지율` 실패 → 알파가 유동성 없는 종목에서만 나온다. 실행 불가능한 팩터다
- `실비용 순알파` 실패 → 신호는 있는데 회전율이 비용을 못 이긴다. 더 느린 신호가 필요하다
- `리밸주기 고원성` 실패 → 특정 주기에서만 되는 절벽. 과최적화 신호다
- `비중첩 구간 부호` 실패 → 특정 시기 한 번의 사건으로 전체 성과가 만들어졌다
- `직교성` 실패 → 이미 Gold 에 있는 팩터의 재발견이다

## 하지 말아야 할 것

- 같은 팩터를 파라미터만 바꿔 여러 번 제출하기 (시행횟수가 원장에 기록되고 다중검정
  보정이 강해진다 — 이득이 없다)
- 실패한 팩터를 미세 변형해 재제출하기 (기각된 정의의 자손도 시행횟수에 가산된다)
- IC 만 보고 판단하기 (IC t=4.05 인데 롱온리 순알파가 −7.64% 인 실측 사례가 있다)
- 유니버스 필터를 팩터 정의에 넣기

## 참고

- 방법론 개요: [README.md](README.md)
- Gold 스키마: [gold/schema.sql](gold/schema.sql)
- Silver 사용법·함정: TeamAlpha-data 레포의 `schema_tables.md`

> 임계값·귀무분포·판별력 분석은 `private/` 에 있고 **읽지 않는다.** 그걸 알면
> 게이트가 목적함수가 되고, 그 순간 게이트는 아무것도 검증하지 못한다.
> 실패 검사의 **이름**만 보고 메커니즘을 다시 생각하라.
