"""Additional price/activity measurements for the new reference generation.

``EXTENDED_PRICE_SQL`` accepts ``(start, end, asset_ids)`` and returns the same
monthly source envelope as reference_gold.PRICE_SQL plus ``FEATURE_CONTRACTS``
and ``COUNT_COLUMNS``. It reads certified common-stock PRICE data only, never
Gold, forward labels, or total-return prices. It is intended for bounded asset
batches inside ONE repeatable-read transaction, not independently resumable
live queries. Source normalization, provenance attestation and publication are
the caller's responsibility. In particular DQ certification does not establish
first-release vintage, and observation-row windows are not exchange calendars.

``calculate(frame, reference_id)`` consumes a validated, attested monthly panel
and returns raw measurements, never ranks, returns, alpha approvals or claims
of profitability. ``REFERENCE_SPECS`` exposes required columns, orientation and
formula for a separately frozen literature catalog. It is not itself a catalog
or certification. Its 13 measurements include diagnostic/estimator controls,
not 13 economically independent, proven return anomalies.

``aggregate_daily_for_validation(daily)`` is an independent, bounded pandas
oracle for adapter tests/parity samples. It requires explicit historic identity
and aware daily known-at clocks; it does not fetch/authorize a source. Production
aggregation stays in PostgreSQL to avoid transferring the full daily history.
"""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd


FEATURE_CONTRACTS = {
    "share_turnover_1m": "MONTH_MEAN_DAILY_VOLUME_DIV_SAME_DAY_POSITIVE_SHARES",
    "share_turnover_cv_1m": "MONTH_SAMPLE_STD_DAILY_TURNOVER_DIV_MEAN",
    "mean_traded_value_1m": "MONTH_MEAN_NONNEGATIVE_KRW_TRADING_VALUE",
    "traded_value_cv_1m": "MONTH_SAMPLE_STD_KRW_TRADING_VALUE_DIV_MEAN",
    "zero_volume_fraction_1m": "MONTH_ZERO_VOLUME_FRACTION_OF_NONNEGATIVE_VOLUME_ROWS",
    "downside_semideviation_252d": "SQRT_MEAN_MIN_PRICE_RETURN_ZERO_SQUARED_LAST_252_ROWS",
    "return_skew_252d": "POPULATION_STANDARDIZED_THIRD_CENTRAL_PRICE_RETURN_MOMENT_LAST_252_ROWS_VARIANCE_GT_1E_MINUS_16",
    "parkinson_variance_1m": "MONTH_MEAN_LOG_HIGH_LOW_SQUARED_DIV_FOUR_LOG_TWO",
    "overnight_return_1m": "MONTH_PRODUCT_OPEN_DIV_CLOSE_TIMES_ADJ_CLOSE_DIV_PRIOR_ADJ_CLOSE_MINUS_ONE",
    "intraday_return_1m": "MONTH_PRODUCT_CLOSE_DIV_OPEN_MINUS_ONE",
    "positive_return_days_1m": "MONTH_COUNT_STRICTLY_POSITIVE_ADJUSTED_PRICE_RETURNS",
    "negative_return_days_1m": "MONTH_COUNT_STRICTLY_NEGATIVE_ADJUSTED_PRICE_RETURNS",
    "nominal_close": "SAME_DAY_UNADJUSTED_CLOSE_KRW",
}
FEATURE_UNITS = {
    "share_turnover_1m": "SHARES_PER_SHARE",
    "share_turnover_cv_1m": "DIMENSIONLESS",
    "mean_traded_value_1m": "KRW",
    "traded_value_cv_1m": "DIMENSIONLESS",
    "zero_volume_fraction_1m": "FRACTION",
    "downside_semideviation_252d": "DECIMAL_RETURN",
    "return_skew_252d": "DIMENSIONLESS",
    "parkinson_variance_1m": "SQUARED_LOG_RETURN",
    "overnight_return_1m": "DECIMAL_RETURN",
    "intraday_return_1m": "DECIMAL_RETURN",
    "positive_return_days_1m": "OBSERVATIONS",
    "negative_return_days_1m": "OBSERVATIONS",
    "nominal_close": "KRW",
}
COUNT_COLUMNS = (
    "turnover_observations_1m", "traded_value_observations_1m",
    "volume_observations_1m", "range_observations_1m",
    "overnight_observations_1m", "intraday_observations_1m",
    "price_observations_1m", "price_return_observations_1m",
)


