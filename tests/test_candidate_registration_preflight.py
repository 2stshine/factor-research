"""Input failures must stop before expensive authenticated Gold reads."""
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import gate, research_policy
from engine.factors import Factor
from scripts import run


def _setup(monkeypatch, *, coverage=.7, monthly_p10=.5):
    factor = Factor(
        name="coverage_probe", category="other", hypothesis="coverage only",
        predicted_sign=1, compute=lambda frame: frame["input"],
    )
    frame = pd.DataFrame({
        "ym": pd.period_range("2019-01", periods=2, freq="M"),
        "f_coverage_probe": [1., 2.],
    })
    mask = pd.Series(True, index=frame.index)
    panel = SimpleNamespace(investable=mask)
    digest = "a" * 64
    campaign = {"input_generation": {"generation_digest": "b" * 64}}
    artifact = research_policy.input_feasibility_artifact(
        [factor], snapshot_digest=digest,
        signal_start=str(gate.RESEARCH_START), signal_end="2023-05",
        metrics={factor.name: {"coverage": coverage,
                               "monthly_coverage_p10": monthly_p10}},
        minimum_coverage=gate.TH["coverage"],
        minimum_monthly_p10=gate.TH["monthly_coverage_p10"],
    )
    monkeypatch.setattr(run, "_candidate_preflight_frame", lambda *_: (
        panel, panel, frame, mask, digest, pd.Period("2023-05", freq="M"),
    ))
    monkeypatch.setattr(run, "_candidate_input_feasibility", lambda *_, **__: artifact)
    return campaign, panel, factor, artifact, frame


@pytest.mark.parametrize("coverage,monthly_p10", [(.49, .5), (.665, 0.)])
def test_failed_input_skips_connection_and_gold(monkeypatch, coverage, monthly_p10):
    campaign, panel, factor, _, _ = _setup(
        monkeypatch, coverage=coverage, monthly_p10=monthly_p10,
    )

    def forbidden(*_, **__):
        pytest.fail("Failed input feasibility must not access RDS or Gold")

    monkeypatch.setattr(run.silver, "connect", forbidden)
    monkeypatch.setattr(run, "_approved_signals", forbidden)
    with pytest.raises(ValueError, match="입력 커버리지 사전검사 실패"):
        run.preflight_candidate_registration(campaign, panel, [factor])


def test_corrupt_input_artifact_skips_connection(monkeypatch):
    campaign, panel, factor, artifact, _ = _setup(monkeypatch)
    artifact["snapshot_digest"] = "c" * 64
    monkeypatch.setattr(run.silver, "connect", lambda **_: pytest.fail("RDS accessed"))
    with pytest.raises(ValueError, match="artifact가 손상"):
        run.preflight_candidate_registration(campaign, panel, [factor])


def test_passing_input_preserves_live_identity_and_gold_checks(monkeypatch):
    campaign, panel, factor, artifact, frame = _setup(monkeypatch)
    calls = []
    connection = object()

    class ConnectionContext:
        def __enter__(self):
            calls.append("connect")
            return connection

        def __exit__(self, *_):
            calls.append("close")

    def connect(*, read_only):
        assert read_only is True
        return ConnectionContext()

    def verify(conn, generation):
        assert conn is connection
        assert generation == campaign["input_generation"]
        calls.append("identity")

    def approved(conn, observed_frame):
        assert conn is connection
        assert observed_frame is frame
        calls.append("gold")
        return {}

    monkeypatch.setattr(run.silver, "connect", connect)
    monkeypatch.setattr(run.silver, "verify_live_research_generation", verify)
    monkeypatch.setattr(run, "_approved_signals", approved)
    feasibility, gold = run.preflight_candidate_registration(campaign, panel, [factor])
    assert feasibility == artifact
    assert calls == ["connect", "identity", "gold", "close"]
    research_policy.assert_gold_signal_preflight_artifact(
        gold, [factor], snapshot_digest=artifact["snapshot_digest"],
        threshold=gate.TH["max_gold_corr"],
        minimum_comparison_months=gate.TH["min_gold_corr_months"],
    )


@pytest.mark.parametrize("coverage,expected", [(.7, "PASS"), (.1, "FAIL")])
def test_input_check_cli_reports_without_registration_or_live_access(monkeypatch, capsys, coverage, expected):
    import json
    from scripts import research as cli

    campaign, panel, factor, artifact, _ = _setup(monkeypatch, coverage=coverage)
    campaign["snapshot"] = {"discovery_input_digest": artifact["snapshot_digest"]}
    monkeypatch.setattr(run, "load_registry", lambda: None)
    monkeypatch.setattr(cli.F, "REGISTRY", {factor.name: factor})
    monkeypatch.setattr(cli.epochs, "load_campaign", lambda *_: campaign)
    monkeypatch.setattr(run, "_load", lambda: panel)
    monkeypatch.setattr(run, "preflight_candidate_inputs", lambda *_: artifact)

    def forbidden(*_, **__):
        pytest.fail("Local input checks cannot authenticate, register, or evaluate")

    monkeypatch.setattr(run.silver, "connect", forbidden)
    monkeypatch.setattr(cli.epochs, "start_epoch", forbidden)
    monkeypatch.setattr(run, "_evaluate", forbidden)
    args = SimpleNamespace(campaign="campaign-probe", factors=[factor.name])
    if expected == "FAIL":
        with pytest.raises(SystemExit, match="입력 커버리지 사전검사 실패"):
            cli.cmd_candidate_input_check(args)
    else:
        cli.cmd_candidate_input_check(args)
    report = json.loads(capsys.readouterr().out)
    assert report["input_feasibility"]["status"] == expected
    assert report["stage"] == "LOCAL_INPUT_CHECK_ONLY"
    assert report["live_identity_checked"] is False
    assert report["registration_authorized"] is False
