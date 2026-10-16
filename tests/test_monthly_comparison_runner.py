"""End-to-end synthetic adapter tests, never market research or database access."""
import hashlib
import json

import pandas as pd
import pytest

from strategies import run_monthly_comparison as runner


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.fixture
def package(tmp_path):
    root = tmp_path / "research"
    (root / "campaigns").mkdir(parents=True)
    catalog = write(tmp_path / "catalog.json", {
        "as_of": "2025-11-01", "status": "NONLIVE_SNAPSHOT", "is_live": False,
        "factors": [{"name": "synthetic_factor", "status": "APPROVED", "definition_hash": "a" * 16}]})
    plan_path = tmp_path / "plan.json"
    registered = runner.prepare(catalog, decision_start="2025-08", decision_end="2025-09",
                                output=plan_path, research_root=root)
    source = tmp_path / "source-proof.json"
    source.write_text('{"synthetic":true}', encoding="utf-8")
    opens = {"2025-09": "2025-09-03T10:00:00+09:00", "2025-10": "2025-10-03T10:00:00+09:00",
             "2025-11": "2025-11-03T10:00:00+09:00"}
    scores, assets, market = [], [], []
    for month, entry, exit_time in (("2025-08", opens["2025-09"], opens["2025-10"]),
                                    ("2025-09", opens["2025-10"], opens["2025-11"])):
        decision = runner._kst_month(month, True)
        for asset_id in range(1, 21):
            scores.append(dict(factor_id="synthetic_factor", signal_month=month, asset_id=asset_id,
                               signed_score=21-asset_id, eligible=True, market_cap=100., available_at=decision))
            assets.append(dict(signal_month=month, asset_id=asset_id, entry_at=entry, exit_at=exit_time,
                               entry_open=100., gross_total_return_multiplier=1.01,
                               return_available_at=exit_time))
        market.append(dict(signal_month=month, entry_at=entry, exit_at=exit_time,
                           gross_total_return_multiplier=1.005, return_available_at=exit_time))
    data = dict(data_kind="SYNTHETIC_TEST", factor_bindings=registered["plan"]["factor_bindings"],
                market_benchmark=registered["plan"]["benchmark_policy"],
                source_files=[{"path": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
                scores=scores, asset_windows=assets, market_windows=market,
                sessions=[dict(session_month=month, open_at=stamp) for month, stamp in opens.items()])
    evidence = dict(schema_version="monthly-execution-evidence-v1", data_sha256=runner.digest(data),
                    as_of="2025-11-05T00:00:00+09:00", calendar_verified=True,
                    asset_open_prices_verified=True, total_return_multipliers_verified=True,
                    market_total_return_verified=True, pit_inputs_verified=True)
    path = write(tmp_path / "inputs.json", dict(schema_version="monthly-comparison-inputs-v1", data=data, evidence=evidence))
    return root, plan_path, path, tmp_path / "result", catalog


def test_full_synthetic_runner_and_reporting(package):
    root, plan, inputs, out, _ = package
    summary = runner.run(plan, inputs=inputs, output=out, research_root=root)
    assert summary["status"] == "SYNTHETIC_TEST_ONLY"
    assert not summary["real_performance_computed"]
    result = runner.read_json(out / "comparison.json")
    variants = result["results"]["synthetic_factor"]["variants"]
    assert list(variants) == ["q20_equal", "q10_equal", "q20_sqrt_cap", "q10_sqrt_cap"]
    assert all(x["summary"]["months"] == 2 for x in variants.values())
    assert "합성 데이터" in (out / "report.md").read_text()
    first = variants["q20_equal"]["monthly"][0]
    assert first["sell_tax"] == 0
    assert first["net_excess_market"] == pytest.approx(first["net_return"] - .005)
    with pytest.raises(FileExistsError):
        runner.run(plan, inputs=inputs, output=out, research_root=root)


def test_no_inputs_yields_readiness_not_performance(package):
    root, plan, _, out, _ = package
    summary = runner.run(plan, output=out, research_root=root)
    assert summary["status"] == "BLOCKED_MISSING_EXECUTION_INPUTS"
    assert not summary["real_performance_computed"]
    assert not (out / "comparison.json").exists()


def test_incomplete_catalog_never_silently_drops_factors(package):
    root, _, _, out, catalog = package
    value = runner.read_json(catalog)
    value["factors"].append(dict(name="unbound_factor", status="APPROVED", definition_hash=None))
    write(catalog, value)
    path = out.parent / "incomplete.json"
    request = runner.prepare(catalog, decision_start="2025-08", decision_end="2025-09", output=path, research_root=root)
    assert request["registration_type"] == "INCOMPLETE_REQUEST_NOT_EXECUTION_PLAN"
    assert request["unresolved_factor_ids"] == ["unbound_factor"]
    summary = runner.run(path, output=out, research_root=root)
    assert summary["factor_count"] == 2
    assert not summary["executable_plan_registered"]
    with pytest.raises(ValueError, match="Unbound"):
        runner.run(path, inputs="must-not-read.json", output=out.parent / "not-created", research_root=root)


@pytest.mark.parametrize("field", ["data_hash", "source_hash", "factor_binding", "market_type", "extra_month", "extra_session", "as_of"])
def test_corrupt_or_out_of_scope_bundle_fails_closed(package, field):
    root, plan, path, out, _ = package
    bundle = runner.read_json(path)
    if field == "data_hash":
        bundle["evidence"]["data_sha256"] = "0" * 64
    elif field == "source_hash":
        bundle["data"]["source_files"][0]["sha256"] = "0" * 64
    elif field == "factor_binding":
        bundle["data"]["factor_bindings"][0]["definition_hash"] = "b" * 16
    elif field == "market_type":
        bundle["data"]["market_benchmark"]["return_type"] = "price_return"
    elif field == "extra_month":
        bundle["data"]["scores"][0]["signal_month"] = "2026-01"
    elif field == "extra_session":
        bundle["data"]["sessions"].append(dict(session_month="2026-01", open_at="2026-01-02T09:00:00+09:00"))
    else:
        bundle["evidence"]["as_of"] = "2026-01-01T00:00:00+09:00"
    if field != "data_hash":
        bundle["evidence"]["data_sha256"] = runner.digest(bundle["data"])
    write(path, bundle)
    with pytest.raises(ValueError):
        runner.run(plan, inputs=path, output=out, research_root=root)
    assert not out.exists()


def test_new_seal_checked_before_input_read(package):
    root, plan, _, out, _ = package
    directory = root / "campaigns" / "new-campaign"
    directory.mkdir()
    write(directory / "manifest.json", {"campaign_id": "new-campaign", "oos": {
        "status": "SEALED", "start": "2025-10", "signal_end": "2028-09", "return_end": "2028-10"}})
    with pytest.raises(ValueError, match="overlaps sealed"):
        runner.run(plan, inputs="must-not-read.json", output=out, research_root=root)


def test_future_shadow_reservations_are_protected(package):
    root, plan, _, out, _ = package
    directory = root / "prospective-shadow"
    directory.mkdir()
    write(directory / "s.json", {"campaign_id": "s", "status": "COLLECTING", "start_month": "2025-10", "required_months": 36})
    with pytest.raises(ValueError, match="shadow:s"):
        runner.run(plan, output=out, research_root=root)


def test_tampered_plan_cannot_run(package):
    root, plan, _, out, _ = package
    value = runner.read_json(plan)
    value["plan"]["costs"]["buy_rate"] = .5
    write(plan, value)
    with pytest.raises(ValueError, match="digest"):
        runner.run(plan, output=out, research_root=root)


def test_summary_includes_initial_nav_in_drawdown():
    frame = pd.DataFrame(dict(net_return=[-.2, .1], net_excess_universe=[-.2, .1],
                              net_excess_market=[-.2, .1], turnover_buy=[1., 0.], turnover_sell=[0., 0.]))
    assert runner.summarize(frame)["net_mdd"] == pytest.approx(-.2)


def test_total_loss_weight_is_explicit_null_but_infinity_is_rejected():
    assert runner._jsonable({"end_weight": float("nan")}) == {"end_weight": None}
    with pytest.raises(ValueError):
        runner._jsonable({"net_return": float("inf")})


@pytest.mark.parametrize("metadata", [{"status": "OPEN"}, {"status": "OPEN", "oos": {}},
                                     {"status": "OPEN", "oos": {"status": "SEALEDD"}},
                                     {"status": "OPEN", "oos": {"status": "REVEALED"}}])
def test_unknown_campaign_state_is_not_silently_unsealed(package, metadata):
    root, plan, _, out, _ = package
    directory = root / "campaigns" / "broken"
    directory.mkdir()
    write(directory / "manifest.json", metadata)
    with pytest.raises(ValueError):
        runner.run(plan, inputs="must-not-read.json", output=out, research_root=root)


def test_unknown_shadow_state_blocks(package):
    root, plan, _, out, _ = package
    directory = root / "prospective-shadow"
    directory.mkdir()
    write(directory / "broken.json", {"campaign_id": "broken", "status": "COLLECTNG"})
    with pytest.raises(ValueError, match="shadow lifecycle"):
        runner.run(plan, inputs="must-not-read.json", output=out, research_root=root)


def test_changed_implementation_requires_new_registration(package, monkeypatch):
    root, plan, _, out, _ = package
    monkeypatch.setattr(runner, "implementation_binding", lambda: {"changed": "0" * 64})
    with pytest.raises(ValueError, match="Execution code differs"):
        runner.run(plan, inputs="must-not-read.json", output=out, research_root=root)