def _spec(columns, formula, orientation, kind="ADAPTED_MEASUREMENT"):
    return {"required_columns": columns, "formula": formula,
            "orientation": orientation, "evidence_kind": kind}


REFERENCE_SPECS = {
    "kr_turnover_1m_v1": _spec(["share_turnover_1m", "turnover_observations_1m"],
        "mean(volume_d/shares_d); valid>=15 observed days", -1),
    "kr_turnover_cv_1m_v1": _spec(["share_turnover_cv_1m", "turnover_observations_1m"],
        "sample_std(volume_d/shares_d)/mean(volume_d/shares_d); valid>=15", -1),
    "kr_traded_value_1m_v1": _spec(["mean_traded_value_1m", "traded_value_observations_1m"],
        "ln(mean(nonnegative trading_value_KRW_d)); positive mean; valid>=15", -1),
    "kr_traded_value_cv_1m_v1": _spec(["traded_value_cv_1m", "traded_value_observations_1m"],
        "sample_std(trading_value_KRW_d)/mean(trading_value_KRW_d); valid>=15", -1),
    "kr_zero_volume_1m_v1": _spec(["zero_volume_fraction_1m", "volume_observations_1m"],
        "count(volume_d=0)/count(volume_d>=0); valid>=15; not Liu composite", 1),
    "kr_downside_risk_252d_v1": _spec(["downside_semideviation_252d", "daily_return_observations_252d"],
        "sqrt(mean(min(r_d,0)^2)); last252 observed rows; valid>=200; not downside beta", -1,
        "RISK_DIAGNOSTIC_CONTROL"),
    "kr_return_skew_252d_v1": _spec(["return_skew_252d", "daily_return_observations_252d"],
        "mean((r_d-mean(r))^3)/mean((r_d-mean(r))^2)^1.5; last252 rows; valid>=200; variance>1e-16 numerical guard", -1),
    "kr_parkinson_1m_v1": _spec(["parkinson_variance_1m", "range_observations_1m"],
        "mean(ln(high_d/low_d)^2/(4*ln(2))); valid>=15; no annualization", -1,
        "ALTERNATIVE_VOLATILITY_ESTIMATOR"),
    "kr_overnight_momentum_1m_v1": _spec(["overnight_return_1m", "overnight_observations_1m", "price_observations_1m"],
        "product((open_d/close_d)*(adj_close_d/adj_close_prev))-1; all observed sessions valid, >=15", 1),
    "kr_intraday_momentum_1m_v1": _spec(["intraday_return_1m", "intraday_observations_1m", "price_observations_1m"],
        "product(close_d/open_d)-1; all observed sessions valid, >=15", 1),
    "kr_information_discreteness_12_2_v1": _spec([
        "adj_close", "positive_return_days_1m", "negative_return_days_1m", "price_return_observations_1m"],
        "sign(P(t-1)/P(t-12)-1)*(negative-positive daily counts)/valid daily count over months t-11..t-1; each month valid>=15", -1),
    "kr_nominal_price_v1": _spec(["nominal_close"],
        "ln(unadjusted close_KRW_t); positive close; nominal-price control, not split invariant", -1,
        "NOMINAL_PRICE_CONTROL"),
    "kr_reversal_36_13_price_v1": _spec(["adj_close"],
        "P(t-12)/P(t-36)-1; 25 positive contiguous calendar-month endpoints; skip latest12 months", -1),
}

