"""Synthetic-only preparation/broker fixtures; no market caches, DB or real OOS."""
from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine import panel as P
from engine import research_v2_pilot as pilot
from engine.boundaries import CampaignWindow
from engine.factors import Factor


def synthetic_signal(frame):
    return frame["synthetic_feature"]


def plan():
    return {"schema_version": "research-v2-completion-plan-v1", "plan_id": "synthetic-pilot",
            "pilot_kind": "EXPLICIT_PROTOCOL_REANALYSIS_NOT_NEW_FACTOR_DISCOVERY",
            "selected_definitions": list(pilot.SELECTED), "selection_locked_before_new_performance": True,
            "replacement_on_poor_performance": False}


def boundary(cutoff="2019-07-31"):
    return CampaignWindow.from_completed_snapshot(
        discovery_data_cutoff=cutoff, snapshot_cutoff="2022-08-31", oos_months=36)


def fixture_frame():
    periods = pd.period_range("2015-01", "2022-09", freq="M")
    assets = np.arange(40)
    months = np.repeat(periods, len(assets))
    ids = np.tile(assets, len(periods))
    rng = np.random.default_rng(927)
    dates = pd.PeriodIndex(months).end_time.normalize()
    return pd.DataFrame({"asset_id": ids, "ym": months, "trade_date": dates,
        "in_universe": True, "adj_close": 10., "market_cap": 1e10 + 1e8 * ids,
        "adv20": 1e9 + rng.uniform(0, 1e8, len(months)),
        "market": np.where(ids % 2, "KOSDAQ", "KOSPI"),
        "synthetic_feature": rng.normal(size=len(months)),
        "fwd_mid": rng.normal(scale=.02, size=len(months)),
        "net_income_ttm": 5 + ids + np.arange(len(months)) / 500,
        "total_assets": 1000 + ids,
        "available_date": dates - pd.Timedelta(days=10),
        "unassigned_source_field": "MUST_NOT_REACH_DIAGNOSTIC_FRAME"})


@pytest.fixture
def setup(monkeypatch, tmp_path):
    from scripts import run
    frame = fixture_frame()
    pan = P.Panel(frame, pd.Series(dtype="datetime64[ns]"))
    factors = [Factor(name=name, category="quality", hypothesis="Synthetic adapter fixture only",
        predicted_sign=1, compute=synthetic_signal, needs=("synthetic_feature",)) for name in pilot.SELECTED]
    context = [{"month": str(month), "decision_at": month.end_time.tz_localize("Asia/Seoul").isoformat(),
                "regime": pilot.REGIME_LABELS[i % 4]} for i, month in enumerate(pd.period_range("2016-02", "2019-06", freq="M"))]
    monkeypatch.setattr(pilot, "validate_adoption", lambda value: None)
    monkeypatch.setattr(pilot, "market_rows", lambda value, market: context if market == "KOSPI" else [])
    monkeypatch.setattr(P, "verify_return_roles", lambda panel: {})
    monkeypatch.setattr(P, "verify_asset_identity", lambda panel: {"asset_identity_digest": "a" * 64})
    monkeypatch.setattr(P, "snapshot_digest", lambda panel: "b" * 64 if len(panel.monthly) == len(frame) else "c" * 64)
    calls = []
    output = tmp_path / "pilot"

    def scope(panel, *, data_cutoff, oos_start):
        calls.append("scope")
        assert (output / "frozen-plan.json").is_file()
        frozen = json.loads((output / "frozen-plan.json").read_text())
        assert [item["name"] for item in frozen["definitions"]] == list(pilot.SELECTED)
        cropped = panel.monthly.loc[(panel.monthly.trade_date <= data_cutoff) & (panel.monthly.ym < oos_start)].copy()
        return P.Panel(cropped, panel.dead.copy())

    def inputs(panel):
        calls.append("inputs")
        return panel

    def compute(panel, selected):
        calls.append("compute")
        assert calls[:3] == ["scope", "inputs", "compute"]
        assert panel.monthly.ym.max() < boundary().oos_signal_start
        result = panel.monthly.copy()
        for factor in selected:
            result[f"f_{factor.name}"] = result.synthetic_feature
        return result

    monkeypatch.setattr(run, "_scope_discovery_panel", scope)
    monkeypatch.setattr(run, "_research_input_panel", inputs)
    monkeypatch.setattr(run, "_ensure_factor_columns", compute)
    exposure = tmp_path / "global-exposure-metadata.json"
    exposure.write_text('{"synthetic_prior_trials": 23}')
    kwargs = dict(plan=plan(), regime_contract={"rules_sha256": "d" * 64, "contract_sha256": "e" * 64},
        audit_receipt={"status": "MATCH", "gold_write": False,
            "cache": {"asset_identity_digest": "a" * 64}, "rds": {"asset_identity_digest": "a" * 64},
            "snapshot_sha256": "b" * 64, "source_panel_file_sha256": "f" * 64,
            "total_return_contract": {"synthetic": True}},
        output=output, source_panel_file_sha256="f" * 64, source_label="SYNTHETIC_ONLY",
        exposure_metadata=pilot.exposure_bindings([exposure]), factors=factors)
    return SimpleNamespace(panel=pan, factors=factors, context=context, kwargs=kwargs, output=output, calls=calls)


