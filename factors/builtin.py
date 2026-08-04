"""검증된 팩터 정의.

아래 수치는 2026-07-31의 구형 Bronze/v1 게이트 기록이며 현재 승격 근거로 사용하지 않는다:
  qual_roe   순알파 4.73%/yr  net_IR 0.75  회전율 181%  ← 유일 통과
  qual_opm   4.68%  0.70  159%   IR 미달
  value_ep   4.51%  0.67  276%   IR 미달
  value_bp   2.73%  0.35  322%
  sue        2.18%  0.48  576%   회전율
  rev_1m    −7.64% −1.08  977%   ← IC t=4.05 인데 롱온리는 마이너스
  mom_12_1  −2.64% −0.28  319%   ← 한국은 모멘텀 부호가 반대
직교성: roe↔opm ρ=0.96, ep↔roe ρ=0.91 → 셋은 사실상 같은 팩터.
sue 만 독립적(|ρ|≤0.36).
"""
from __future__ import annotations

import numpy as np

from engine.factors import REGISTRY, Factor

def _add(**kw):
    REGISTRY.add(Factor(**kw))


# ------------------------------------------------------------------ value
_add(
    name="value_bp", category="value", predicted_sign=1,
    hypothesis="장부가 대비 저평가된 주식은 위험보상 또는 과잉반응 교정으로 초과수익을 낸다 "
               "(Fama-French 1992). 한국은 지주·금융 비중이 커 섹터 편향 주의.",
    needs=("total_equity",),
    compute=lambda d: d["total_equity"] / d["market_cap"],
)
_add(
    name="value_ep", category="value", predicted_sign=1,
    hypothesis="이익 대비 저평가. B/P 와 달리 수익성이 반영돼 가치함정을 덜 만든다. "
               "실측상 quality 군과 ρ=0.91 로 사실상 수익성 팩터에 가깝다.",
    needs=("net_income_ttm",),
    compute=lambda d: d["net_income_ttm"] / d["market_cap"],
)
_add(
    name="value_sp", category="value", predicted_sign=1,
    hypothesis="매출 대비 저평가. 적자 기업에서도 정의되어 E/P 의 결측을 보완한다.",
    needs=("revenue_ttm",),
    compute=lambda d: d["revenue_ttm"] / d["market_cap"],
)

# ---------------------------------------------------------------- quality
_add(
    name="qual_roe", category="quality", predicted_sign=1,
    hypothesis="자기자본이익률이 높은 기업은 이익 지속성이 높고 시장이 그 지속성을 과소평가한다 "
               "(Novy-Marx 2013 의 수익성 팩터 계열). ⚠️ 섹터 중립화 미검정 — "
               "고ROE 가 특정 업종에 쏠려 있으면 섹터 베팅일 수 있다.",
    needs=("net_income_ttm", "total_equity"),
    compute=lambda d: d["net_income_ttm"] / d["total_equity"].where(d["total_equity"] > 0),
)
_add(
    name="qual_opm", category="quality", predicted_sign=1,
    hypothesis="영업이익률이 높으면 가격결정력·비용구조 우위가 있고 이익의 질이 높다. "
               "ROE 와 ρ=0.96 이라 T5.1 직교성에서 둘 중 하나만 남는다.",
    needs=("operating_income_ttm", "revenue_ttm"),
    compute=lambda d: d["operating_income_ttm"] / d["revenue_ttm"].where(d["revenue_ttm"] > 0),
)
_add(
    name="qual_lev", category="quality", predicted_sign=-1,
    hypothesis="부채비율이 낮으면 재무위험이 낮아 부실 시 손실을 피한다. "
               "실측 t=0.48 로 한국에서는 무의미했다 — 기록용으로 유지.",
    needs=("total_liabilities", "total_equity"),
    compute=lambda d: d["total_liabilities"] / d["total_equity"].where(d["total_equity"] > 0),
)

# --------------------------------------------------------------- momentum
_add(
    name="mom_12_1", category="momentum", predicted_sign=1, params={"lookback": 12, "skip": 1},
    hypothesis="과거 승자가 계속 이긴다(Jegadeesh-Titman 1993). "
               "⚠️ 한국 실측은 t=−1.34 로 **부호가 반대** — 미국식 템플릿이 그대로 안 통한다.",
    compute=lambda d: (d.groupby("asset_id")["return_close"].shift(1)
                       / d.groupby("asset_id")["return_close"].shift(12) - 1),
)
_add(
    name="rev_1m", category="momentum", predicted_sign=-1,
    hypothesis="1개월 단기 반전 — 유동성 공급 보상(Lehmann 1990). "
               "⚠️ IC t=4.05 로 강하지만 롱온리 순알파 −7.64%. IC 는 숏레그·마이크로캡이 만든 것.",
    compute=lambda d: d["return_close"] / d.groupby("asset_id")["return_close"].shift(1) - 1,
)

# ------------------------------------------------------------------- size
_add(
    name="size", category="size", predicted_sign=-1,
    hypothesis="소형주 프리미엄. ⚠️ 실측상 전체 유니버스 t=0.75 인데 투자가능 유니버스에서 "
               "부호가 뒤집힌다(t=−4.39) — 유동성 없는 종목이 만든 착시.",
    compute=lambda d: np.log(d["market_cap"].where(d["market_cap"] > 0)),
)

# --------------------------------------------------------------- earnings
_add(
    name="sue", category="earnings", predicted_sign=1, params={"std_window": 8},
    rebalance_months=3,
    hypothesis="계절 랜덤워크 기대 대비 실적 서프라이즈가 이후 수익률로 이어진다(PEAD; "
               "Bernard-Thomas 1989). 컨센서스 없이 시계열만으로 구성 가능하고 "
               "애널리스트 미커버 소형주까지 잡는다. 실측상 모든 팩터와 |ρ|≤0.36 으로 가장 독립적.",
    needs=("sue_score",),
    compute=lambda d: d["sue_score"],
)

# ------------------------------------------------- 총자산회전율 (2026-08 추가)
_add(
    name="asset_turnover", category="quality", predicted_sign=1, rebalance_months=3,
    hypothesis="총자산 대비 매출이 높으면 자산을 효율적으로 굴리는 기업이고, "
               "시장은 이 효율성의 지속성을 과소평가한다. 순이익 기반 지표보다 "
               "회계 조작에 덜 노출된다(Novy-Marx 2013 계열).",
    needs=("revenue_ttm", "total_assets"),
    compute=lambda d: d["revenue_ttm"] / d["total_assets"].where(d["total_assets"] > 0),
)