# Preserve the original seven features in this new source capture. Querying all
# columns from the same transaction avoids silently mixing old and new vintages.
EXTENDED_PRICE_SQL = """
WITH p AS (
 SELECT p.asset_id,p.trade_date,p.adj_close::float8 AS adj_close,
   p.market_cap::float8 AS market_cap,p.trading_value::float8 AS trading_value,
   p.open::float8 AS session_open,p.close::float8 AS nominal_close,
   p.high::float8 AS session_high,p.low::float8 AS session_low,
   p.volume::float8 AS share_volume,p.shares::float8 AS listed_shares,
   p.market,p.quality_run_id::text AS quality_run_id
 FROM public.price_daily p
 JOIN public.asset a ON a.asset_id=p.asset_id
 JOIN public.dq_run q ON q.run_id=p.quality_run_id AND q.status='CERTIFIED'
 WHERE p.source='KRX' AND a.exchange='KRX' AND a.asset_type='stock'
   AND a.instrument_type='common_stock' AND p.market IN ('KOSPI','KOSDAQ')
   AND p.trade_date BETWEEN %s::date AND %s::date
   AND p.asset_id=ANY(%s::bigint[])
), r AS (
 SELECT p.*,
   CASE WHEN adj_close>0 AND lag(adj_close) OVER w>0
        THEN adj_close/lag(adj_close) OVER w-1 END AS price_return,
   CASE WHEN share_volume>=0 AND listed_shares>0
        THEN share_volume/listed_shares END AS share_turnover,
   CASE WHEN trading_value>=0 THEN trading_value END AS nonnegative_traded_value,
   CASE WHEN share_volume>=0 THEN CASE WHEN share_volume=0 THEN 1.0 ELSE 0.0 END END AS zero_volume,
   CASE WHEN session_high>=session_low AND session_low>0
        THEN power(ln(session_high/session_low),2)/(4*ln(2.0)) END AS parkinson_daily,
   CASE WHEN session_open>0 AND nominal_close>0 AND adj_close>0 AND lag(adj_close) OVER w>0
        THEN ln(session_open/nominal_close)+ln(adj_close/lag(adj_close) OVER w) END AS overnight_log,
   CASE WHEN session_open>0 AND nominal_close>0
        THEN ln(nominal_close/session_open) END AS intraday_log
 FROM p WINDOW w AS (PARTITION BY asset_id ORDER BY trade_date)
), f AS (
 SELECT r.*,
   stddev_samp(price_return) OVER w AS daily_volatility_252d,
   count(price_return) OVER w AS daily_return_observations_252d,
   max(adj_close) OVER w AS price_high_252d,
   count(adj_close) OVER w AS price_high_observations_252d,
   avg(abs(price_return)/trading_value) FILTER(WHERE trading_value>0) OVER m AS amihud_illiquidity_1m,
   count(price_return) FILTER(WHERE trading_value>0) OVER m AS amihud_observations_1m,
   max(price_return) OVER m AS max_daily_return_1m,
   count(price_return) OVER m AS max_daily_return_observations_1m,
   avg(share_turnover) OVER m AS share_turnover_1m,
   stddev_samp(share_turnover) OVER m/nullif(avg(share_turnover) OVER m,0) AS share_turnover_cv_1m,
   count(share_turnover) OVER m AS turnover_observations_1m,
   avg(nonnegative_traded_value) OVER m AS mean_traded_value_1m,
   stddev_samp(nonnegative_traded_value) OVER m/nullif(avg(nonnegative_traded_value) OVER m,0) AS traded_value_cv_1m,
   count(nonnegative_traded_value) OVER m AS traded_value_observations_1m,
   avg(zero_volume) OVER m AS zero_volume_fraction_1m,
   count(zero_volume) OVER m AS volume_observations_1m,
   sqrt(avg(CASE WHEN price_return IS NOT NULL THEN power(least(price_return,0),2) END) OVER w) AS downside_semideviation_252d,
   avg(price_return::numeric) OVER w AS return_raw_moment1,
   avg(power(price_return::numeric,2)) OVER w AS return_raw_moment2,
   avg(power(price_return::numeric,3)) OVER w AS return_raw_moment3,
   avg(parkinson_daily) OVER m AS parkinson_variance_1m,
   count(parkinson_daily) OVER m AS range_observations_1m,
   exp(sum(overnight_log) OVER m)-1 AS overnight_return_1m,
   count(overnight_log) OVER m AS overnight_observations_1m,
   exp(sum(intraday_log) OVER m)-1 AS intraday_return_1m,
   count(intraday_log) OVER m AS intraday_observations_1m,
   count(*) OVER m AS price_observations_1m,
   count(price_return) OVER m AS price_return_observations_1m,
   count(price_return) FILTER(WHERE price_return>0) OVER m AS positive_return_days_1m,
   count(price_return) FILTER(WHERE price_return<0) OVER m AS negative_return_days_1m,
   row_number() OVER(PARTITION BY asset_id,date_trunc('month',trade_date) ORDER BY trade_date DESC) AS rn
 FROM r WINDOW w AS (PARTITION BY asset_id ORDER BY trade_date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW),
   m AS (PARTITION BY asset_id,date_trunc('month',trade_date))
)
SELECT f.*,
 CASE WHEN daily_volatility_252d>1e-8 AND return_raw_moment2-power(return_raw_moment1,2)>1e-16
 THEN (return_raw_moment3-3*return_raw_moment1*return_raw_moment2+2*power(return_raw_moment1,3)) /
       power(return_raw_moment2-power(return_raw_moment1,2),1.5) END AS return_skew_252d,
 i.stock_code,i.n AS ticker_match_count
FROM f JOIN LATERAL (
 SELECT min(identifier) AS stock_code,count(*) AS n FROM public.asset_identifier ai
 WHERE ai.asset_id=f.asset_id AND ai.source='KRX' AND ai.identifier_type='ticker'
   AND ai.valid_from<=f.trade_date AND (ai.valid_to IS NULL OR ai.valid_to>=f.trade_date)
) i ON true
WHERE rn=1 ORDER BY asset_id,trade_date
"""