def prepare(setup, *, window=None):
    return pilot.prepare_pilot(setup.panel, window or boundary(), **setup.kwargs)


def test_prepare_freezes_all_before_compute_and_projects_exact_scope(setup):
    manifest = prepare(setup)
    assert setup.calls == ["scope", "inputs", "compute"]
    assert manifest["factor_admission_trials"] == manifest["oos_reads"] == manifest["gold_writes"] == 0
    assert len(manifest["cases"]) == 6
    frame = pd.read_parquet(setup.output / manifest["cases"][0]["frame_file"])
    assert frame.month.min() == "2016-02" and frame.month.max() == "2019-06"
    assert set(frame.columns) == {"month", "asset_id", "signal", "forward_return", "return_known_at",
        "market", "log_market_cap", "log_adv20", "market_regime", "regime_known_at", "economic_outcome", "economic_known_at"}
    assert frame.return_known_at.eq(pd.Timestamp("2019-07-31 23:59:59.999999999")).all()
    assert frame.groupby("month").market_regime.nunique().eq(1).all()
    assert frame.signal.notna().all()
    broker = pilot.PilotBroker(setup.output)
    assert broker.frozen["prior_exposure_metadata"]["trial_counts_reset"] is False
    assert broker._lab(pilot.SELECTED[0]).public_case()["factor_approval_allowed"] is False
    with pytest.raises(FileExistsError):
        prepare(setup)


def test_actual_availability_and_economic_level_vs_change(setup):
    prepare(setup)
    profit = pd.read_parquet(setup.output / "cases/net_roa/frame.parquet")
    investment = pd.read_parquet(setup.output / "cases/asset_growth_12m/frame.parquet")
    expected = setup.panel.monthly.query("asset_id == 0").set_index("ym")
    future = expected.loc[pd.Period("2017-02")]
    current = expected.loc[pd.Period("2016-02")]
    p = profit.query("month == '2016-02' and asset_id == 0").iloc[0]
    i = investment.query("month == '2016-02' and asset_id == 0").iloc[0]
    assert p.economic_outcome == pytest.approx(future.net_income_ttm / future.total_assets)
    assert i.economic_outcome == pytest.approx(p.economic_outcome - current.net_income_ttm / current.total_assets)
    assert p.economic_known_at == future.available_date
    assert pd.isna(profit.query("month == '2019-06'").iloc[0].economic_outcome)
    assert "economic_outcome" not in pd.read_parquet(setup.output / "cases/price_momentum_6_1/frame.parquet")


def test_exact_day_cutoff_does_not_mature_later_monthend(setup):
    # Trading cutoff before calendar month end cannot certify a full 12-month horizon.
    scoped = setup.panel.monthly.query("trade_date <= '2019-07-31'").copy()
    scoped.loc[scoped.ym.eq(pd.Period("2019-07")), "trade_date"] = pd.Timestamp("2019-07-28")
    for factor in setup.factors:
        scoped[f"f_{factor.name}"] = scoped.synthetic_feature
    result, _, _, _ = pilot._project_case(scoped, pd.Series(True, index=scoped.index), setup.factors[0],
        window=boundary("2019-07-28"), regime_contract=setup.kwargs["regime_contract"])
    assert result.loc[result.month.eq("2018-07"), "economic_outcome"].isna().all()


