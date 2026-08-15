from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine import epochs, gate, research
from engine.factors import Factor, Registry
from scripts import run as run_script


def _identity(frame):
    return frame["x"]


def _negative(frame):
    return -frame["x"]


def _make_factor(name, compute=_identity):
    return Factor(
        name=name,
        family=name,
        category="other",
        hypothesis=f"{name} 사전등록 가설",
        predicted_sign=1,
        compute=compute,
    )


def test_operational_timing_is_stderr_and_append_log_without_outcome(
    monkeypatch, capsys, tmp_path,
):
    timing_log = tmp_path / "research-timings.jsonl"
    monkeypatch.setenv("RESEARCH_TIMING_LOG", str(timing_log))
    monkeypatch.setattr(run_script.time, "perf_counter", lambda: 12.5)
    run_script._log_timing(
        "parity.sql_query", 10.0, sql="batch.sql", factor_count=5,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    recorded_at = payload.pop("recorded_at")
    assert recorded_at.endswith("+00:00")
    assert payload == {
        "event": "research_timing_v1",
        "factor_count": 5,
        "seconds": 2.5,
        "sql": "batch.sql",
        "stage": "parity.sql_query",
    }
    persisted = json.loads(timing_log.read_text(encoding="utf-8"))
    assert persisted.pop("recorded_at") == recorded_at
    assert persisted == payload


def test_parity_query_windows_are_exact_non_overlapping_month_chunks():
    assert run_script._parity_query_windows("2018-03", "2023-04", 24) == [
        (pd.Period("2018-03", freq="M"), pd.Period("2020-02", freq="M")),
        (pd.Period("2020-03", freq="M"), pd.Period("2022-02", freq="M")),
        (pd.Period("2022-03", freq="M"), pd.Period("2023-04", freq="M")),
    ]
    assert run_script._parity_query_windows("2023-04", "2023-04", None) == [
        (pd.Period("2023-04", freq="M"), pd.Period("2023-04", freq="M"))
    ]


def test_parity_query_windows_reject_invalid_chunk_contract():
    for invalid in (0, -1, True, 1.5, "24"):
        with np.testing.assert_raises(ValueError):
            run_script._parity_query_windows("2018-03", "2023-04", invalid)


def test_database_temp_usage_reads_current_database_counters():
    class Cursor:
        statements = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql):
            self.statements.append(sql)

        def fetchone(self):
            return (7, 8192)

    class Connection:
        def cursor(self):
            return Cursor()

    assert run_script._database_temp_usage(Connection()) == (7, 8192)
    assert Cursor.statements == [
        "SELECT pg_stat_clear_snapshot()",
        (
            "SELECT temp_files, temp_bytes FROM pg_stat_database "
            "WHERE datname = current_database()"
        ),
    ]