# Columns the trusted adapter should project from its source envelope. Original
# library base/price/count columns are supplied separately by that adapter.
ADDITIONAL_COLUMNS = tuple(FEATURE_CONTRACTS) + COUNT_COLUMNS


def _finite(frame: pd.DataFrame, column: str) -> pd.Series:
    value = frame[column]
    if not pd.api.types.is_numeric_dtype(value) or pd.api.types.is_bool_dtype(value):
        raise ValueError(f"Numeric feature required: {column}")
    return value.astype(float).where(np.isfinite(value))


def _count(frame: pd.DataFrame, column: str, low=15, high=31) -> pd.Series:
    value = _finite(frame, column)
    return value.between(low, high) & value.eq(np.floor(value))


def _calendar_path(frame: pd.DataFrame, start_lag: int, end_lag: int) -> pd.Series:
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, group in frame.groupby("asset_id", sort=False):
        periods = pd.to_datetime(group.date).dt.to_period("M")
        calendar = pd.period_range(periods.min(), periods.max(), freq="M")
        value = _finite(group, "adj_close").where(group.adj_close.gt(0))
        prices = pd.Series(value.to_numpy(), index=periods).reindex(calendar)
        width = start_lag-end_lag+1
        valid = prices.shift(end_lag).rolling(width, min_periods=width).count().eq(width)
        raw = (prices.shift(end_lag)/prices.shift(start_lag)-1).where(valid)
        result.loc[group.index] = raw.reindex(periods).to_numpy()
    return result


