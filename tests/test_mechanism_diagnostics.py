import json

import numpy as np
import pandas as pd
import pytest

from engine.mechanism_diagnostics import build_diagnostics


def sample(n_months=24, n_assets=100):
    rng = np.random.default_rng(7105)
    months = pd.period_range("2018-01", periods=n_months, freq="M")
    frames = []
    for month in months:
        size = rng.normal(size=n_assets)
        sector = np.where(np.arange(n_assets) % 2, "A", "B")
        signal = size + rng.normal(scale=.3, size=n_assets)
        returns = .04 * size + rng.normal(scale=.02, size=n_assets)
        frames.append(pd.DataFrame({
            "asset_id": np.arange(n_assets), "ym": month, "signal": signal,
            "size": size, "sector": sector, "fwd_return": returns,
            "fwd_return__known_at": (month + 1).end_time.normalize(),
            "future_margin": .1 * size + rng.normal(scale=.1, size=n_assets),
            "future_margin__known_at": (month + 4).end_time.normalize(),
        }))
    return pd.concat(frames, ignore_index=True)


def run(frame, **kwargs):
    options = dict(signal="signal", forward_return="fwd_return", controls=["size", "sector"],
                   outcomes=["future_margin"], as_of="2023-12-31")
    options.update(kwargs)
    result = build_diagnostics(frame, **options)
    json.dumps(result, allow_nan=False)
    return result


def test_synthetic_association_weakens_after_control_on_same_sample():
    frame = sample()
    original = frame.copy(deep=True)
    frame.loc[::9, "size"] = np.nan
    result = run(frame)
    controlled = result["controlled_comparison"]
    assert controlled["status"] == "AVAILABLE"
    assert controlled["data"]["raw_rank_ic"]["mean"] > .7
    assert abs(controlled["data"]["adjusted_rank_ic"]["mean"]) < .1
    for row in controlled["data"]["monthly"]:
        block = frame.loc[frame.ym.astype(str).eq(row["month"])].dropna(subset=["size"])
        assert row["n_common"] == len(block)
        expected = block.signal.rank().corr(block.fwd_return.rank())
        assert row["raw_rank_ic"] == pytest.approx(expected)
    assert result["selection_profile"]["status"] == "PARTIAL"
    assert any("not causality" in text for text in controlled["limitations"])
    # Only the intentional input edit occurred; build_diagnostics is pure.
    pd.testing.assert_frame_equal(frame.drop(columns="size"), original.drop(columns="size"))


def test_missing_availability_never_falls_back_to_values():
    result = run(sample().drop(columns=["fwd_return__known_at", "future_margin__known_at"]))
    assert result["monthly_performance"]["status"] == "NOT_COLLECTED"
    assert result["economic_outcomes"]["status"] == "NOT_COLLECTED"
    assert all(row["n_pairs"] == 0 for row in result["monthly_performance"]["data"]["monthly"])
    assert result["controlled_comparison"]["status"] == "NOT_COLLECTED"


def test_late_and_unknown_outcomes_are_masked_per_column():
    frame = sample(n_months=1)
    frame.loc[0:19, "fwd_return__known_at"] = pd.NaT
    frame.loc[20:39, "fwd_return__known_at"] = pd.Timestamp("2099-01-01")
    frame.loc[0:49, "future_margin__known_at"] = pd.Timestamp("2099-01-01")
    result = run(frame)
    assert result["monthly_performance"]["data"]["monthly"][0]["n_pairs"] == 60
    assert result["economic_outcomes"]["data"]["outcomes"][0]["monthly"][0]["n_pairs"] == 50
    info = result["input_quality"]["data"]["outcome_availability"][0]
    assert info["n_missing_or_invalid_known_at"] == 20
    assert info["n_late_known_at"] == 20
    changed = frame.copy()
    changed.loc[:39, "fwd_return"] = 10_000
    assert run(changed)["monthly_performance"] == result["monthly_performance"]


def test_numeric_availability_is_not_interpreted_as_unix_nanoseconds():
    frame = sample(n_months=1)
    frame["fwd_return__known_at"] = 0
    assert run(frame)["monthly_performance"]["status"] == "NOT_COLLECTED"


