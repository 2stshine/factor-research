from copy import deepcopy
import json

import pandas as pd
import pytest

from engine.korea_macro_direction import PARENTS, classify
from engine.regime_inputs import read_context, freeze_context
from scripts.build_assumed_fmp_regimes import save
from scripts.build_korea_macro_direction import build
from tests.test_assumed_regime_inputs import accept, policy


def snapshots(values):
    return [{"month": str(m), "known_at": m.end_time.floor("s").isoformat(),
             "selected_available_at_assumed": m.start_time.tz_localize("Asia/Seoul").isoformat(),
             "selected_observation_ids": [f"release-{i}"], "value": v,
             "latest_provider_dates": [str(m.start_time.date())], "state": "UNKNOWN"}
            for i, (m, v) in enumerate(zip(pd.period_range("2025-01", periods=len(values), freq="M"), values))]


def run(g, i, as_of="2025-07-01"):
    return classify(g, i, start_month="2025-01", as_of=as_of)


@pytest.mark.parametrize("g,i,expected", [(1, -1, "PRODUCTION_UP_INFLATION_DOWN"),
    (1, 1, "PRODUCTION_UP_INFLATION_UP"), (-1, 1, "PRODUCTION_DOWN_INFLATION_UP"),
    (-1, -1, "PRODUCTION_DOWN_INFLATION_DOWN"), (0, 1, "NEUTRAL")])
def test_fixed_six_snapshots_not_parent_level_state(g, i, expected):
    rows = run(snapshots([g*x for x in range(6)]), snapshots([i*x for x in range(6)]))
    assert all(r["state"] == "UNKNOWN" for r in rows[:5])
    assert rows[-1]["state"] == expected
    assert rows[-1]["directions"] == {"production": 3*g, "inflation": 3*i}
    assert rows[-1]["effective_month"] == "2025-07"


@pytest.mark.parametrize("problem", ["gap", "null", "stale", "future_release", "late_snapshot", "boolean", "infinite", "no_ids"])
def test_unknown_when_a_window_member_invalid(problem):
    g = snapshots(list(range(6)))
    if problem == "gap":
        g.pop(2)
    elif problem == "null":
        g[2]["value"] = None
    elif problem == "stale":
        g[2]["selected_available_at_assumed"] = "2024-11-01T00:00:00+09:00"
    elif problem == "future_release":
        g[2]["selected_available_at_assumed"] = "2025-04-01T00:00:00+09:00"
    elif problem == "late_snapshot":
        g[2]["known_at"] = "2025-04-01T00:00:00"
    elif problem == "boolean":
        g[2]["value"] = True
    elif problem == "infinite":
        g[2]["value"] = float("inf")
    else:
        g[2]["selected_observation_ids"] = []
    assert run(g, snapshots(list(range(6))))[-1]["state"] == "UNKNOWN"


def test_append_future_cannot_change_past_and_partial_month_omitted():
    old = snapshots(list(range(6)))
    future = snapshots(list(range(6)) + [-999999])
    assert run(old, old) == run(future, future)
    assert run(future, future, "2025-07-20") == run(old, old)
    assert run(future, future, "2025-08-01")[:6] == run(old, old)


def test_repeat_release_preserved_without_invented_reference_month():
    g = snapshots(list(range(6)))
    g[1].update(value=0, selected_observation_ids=g[0]["selected_observation_ids"],
                selected_available_at_assumed=g[0]["selected_available_at_assumed"])
    last = run(g, snapshots(list(range(6))))[-1]
    assert last["inputs"]["production"]["reused_snapshot_count"] == 1
    assert all(s["statistical_reference_period"] is None for s in last["inputs"]["production"]["snapshots"])


def test_duplicate_snapshot_rejected():
    g = snapshots(list(range(6)))
    with pytest.raises(ValueError, match="Duplicate"):
        run([*g, g[0]], g)


def test_build_acceptance_is_additive_frozen_and_not_verified(tmp_path):
    contexts = []
    for name, cid in PARENTS.items():
        source = {"context_id": cid, "source_id": name, "kind": "macro_state",
                  "macro_type": "assumed_macro", "pit_status": "PIT_ASSUMED",
                  "known_at_semantics": "ASSUMED_HISTORICAL_AVAILABILITY",
                  "scope": {"start_month": "2025-01", "end_month": "2025-06"},
                  "assumptions": ["Synthetic"], "normalized_sha256": "a"*64,
                  "rows": snapshots(list(range(6)))}
        approval = accept(source)
        sha = save(tmp_path / f"{name}.json", approval)
        contexts.append({"source": source, "approval_file": f"{name}.json", "approval_sha256": sha})
    parent = tmp_path / "parent.json"
    save(parent, {"schema_version": "diagnostic-regime-input-v1", "contexts": contexts})
    save(tmp_path / "policy.json", policy())
    original = parent.read_bytes()
    summary = build(parent, tmp_path / "policy.json", tmp_path / "new", as_of="2025-09-23")
    assert summary["latest_month"] == "2025-06"  # cannot exceed accepted parents
    assert summary["first_classified_month"] == "2025-06"
    item = read_context(tmp_path / "new/context.json")["contexts"][0]
    assert not item["approval"]["pit_approved"]
    assert not item["approval"]["intraday_allowed"]
    assert item["source"]["parent_lineage"]["parents"]["production"]["source_sha256"]
    assert parent.read_bytes() == original
    frozen = freeze_context(read_context(tmp_path / "new/context.json"),
                            data_cutoff="2025-07-31", oos_start="2025-08")
    assert frozen["contexts"][0]["context_id"] == "KR_PRODUCTION_INFLATION_DIRECTION"
    assert frozen["contexts"][0]["rows"][-1]["month"] == "2025-06"
    with pytest.raises(FileExistsError):
        build(parent, tmp_path / "policy.json", tmp_path / "new", as_of="2025-09-23")