def aggregate_daily_for_validation(daily: pd.DataFrame) -> pd.DataFrame:
    """Independent bounded daily->monthly oracle; no certification/publication.

    Input columns are ``asset_id, stock_code, trade_date, known_at, market,
    adj_close, market_cap, trading_value, open, high, low, close, volume, shares``.
    Maximum 100,000 rows/150 assets keeps this a parity/test helper. All source
    dates must be observed historical sessions and all clocks must fall during
    that day's post-close information window (15:30 through KST day-end).
    No missing sessions are invented. A monthly row represents last OBSERVED
    session, not proof that an exchange calendar's month is complete; the trusted
    extractor must omit unclosed months before this function is used.
    """
    identity = {"asset_id", "stock_code", "trade_date", "known_at", "market"}
    numeric = {"adj_close", "market_cap", "trading_value", "open", "high", "low", "close", "volume", "shares"}
    if not isinstance(daily, pd.DataFrame) or daily.empty or len(daily)>100000:
        raise ValueError("Nonempty bounded daily input (<=100000 rows) required")
    if set(daily) != identity | numeric:
        raise ValueError("Exact feature-only daily schema required; no labels or implicit columns")
    frame = daily.copy()
    if frame[list(identity)].isna().any().any():
        raise ValueError("Null identity/time values forbidden")
    if not frame.stock_code.map(lambda s: isinstance(s,str) and bool(re.fullmatch(r"[0-9A-Z]{6}",s))).all():
        raise ValueError("Six-character uppercase historical ticker strings required")
    if not frame.asset_id.map(lambda v: isinstance(v,(str,int,np.integer)) and not isinstance(v,bool) and str(v).strip()==str(v) and str(v)!="").all():
        raise ValueError("Stable asset identities required")
    if frame.asset_id.nunique()>150 or not frame.market.isin(["KOSPI","KOSDAQ"]).all():
        raise ValueError("Bounded KOSPI/KOSDAQ source scope required")
    frame.asset_id = frame.asset_id.astype(str)
    dates = pd.to_datetime(frame.trade_date, errors="raise")
    if dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Timezone-naive normalized daily dates required")
    if not frame.known_at.map(lambda v: pd.Timestamp(v).tzinfo is not None).all():
        raise ValueError("Aware known_at required")
    clocks = pd.to_datetime(frame.known_at, utc=True)
    day_start = dates.dt.tz_localize("Asia/Seoul").dt.tz_convert("UTC")
    if ((clocks<day_start+pd.Timedelta(hours=15,minutes=30)) |
        (clocks>=day_start+pd.Timedelta(days=1))).any():
        raise ValueError("Daily price known_at must be post-close and no later than observed day-end")
    frame["trade_date"], frame["known_at"] = dates, clocks
    if frame.duplicated(["asset_id","trade_date"]).any() or frame.duplicated(["stock_code","trade_date"]).any():
        raise ValueError("Duplicate or ambiguous historic daily identity")
    for column in numeric:
        if not pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_bool_dtype(frame[column]):
            raise ValueError(f"Numeric daily field required: {column}")
        frame[column] = frame[column].astype(float).where(np.isfinite(frame[column]))
    frame = frame.sort_values(["asset_id","trade_date"]).reset_index(drop=True)
    outputs: list[dict[str, Any]] = []
    for _, group in frame.groupby("asset_id",sort=False):
        group = group.reset_index(drop=True)
        price = group.adj_close.where(group.adj_close.gt(0))
        returns = price/price.shift(1)-1
        turnover = (group.volume/group.shares).where(group.volume.ge(0) & group.shares.gt(0))
        value = group.trading_value.where(group.trading_value.ge(0))
        zero = pd.Series(np.where(group.volume.eq(0),1.0,0.0)).where(group.volume.ge(0))
        ranges = np.log((group.high/group.low).where(group.high.ge(group.low) & group.low.gt(0)))**2/(4*math.log(2))
        intra_gross = (group.close/group.open).where(group.close.gt(0) & group.open.gt(0))
        over_gross = (group.open/group.close * price/price.shift(1)).where(
            group.open.gt(0) & group.close.gt(0))
        for _, month in group.groupby(group.trade_date.dt.to_period("M"),sort=True):
            positions = month.index
            end = int(positions[-1])
            window = slice(max(0,end-251),end+1)
            rw = returns.iloc[window].dropna().to_numpy()
            valid_prices = group.adj_close.iloc[window].dropna()
            mr = returns.loc[positions].dropna()
            mt, mv, mz, mg = (s.loc[positions].dropna() for s in (turnover,value,zero,ranges))
            overnight, intraday = (s.loc[positions].dropna() for s in (over_gross,intra_gross))
            last = month.iloc[-1]
            centered = rw-rw.mean() if len(rw) else np.array([])
            variance = float(np.mean(centered**2)) if len(rw) else np.nan
            # Deliberately use centered values, unlike SQL's raw-moment formula.
            skew = float(np.mean(centered**3)/variance**1.5) if variance>1e-16 else np.nan
            positive_value_returns = returns.loc[positions].where(group.trading_value.loc[positions].gt(0))
            amihud = (returns.loc[positions].abs()/group.trading_value.loc[positions]).where(
                group.trading_value.loc[positions].gt(0)).dropna()
            outputs.append({
                "asset_id":last.asset_id, "stock_code":last.stock_code,
                "trade_date":last.trade_date, "date":last.trade_date.to_period("M").end_time.normalize(),
                "known_at":last.known_at, "market":last.market,
                "adj_close":last.adj_close, "market_cap":last.market_cap, "nominal_close":last.close,
                "daily_volatility_252d":float(np.std(rw,ddof=1)) if len(rw)>1 else np.nan,
                "daily_return_observations_252d":len(rw),
                "price_high_252d":valid_prices.max(), "price_high_observations_252d":len(valid_prices),
                "amihud_illiquidity_1m":amihud.mean(), "amihud_observations_1m":int(positive_value_returns.count()),
                "max_daily_return_1m":mr.max(), "max_daily_return_observations_1m":len(mr),
                "share_turnover_1m":mt.mean(),
                "share_turnover_cv_1m":mt.std(ddof=1)/mt.mean() if len(mt)>1 and mt.mean()>0 else np.nan,
                "turnover_observations_1m":len(mt),
                "mean_traded_value_1m":mv.mean(),
                "traded_value_cv_1m":mv.std(ddof=1)/mv.mean() if len(mv)>1 and mv.mean()>0 else np.nan,
                "traded_value_observations_1m":len(mv),
                "zero_volume_fraction_1m":mz.mean(), "volume_observations_1m":len(mz),
                "downside_semideviation_252d":float(np.sqrt(np.mean(np.minimum(rw,0)**2))) if len(rw) else np.nan,
                "return_skew_252d":skew, "parkinson_variance_1m":mg.mean(), "range_observations_1m":len(mg),
                "overnight_return_1m":float(np.prod(overnight)-1) if len(overnight) else np.nan,
                "intraday_return_1m":float(np.prod(intraday)-1) if len(intraday) else np.nan,
                "overnight_observations_1m":len(overnight), "intraday_observations_1m":len(intraday),
                "price_observations_1m":len(month), "price_return_observations_1m":len(mr),
                "positive_return_days_1m":int(mr.gt(0).sum()), "negative_return_days_1m":int(mr.lt(0).sum()),
            })
    return pd.DataFrame(outputs).sort_values(["asset_id","date"]).reset_index(drop=True)