def test_ties_are_never_split_and_input_order_does_not_matter():
    frame = sample(n_months=1)
    frame["signal"] = np.repeat([1.0, 2.0], 50)
    result = run(frame)["monthly_performance"]
    rows = result["data"]["monthly"][0]["groups"]
    assert [row["n_signal"] for row in rows] == [0, 50, 0, 50, 0]
    assert result["data"]["monthly"][0]["top_minus_bottom"] is None
    shuffled = run(frame.sample(frac=1, random_state=17))["monthly_performance"]
    assert shuffled["data"]["monthly"][0]["rank_ic"] == pytest.approx(result["data"]["monthly"][0]["rank_ic"])
    assert [row["n_signal"] for row in shuffled["data"]["monthly"][0]["groups"]] == [0, 50, 0, 50, 0]
    frame["signal"] = 1.0
    constant = run(frame)["monthly_performance"]["data"]["monthly"][0]
    assert constant["groups"][2]["n_signal"] == len(frame)
    assert constant["rank_ic"] is None


def test_duplicate_keys_and_outcome_controls_rejected():
    frame = sample(n_months=1)
    with pytest.raises(ValueError, match="Duplicate asset-month"):
        run(pd.concat([frame, frame.iloc[:1]], ignore_index=True))
    for control in ["fwd_return", "future_margin", "fwd_return__known_at", "signal", "asset_id"]:
        with pytest.raises(ValueError, match="Controls must exclude"):
            run(frame, controls=[control])


def test_future_signal_months_cannot_change_existing_months():
    frame = sample(n_months=8)
    prefix = frame.loc[frame.ym <= pd.Period("2018-04", freq="M")]
    full = run(frame, as_of="2018-04-30")
    short = run(prefix, as_of="2018-04-30")
    for section in ["monthly_performance", "selection_profile", "economic_outcomes", "controlled_comparison"]:
        assert full[section] == short[section]
    assert full["input_quality"]["data"]["n_excluded_unfinished_or_future_signal_rows"] == 400
    assert len(run(frame, as_of="2018-04-29")["monthly_performance"]["data"]["monthly"]) == 3


def test_inference_support_uses_months_not_stock_rows():
    frame = sample(n_months=3, n_assets=1000)
    uncertainty = run(frame)["monthly_performance"]["data"]["top_minus_bottom"]
    assert uncertainty["n_months"] == 3
    assert uncertainty["status"] == "INSUFFICIENT_MONTHS"
    assert uncertainty["ci95"] is None
    enough = run(sample(n_months=12))["monthly_performance"]["data"]["top_minus_bottom"]
    assert enough["n_months"] == 12
    assert enough["status"] == "AVAILABLE"
    assert enough["ci95"][0] <= enough["mean"] <= enough["ci95"][1]


def test_replicating_assets_does_not_increase_monthly_inference_support():
    frame = sample(n_months=12)
    extra = frame.copy()
    extra["asset_id"] += 1000
    original = run(frame)["monthly_performance"]["data"]["top_minus_bottom"]
    replicated = run(pd.concat([frame, extra], ignore_index=True))["monthly_performance"]["data"]["top_minus_bottom"]
    assert replicated["n_months"] == original["n_months"]
    assert replicated["standard_error"] == pytest.approx(original["standard_error"])
    assert replicated["ci95"] == pytest.approx(original["ci95"])


def test_raw_adjusted_summaries_use_same_month_support():
    frame = sample(n_months=13)
    first = frame.ym.eq(frame.ym.iloc[0])
    frame.loc[first, "signal"] = frame.loc[first, "size"]
    data = run(frame)["controlled_comparison"]["data"]
    assert data["monthly"][0]["raw_rank_ic"] is not None
    assert data["monthly"][0]["adjusted_rank_ic"] is None
    assert data["raw_rank_ic"]["n_months"] == data["adjusted_rank_ic"]["n_months"] == 12


