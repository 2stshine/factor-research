"""Mock-only confirmation/publication separation; no research artifacts or DB."""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pandas as pd
import pytest

from scripts import research as cli


@pytest.mark.parametrize("no_publish", [True, False])
def test_cli_passes_publication_choice_to_reveal(monkeypatch, no_publish):
    callback = Mock()
    argv = ["research.py", "campaign-reveal", "--campaign", "synthetic-campaign"]
    if no_publish:
        argv.append("--no-publish")
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(cli, "cmd_campaign_reveal", callback)

    cli.main()

    callback.assert_called_once()
    parsed = callback.call_args.args[0]
    assert parsed.campaign == "synthetic-campaign"
    assert parsed.no_publish is no_publish


@pytest.fixture
def reveal_flow(monkeypatch):
    factor = SimpleNamespace(name="synthetic_candidate", definition_hash="1" * 16)
    strategy_sha = "2" * 64
    panel = SimpleNamespace(monthly=pd.DataFrame({
        "trade_date": [pd.Timestamp("2022-03-31")],
    }))
    snapshot = object()
    bindings = [{"factor": factor.name, "implementation_sha256": "3" * 64}]
    campaign = {
        "qualified_factors": [{
            "name": factor.name,
            "definition_hash": factor.definition_hash,
            "strategy_sha256": strategy_sha,
        }],
        "snapshot": {
            "data_cutoff": "2021-12-31",
            "asset_identity_digest": "4" * 64,
            "discovery_input_digest": "5" * 64,
            "discovery_asset_identity_digest": "6" * 64,
            "closure_asset_identity_digest": "7" * 64,
        },
        "discovery": {"data_cutoff": "2018-12-31"},
        "oos": {
            "start": "2019-01", "signal_end": "2021-12",
            "mode": "HISTORICAL_HOLDOUT",
        },
        "discovery_family_size": 4,
        "discovery_family_digest": "8" * 64,
        "oos_family_digest": "9" * 64,
        "qualification_policy": "synthetic-frozen-policy",
        "input_generation": {"generation_id": "synthetic-generation"},
    }
    discovery = {"definition_hash": factor.definition_hash, "frozen": True}
    result = SimpleNamespace(verdict=SimpleNamespace(value="PROMOTE"))
    serialized = {"synthetic": True}
    publication = {"status": "PUBLISHED", "published_factors": [factor.name]}
    events = []

    def tracked(name, return_value):
        def invoke(*args, **kwargs):
            events.append(name)
            return return_value
        return Mock(side_effect=invoke)

    mocks = {
        "registry": tracked("registry", None),
        "load": tracked("load", panel),
        "bindings": tracked("bindings", bindings),
        "scope": tracked("scope", snapshot),
        "digest": tracked("digest", "a" * 64),
        "identity": tracked("identity", {
            "asset_identity_digest": campaign["snapshot"]["asset_identity_digest"],
        }),
        "ready": tracked("ready", campaign),
        "evaluate": tracked("evaluate", (None, None, [factor], [result])),
        "serialize": tracked("serialize", serialized),
        "record": tracked("record", (Path("synthetic-report.md"), {"closed": True})),
        "memory": tracked("memory", Path("synthetic-memory.md")),
        "publish": tracked("publish", publication),
        "record_publication": tracked("record_publication", Path("synthetic-publication.json")),
        "context": tracked("context", Path("synthetic-context.md")),
    }
    monkeypatch.setattr(cli.F, "REGISTRY", {factor.name: factor})
    monkeypatch.setattr(cli, "RESEARCH_SPECS", {
        factor.name: {"strategy_sha256": strategy_sha},
    })
    monkeypatch.setattr(cli.run, "load_registry", mocks["registry"])
    monkeypatch.setattr(cli.run, "_load", mocks["load"])
    monkeypatch.setattr(cli.run, "_implementation_bindings", mocks["bindings"])
    monkeypatch.setattr(cli.run, "_scope_snapshot_panel", mocks["scope"])
    monkeypatch.setattr(cli.P, "snapshot_digest", mocks["digest"])
    monkeypatch.setattr(cli.P, "verify_asset_identity", mocks["identity"])
    monkeypatch.setattr(cli.epochs, "load_campaign", Mock(return_value=campaign))
    monkeypatch.setattr(cli.epochs, "load_discovery_multiple_testing", Mock(
        return_value={"results": [discovery]},
    ))
    monkeypatch.setattr(cli.epochs, "assert_reveal_ready", mocks["ready"])
    monkeypatch.setattr(cli.run, "_evaluate", mocks["evaluate"])
    monkeypatch.setattr(cli.research, "serialize_result", mocks["serialize"])
    monkeypatch.setattr(cli.epochs, "record_reveal", mocks["record"])
    monkeypatch.setattr(cli, "_refresh_research_memory", mocks["memory"])
    monkeypatch.setattr(cli.run, "publish_revealed_campaign", mocks["publish"])
    monkeypatch.setattr(cli.epochs, "record_gold_publication", mocks["record_publication"])
    monkeypatch.setattr(cli.research, "write_context", mocks["context"])
    monkeypatch.setattr(cli.silver, "connect", Mock(
        side_effect=AssertionError("Mock regression tests must not connect to a DB"),
    ))
    return SimpleNamespace(
        factor=factor, panel=panel, snapshot=snapshot, bindings=bindings,
        campaign=campaign, discovery=discovery, serialized=serialized,
        publication=publication, mocks=mocks, events=events,
    )