def test_stale_or_future_filing_outcomes_remain_missing(setup):
    source = setup.panel.monthly
    source.loc[(source.ym == pd.Period("2017-02")) & (source.asset_id == 0), "available_date"] = pd.Timestamp("2016-01-01")
    source.loc[(source.ym == pd.Period("2017-02")) & (source.asset_id == 1), "available_date"] = pd.Timestamp("2017-03-01")
    prepare(setup)
    result = pd.read_parquet(setup.output / "cases/net_roa/frame.parquet")
    assert result.loc[result.month.eq("2016-02") & result.asset_id.isin([0, 1]), "economic_outcome"].isna().all()


def test_missing_input_case_is_kept_not_replaced(setup):
    from dataclasses import replace
    setup.kwargs["factors"] = [replace(f, needs=("absent_fixture_input",)) if i == 0 else f for i, f in enumerate(setup.factors)]
    manifest = prepare(setup)
    assert manifest["cases"][0]["status"] == "NOT_COMPUTED"
    assert manifest["cases"][0]["missing_inputs"] == ["absent_fixture_input"]
    assert len(manifest["cases"]) == 6


@pytest.mark.parametrize("field", ["snapshot_sha256", "source_panel_file_sha256", "status", "identity", "plan"])
def test_receipt_and_selection_fail_before_outputs(setup, field):
    if field == "identity":
        setup.kwargs["audit_receipt"]["rds"]["asset_identity_digest"] = "0" * 64
    elif field == "plan":
        setup.kwargs["plan"]["selected_definitions"] = list(reversed(pilot.SELECTED))
    else:
        setup.kwargs["audit_receipt"][field] = "invalid"
    with pytest.raises(ValueError):
        prepare(setup)
    assert not setup.output.exists() and not setup.calls


def test_fixed_collects_all_six_but_never_authors_stop(setup):
    prepare(setup)
    broker = pilot.PilotBroker(setup.output)
    result = broker.collect_fixed("net_roa")
    assert result["state"]["state"] == "ACTIVE"
    assert result["state"]["actions_used"] == 6
    assert [e["diagnostic_id"] for e in result["state"]["evidence"]] == list(pilot.FIXED_ORDER)
    assert "INDEPENDENT_LLM" in result["collection_status"]
    assert not broker.export("net_roa", "FIXED_REFERENCE")["live_model_interpretation_certified"]
    assert broker.collect_fixed("net_roa")["state"]["actions_used"] == 6
    host = broker.init_session("net_roa", "HOST_LLM")
    assert host["state"]["actions_used"] == 0 and not host["state"]["evidence"]


def test_host_packet_act_roundtrip_and_hash_bound_export(setup):
    prepare(setup)
    broker = pilot.PilotBroker(setup.output)
    broker.init_session("net_roa", "HOST_LLM")
    packet = broker.packet("net_roa", "HOST_LLM")
    action = {"kind": "TEST", "reason": "Synthetic boundary audit first", "evidence_ids": [], "payload": {
        "diagnostic_id": "input_audit", "rivals": [
            {"explanation": "Usable input", "expected_if_true": "Available observations"},
            {"explanation": "Missing input", "expected_if_true": "Explicit missingness"}],
        "changes_mind_if": "Missing coverage limits interpretation"}}
    receipt = broker.act("net_roa", "HOST_LLM", action, request_id="fixture-audit", expected_revision=packet["state"]["revision"])
    assert receipt["status"] == "OBSERVED"
    assert broker.act("net_roa", "HOST_LLM", action, request_id="fixture-audit", expected_revision=0) == receipt
    exported = broker.export("net_roa", "HOST_LLM")
    assert exported["pilot_manifest_sha256"] == broker.manifest["manifest_sha256"]
    assert any(event["type"] == "PROMPT" for event in exported["events"])


@pytest.mark.parametrize("target", ["frame", "contract", "frozen", "manifest", "regime"])
def test_frozen_artifact_tamper_is_rejected(setup, target):
    manifest = prepare(setup)
    targets = {"frame": manifest["cases"][0]["frame_file"], "contract": manifest["cases"][0]["contract_file"],
               "frozen": "frozen-plan.json", "manifest": "manifest.json", "regime": "regime-contract.json"}
    path = setup.output / targets[target]
    if target == "manifest":
        payload = json.loads(path.read_text())
        payload["gold_writes"] = 1
        path.write_text(json.dumps(payload))
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        pilot.PilotBroker(setup.output)._lab("net_roa")


