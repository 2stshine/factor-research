import numpy as np
import pandas as pd
import pytest
import json
import sys

from engine.regimes import RULES, RULES_V1, RULE_HASHES, classify_monthly_market, detailed_regime


def sample(n=90):
    months = pd.period_range("2015-01", periods=n, freq="M")
    returns = .008 + .025 * np.sin(np.arange(n) * 1.7)
    return pd.DataFrame({
        "month": months.astype(str), "close": 100 * np.cumprod(1 + returns),
        "known_at": months.to_timestamp("M"),
    })


def run(data, as_of="2022-06-30"):
    return classify_monthly_market(
        data, as_of=as_of, market_id="TEST", source_id="synthetic-v1",
    )


def test_exact_formula_and_warmup():
    data = sample()
    out = run(data)
    vol = data.close.pct_change(fill_method=None).rolling(12).std() * np.sqrt(12)
    assert out.loc[35, "regime"] == "UNKNOWN"
    assert out.loc[36, "status"] == "READY"
    assert out.loc[36, "prior_vol_n"] == 24
    assert out.iloc[-1].sma_10m == pytest.approx(data.close.iloc[-10:].mean())
    assert out.iloc[-1].vol_12m_annualized == pytest.approx(vol.iloc[-1])
    assert out.iloc[-1].prior_vol_median == pytest.approx(vol.iloc[:-1].median())
    assert out.iloc[-1].effective_month == "2022-07"


def test_prefix_invariance_including_fingerprints():
    data = sample()
    old = run(data.iloc[:60], "2019-12-31")
    pd.testing.assert_frame_equal(old, run(data).iloc[:60].reset_index(drop=True))
    changed = data.copy()
    changed.loc[60:, "close"] *= 50
    pd.testing.assert_frame_equal(old, run(changed, "2019-12-31"))


def test_current_vol_does_not_change_its_threshold():
    data = sample()
    old = run(data).iloc[-1]
    data.loc[len(data) - 1, "close"] *= 2
    new = run(data).iloc[-1]
    assert new.prior_vol_median == old.prior_vol_median
    assert new.vol_12m_annualized > old.vol_12m_annualized


def test_unfinished_month_excluded():
    data = sample()
    data.loc[len(data) - 1, "known_at"] = pd.Timestamp("2022-06-15")
    out = run(data, "2022-06-20")
    assert out.iloc[-1].month == "2022-05"


def test_missing_month_not_forward_filled():
    out = run(sample().drop(index=70))
    assert out.loc[70, "regime"] == "UNKNOWN"
    assert "MISSING_OR_LATE_MONTH" in out.loc[70, "reason"]
    assert out.loc[71, "regime"] == "UNKNOWN"
    assert out.iloc[-1].status == "READY"


def test_late_input_does_not_rewrite_past_decision():
    data = sample()
    data.loc[60, "known_at"] = pd.Timestamp("2020-03-01")
    out = run(data)
    assert out.loc[60, "regime"] == "UNKNOWN"
    assert out.loc[61, "regime"] == "UNKNOWN"
    pd.testing.assert_frame_equal(
        run(data, "2020-02-29"), out.iloc[:62].reset_index(drop=True),
    )


@pytest.mark.parametrize("change", ["duplicate", "zero", "inf", "early_date"])
def test_invalid_input_rejected(change):
    data = sample()
    if change == "duplicate":
        data = pd.concat([data, data.iloc[:1]])
    elif change == "zero":
        data.loc[1, "close"] = 0
    elif change == "inf":
        data.loc[1, "close"] = np.inf
    else:
        data.loc[1, "known_at"] = pd.Timestamp("2015-01-31")
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize("direction,risk", [(1, "LOW"), (-1, "LOW"), (1, "HIGH"), (-1, "HIGH")])
def test_four_states(direction, risk):
    data = sample()
    data.loc[89, "close"] = data.loc[88, "close"] * (
        (2 if direction > 0 else .5) if risk == "HIGH"
        else (1.01 if direction > 0 else .99)
    )
    if risk == "LOW":
        data.loc[60:, "close"] = data.loc[59, "close"] * (
            (1 + direction * .005) ** np.arange(1, 31)
        )
    assert run(data).iloc[-1].regime == f"{'UP' if direction > 0 else 'DOWN'}_{risk}"


def test_flat_market_ties_and_no_future_labels():
    data = sample()
    data["close"] = 100.0
    data["fwd_return"] = 999.0
    out = run(data)
    assert out.iloc[-1].regime == "UP_LOW"
    pd.testing.assert_frame_equal(out, run(data.drop(columns="fwd_return")))


