from __future__ import annotations

import sqlite3

import pytest

from engine import gate
from engine import trials
from engine.factors import Factor


def test_read_trial_summary_uses_existing_ledger_in_sqlite_read_only_mode(
    tmp_path, monkeypatch,
):
    path = tmp_path / "ledger with spaces.sqlite3"
    ledger = trials.TrialLedger(path)
    factor = Factor(
        name="readonly_candidate",
        category="other",
        hypothesis="읽기 전용 시행 요약 테스트",
        predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )
    result = gate.Result(
        factor=factor.name,
        definition_hash=factor.definition_hash,
        metrics={"net_ir": .4, "ic_p_investable": .02},
    )
    ledger.record(
        factor, result, data_cutoff="2026-01-31", ruleset_version="scope-a",
    )
    before = path.read_bytes()
    real_connect = sqlite3.connect
    calls = []

    def connect(database, *args, **kwargs):
        calls.append((database, kwargs.copy()))
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(trials.sqlite3, "connect", connect)
    summary = trials.read_trial_summary(
        path,
        current_hashes=("current",),
        external=(("gold", None, .03),),
        ruleset_version="scope-a",
    )

    assert summary.count == 3
    assert summary.ic_count == 3
    assert summary.sharpes == (.4,)
    assert summary.pvalues == (
        (factor.definition_hash, .02),
        ("gold", .03),
    )
    assert len(calls) == 1
    assert calls[0][0].startswith("file:")
    assert calls[0][0].endswith("?mode=ro")
    assert calls[0][1]["uri"] is True
    assert path.read_bytes() == before
    assert not path.with_name(path.name + "-journal").exists()
    assert not path.with_name(path.name + "-wal").exists()


def test_read_trial_summary_never_creates_a_missing_ledger(tmp_path):
    parent = tmp_path / "missing-parent"
    path = parent / "trials.sqlite3"

    with pytest.raises(FileNotFoundError):
        trials.read_trial_summary(path)

    assert not parent.exists()