def test_path_traversal_unknown_case_and_code_drift_fail(setup, monkeypatch):
    prepare(setup)
    broker = pilot.PilotBroker(setup.output)
    with pytest.raises(ValueError):
        broker._path("../outside")
    with pytest.raises(ValueError):
        broker.init_session("../unknown", "HOST_LLM")
    monkeypatch.setattr(pilot, "_code_bindings", lambda: {"changed": "0" * 64})
    with pytest.raises(ValueError, match="code changed"):
        pilot.PilotBroker(setup.output)


def closed_synthetic_session(setup):
    """Actually close a synthetic fixture through the ordinary audited runtime."""
    prepare(setup)
    broker = pilot.PilotBroker(setup.output)
    broker.init_session("net_roa", "HOST_LLM")
    packet = broker.packet("net_roa", "HOST_LLM")
    action = {"kind": "TEST", "reason": "Synthetic archive regression fixture", "evidence_ids": [], "payload": {
        "diagnostic_id": "input_audit", "rivals": [
            {"explanation": "Usable input", "expected_if_true": "Available observations"},
            {"explanation": "Missing input", "expected_if_true": "Explicit missingness"}],
        "changes_mind_if": "Missing coverage limits interpretation"}}
    broker.act("net_roa", "HOST_LLM", action, request_id="archive-audit", expected_revision=packet["state"]["revision"])
    packet = broker.packet("net_roa", "HOST_LLM")
    ids = [item["evidence_id"] for item in packet["state"]["evidence"]]
    action = {"kind": "STOP", "reason": "Close synthetic archive fixture", "evidence_ids": ids,
              "payload": {"conclusion": "INCONCLUSIVE", "observations": [{"statement": "Input was audited.", "evidence_ids": ids}],
                          "unresolved": ["Other diagnostics were not run."], "limitations": "Synthetic fixture, not real evidence.",
                          "mechanism_identified": False}}
    assert broker.act("net_roa", "HOST_LLM", action, request_id="archive-stop",
                      expected_revision=packet["state"]["revision"])["status"] == "STOPPED"
    return broker.export("net_roa", "HOST_LLM")


def test_archive_exports_closed_original_after_code_drift_without_frames_or_writes(setup, monkeypatch):
    original = closed_synthetic_session(setup)
    before = {str(path.relative_to(setup.output)): pilot._sha_file(path)
              for path in setup.output.rglob("*") if path.is_file()}
    monkeypatch.setattr(pilot, "_code_bindings", lambda: {"changed": "0" * 64})
    with pytest.raises(ValueError, match="code changed"):
        pilot.PilotBroker(setup.output)
    def forbidden(*args, **kwargs):
        raise AssertionError("Read-only export must not load frames or instantiate a diagnostic lab")
    monkeypatch.setattr(pilot.pd, "read_parquet", forbidden)
    monkeypatch.setattr(pilot, "RealDiagnosticLab", forbidden)
    archive = pilot.PilotBroker(setup.output, read_only=True)
    assert archive.export("net_roa", "HOST_LLM") == original
    session = archive._session("net_roa", "HOST_LLM")
    import sqlite3
    with session._connect() as db:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            db.execute("DELETE FROM events")
    after = {str(path.relative_to(setup.output)): pilot._sha_file(path)
             for path in setup.output.rglob("*") if path.is_file()}
    assert after == before


@pytest.mark.parametrize("operation", ["packet", "act", "init_session", "collect_fixed", "_lab", "session_request"])
def test_archive_cannot_resume_mutate_or_compute(setup, operation):
    closed_synthetic_session(setup)
    archive = pilot.PilotBroker(setup.output, read_only=True)
    with pytest.raises(ValueError, match="closed export only"):
        if operation == "act":
            archive.act("net_roa", "HOST_LLM", {}, request_id="forbidden", expected_revision=0)
        elif operation in {"collect_fixed", "_lab"}:
            getattr(archive, operation)("net_roa")
        elif operation == "session_request":
            archive._session("net_roa", "HOST_LLM").request()
        else:
            getattr(archive, operation)("net_roa", "HOST_LLM")


