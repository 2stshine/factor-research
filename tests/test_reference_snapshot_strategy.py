import numpy as np
import pandas as pd
import pytest

from engine import reference_snapshot_strategy as s


def prices():
    rows = []
    for month in pd.period_range("2019-01", "2019-08", freq="M"):
        for asset in range(1, 21):
            rows.append({"asset_id": asset, "date": month.end_time.normalize(),
                         "known_at": month.end_time.floor("s").tz_localize("Asia/Seoul"),
                         "adj_close": 100 + asset + (month.month - 1) * asset / 10,
                         "market_cap": 1e9 + asset * 1e8, "market": "KOSPI"})
    return pd.DataFrame(rows)


def fixture():
    panel = s.build_price_panel(prices())
    panel["f_a"] = panel.asset_id.astype(float)
    panel["f_b"] = panel.asset_id.mod(3).astype(float)
    settings = {"train_window_months": 60, "min_train_months": 2, "min_train_rows": 20,
                "purge_gap_months": 1, "selected_max_features": 2, "pca_components": 1, "alpha": 10.,
                "selection": {"max_abs_correlation": .95, "max_missing_fraction": .6, "min_variance": 0.}}
    return panel, settings


def test_exact_calendar_join_never_spans_missing_month():
    p = prices()
    p = p.loc[~((p.asset_id == 1) & (p.date.dt.month == 2))]
    panel = s.build_price_panel(p)
    assert pd.isna(panel.loc[(panel.asset_id == 1) & (panel.month == "2019-01"), "outcome"].iloc[0])
    assert panel.loc[panel.month == "2019-08", "outcome"].isna().all()


def test_future_price_clock_rejected():
    p = prices()
    p.loc[0, "known_at"] = pd.Timestamp("2026-01-01", tz="UTC")
    with pytest.raises(ValueError, match="Future"):
        s.build_price_panel(p)


def test_future_outcomes_do_not_change_model_or_selected_stocks():
    p, config = fixture()
    before = s.run_month(p, ["f_a", "f_b"], config, "2019-05", round_trip_bps=50)
    p.loc[p.month >= "2019-05", "outcome"] = 99.
    after = s.run_month(p, ["f_a", "f_b"], config, "2019-05", round_trip_bps=50)
    for model in s.MODELS:
        assert before["models"][model]["fit"] == after["models"][model]["fit"]
        for a, b in zip(before["models"][model]["portfolios"], after["models"][model]["portfolios"]):
            assert a["selected_assets"] == b["selected_assets"]


def test_unavailable_labels_excluded_from_training():
    p, config = fixture()
    p.loc[p.month == "2019-03", "label_known_at"] = pd.Timestamp("2026-01-01", tz="UTC")
    fold = s.run_month(p, ["f_a", "f_b"], config, "2019-05", round_trip_bps=50)
    assert "2019-03" not in fold["train_months"]


def test_missing_selected_return_does_not_remove_stock_or_zero_fill():
    p, _ = fixture()
    p = p.loc[p.month == "2019-05"].copy()
    p.loc[p.asset_id == 20, "outcome"] = np.nan
    result = s.portfolio_month(p, p.asset_id.to_numpy(), round_trip_bps=50)
    for item in result:
        assert 20 in item["selected_assets"]
        assert item["net_return_cost_scenario"] is None
        assert item["status"] == "UNRESOLVED_MISSING_OUTCOMES"
        assert item["universe_ew_price_return"] is None
        scenario = item["sensitivity_net_returns_not_observed"]
        assert scenario["MISSING_FLAT_ASSUMPTION"] - scenario["MISSING_TOTAL_LOSS_ASSUMPTION"] == pytest.approx(item["missing_outcome_weight"] * .995)


def test_cost_scenario_arithmetic_and_incomplete_history_no_cagr():
    p, c = fixture()
    fold = s.run_month(p, ["f_a", "f_b"], c, "2019-05", round_trip_bps=50)
    for model in s.MODELS:
        item = fold["models"][model]["portfolios"][0]
        assert item["net_return_cost_scenario"] == pytest.approx((1 + item["gross_price_return"]) * .995 - 1)
        item["status"] = "UNRESOLVED_MISSING_OUTCOMES"
        item["net_return_cost_scenario"] = None
    for row in s.summarize([fold]):
        if row["portfolio"] == "q20_equal":
            assert row["annualized_net_return_cost_scenario"] is None