def test_sql_chunk_checkpoint_is_atomic_digest_bound_and_resumable(
    monkeypatch, tmp_path,
):
    monkeypatch.setattr(
        run_script, "PARITY_CHECKPOINT_ROOT", tmp_path / "checkpoints",
    )
    binding = {
        "schema_version": run_script._PARITY_CHECKPOINT_SCHEMA,
        "campaign_id": "campaign-test",
        "discovery_snapshot_digest": "a" * 64,
        "sql_path": "implementations/gold/factors/test.sql",
        "sql_sha256": "b" * 64,
        "factor_names": ["factor_a"],
        "manifest_entry_digests": ["c" * 64],
        "query_start_month": "2018-03",
        "query_end_month": "2020-02",
    }
    frame = pd.DataFrame({
        "asset_id": [2, 1],
        "as_of_date": pd.to_datetime(["2018-03-29", "2018-03-29"]),
        "value": [2.5, 1.5],
        "rank": [2, 1],
    })

    data_path, manifest_path = run_script._write_parity_checkpoint(binding, frame)
    loaded = run_script._load_parity_checkpoint(binding)

    pd.testing.assert_frame_equal(loaded, frame)
    assert not list(data_path.parent.glob(".*.tmp"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["result_digest"] == run_script._sql_result_digest(frame)
    data_path.write_bytes(data_path.read_bytes() + b"tamper")
    with pytest.raises(RuntimeError, match="SHA-256"):
        run_script._load_parity_checkpoint(binding)


def test_split_pipeline_assembly_is_exactly_equal_to_legacy_combined_rows():
    legacy = pd.DataFrame({
        "factor": ["accounting_a", "accounting_b", "idio", "idio"],
        "asset_id": [1, 2, 1, 2],
        "as_of_date": pd.to_datetime(["2020-01-31"] * 4),
        "value": [0.5, 2.0, 0.2, 0.4],
        "rank": [1, 1, 1, 2],
    })
    accounting = legacy.loc[legacy["factor"].str.startswith("accounting")]
    idio_chunks = [
        legacy.loc[
            legacy["factor"].eq("idio") & legacy["asset_id"].eq(asset)
        ].drop(columns="factor")
        for asset in (1, 2)
    ]
    rebuilt_idio = pd.concat(idio_chunks, ignore_index=True)
    rebuilt_idio.insert(0, "factor", "idio")
    optimized = pd.concat([accounting, rebuilt_idio], ignore_index=True)
    columns = ["factor", "asset_id", "as_of_date", "value", "rank"]

    pd.testing.assert_frame_equal(
        legacy[columns].sort_values(columns[:3]).reset_index(drop=True),
        optimized[columns].sort_values(columns[:3]).reset_index(drop=True),
        check_exact=True,
    )
    assert run_script._sql_result_digest(legacy) == run_script._sql_result_digest(
        optimized,
    )


def test_confirmation_reuses_exact_discovery_subset_without_factor_recompute():
    factor = _make_factor("candidate")
    source = pd.DataFrame({
        "asset_id": [1, 2, 1, 2],
        "trade_date": pd.to_datetime([
            "2023-04-28", "2023-04-28", "2023-05-31", "2023-05-31",
        ]),
        "f_candidate": [1.5, 2.5, 3.5, 4.5],
    })
    target = source.iloc[[3, 0]].drop(columns="f_candidate").copy()
    panel = SimpleNamespace(monthly=target)
    run_script.research_policy.bind_authoritative_factor_column(
        factor, source, "f_candidate",
    )

    reused = run_script._reuse_factor_columns(source, panel, [factor])

    assert reused["f_candidate"].tolist() == [4.5, 1.5]
    pd.testing.assert_series_equal(
        reused["f_candidate"],
        source.set_index(["asset_id", "trade_date"])["f_candidate"]
        .reindex(pd.MultiIndex.from_frame(target[["asset_id", "trade_date"]]))
        .set_axis(target.index),
    )
    raw = run_script.research_policy.authoritative_factor_values(
        factor, reused, "f_candidate",
    )
    pd.testing.assert_series_equal(raw, reused["f_candidate"])


def test_authoritative_factor_binding_reuses_only_exact_values(monkeypatch):
    factor = _make_factor("candidate")
    frame = pd.DataFrame({
        "asset_id": [1, 2],
        "trade_date": pd.to_datetime(["2023-04-28", "2023-04-28"]),
        "ym": [pd.Period("2023-04", freq="M")] * 2,
        "x": [1.0, 2.0],
        "f_candidate": [1.0, 2.0],
    })
    run_script.research_policy.bind_authoritative_factor_column(
        factor, frame, "f_candidate",
    )

    bound = run_script.research_policy.authoritative_factor_values(
        factor, frame, "f_candidate",
    )
    pd.testing.assert_series_equal(bound, frame["f_candidate"])

    frame.loc[0, "f_candidate"] = 9.0
    assert run_script.research_policy.authoritative_factor_values(
        factor, frame, "f_candidate",
    ) is None


def test_authoritative_binding_preserves_exact_t0_checks_with_one_less_compute(
    monkeypatch,
):
    factor = _make_factor("candidate")
    frame = pd.DataFrame({
        "asset_id": [1, 2],
        "trade_date": pd.to_datetime(["2023-04-28", "2023-04-28"]),
        "ym": [pd.Period("2023-04", freq="M")] * 2,
        "instrument_type": ["common_stock"] * 2,
        "market": ["KOSPI"] * 2,
        "x": [1.0, 2.0],
        "f_candidate": [1.0, 2.0],
    })
    calls = []

    def compute(_factor, values):
        calls.append("compute")
        return values["x"].copy()

    monkeypatch.setattr(run_script.research_policy, "compute_factor", compute)
    monkeypatch.setattr(
        run_script.research_policy,
        "causal_lookback_check",
        lambda _factor, _frame, _reference: (True, "exact anchors"),
    )

    baseline = gate._validate_factor(factor, frame.copy(), "f_candidate")
    assert calls == ["compute", "compute"]

    bound_frame = frame.copy()
    run_script.research_policy.bind_authoritative_factor_column(
        factor, bound_frame, "f_candidate",
    )
    calls.clear()
    optimized = gate._validate_factor(factor, bound_frame, "f_candidate")

    assert calls == ["compute"]
    assert optimized == baseline


def test_parity_computes_local_python_before_opening_live_transaction(
    monkeypatch, tmp_path,
):
    """The bounded SSM/RDS lifetime must exclude local factor computation."""
    from factors import candidate_loader

    events = []
    factor = _make_factor("candidate")
    monthly = pd.DataFrame({
        "asset_id": [1],
        "trade_date": [pd.Timestamp("2023-04-28")],
        "ym": [pd.Period("2023-04", freq="M")],
        "x": [1.0],
    })
    panel = SimpleNamespace(monthly=monthly, meta={})
    research_panel = SimpleNamespace(
        monthly=monthly,
        universe=pd.Series(True, index=monthly.index),
    )
    window = SimpleNamespace(
        discovery_data_cutoff="2023-05-31",
        oos_signal_start="2023-06",
        discovery_signal_end="2023-04",
    )
    campaign = {
        "snapshot": {
            "discovery_input_digest": "a" * 64,
            "discovery_asset_identity_digest": "b" * 64,
        }
    }
    binding = {
        "strategy_sha256": "c" * 64,
        "implementation_uri": "repo://factor-research/test.sql",
        "implementation_sha256": "d" * 64,
    }
    monkeypatch.setattr(run_script, "validate_manifest", lambda *_a, **_k: window)
    monkeypatch.setattr(run_script, "_load", lambda: panel)
    monkeypatch.setattr(run_script, "_scope_discovery_panel", lambda *_a, **_k: panel)
    monkeypatch.setattr(run_script.P, "snapshot_digest", lambda _p: "a" * 64)
    monkeypatch.setattr(
        run_script.P,
        "verify_asset_identity",
        lambda _p: {"asset_identity_digest": "b" * 64},
    )
    monkeypatch.setattr(run_script, "_research_input_panel", lambda _p: research_panel)
    monkeypatch.setitem(
        candidate_loader.RESEARCH_SPECS,
        factor.name,
        {"strategy_sha256": "c" * 64},
    )
    monkeypatch.setattr(
        run_script,
        "_implementation_contract",
        lambda _f: (None, {}, tmp_path / "test.sql", binding),
    )
    monkeypatch.setattr(
        run_script.research_policy,
        "assert_allowed_lookback",
        lambda **_kwargs: None,
    )

    def compute(_factor, frame):
        events.append("python")
        return frame["x"]

    monkeypatch.setattr(run_script.research_policy, "compute_factor", compute)

    class Connection:
        def __enter__(self):
            events.append("connect")
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        run_script.silver, "connect", lambda **_kwargs: Connection(),
    )

    def fail_after_connect(*_args, **_kwargs):
        events.append("live")
        raise OSError("stop before SQL")

    monkeypatch.setattr(
        run_script.silver,
        "verify_live_total_return_contract",
        fail_after_connect,
    )
    monkeypatch.setattr(
        run_script.implementation,
        "failure_evidence",
        lambda factor, **_kwargs: {"factor": factor.name, "passed": False},
    )

    assert run_script.verify_implementations(campaign, [factor]) == [
        {"factor": "candidate", "passed": False}
    ]
    assert events == ["python", "connect", "live"]


def _relationship_frame():
    rows = []
    for month in pd.period_range("2018-03", "2018-05", freq="M"):
        for asset_id in range(40):
            rows.append({
                "asset_id": asset_id,
                "ym": month,
                "instrument_type": "common_stock",
                "market": "KOSPI",
                "x": float(asset_id % 9),
            })
    frame = pd.DataFrame(rows)
    frame["f_target_a"] = frame["x"]
    frame["f_target_b"] = -frame["x"]
    frame["f_other_a"] = frame["x"].where(frame["asset_id"].ne(0))
    frame["f_other_b"] = (frame["asset_id"] % 5).astype(float)
    return frame


def test_batch_relationships_match_single_candidate_contract(monkeypatch):
    frame = _relationship_frame()
    panel = SimpleNamespace(investable=pd.Series(True, index=frame.index))
    registry = Registry()
    factors = [
        _make_factor("target_a"),
        _make_factor("target_b", _negative),
        _make_factor("other_a"),
        _make_factor("other_b"),
    ]
    for factor in factors:
        registry.add(factor)
    monkeypatch.setattr(
        research.research_policy,
        "assert_allowed_lookback",
        lambda **_kwargs: 0,
    )

    expected = {
        factor.name: research.factor_relationships(
            panel, frame, factor, registry,
        )
        for factor in factors[:2]
    }
    monkeypatch.setattr(
        pd.DataFrame,
        "corr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("registry 전체 상관행렬을 계산하면 안 됩니다")
        ),
    )
    actual = research.factor_relationships_batch(
        panel, frame, factors[:2], registry,
    )

    assert actual == expected


