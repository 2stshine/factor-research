from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from engine import gate, silver
from engine import null as null_engine
from engine.panel import Panel


def _confirmation_panel() -> Panel:
    months = pd.period_range("2025-12", "2029-01", freq="M")
    frame = pd.DataFrame({
        "asset_id": np.tile([1, 2, 3], len(months)),
        "ym": np.repeat(months, 3),
        "trade_date": np.repeat(
            months.to_timestamp(how="end").normalize(), 3,
        ),
        "in_universe": True,
        "market_cap": np.tile([100.0, 200.0, 300.0], len(months)),
        "adj_close": np.arange(len(months) * 3, dtype=float) + 100.0,
        "total_return_close": np.arange(
            len(months) * 3, dtype=float,
        ) + 100.0,
        "adv20": 1.0,
    })
    return Panel(
        frame,
        pd.Series(dtype="datetime64[ns]"),
        meta=silver.return_role_contract(),
    )


def _stub_gate(monkeypatch, control):
    def evaluate(factor, _panel, frame, **_kwargs):
        if control["fail_after"] == control["calls"]:
            raise RuntimeError("simulated interruption")
        control["calls"] += 1
        signal_mean = float(frame[f"f_{factor.name}"].mean())
        return gate.Result(
            factor=factor.name,
            definition_hash=factor.definition_hash,
            labels=["oos_sealed"],
            metrics={
                "ic_p_investable": .001,
                "ic_investable": signal_mean,
            },
            checks=[gate.Check("T4.3", "다중검정 FDR", None)],
        )

    def evaluate_oos(factor, _panel, _frame, **_kwargs):
        return gate.Result(
            factor=factor.name,
            definition_hash=factor.definition_hash,
            metrics={"oos_ic_p": .001},
            checks=[gate.Check("T4.1", "고정 OOS IC", True)],
        )

    monkeypatch.setattr(gate, "evaluate", evaluate)
    monkeypatch.setattr(gate, "evaluate_oos", evaluate_oos)


def _measure(
    panel,
    *,
    checkpoint_path=None,
    seed=20260731,
    discovery_family_digest="standalone",
    oos_family_digest="standalone",
    oos_family_size=2,
    input_generation_digest="e" * 64,
):
    return null_engine.measure(
        panel,
        n=2,
        seed=seed,
        oos_start=pd.Period("2026-01", freq="M"),
        oos_end=pd.Period("2028-12", freq="M"),
        research_data_cutoff="2025-12-31",
        discovery_family_size=2,
        oos_family_size=oos_family_size,
        discovery_family_digest=discovery_family_digest,
        oos_family_digest=oos_family_digest,
        checkpoint_path=checkpoint_path,
        input_generation_digest=input_generation_digest,
        verbose=False,
    )


def _checkpoint_records(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_null_measure_resumes_without_recomputing_completed_families(
    tmp_path, monkeypatch,
):
    checkpoint = tmp_path / "null-checkpoint.json"
    interrupted_panel = _confirmation_panel()
    control = {"calls": 0, "fail_after": 6}
    _stub_gate(monkeypatch, control)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        _measure(interrupted_panel, checkpoint_path=checkpoint)

    header, *partial = _checkpoint_records(checkpoint)
    durable_prefix = checkpoint.read_bytes()
    assert header["schema_version"] == 2
    assert [
        (entry["kind"], entry["replicate"])
        for entry in partial
    ] == [("random", 0), ("random", 1), ("ar1_095", 0)]
    assert all("row" in entry and "rng_state" in entry for entry in partial)
    assert not any(
        column.startswith(("_raw_null_", "f_null_"))
        for column in interrupted_panel.monthly
    )

    control.update(calls=0, fail_after=None)
    resumed = _measure(interrupted_panel, checkpoint_path=checkpoint)
    # Five remaining families with two definitions each; the first three were
    # loaded from checkpoint and were not evaluated again.
    assert control["calls"] == 10
    assert len(_checkpoint_records(checkpoint)[1:]) == 8
    assert checkpoint.read_bytes().startswith(durable_prefix)
    assert not list(tmp_path.glob(".null-checkpoint.json.*.tmp"))

    control.update(calls=0, fail_after=None)
    uninterrupted = _measure(_confirmation_panel())
    pd.testing.assert_frame_equal(resumed, uninterrupted)


def test_null_measure_rejects_checkpoint_from_different_scope(tmp_path, monkeypatch):
    checkpoint = tmp_path / "null-checkpoint.json"
    control = {"calls": 0, "fail_after": None}
    _stub_gate(monkeypatch, control)
    _measure(_confirmation_panel(), checkpoint_path=checkpoint)

    control["calls"] = 0
    with pytest.raises(ValueError, match="범위 또는 무결성"):
        _measure(
            _confirmation_panel(), checkpoint_path=checkpoint, seed=20260732,
        )
    assert control["calls"] == 0

    records = _checkpoint_records(checkpoint)
    records[1]["row"]["research_data_cutoff"] = "2020-01-31"
    checkpoint.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="무결성"):
        _measure(_confirmation_panel(), checkpoint_path=checkpoint)


def test_null_calculation_cache_rebinds_campaign_family_evidence(
    tmp_path, monkeypatch,
):
    cache_root = tmp_path / "by-calculation"
    control = {"calls": 0, "fail_after": None}
    _stub_gate(monkeypatch, control)
    first = _measure(
        _confirmation_panel(),
        checkpoint_path=cache_root,
        discovery_family_digest="a" * 64,
        oos_family_digest="b" * 64,
    )
    assert control["calls"] == 16
    assert len(list(cache_root.glob("*.jsonl"))) == 1

    control["calls"] = 0
    rebound = _measure(
        _confirmation_panel(),
        checkpoint_path=cache_root,
        discovery_family_digest="c" * 64,
        oos_family_digest="d" * 64,
        oos_family_size=1,
    )
    assert control["calls"] == 0
    assert rebound["discovery_family_digest"].eq("c" * 64).all()
    assert rebound["oos_family_digest"].eq("d" * 64).all()
    assert rebound["oos_family_size"].eq(1).all()
    comparable = [
        column for column in first.columns
        if column not in {
            "discovery_family_digest", "oos_family_digest", "oos_family_size",
        }
    ]
    pd.testing.assert_frame_equal(first[comparable], rebound[comparable])

    control["calls"] = 0
    _measure(
        _confirmation_panel(),
        checkpoint_path=cache_root,
        discovery_family_digest="c" * 64,
        oos_family_digest="d" * 64,
        input_generation_digest="f" * 64,
    )
    assert control["calls"] == 16
    assert len(list(cache_root.glob("*.jsonl"))) == 2


def test_null_checkpoint_discards_only_an_incomplete_final_append(
    tmp_path, monkeypatch,
):
    checkpoint = tmp_path / "null-checkpoint.json"
    control = {"calls": 0, "fail_after": 2}
    _stub_gate(monkeypatch, control)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        _measure(_confirmation_panel(), checkpoint_path=checkpoint)
    with checkpoint.open("ab") as handle:
        handle.write(b'{"torn":')

    control.update(calls=0, fail_after=None)
    resumed = _measure(_confirmation_panel(), checkpoint_path=checkpoint)
    assert len(resumed) == 8
    assert checkpoint.read_bytes().endswith(b"\n")
    assert len(_checkpoint_records(checkpoint)) == 9