def test_cli_outputs_json_nulls_and_refuses_overwrite(tmp_path, monkeypatch):
    from scripts.market_regimes import main

    source = tmp_path / "index.json"
    target = tmp_path / "regimes.json"
    source.write_text(sample().to_json(orient="records", date_format="iso"))
    monkeypatch.setattr(sys, "argv", [
        "market_regimes", "--input", str(source), "--output", str(target),
        "--as-of", "2022-06-30", "--market-id", "TEST", "--source-id", "fixture",
    ])
    main()
    payload = json.loads(target.read_text())
    assert payload["rows"][0]["prior_vol_median"] is None
    assert payload["rows"][-1]["status"] == "READY"
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        main()
    assert target.read_bytes() == before


def test_v2_short_horizon_formulas_and_own_historical_threshold():
    data = sample()
    out = run(data)
    short_vols = data.close.pct_change(fill_method=None).rolling(3).std(ddof=1) * np.sqrt(12)
    last = out.iloc[-1]
    assert last.return_3m == pytest.approx(data.close.iloc[-1] / data.close.iloc[-4] - 1)
    assert last.vol_3m_annualized == pytest.approx(short_vols.iloc[-1])
    assert last.prior_short_vol_median == pytest.approx(short_vols.iloc[:-1].median())
    assert out.loc[26, "volatility_short"] == "UNKNOWN"
    assert out.loc[27, "volatility_short"] in {"HIGH", "LOW"}
    assert out.loc[35, "regime_detail"] == "UNKNOWN"
    assert out.loc[36, "detail_status"] == "READY"
    changed = data.copy()
    changed.loc[89, "close"] *= 3
    altered = run(changed).iloc[-1]
    assert altered.prior_short_vol_median == last.prior_short_vol_median
    assert altered.prior_vol_median == last.prior_vol_median
    assert altered.vol_3m_annualized > last.vol_3m_annualized


@pytest.mark.parametrize("long,short", [(lt, st) for lt in ("UP", "DOWN") for st in ("UP", "DOWN")])
@pytest.mark.parametrize("long_vol,short_vol", [(lv, sv) for lv in ("HIGH", "LOW") for sv in ("HIGH", "LOW")])
def test_sixteen_labels_are_unambiguous(long, short, long_vol, short_vol):
    assert detailed_regime(long, short, long_vol, short_vol) == f"LT_{long}_ST_{short}_LV_{long_vol}_SV_{short_vol}"
    assert detailed_regime(long, "UNKNOWN", long_vol, short_vol) == "UNKNOWN"


@pytest.mark.parametrize("direction,phase", [(1, "UP_PULLBACK"), (-1, "DOWN_REBOUND")])
def test_long_trend_and_short_reversal_are_separate(direction, phase):
    data = sample()
    levels = data.close.to_numpy().copy()
    for i in range(81, 87):
        levels[i] = levels[i - 1] * (1 + direction * .06)
    for i in range(87, 90):
        levels[i] = levels[i - 1] * (1 - direction * .01)
    data["close"] = levels
    assert run(data).iloc[-1].trend_phase == phase


def test_short_trend_requires_intermediate_months_and_zero_ties_are_explicit():
    data = sample().drop(index=88)
    last = run(data).iloc[-1]
    assert last.trend_short == "UNKNOWN"
    assert last.regime_detail == "UNKNOWN"
    flat = sample()
    flat["close"] = 100.0
    row = run(flat).iloc[-1]
    assert row.trend_short == "UP"
    assert row.volatility_short == "LOW"
    assert row.volatility_phase == "LOW_BOTH"


def test_v1_replay_retains_its_original_columns_values_and_hash():
    data = sample()
    legacy = classify_monthly_market(data, as_of="2022-06-30", market_id="TEST",
                                    source_id="synthetic-v1", rules_version=RULES_V1["version"])
    current = run(data)
    assert "trend_short" not in legacy.columns
    assert legacy.iloc[-1].rules_sha256 == RULE_HASHES[RULES_V1["version"]]
    assert current.iloc[-1].rules_sha256 == RULE_HASHES[RULES["version"]]
    assert legacy.iloc[-1].rules_sha256 != current.iloc[-1].rules_sha256
    columns = [c for c in legacy.columns if c not in {"rules_sha256", "rules_version"}]
    pd.testing.assert_frame_equal(legacy[columns], current[columns])
    with pytest.raises(ValueError, match="Unknown regime rules"):
        classify_monthly_market(data, as_of="2022-06-30", market_id="TEST", source_id="test", rules_version="guess")