def test_hac_uses_calendar_lags_and_reports_gaps():
    from engine.mechanism_diagnostics import _uncertainty

    months = pd.period_range("2018-01", periods=24, freq="M")
    values = np.arange(12, dtype=float)
    gapped = [{"month": str(month), "value": value} for month, value in zip(months[::2], values)]
    result = _uncertainty(gapped, "value")
    centered = values - values.mean()
    # Only lag two has observed pairs; lags one and three do not bridge gaps.
    expected_variance = (np.dot(centered, centered) + np.dot(centered[:-1], centered[1:])) / (12 * 11)
    assert result["standard_error"] == pytest.approx(np.sqrt(expected_variance))
    assert result["n_calendar_consecutive_runs"] == 12
    assert result["longest_consecutive_run"] == 1


def test_regime_alignment_unknown_and_calendar_episode_counts():
    frame = sample(n_months=6)
    frame = frame.loc[frame.ym != pd.Period("2018-03", freq="M")]
    labels = pd.DataFrame({"month": ["2018-01", "2018-02", "2018-04", "2018-05"],
                           "effective_month": ["2018-02", "2018-03", "2018-05", "2018-06"],
                           "regime": ["UP_LOW", "UP_LOW", "UP_LOW", "DOWN_HIGH"],
                           "status": ["READY"] * 4})
    result = run(frame, regimes=labels)["regime_comparison"]
    assert result["status"] == "PARTIAL"
    by_regime = {row["regime"]: row for row in result["data"]["regimes"]}
    assert by_regime["UP_LOW"]["n_months"] == 3
    assert by_regime["UP_LOW"]["n_episodes"] == 2
    assert by_regime["UP_LOW"]["longest_episode_months"] == 2
    assert by_regime["UNKNOWN"]["n_months"] == 1
    first = result["data"]["monthly"][0]
    assert first["month"] == "2018-01" and first["effective_month"] == "2018-02"
    with pytest.raises(ValueError, match="Duplicate regime"):
        run(frame, regimes=pd.concat([labels, labels.iloc[:1]]))
    labels.loc[0, "effective_month"] = "2018-01"
    with pytest.raises(ValueError, match="must equal signal month"):
        run(frame, regimes=labels)


def test_missing_controls_empty_input_and_exactly_explained_signal():
    frame = sample(n_months=1)
    assert run(frame, controls=["absent"])["controlled_comparison"]["status"] == "NOT_COLLECTED"
    empty = run(frame.iloc[:0])
    assert all(section["status"] == "NOT_COLLECTED" for section in empty.values())
    frame["signal"] = frame["size"]
    controlled = run(frame)["controlled_comparison"]["data"]["monthly"][0]
    assert controlled["adjusted_rank_ic"] is None
    assert controlled["status"] == "NO_RESIDUAL_OR_RANK_VARIATION"


def test_small_cross_section_is_not_controlled_evidence():
    controlled = run(sample(n_months=24, n_assets=20))["controlled_comparison"]
    assert controlled["status"] == "NOT_COLLECTED"
    assert all(row["status"] == "INSUFFICIENT_SAMPLE" for row in controlled["data"]["monthly"])


def test_numeric_and_categorical_profiles_have_expected_schema():
    selection = run(sample(n_months=1))["selection_profile"]["data"]["controls"]
    numeric, categorical = selection
    assert numeric["type"] == "numeric"
    assert numeric["monthly"][0]["groups"][0]["mean_percentile_rank"] < numeric["monthly"][0]["groups"][4]["mean_percentile_rank"]
    assert categorical["type"] == "categorical"
    for group in categorical["monthly"][0]["groups"]:
        assert sum(row["share"] for row in group["category_shares"]) == pytest.approx(1)


def test_economic_outcome_inference_is_suppressed_without_horizon_contract():
    outcomes = run(sample(n_months=24))["economic_outcomes"]["data"]["outcomes"]
    for field in ("rank_ic", "top_minus_bottom"):
        summary = outcomes[0][field]
        assert summary["status"] == "DESCRIPTIVE_ONLY_HORIZON_NOT_CONFIGURED"
        assert summary["mean"] is not None
        assert summary["n_months"] == 24
        assert summary["standard_error"] is None
        assert summary["ci95"] is None