def calculate(frame: pd.DataFrame, reference_id: str) -> pd.Series:
    """Return raw measurements for one registered expansion definition.

    This is an estimator helper, not an attestation boundary: the calling v2
    library must validate complete identity, clocks, source digest and units.
    Missing columns are errors; invalid observations produce NaN, never zeros.
    """
    if reference_id not in REFERENCE_SPECS:
        raise ValueError(f"Unknown price expansion reference: {reference_id}")
    missing = set(REFERENCE_SPECS[reference_id]["required_columns"])-set(frame)
    if missing:
        raise ValueError(f"Missing measurement columns: {sorted(missing)}")
    if not frame.index.is_unique:
        raise ValueError("Unique frame index required")
    direct = {
        "kr_turnover_1m_v1": ("share_turnover_1m", "turnover_observations_1m", 0, np.inf),
        "kr_turnover_cv_1m_v1": ("share_turnover_cv_1m", "turnover_observations_1m", 0, np.inf),
        "kr_traded_value_cv_1m_v1": ("traded_value_cv_1m", "traded_value_observations_1m", 0, np.inf),
        "kr_zero_volume_1m_v1": ("zero_volume_fraction_1m", "volume_observations_1m", 0, 1),
        "kr_parkinson_1m_v1": ("parkinson_variance_1m", "range_observations_1m", 0, np.inf),
    }
    if reference_id in direct:
        column, count, low, high = direct[reference_id]
        value = _finite(frame, column)
        return value.where(value.between(low, high) & _count(frame, count))
    if reference_id in {"kr_traded_value_1m_v1", "kr_nominal_price_v1"}:
        column = "mean_traded_value_1m" if reference_id=="kr_traded_value_1m_v1" else "nominal_close"
        value = _finite(frame, column)
        result = np.log(value.where(value.gt(0)))
        return result.where(_count(frame, "traded_value_observations_1m")) if column=="mean_traded_value_1m" else result
    if reference_id in {"kr_downside_risk_252d_v1", "kr_return_skew_252d_v1"}:
        column = "downside_semideviation_252d" if reference_id=="kr_downside_risk_252d_v1" else "return_skew_252d"
        value = _finite(frame, column)
        if column=="downside_semideviation_252d":
            value = value.where(value.ge(0))
        return value.where(_count(frame, "daily_return_observations_252d", 200, 252))
    if reference_id in {"kr_overnight_momentum_1m_v1", "kr_intraday_momentum_1m_v1"}:
        kind = "overnight" if reference_id=="kr_overnight_momentum_1m_v1" else "intraday"
        value = _finite(frame, f"{kind}_return_1m")
        valid = (_count(frame, f"{kind}_observations_1m") & _count(frame, "price_observations_1m") &
                 frame[f"{kind}_observations_1m"].eq(frame.price_observations_1m))
        return value.where(value.gt(-1) & valid)
    if reference_id=="kr_reversal_36_13_price_v1":
        return _calendar_path(frame, 36, 12)
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    path = _calendar_path(frame, 12, 1)
    for _, group in frame.groupby("asset_id", sort=False):
        periods = pd.to_datetime(group.date).dt.to_period("M")
        calendar = pd.period_range(periods.min(), periods.max(), freq="M")
        positive = _finite(group, "positive_return_days_1m")
        negative = _finite(group, "negative_return_days_1m")
        count = _finite(group, "price_return_observations_1m")
        valid = (_count(group, "price_return_observations_1m") & positive.ge(0) & negative.ge(0) &
                 positive.eq(np.floor(positive)) & negative.eq(np.floor(negative)) &
                 (positive+negative).le(count))
        def history_sum(value):
            series = pd.Series(value.where(valid).to_numpy(), index=periods).reindex(calendar)
            return series.shift(1).rolling(11, min_periods=11).sum().reindex(periods).to_numpy()
        raw = np.sign(path.loc[group.index]) * history_sum(negative-positive)/history_sum(count)
        result.loc[group.index] = raw
    return result
