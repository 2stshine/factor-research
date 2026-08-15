#!/usr/bin/env python3
"""Generate the fixed, outcome-blind 2026-08-16 diversified candidate pool.

The generator is intentionally deterministic and refuses to overwrite an
existing strategy.  It uses no returns, trial outcomes, or Gold values when
choosing definitions; those remain downstream gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "factors" / "candidates"


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    category: str
    domain: str
    sign: int
    hypothesis: str
    mechanism: str
    expected: str
    data_notes: str
    needs: tuple[str, ...]
    constants: tuple[tuple[str, object], ...]
    params: tuple[tuple[str, str], ...]
    compute: str
    rebalance_months: int = 1


def _render(candidate: Candidate) -> str:
    constants = "\n".join(
        f"{name} = {value!r}" for name, value in candidate.constants
    )
    params = ", ".join(f"{key!r}: {value}" for key, value in candidate.params)
    needs = repr(candidate.needs)
    return f'''"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


{constants}


def compute(frame):
{candidate.compute}


FACTOR = Factor(
    name={candidate.name!r},
    family={candidate.family!r},
    category={candidate.category!r},
    exploration_domain={candidate.domain!r},
    hypothesis={candidate.hypothesis!r},
    predicted_sign={candidate.sign},
    params={{{params}}},
    rebalance_months={candidate.rebalance_months},
    needs={needs},
    compute=compute,
)


RESEARCH_SPEC = {{
    "thesis": {candidate.hypothesis!r},
    "mechanism": {candidate.mechanism!r},
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": {candidate.expected!r},
    "data_notes": {candidate.data_notes!r},
}}
'''


def _history_return(name: str, lookback: int, skip: int, sign: int) -> Candidate:
    direction = "높은" if sign > 0 else "낮은"
    return Candidate(
        name=name, family=name, category="momentum",
        domain="momentum_trend_reversal", sign=sign,
        hypothesis=(
            f"분할조정 가격의 {lookback}개월 전 대비 {skip}개월 전 수익률이 {direction} "
            "종목은 정보의 지연반영 또는 장기 과잉반응 교정으로 이후 상대수익이 높다."
        ),
        mechanism=(
            "서로 다른 시작·종료 시점의 가격 경로는 최근 한 달 잡음과 장기 추세를 분리하며, "
            "사전 고정한 부호는 점진적 정보확산 또는 과잉반응 교정을 검증한다."
        ),
        expected="기존 모멘텀·반전과 관련될 수 있으나 정확한 구간이 달라 Gold 0.70 gate로 독립성을 확인한다.",
        data_notes="PIT feature로 허용된 adj_close와 정확한 달력 시차만 사용하며 total_return_close는 사용하지 않는다.",
        needs=(),
        constants=(("LOOKBACK_MONTHS", lookback), ("SKIP_MONTHS", skip)),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("skip_months", "SKIP_MONTHS")),
        compute='''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    recent = grouped["adj_close"].shift(SKIP_MONTHS)
    distant = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    recent_month = grouped["ym"].shift(SKIP_MONTHS)
    distant_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    value = recent / distant.where(distant > 0) - 1.0
    exact = ordered["ym"].eq(recent_month + SKIP_MONTHS) & ordered["ym"].eq(
        distant_month + LOOKBACK_MONTHS
    )
    return value.where(exact).reindex(frame.index)''',
    )


def _rolling_price(candidate: Candidate, mode: str) -> Candidate:
    bodies = {
        "high": '''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    anchor = grouped["adj_close"].rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).max().reset_index(level=0, drop=True)
    oldest = grouped["ym"].shift(WINDOW_MONTHS - 1)
    value = ordered["adj_close"] / anchor.where(anchor > 0)
    return value.where(ordered["ym"].eq(oldest + WINDOW_MONTHS - 1)).reindex(frame.index)''',
        "low": '''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    anchor = grouped["adj_close"].rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).min().reset_index(level=0, drop=True)
    oldest = grouped["ym"].shift(WINDOW_MONTHS - 1)
    value = ordered["adj_close"] / anchor.where(anchor > 0) - 1.0
    return value.where(ordered["ym"].eq(oldest + WINDOW_MONTHS - 1)).reindex(frame.index)''',
        "positive": '''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(1)
    prior_month = grouped["ym"].shift(1)
    monthly = (ordered["adj_close"] / prior.where(prior > 0) - 1.0).where(
        ordered["ym"].eq(prior_month + 1)
    )
    positive = monthly.gt(0).astype(float).where(monthly.notna())
    value = positive.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    return value.reindex(frame.index)''',
        "efficiency": '''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(WINDOW_MONTHS)
    prior_month = grouped["ym"].shift(WINDOW_MONTHS)
    one_month = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    absolute_monthly = one_month.where(one_month.gt(0), -one_month)
    path = absolute_monthly.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True) * WINDOW_MONTHS
    value = (ordered["adj_close"] / prior.where(prior > 0) - 1.0) / path.where(path > 0)
    return value.where(ordered["ym"].eq(prior_month + WINDOW_MONTHS)).reindex(frame.index)''',
        "persistence": '''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    monthly = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    lagged = monthly.groupby(ordered["asset_id"], sort=False).shift(1)
    products = monthly * lagged
    value = products.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    oldest = grouped["ym"].shift(WINDOW_MONTHS + 1)
    return value.where(ordered["ym"].eq(oldest + WINDOW_MONTHS + 1)).reindex(frame.index)''',
    }
    return Candidate(**{**candidate.__dict__, "compute": bodies[mode]})


def _market_relative(name: str, lookback: int, skip: int) -> Candidate:
    return Candidate(
        name=name, family=name, category="momentum", domain="momentum_trend_reversal",
        sign=1,
        hypothesis=f"시장 공통 추세를 뺀 {lookback}-{skip}개월 종목 고유 모멘텀이 높은 종목의 이후 상대수익이 높다.",
        mechanism="동일 월·동일 시장 평균을 제거해 거시 재평가가 아닌 기업고유 정보의 지연 반영을 측정한다.",
        expected="일반 가격 모멘텀과 관련되지만 시장 공통성분 제거로 완전 중복은 아닐 것으로 예상한다.",
        data_notes="adj_close, 동시점 market, 정확한 달력 시차만 사용한다.", needs=(),
        constants=(("LOOKBACK_MONTHS", lookback), ("SKIP_MONTHS", skip)),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("skip_months", "SKIP_MONTHS")),
        compute='''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    recent = grouped["adj_close"].shift(SKIP_MONTHS)
    distant = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    recent_month = grouped["ym"].shift(SKIP_MONTHS)
    distant_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    raw = recent / distant.where(distant > 0) - 1.0
    relative = raw - raw.groupby([ordered["ym"], ordered["market"]]).transform("mean")
    exact = ordered["ym"].eq(recent_month + SKIP_MONTHS) & ordered["ym"].eq(
        distant_month + LOOKBACK_MONTHS
    )
    return relative.where(exact).reindex(frame.index)''',
    )


def _rolling_liquidity(name: str, field: str, window: int, reducer: str) -> Candidate:
    if field == "amihud":
        source = 'ordered["amihud_illiquidity_1m"]'
        label = "Amihud 가격충격 비유동성"
    elif field == "adv_turnover":
        source = 'ordered["adv20"] / ordered["market_cap"].where(ordered["market_cap"] > 0)'
        label = "ADV20/시가총액 거래회전"
    else:
        source = 'ordered["trading_value"] / ordered["market_cap"].where(ordered["market_cap"] > 0)'
        label = "월말 거래대금/시가총액 활동"
    operation = "mean" if reducer == "mean" else "std"
    sign = -1 if reducer == "std" or field != "amihud" else 1
    direction = "낮은" if sign < 0 else "높은"
    body = f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    source = {source}
    value = source.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).{operation}().reset_index(level=0, drop=True)
    return value.reindex(frame.index)'''
    return Candidate(
        name=name, family=name, category="other", domain="liquidity_trading", sign=sign,
        hypothesis=f"최근 {window}개월 {label}의 {reducer}가 {direction} 종목은 유동성 보상 또는 과도한 관심 교정으로 이후 상대수익이 높다.",
        mechanism="거래 규모를 기업가치로 정규화하거나 가격충격을 직접 측정해 단순 대형주 노출과 구분한다.",
        expected="기존 유동성 수준·변화 신호와 관련될 수 있어 Gold 상관 gate로 독립성을 확인한다.",
        data_notes="인증된 월말 거래·시가총액·Amihud 입력만 사용하며 결측을 채우지 않는다.", needs=(),
        constants=(("WINDOW_MONTHS", window), ("MIN_OBSERVATIONS", max(3, window * 3 // 4))),
        params=(("window_months", "WINDOW_MONTHS"), ("min_observations", "MIN_OBSERVATIONS"),
                ("source", repr(field)), ("reducer", repr(reducer))),
        compute=body,
    )


def _liquidity_change(name: str, field: str, lookback: int) -> Candidate:
    source = (
        'ordered["trading_value"] / ordered["market_cap"].where(ordered["market_cap"] > 0)'
        if field == "trading_value_turnover" else
        'ordered["adv20"] / ordered["market_cap"].where(ordered["market_cap"] > 0)'
    )
    return Candidate(
        name=name, family=name, category="other", domain="liquidity_trading", sign=-1,
        hypothesis=f"최근 {lookback}개월 {field} 급증이 작은 종목은 과도한 관심과 투기수요를 피하여 이후 상대수익이 높다.",
        mechanism="거래활동 수준 대신 기업가치 정규화 회전의 변화를 측정해 기존 Gold 유동성 수준과 구분한다.",
        expected="거래활동 수준과 일부 관계가 예상되지만 변화율이므로 0.70 Gold gate를 요구한다.",
        data_notes="월말 거래대금·ADV20·시가총액과 정확한 달력 시차만 사용한다.", needs=(),
        constants=(("LOOKBACK_MONTHS", lookback),),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("source", repr(field))),
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = {source}
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)''',
    )


def _rolling_risk(name: str, mode: str, window: int) -> Candidate:
    min_obs = max(4, window * 3 // 4)
    base = '''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(1)
    prior_month = grouped["ym"].shift(1)
    monthly = (ordered["adj_close"] / prior.where(prior > 0) - 1.0).where(
        ordered["ym"].eq(prior_month + 1)
    )
'''
    operations = {
        "downside": '''    source = (-monthly).where((-monthly).gt(0))
    value = source.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)''',
        "upside": '''    source = monthly.where(monthly.gt(0))
    value = source.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)''',
        "skew": '''    value = monthly.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).skew().reset_index(level=0, drop=True)''',
        "kurt": '''    value = monthly.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).kurt().reset_index(level=0, drop=True)''',
        "max": '''    value = monthly.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).max().reset_index(level=0, drop=True)''',
        "semivol_ratio": '''    losses = (-monthly).where((-monthly).gt(0)).pow(2)
    gains = monthly.where(monthly.gt(0)).pow(2)
    downside = losses.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    upside = gains.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    value = np.sqrt(downside) / np.sqrt(upside.where(upside > 0))''',
    }
    signs = {"downside": -1, "upside": -1, "skew": -1, "kurt": -1,
             "max": -1, "semivol_ratio": -1}
    return Candidate(
        name=name, family=name, category="quality", domain="low_risk",
        sign=signs[mode],
        hypothesis=f"최근 {window}개월 월수익의 {mode} 위험이 낮은 종목은 복권형 수요와 레버리지 제약으로 이후 상대수익이 높다.",
        mechanism="수익률 분포의 특정 꼬리·비대칭을 분리해 총변동성과 다른 방어적 위험 프리미엄을 측정한다.",
        expected="기존 idiosyncratic_volatility_24m·price_range_12m과 일부 관계가 예상되며 0.70 gate를 요구한다.",
        data_notes="PIT adj_close의 연속 월 가격수익률과 고정 달력창만 사용한다.", needs=(),
        constants=(("WINDOW_MONTHS", window), ("MIN_OBSERVATIONS", min_obs)),
        params=(("window_months", "WINDOW_MONTHS"), ("min_observations", "MIN_OBSERVATIONS"),
                ("risk_measure", repr(mode))),
        compute=base + operations[mode] + '\n    return value.reindex(frame.index)',
    )


def _rolling_feature_risk(name: str, field: str, window: int, reducer: str) -> Candidate:
    min_obs = max(3, window * 3 // 4)
    return Candidate(
        name=name, family=name, category="quality", domain="low_risk", sign=-1,
        hypothesis=(
            f"최근 {window}개월 {field}의 {reducer}가 낮은 종목은 복권형 수요와 "
            "위험추종 수요의 과대가격을 피하여 이후 상대수익이 높다."
        ),
        mechanism=(
            "인증된 일별 수익 분포의 월별 요약을 고정 창에서 다시 집계해 가격 추세가 아닌 "
            "실현 위험의 수준 또는 불안정성을 측정한다."
        ),
        expected="기존 고유변동성·가격범위와 일부 관계가 예상되며 Gold 0.70 gate로 독립성을 확인한다.",
        data_notes="Silver가 월말에 고정한 일별 위험 요약과 36개월 이하 달력창만 사용한다.",
        needs=(),
        constants=(("WINDOW_MONTHS", window), ("MIN_OBSERVATIONS", min_obs)),
        params=(("window_months", "WINDOW_MONTHS"), ("min_observations", "MIN_OBSERVATIONS"),
                ("source_field", repr(field)), ("reducer", repr(reducer))),
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    source = ordered[{field!r}]
    value = source.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).{reducer}().reset_index(level=0, drop=True)
    return value.reindex(frame.index)''',
    )


def _feature_change_risk(name: str, field: str, lookback: int) -> Candidate:
    return Candidate(
        name=name, family=name, category="quality", domain="low_risk", sign=-1,
        hypothesis=f"최근 {lookback}개월 {field} 악화가 작은 종목은 위험수요의 과대가격을 피하여 이후 상대수익이 높다.",
        mechanism="위험 수준이 아니라 사전 고정 기간의 변화를 측정해 기존 Gold 저위험 수준 신호와 구분한다.",
        expected="저위험 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.",
        data_notes="Silver 월말 위험 요약과 정확한 달력 시차만 사용한다.", needs=(),
        constants=(("LOOKBACK_MONTHS", lookback),),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("source_field", repr(field))),
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered[{field!r}]
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)''',
    )


def _market_risk(name: str, mode: str, window: int) -> Candidate:
    min_obs = max(6, window * 2 // 3)
    metric = (
        '''covariance / market_variance.where(market_variance > 0)'''
        if mode == "beta" else
        '''covariance / np.sqrt(
            asset_variance.where(asset_variance > 0) * market_variance.where(market_variance > 0)
        )'''
    )
    body = f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort").copy()
    asset = ordered["asset_id"]
    prior_close = ordered["adj_close"].groupby(asset).shift(1)
    prior_month = ordered["ym"].groupby(asset).shift(1)
    prior_market = ordered["market"].groupby(asset).shift(1)
    prior_cap = ordered["market_cap"].groupby(asset).shift(1)
    asset_return = (ordered["adj_close"] / prior_close.where(prior_close > 0) - 1.0).where(
        ordered["ym"].eq(prior_month + 1)
    )
    weight = prior_cap.where(prior_cap > 0)
    valid = asset_return.notna() & weight.notna() & prior_market.notna()
    groups = [ordered["ym"], prior_market]
    weighted = (asset_return * weight).where(valid).groupby(groups).transform("sum")
    total = weight.where(valid).groupby(groups).transform("sum")
    market_return = weighted / total.where(total > 0)
    paired_asset = asset_return.where(market_return.notna())
    paired_market = market_return.where(asset_return.notna())
    product = paired_asset * paired_market
    asset_square = paired_asset.pow(2)
    market_square = paired_market.pow(2)
    rolling_asset = paired_asset.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_market = paired_market.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_product = product.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_asset_square = asset_square.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_market_square = market_square.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    covariance = rolling_product - rolling_asset * rolling_market
    asset_variance = rolling_asset_square - rolling_asset.pow(2)
    market_variance = rolling_market_square - rolling_market.pow(2)
    value = {metric}
    oldest_month = ordered["ym"].groupby(asset).shift(WINDOW_MONTHS)
    exact = ordered["ym"].eq(oldest_month + WINDOW_MONTHS)
    return value.where(exact).reindex(frame.index)'''
    return Candidate(
        name=name, family=name, category="quality", domain="low_risk", sign=-1,
        hypothesis=f"최근 {window}개월 {mode}가 낮은 종목은 고위험 선호에 따른 과대가격을 피하여 이후 상대수익이 높다.",
        mechanism="전월 시가총액 가중 시장수익과의 공분산 구조를 사용해 총변동성과 다른 시장위험을 측정한다.",
        expected="기존 24개월 고유변동성과 관련되지만 시장 공통성분의 민감도 또는 상관을 직접 측정한다.",
        data_notes="adj_close, 전월 market·market_cap으로 내부 PIT 시장 벤치마크를 구성하고 결측을 채우지 않는다.",
        needs=(), constants=(("WINDOW_MONTHS", window), ("MIN_OBSERVATIONS", min_obs)),
        params=(("window_months", "WINDOW_MONTHS"), ("min_observations", "MIN_OBSERVATIONS"),
                ("risk_measure", repr(mode)), ("benchmark", repr("lagged_market_cap_weighted"))),
        compute=body,
    )


def _growth(name: str, field: str, lookback: int, *, operating: bool = False) -> Candidate:
    if operating:
        source = 'ordered["total_assets"] - ordered["current_liabilities"]'
        needs = ("total_assets", "current_liabilities")
        label = "영업자산"
    else:
        source = f'ordered[{field!r}]'
        needs = (field,)
        label = field
    return Candidate(
        name=name, family=name, category="quality", domain="investment_capital_allocation", sign=-1,
        hypothesis=f"최근 {lookback}개월 {label} 증가율이 낮은 기업은 과잉투자·자산팽창 위험이 작아 이후 상대수익이 높다.",
        mechanism="PIT 재무규모의 시간 변화를 이용해 경영자의 자본배분과 투자 확대를 측정한다.",
        expected="기존 12개월 자산성장과 관련되지만 기간 또는 영업자산 범위가 다르다.",
        data_notes="DART available_date PIT 값의 정확한 달력 시차와 양의 전기 분모만 사용한다.",
        needs=needs, constants=(("LOOKBACK_MONTHS", lookback),),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("source_field", repr(field))),
        rebalance_months=3,
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = {source}
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)''',
    )


def _financing(name: str, mode: str, lookback: int) -> Candidate:
    if mode == "capital_stock":
        source = 'ordered["capital_stock"]'
        body = '''    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0'''
        needs = ("capital_stock",)
    elif mode == "market_leverage":
        source = 'ordered["total_liabilities"] / (ordered["market_cap"] + ordered["total_liabilities"]).where((ordered["market_cap"] + ordered["total_liabilities"]) > 0)'
        body = '''    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    value = source - prior'''
        needs = ("total_liabilities",)
    elif mode == "price_adjusted_issuance":
        source = 'ordered["market_cap"] / ordered["adj_close"].where(ordered["adj_close"] > 0)'
        body = '''    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0'''
        needs = ()
    else:
        source = 'ordered["total_equity"]'
        body = '''    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0'''
        needs = ("total_equity",)
    return Candidate(
        name=name, family=name, category="other", domain="financing_issuance", sign=-1,
        hypothesis=f"최근 {lookback}개월 {mode} 확대가 큰 기업은 외부자금 수요나 고평가 활용 가능성이 높아 이후 상대수익이 낮다.",
        mechanism="발행·부채조달·자본금 변화 중 하나를 PIT 시점에서 분리하여 경영자의 자금조달 결정을 측정한다.",
        expected="자산성장과 일부 관계가 예상되지만 조달 측면만 측정한다.",
        data_notes="정확한 달력 시차와 양의 분모만 사용하며 기업행사 후행 라벨은 사용하지 않는다.",
        needs=needs, constants=(("LOOKBACK_MONTHS", lookback),),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("financing_measure", repr(mode))),
        rebalance_months=3,
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = {source}
{body}
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)''',
    )


def _value_change(name: str, numerator: str, lookback: int, *, ev: bool = False) -> Candidate:
    needs = tuple(sorted({numerator, "total_liabilities"} if ev else {numerator}))
    denominator = (
        '(ordered["market_cap"] + ordered["total_liabilities"]).where((ordered["market_cap"] + ordered["total_liabilities"]) > 0)'
        if ev else 'ordered["market_cap"].where(ordered["market_cap"] > 0)'
    )
    return Candidate(
        name=name, family=name, category="value", domain="value", sign=1,
        hypothesis=f"{numerator} 대비 시장가치의 {lookback}개월 개선이 큰 기업은 펀더멘털 대비 가격이 덜 반영되어 이후 상대수익이 높다.",
        mechanism="가치비율의 현재 수준 대신 사전 고정 기간의 개선을 측정해 기존 Gold 가치 수준 신호와 구분한다.",
        expected="가치 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.",
        data_notes="PIT 재무 분자와 동시점 양의 market_cap 또는 enterprise value, 정확한 달력 시차만 사용한다.",
        needs=needs, constants=(("LOOKBACK_MONTHS", lookback),),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("numerator", repr(numerator)),
                ("denominator", repr("enterprise_value" if ev else "market_cap"))),
        rebalance_months=3,
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    ratio = ordered[{numerator!r}] / {denominator}
    prior = ratio.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = ratio - prior
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)''',
    )


def _quality_level(name: str, numerator: str, denominator: str, sign: int = 1) -> Candidate:
    needs = tuple(sorted({numerator, denominator}))
    return Candidate(
        name=name, family=name, category="earnings", domain="profitability_quality", sign=sign,
        hypothesis=f"PIT {numerator}/{denominator} 비율이 {'높은' if sign > 0 else '낮은'} 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.",
        mechanism="서로 다른 포괄·영업·세전 이익 단계의 변환 또는 자본 효율성을 하나의 경제 비율로 측정한다.",
        expected="기존 수익성 신호와 관련될 수 있으나 분자·분모 단계가 다르다.",
        data_notes="동일 available_date PIT 재무값과 0이 아닌 분모만 사용한다.",
        needs=needs, constants=(),
        params=(("numerator", repr(numerator)), ("denominator", repr(denominator))),
        rebalance_months=3,
        compute=f'''    denominator = frame[{denominator!r}]
    return frame[{numerator!r}] / denominator.where(denominator != 0)''',
    )


def _quality_ratio_change(
    name: str, numerator: str, denominator: str, lookback: int,
) -> Candidate:
    return Candidate(
        name=name, family=name, category="earnings", domain="profitability_quality", sign=1,
        hypothesis=f"최근 {lookback}개월 {numerator}/{denominator} 개선이 큰 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.",
        mechanism="수익성 수준이 아니라 동일 PIT 비율의 개선을 측정해 기존 Gold 수준 신호와 구분한다.",
        expected="관련 수익성 수준 신호와 일부 관계가 예상되지만 변화율은 별도 메커니즘이다.",
        data_notes="DART available_date PIT 값과 정확한 달력 시차, 0이 아닌 분모만 사용한다.",
        needs=tuple(sorted({numerator, denominator})),
        constants=(("LOOKBACK_MONTHS", lookback),),
        params=(("lookback_months", "LOOKBACK_MONTHS"), ("numerator", repr(numerator)),
                ("denominator", repr(denominator))), rebalance_months=3,
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    ratio = ordered[{numerator!r}] / ordered[{denominator!r}].where(ordered[{denominator!r}] != 0)
    prior = ratio.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = ratio - prior
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)''',
    )


def _quality_ratio_volatility(
    name: str, numerator: str, denominator: str, window: int,
) -> Candidate:
    return Candidate(
        name=name, family=name, category="earnings", domain="profitability_quality", sign=-1,
        hypothesis=f"최근 {window}개월 {numerator}/{denominator} 변동성이 낮은 기업은 이익의 질이 높아 이후 상대수익이 높다.",
        mechanism="PIT 누적이익 비율의 안정성을 측정해 단일 시점 수익성 수준과 구분한다.",
        expected="수익성·자본축적 수준과 관련될 수 있으나 시계열 안정성은 별도 메커니즘이다.",
        data_notes="DART available_date PIT 비율의 고정 달력창만 사용한다.",
        needs=tuple(sorted({numerator, denominator})),
        constants=(("WINDOW_MONTHS", window), ("MIN_OBSERVATIONS", max(3, window * 3 // 4))),
        params=(("window_months", "WINDOW_MONTHS"), ("min_observations", "MIN_OBSERVATIONS"),
                ("numerator", repr(numerator)), ("denominator", repr(denominator))),
        rebalance_months=3,
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    ratio = ordered[{numerator!r}] / ordered[{denominator!r}].where(ordered[{denominator!r}] != 0)
    value = ratio.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)
    return value.reindex(frame.index)''',
    )


def _quality_rolling(name: str, mode: str, window: int) -> Candidate:
    if mode == "working_capital_accrual":
        source = 'ordered["current_assets"] - ordered["current_liabilities"]'
        needs = ("current_assets", "current_liabilities", "total_assets")
        body = '''    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_assets = ordered["total_assets"].groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (source - prior) / prior_assets.where(prior_assets > 0)
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)'''
        sign = -1
    elif mode in {"operating_margin_volatility", "net_margin_volatility"}:
        income = "operating_income_ttm" if mode.startswith("operating") else "net_income_ttm"
        source = f'ordered[{income!r}] / ordered["revenue_ttm"].where(ordered["revenue_ttm"] != 0)'
        needs = (income, "revenue_ttm")
        body = '''    value = source.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)
    return value.reindex(frame.index)'''
        sign = -1
    else:
        source = 'ordered["sue_score"]'
        needs = ("sue_score",)
        body = '''    value = source.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    return value.reindex(frame.index)'''
        sign = 1
    constants = (("LOOKBACK_MONTHS", window),) if mode == "working_capital_accrual" else (
        ("WINDOW_MONTHS", window), ("MIN_OBSERVATIONS", max(3, window * 3 // 4))
    )
    params = (("lookback_months", "LOOKBACK_MONTHS"), ("quality_measure", repr(mode))) if mode == "working_capital_accrual" else (
        ("window_months", "WINDOW_MONTHS"), ("min_observations", "MIN_OBSERVATIONS"),
        ("quality_measure", repr(mode)),
    )
    return Candidate(
        name=name, family=name, category="earnings", domain="profitability_quality", sign=sign,
        hypothesis=f"{mode} 신호가 {'높은' if sign > 0 else '낮은'} 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.",
        mechanism="PIT 이익·운전자본의 수준 변화 또는 변동성을 이용해 단순 수익성 수준과 다른 이익의 질을 측정한다.",
        expected="기존 수익성 또는 자산성장과 일부 관계가 예상되지만 측정 대상이 발생액·안정성이다.",
        data_notes="DART available_date PIT 재무값과 고정 36개월 이하 달력창만 사용한다.",
        needs=needs, constants=constants, params=params, rebalance_months=3,
        compute=f'''    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = {source}
{body}''',
    )


def candidates() -> list[Candidate]:
    momentum_primary = [
        _history_return("price_momentum_9_2", 9, 2, 1),
        _history_return("price_momentum_15_3", 15, 3, 1),
        _history_return("price_momentum_18_6", 18, 6, 1),
        _history_return("price_momentum_24_6", 24, 6, 1),
        _history_return("price_reversal_3_1", 3, 1, -1),
        _history_return("price_reversal_6_3", 6, 3, -1),
        _history_return("price_reversal_24_12", 24, 12, -1),
        _history_return("price_reversal_36_24", 36, 24, -1),
        _history_return("price_momentum_6_1", 6, 1, 1),
        _history_return("price_momentum_12_3", 12, 3, 1),
    ]
    momentum_secondary = [
        _rolling_price(Candidate("high_24m_proximity", "high_24m_proximity", "momentum", "momentum_trend_reversal", 1, "24개월 고점에 가까운 종목의 추세가 이후에도 지속된다.", "장기 고점 근접도는 지속적 수요와 정보 확산을 포착한다.", "12개월 고점 신호와 기간이 다르다.", "adj_close 24개월 창만 사용한다.", (), (("WINDOW_MONTHS", 24),), (("window_months", "WINDOW_MONTHS"),), ""), "high"),
        _rolling_price(Candidate("price_recovery_24m", "price_recovery_24m", "momentum", "momentum_trend_reversal", 1, "24개월 저점에서 크게 회복한 종목의 개선이 이후에도 이어진다.", "장기 악재 해소의 지연반영을 측정한다.", "12개월 회복과 기간이 다르다.", "adj_close 24개월 창만 사용한다.", (), (("WINDOW_MONTHS", 24),), (("window_months", "WINDOW_MONTHS"),), ""), "low"),
        _rolling_price(Candidate("positive_return_share_24m", "positive_return_share_24m", "momentum", "momentum_trend_reversal", 1, "24개월 상승월 비중이 높은 종목은 넓은 추세 참여로 이후 상대수익이 높다.", "소수 급등월이 아닌 추세의 폭을 측정한다.", "12개월 상승월 비중과 기간이 다르다.", "연속 월 adj_close 수익률만 사용한다.", (), (("WINDOW_MONTHS", 24),), (("window_months", "WINDOW_MONTHS"),), ""), "positive"),
        _rolling_price(Candidate("price_trend_efficiency_6m", "price_trend_efficiency_6m", "momentum", "momentum_trend_reversal", 1, "6개월 가격경로 대비 방향효율이 높은 추세는 이후에도 지속된다.", "왕복 잡음이 적은 단기 추세를 분리한다.", "12개월 효율성과 기간이 다르다.", "adj_close의 연속 6개월 경로만 사용한다.", (), (("WINDOW_MONTHS", 6),), (("window_months", "WINDOW_MONTHS"),), ""), "efficiency"),
        _rolling_price(Candidate("price_trend_efficiency_24m", "price_trend_efficiency_24m", "momentum", "momentum_trend_reversal", 1, "24개월 가격경로 대비 방향효율이 높은 추세는 이후에도 지속된다.", "왕복 잡음이 적은 장기 추세를 분리한다.", "12개월 효율성과 기간이 다르다.", "adj_close의 연속 24개월 경로만 사용한다.", (), (("WINDOW_MONTHS", 24),), (("window_months", "WINDOW_MONTHS"),), ""), "efficiency"),
        _market_relative("market_relative_momentum_6_1", 6, 1),
        _market_relative("market_relative_momentum_18_3", 18, 3),
        _rolling_price(Candidate("return_persistence_24m", "return_persistence_24m", "momentum", "momentum_trend_reversal", 1, "24개월 인접 월수익 연속성이 높은 종목의 정보 반영이 이후에도 이어진다.", "월수익 자기공분산으로 추세 지속성을 측정한다.", "12개월 지속성과 기간이 다르다.", "adj_close의 25개월 경로만 사용한다.", (), (("WINDOW_MONTHS", 24),), (("window_months", "WINDOW_MONTHS"),), ""), "persistence"),
        _market_relative("market_relative_momentum_24_6", 24, 6),
        _rolling_price(Candidate("positive_return_share_18m", "positive_return_share_18m", "momentum", "momentum_trend_reversal", 1, "18개월 상승월 비중이 높은 종목의 폭넓은 추세가 이후에도 지속된다.", "누적수익보다 상승 참여 폭을 측정한다.", "12·24개월 비중과 기간이 다르다.", "연속 월 adj_close만 사용한다.", (), (("WINDOW_MONTHS", 18),), (("window_months", "WINDOW_MONTHS"),), ""), "positive"),
    ]
    liquidity_primary = [
        _rolling_liquidity(f"amihud_mean_{window}m", "amihud", window, "mean")
        for window in (6, 18, 24, 36)
    ] + [
        _rolling_liquidity(f"adv_turnover_mean_{window}m", "adv_turnover", window, "mean")
        for window in (18, 24, 36)
    ] + [
        _liquidity_change(f"trading_value_turnover_change_{window}m", "trading_value_turnover", window)
        for window in (3, 6, 12)
    ]
    liquidity_secondary = [
        _rolling_liquidity(f"amihud_volatility_{window}m", "amihud", window, "std")
        for window in (6, 18, 24, 36)
    ] + [
        _rolling_liquidity(f"adv_turnover_volatility_{window}m", "adv_turnover", window, "std")
        for window in (6, 18, 24, 36)
    ] + [
        _rolling_liquidity(f"trading_value_turnover_volatility_{window}m", "trading_value_turnover", window, "std")
        for window in (6, 24)
    ]
    risk_primary = [
        _feature_change_risk("realized_daily_volatility_change_6m", "daily_volatility_252d", 6),
        _feature_change_risk("max_daily_return_change_6m", "max_daily_return_1m", 6),
        _feature_change_risk("realized_daily_volatility_change_24m", "daily_volatility_252d", 24),
        _rolling_feature_risk("realized_daily_volatility_instability_6m", "daily_volatility_252d", 6, "std"),
        _rolling_feature_risk("realized_daily_volatility_instability_18m", "daily_volatility_252d", 18, "std"),
        _rolling_feature_risk("realized_daily_volatility_instability_36m", "daily_volatility_252d", 36, "std"),
        _rolling_feature_risk("max_daily_return_mean_6m", "max_daily_return_1m", 6, "mean"),
        _feature_change_risk("max_daily_return_change_18m", "max_daily_return_1m", 18),
        _rolling_feature_risk("max_daily_return_instability_6m", "max_daily_return_1m", 6, "std"),
        _rolling_feature_risk("max_daily_return_instability_18m", "max_daily_return_1m", 18, "std"),
    ]
    risk_secondary = [
        _market_risk("market_beta_6m", "beta", 6),
        _market_risk("market_beta_9m", "beta", 9),
        _market_risk("market_beta_12m", "beta", 12),
        _market_risk("market_beta_18m", "beta", 18),
        _market_risk("market_beta_24m", "beta", 24),
        _market_risk("market_return_correlation_6m", "correlation", 6),
        _market_risk("market_return_correlation_9m", "correlation", 9),
        _market_risk("market_return_correlation_12m", "correlation", 12),
        _market_risk("market_return_correlation_18m", "correlation", 18),
        _market_risk("market_return_correlation_24m", "correlation", 24),
    ]
    investment = [
        *[_growth(f"total_asset_growth_{window}m", "total_assets", window) for window in (6, 18, 24, 30)],
        *[_growth(f"noncurrent_asset_growth_{window}m", "noncurrent_assets", window) for window in (6, 18, 24, 30)],
        _growth("operating_asset_growth_12m", "operating_assets", 12, operating=True),
        _growth("operating_asset_growth_24m", "operating_assets", 24, operating=True),
    ]
    financing = [
        *[_financing(f"capital_stock_growth_{window}m", "capital_stock", window) for window in (6, 18, 24)],
        _financing("equity_growth_24m", "book_equity", 24),
        *[_financing(f"market_leverage_change_{window}m", "market_leverage", window) for window in (6, 18, 24, 30)],
        _financing("net_equity_issuance_price_adjusted_24m", "price_adjusted_issuance", 24),
        _financing("net_equity_issuance_price_adjusted_36m", "price_adjusted_issuance", 36),
    ]
    value = [
        _value_change("book_to_market_change_6m", "total_equity", 6),
        _value_change("earnings_yield_change_12m", "net_income_ttm", 12),
        _value_change("pretax_yield_change_6m", "pretax_income_ttm", 6),
        _value_change("asset_to_market_change_6m", "total_assets", 6),
        _value_change("operating_yield_change_12m", "operating_income_ttm", 12),
        _value_change("enterprise_sales_yield_change_12m", "revenue_ttm", 12, ev=True),
        _value_change("enterprise_earnings_yield_change_12m", "net_income_ttm", 12, ev=True),
        _value_change("retained_earnings_yield_change_12m", "retained_earnings", 12),
        _value_change("capital_stock_yield_change_12m", "capital_stock", 12),
        _value_change("pretax_yield_change_12m", "pretax_income_ttm", 12),
    ]
    quality = [
        _quality_ratio_change("operating_margin_change_6m", "operating_income_ttm", "revenue_ttm", 6),
        _quality_ratio_change("net_margin_change_6m", "net_income_ttm", "revenue_ttm", 6),
        _quality_ratio_change("retained_earnings_to_assets_change_6m", "retained_earnings", "total_assets", 6),
        _quality_level("net_to_operating_income_conversion", "net_income_ttm", "operating_income_ttm"),
        _quality_level("pretax_to_operating_income_conversion", "pretax_income_ttm", "operating_income_ttm"),
        _quality_rolling("working_capital_accruals_6m", "working_capital_accrual", 6),
        _quality_rolling("working_capital_accruals_24m", "working_capital_accrual", 24),
        _quality_rolling("operating_margin_volatility_12m", "operating_margin_volatility", 12),
        _quality_rolling("net_margin_volatility_12m", "net_margin_volatility", 12),
        _quality_ratio_volatility("retained_earnings_to_assets_volatility_12m", "retained_earnings", "total_assets", 12),
    ]
    groups = [momentum_primary, momentum_secondary, liquidity_primary, liquidity_secondary,
              risk_primary, risk_secondary, investment, financing, value, quality]
    if any(len(group) != 10 for group in groups):
        raise RuntimeError("각 메커니즘 축은 정확히 10개 후보여야 합니다")
    output: list[Candidate] = []
    for batch in range(10):
        output.extend(group[batch] for group in groups)
    if len({candidate.name for candidate in output}) != 100:
        raise RuntimeError("후보 이름은 정확히 100개로 고유해야 합니다")
    return output


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    created = []
    for candidate in candidates():
        path = DESTINATION / f"{candidate.name}.py"
        content = _render(candidate)
        if path.exists():
            if path.read_text(encoding="utf-8") != content:
                raise RuntimeError(f"기존 후보를 덮어쓸 수 없습니다: {path}")
            continue
        path.write_text(content, encoding="utf-8")
        created.append(path)
    print(f"diversified candidate program: total=100 created={len(created)}")


if __name__ == "__main__":
    main()