def test_snapshot_tampering_rejected_without_network(tmp_path, monkeypatch):
    import socket
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: pytest.fail("Network accessed"))
    m = {"schema": s.SCHEMA, "files": {name: "a" * 64 for name in ("panel.parquet", "admission.json", "policy.json")}}
    m["snapshot_sha256"] = s.digest(m)
    s.write_json(tmp_path / "manifest.json", m)
    s.write_json(tmp_path / "panel.parquet", {"tampered": True})
    with pytest.raises(ValueError, match="file changed"):
        s.load_snapshot(tmp_path)


def test_prepare_and_consume_fixed_files_offline_without_original_sources(tmp_path, monkeypatch):
    import socket
    from engine import reference_admission as admission
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: pytest.fail("Network accessed"))
    p = prices()
    price_path = tmp_path / "price.parquet"
    p.to_parquet(price_path)
    values = p[["asset_id", "date", "known_at"]].copy()
    values["reference_id"], values["definition_hash"] = "test_reference", "b" * 64
    values["value"] = values.asset_id.astype(float)
    values["asset_id"] = values.asset_id.astype(str)
    value_path = tmp_path / "values.parquet"
    values.to_parquet(value_path)
    # Fake historical attestation is a test fixture only, not an actual admission.
    a = {"schema": admission.SCHEMA, "program_sha256": "a" * 64, "origin": "OBSERVED",
         "live_database_verified": True, "status": "ADMISSION_EVALUATED",
         "decisions": [{"reference_id": "test_reference", "definition_sha256": "b" * 64, "status": "ADMITTED"}],
         "source_receipts": [{"dataset_id": "c" * 64, "live_all_row_verified": True,
                              "cache_sha256": s.file_hash(value_path), "rows": len(values)}]}
    a["admission_sha256"] = s.digest(a)
    s.write_json(tmp_path / "admission.json", a)
    s.write_json(tmp_path / "cache.json", {"cache_paths": {"c" * 64: str(value_path)}})
    s.write_json(tmp_path / "policy.json", {"program_sha256": "a" * 64, "strategy_comparison": {"max_feature_age_days": 550}})
    directory = tmp_path / "snapshot"
    m = s.prepare(admission_path=tmp_path / "admission.json", cache_receipt=tmp_path / "cache.json",
                  prices_path=price_path, policy_path=tmp_path / "policy.json", output=directory)
    price_path.rename(tmp_path / "price-moved.parquet")
    value_path.rename(tmp_path / "values-moved.parquet")
    panel, loaded, _ = s.load_snapshot(directory)
    assert loaded == m and len(panel) == len(p)
    assert not loaded["refresh_required"] and not loaded["live_database_rechecked"]
    assert loaded["last_signal_month"] == "2019-07"
    assert "f_test_reference" in panel
    assert panel.f_test_reference.notna().all()


def test_snapshot_month_selection_and_resumption_cli(tmp_path, monkeypatch):
    from scripts import run_reference_snapshot as cli
    p, settings = fixture()
    m = {"snapshot_sha256": "a" * 64, "first_month": "2019-01", "last_signal_month": "2019-07",
         "fields": [{"field": "f_a"}, {"field": "f_b"}], "return_basis": "TEST_ONLY_PRICE_RETURN",
         "pit_status": "SYNTHETIC_TEST_FIXTURE"}
    monkeypatch.setattr(s, "load_snapshot", lambda *a: (p, m, {"strategy_comparison": settings}))
    args = cli.parser().parse_args(["run", "--snapshot", str(tmp_path), "--output", str(tmp_path / "run"),
                                    "--first-month", "2019-05", "--last-month", "2019-06"])
    initial = cli.run(args)
    monkeypatch.setattr(s, "run_month", lambda *a, **kw: pytest.fail("Checkpoint should be reused"))
    assert cli.run(args) == initial
    args.last_month = "2019-08"
    with pytest.raises(ValueError, match="outside completed"):
        cli.run(args)