@pytest.mark.parametrize("no_publish", [True, False, None], ids=[
    "confirmation-only", "explicit-default", "legacy-namespace",
])
def test_publication_flag_preserves_frozen_confirmation_and_bookkeeping(reveal_flow, no_publish):
    flow = reveal_flow
    args = argparse.Namespace(campaign="synthetic-campaign")
    if no_publish is not None:
        args.no_publish = no_publish

    cli.cmd_campaign_reveal(args)

    flow.mocks["bindings"].assert_called_once_with([flow.factor])
    flow.mocks["scope"].assert_called_once_with(flow.panel, snapshot_cutoff="2021-12-31")
    flow.mocks["digest"].assert_called_once_with(flow.snapshot)
    flow.mocks["identity"].assert_called_once_with(flow.snapshot)
    flow.mocks["ready"].assert_called_once_with(
        "research", args.campaign, pd.Timestamp("2022-03-31"),
        snapshot_digest="a" * 64, current_bindings=flow.bindings,
    )
    flow.mocks["evaluate"].assert_called_once()
    evaluation = flow.mocks["evaluate"].call_args
    assert vars(evaluation.args[0]) == {"factor": None}
    assert evaluation.kwargs == {
        "phase": "full",
        "oos_start": "2019-01", "oos_end": "2021-12",
        "data_cutoff": "2018-12-31",
        "factor_names": [flow.factor.name],
        "calibration_scope": {
            "discovery_family_size": 4, "oos_family_size": 1,
            "discovery_family_digest": "8" * 64,
            "oos_family_digest": "9" * 64,
            "research_data_cutoff": "2018-12-31",
            "qualification_policy": "synthetic-frozen-policy",
        },
        "frozen_discovery": {flow.factor.definition_hash: flow.discovery},
        "discovery_snapshot_digest": "5" * 64,
        "discovery_asset_identity_digest": "6" * 64,
        "snapshot_asset_identity_digest": "4" * 64,
        "closure_asset_identity_digest": "7" * 64,
        "confirmation_mode": "HISTORICAL_HOLDOUT",
        "preloaded_panel": flow.panel,
        "input_generation": flow.campaign["input_generation"],
    }
    flow.mocks["record"].assert_called_once_with(
        "research", args.campaign, [{
            "factor": flow.factor.name,
            "definition_hash": flow.factor.definition_hash,
            "strategy_sha256": "2" * 64,
            "verdict": "PROMOTE",
            "evaluation": flow.serialized,
        }],
        panel_as_of=pd.Timestamp("2022-03-31"),
        snapshot_digest="a" * 64, current_bindings=flow.bindings,
    )
    flow.mocks["memory"].assert_called_once_with()
    flow.mocks["context"].assert_called_once_with(flow.panel, cli.F.REGISTRY)
    expected = ["registry", "load", "bindings", "scope", "digest", "identity",
                "ready", "evaluate", "serialize", "record", "memory"]
    if no_publish:
        flow.mocks["publish"].assert_not_called()
        flow.mocks["record_publication"].assert_not_called()
    else:
        flow.mocks["publish"].assert_called_once_with(args.campaign, flow.panel)
        flow.mocks["record_publication"].assert_called_once_with(
            "research", args.campaign, flow.publication,
        )
        expected += ["publish", "record_publication"]
    assert flow.events == expected + ["context"]


@pytest.mark.parametrize("no_publish", [True, False])
@pytest.mark.parametrize("guard", ["definition", "strategy", "identity", "readiness", "null"])
def test_publication_flag_cannot_bypass_frozen_identity_readiness_or_null_guards(
    reveal_flow, no_publish, guard,
):
    flow = reveal_flow
    if guard == "definition":
        flow.campaign["qualified_factors"][0]["definition_hash"] = "b" * 16
    elif guard == "strategy":
        flow.campaign["qualified_factors"][0]["strategy_sha256"] = "b" * 64
    elif guard == "identity":
        flow.mocks["identity"].side_effect = None
        flow.mocks["identity"].return_value = {"asset_identity_digest": "b" * 64}
    elif guard == "readiness":
        flow.mocks["ready"].side_effect = ValueError("synthetic readiness failure")
    else:
        flow.mocks["evaluate"].side_effect = SystemExit("synthetic null calibration failure")

    with pytest.raises(SystemExit):
        cli.cmd_campaign_reveal(argparse.Namespace(
            campaign="synthetic-campaign", no_publish=no_publish,
        ))

    for name in ("record", "memory", "publish", "record_publication", "context"):
        flow.mocks[name].assert_not_called()
    if guard == "null":
        flow.mocks["ready"].assert_called_once()
        flow.mocks["evaluate"].assert_called_once()
    else:
        flow.mocks["evaluate"].assert_not_called()


@pytest.mark.parametrize("no_publish", [True, False])
def test_reveal_record_failure_never_publishes_or_refreshes_memory(reveal_flow, no_publish):
    flow = reveal_flow
    flow.mocks["record"].side_effect = ValueError("synthetic reveal already consumed")

    with pytest.raises(SystemExit, match="synthetic reveal already consumed"):
        cli.cmd_campaign_reveal(argparse.Namespace(
            campaign="synthetic-campaign", no_publish=no_publish,
        ))

    flow.mocks["evaluate"].assert_called_once()
    flow.mocks["record"].assert_called_once()
    for name in ("memory", "publish", "record_publication", "context"):
        flow.mocks[name].assert_not_called()