def test_batch_relationships_compute_each_registry_signal_once(monkeypatch):
    frame = _relationship_frame().drop(columns=["f_other_a", "f_other_b"])
    panel = SimpleNamespace(investable=pd.Series(True, index=frame.index))
    registry = Registry()
    targets = [_make_factor("target_a"), _make_factor("target_b", _negative)]
    others = [_make_factor("other_a"), _make_factor("other_b", _negative)]
    for factor in [*targets, *others]:
        registry.add(factor)
    monkeypatch.setattr(
        research.research_policy,
        "assert_allowed_lookback",
        lambda **_kwargs: 0,
    )
    calls = []

    def compute_once(factor, source, **_kwargs):
        calls.append(factor.name)
        return factor.compute(source)

    monkeypatch.setattr(research.research_policy, "compute_factor", compute_once)
    output = research.factor_relationships_batch(panel, frame, targets, registry)

    assert calls == ["other_a", "other_b"]
    assert set(output) == {"target_a", "target_b"}


def test_abort_open_campaign_preserves_candidates_and_does_not_use_oos(tmp_path):
    root = tmp_path / "research"
    epochs.start_campaign(
        root,
        "campaign-test",
        discovery_data_cutoff="2023-05-31",
        snapshot_cutoff="2026-06-30",
        snapshot_digest="1" * 64,
        discovery_snapshot_digest="2" * 64,
        snapshot_asset_identity_digest="3" * 64,
        discovery_asset_identity_digest="4" * 64,
        closure_asset_identity_digest="5" * 64,
        closure_asset_identity_cutoff="2026-07-31",
        planned_epoch_count=1,
    )
    factor = _make_factor("candidate")
    epochs.start_epoch(
        root,
        "campaign-test",
        "epoch-001",
        [factor],
        strategy_digests={"candidate": "6" * 64},
    )

    epochs.abort_open_campaign(
        root,
        "campaign-test",
        reason="interrupted before durable result artifact",
    )

    campaign = epochs.load_campaign(root, "campaign-test")
    epoch = epochs.load_epoch(root, "campaign-test", "epoch-001")
    assert campaign["status"] == epochs.ABORTED_CAMPAIGN_STATUS
    assert campaign["oos"]["status"] == "NOT_USED"
    assert campaign["qualified_factors"] == []
    assert epoch["status"] == "ABORTED"
    assert epoch["candidates"][0]["definition_hash"] == factor.definition_hash
    assert epoch["candidates"][0]["status"] == "REGISTERED"