def test_archive_rejects_open_or_missing_session_and_tampered_audit(setup):
    prepare(setup)
    normal = pilot.PilotBroker(setup.output)
    normal.init_session("net_roa", "HOST_LLM")
    archive = pilot.PilotBroker(setup.output, read_only=True)
    with pytest.raises(ValueError, match="already STOPPED"):
        archive.export("net_roa", "HOST_LLM")
    with pytest.raises(FileNotFoundError):
        archive.export("operating_roa", "HOST_LLM")
    assert not (setup.output / "sessions/HOST_LLM/operating_roa.sqlite").exists()
    import sqlite3
    with sqlite3.connect(setup.output / "sessions/HOST_LLM/net_roa.sqlite") as db:
        db.execute("UPDATE events SET sha = 'tampered' WHERE revision = 0")
    with pytest.raises(ValueError, match="Audit chain"):
        archive.export("net_roa", "HOST_LLM")


@pytest.mark.parametrize("target", ["frame", "contract", "frozen", "manifest", "regime"])
def test_archive_still_verifies_all_frozen_artifacts(setup, target):
    closed_synthetic_session(setup)
    manifest = json.loads((setup.output / "manifest.json").read_text())
    targets = {"frame": manifest["cases"][0]["frame_file"], "contract": manifest["cases"][0]["contract_file"],
               "frozen": "frozen-plan.json", "manifest": "manifest.json", "regime": "regime-contract.json"}
    path = setup.output / targets[target]
    path.write_bytes(path.read_bytes() + (b"tampered" if target == "manifest" else b"\n"))
    with pytest.raises(ValueError):
        pilot.PilotBroker(setup.output, read_only=True)


def test_public_exporter_explicitly_uses_read_only_archive(monkeypatch, tmp_path):
    from scripts import export_research_v2
    seen = []
    def capture(root, *, read_only=False):
        seen.append(read_only)
        raise RuntimeError("SYNTHETIC_STOP_BEFORE_ANY_REAL_ARTIFACT_READ")
    monkeypatch.setattr(export_research_v2, "PilotBroker", capture)
    with pytest.raises(RuntimeError, match="SYNTHETIC_STOP"):
        export_research_v2.build_summary(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path)
    assert seen == [True]


def test_exposure_binding_is_hash_only_and_nonempty(tmp_path):
    file = tmp_path / "metadata"
    file.write_bytes(b"opaque-non-json-trial-metadata")
    binding = pilot.exposure_bindings([file])
    assert not binding["payloads_parsed"] and not binding["trial_counts_reset"]
    assert binding["files"][0]["sha256"] == pilot._sha_file(file)
    with pytest.raises(ValueError):
        pilot.exposure_bindings([])


def test_cli_help_does_not_load_market_data(monkeypatch, capsys):
    from scripts import research_v2
    with pytest.raises(SystemExit) as caught:
        research_v2.main(["--help"])
    assert caught.value.code == 0
    assert "prepare" in capsys.readouterr().out


def compiled_factor(tmp_path, suffix=None):
    import linecache
    source = "def compute(frame):\n    return frame['synthetic_feature']\n"
    physical = tmp_path / "fixture_factor.py"
    physical.write_text(source)
    digest = pilot._sha_file(physical)
    virtual = f"{physical}#sha256={suffix if suffix is not None else digest}"
    namespace = {}
    linecache.cache[virtual] = (len(source), None, source.splitlines(keepends=True), virtual)
    exec(compile(source, virtual, "exec"), namespace)
    factor = Factor(name="net_roa", category="quality", hypothesis="Compiled filename regression only",
                    predicted_sign=1, compute=namespace["compute"])
    return factor, physical, digest


def test_content_addressed_compiled_factor_resolves_and_binds_physical_bytes(tmp_path):
    factor, physical, digest = compiled_factor(tmp_path)
    identity = pilot.definition_identity(factor)
    assert identity["source_file"] == str(physical.resolve())
    assert identity["source_file_sha256"] == digest
    assert "def compute(frame):" in identity["source"]
    assert identity == pilot.definition_identity(factor)


@pytest.mark.parametrize("suffix", ["0" * 64, "short", "A" * 64, "0" * 64 + "#extra"])
def test_content_addressed_factor_never_silently_strips_unchecked_suffix(tmp_path, suffix):
    factor, _, _ = compiled_factor(tmp_path, suffix)
    with pytest.raises(ValueError, match="(hash no longer matches|Malformed)"):
        pilot.definition_identity(factor)


def test_compiled_factor_disk_drift_is_rejected(tmp_path):
    factor, physical, _ = compiled_factor(tmp_path)
    physical.write_text(physical.read_text() + "# changed after compile\n")
    with pytest.raises(ValueError, match="hash no longer matches"):
        pilot.definition_identity(factor)