def test_discovery_persistence_writes_trial_ledger_last(monkeypatch, tmp_path):
    from scripts import research as research_script

    events = []
    factor = _make_factor("candidate")
    result = SimpleNamespace(verdict=SimpleNamespace(value="PROVISIONAL"))
    panel = SimpleNamespace(
        monthly=pd.DataFrame({"trade_date": [pd.Timestamp("2023-05-31")]})
    )
    args = SimpleNamespace(campaign="campaign-test", epoch="epoch-001")

    monkeypatch.setitem(
        research_script.RESEARCH_SPECS,
        factor.name,
        {"strategy_sha256": "7" * 64},
    )
    monkeypatch.setattr(
        research_script.research,
        "record_cycle",
        lambda *_args, **_kwargs: (
            events.append("report") or tmp_path / "report.md",
            tmp_path / "latest.md",
        ),
    )
    monkeypatch.setattr(
        research_script.epochs,
        "mark_evaluated",
        lambda *_args, **_kwargs: events.append("epoch"),
    )

    class Ledger:
        def __init__(self, _path):
            pass

        def record(self, *_args, **_kwargs):
            events.append("ledger")

    monkeypatch.setattr(research_script.trials, "TrialLedger", Ledger)
    research_script._persist_discovery_result(
        args, panel, factor, result, [],
    )

    assert events == ["report", "epoch", "ledger"]
