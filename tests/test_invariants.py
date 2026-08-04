"""Invariants whose failure can silently reverse a factor decision."""
from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import fundamentals as FU
from engine import gate
from engine import research
from engine.factors import Factor, Registry
from engine.panel import Panel, forward_returns, from_silver_frame
from engine.trials import TrialLedger
from factors.candidate_loader import load_candidates


def _financial_rows() -> pd.DataFrame:
    rows = []
    quarters = [
        ("2024-03-31", "Q1", "2024-05-15", 71.9, 470.9),
        ("2024-06-30", "Q2", "2024-08-15", 74.1, 485.8),
        ("2024-09-30", "Q3", "2024-11-15", 79.1, 491.3),
        ("2024-12-31", "FY", "2025-03-31", 300.9, 514.5),
    ]
    for period, fiscal, available, revenue, assets in quarters:
        for metric, value, statement in (
            ("revenue", revenue, "IS"),
            ("total_assets", assets, "BS"),
        ):
            rows.append({
                "asset_id": 1,
                "period_end": period,
                "fiscal_period": fiscal,
                "fs_type": "CFS",
                "statement_type": statement,
                "available_date": available,
                "available_at": available,
                "metric": metric,
                "value": value,
                "revision_key": available.replace("-", ""),
                "quality_run_id": "q",
            })
    return pd.DataFrame(rows)


def test_flow_stock_sets_are_disjoint_and_complete():
    assert not (FU.FLOW & FU.STOCK)
    assert FU.ALL_METRICS == FU.FLOW | FU.STOCK


def test_q4_derivation_applies_only_to_flow():
    snapshots = FU.materialize_pit(_financial_rows(), verbose=False)
    final = snapshots.iloc[-1]
    assert final["total_assets"] == pytest.approx(514.5)
    assert final["revenue"] == pytest.approx(300.9 - 71.9 - 74.1 - 79.1)
    assert final["revenue_ttm"] == pytest.approx(300.9)


def test_revision_replay_never_leaks_future_filing():
    rows = pd.DataFrame([
        {"asset_id": 1, "period_end": "2023-12-31", "fiscal_period": "FY",
         "fs_type": "CFS", "available_date": "2024-02-15", "metric": "total_equity",
         "value": 100.0, "revision_key": "a"},
        {"asset_id": 1, "period_end": "2023-12-31", "fiscal_period": "FY",
         "fs_type": "CFS", "available_date": "2024-05-15", "metric": "total_equity",
         "value": 999.0, "revision_key": "b"},
    ])
    fund = FU.materialize_pit(rows, verbose=False)
    monthly = pd.DataFrame({
        "asset_id": [1, 1, 1, 1],
        "trade_date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-05-31"]),
        "ym": pd.period_range("2024-01", periods=4, freq="M").delete(3).insert(3, pd.Period("2024-05")),
    })
    output = FU.attach(monthly, fund, ["total_equity"])
    values = dict(zip(output["ym"].astype(str), output["total_equity"]))
    assert pd.isna(values["2024-01"])
    assert values["2024-02"] == 100.0
    assert values["2024-03"] == 100.0
    assert values["2024-05"] == 999.0


def test_older_cfs_dominates_later_ofs_for_same_period():
    rows = pd.DataFrame([
        {"asset_id": 1, "period_end": "2023-12-31", "fiscal_period": "FY",
         "fs_type": "CFS", "available_date": "2024-02-15", "metric": "total_equity",
         "value": 100.0, "revision_key": "a"},
        {"asset_id": 1, "period_end": "2023-12-31", "fiscal_period": "FY",
         "fs_type": "OFS", "available_date": "2024-03-15", "metric": "total_equity",
         "value": 200.0, "revision_key": "b"},
    ])
    fund = FU.materialize_pit(rows, verbose=False)
    assert fund.iloc[-1]["total_equity"] == 100.0


def test_factor_requires_hypothesis_and_valid_contract():
    with pytest.raises(ValueError, match="hypothesis"):
        Factor(name="x", category="value", hypothesis=" ", predicted_sign=1,
               compute=lambda frame: frame["a"])
    with pytest.raises(ValueError, match="category"):
        Factor(name="x", category="mystery", hypothesis="가설", predicted_sign=1,
               compute=lambda frame: frame["a"])


def test_undeclared_constant_is_detected():
    def hidden(frame):
        return frame["market_cap"] ** 0.37

    factor = Factor(name="sneaky", category="other", hypothesis="테스트", predicted_sign=1,
                    compute=hidden)
    assert 0.37 in factor.undeclared_constants()


def test_registry_rejects_duplicates():
    registry = Registry()
    factor = Factor(name="a", category="value", hypothesis="테스트", predicted_sign=1,
                    compute=lambda frame: frame["x"])
    registry.add(factor)
    with pytest.raises(ValueError, match="중복"):
        registry.add(factor)


def test_definition_hash_includes_sign_inputs_and_parameters():
    def compute(frame):
        return frame["x"]

    def make(sign=1, needs=("x",), params=None):
        return Factor(name="a", category="value", hypothesis="테스트", predicted_sign=sign,
                      compute=compute, needs=needs, params=params or {})

    assert make().definition_hash == make().definition_hash
    assert make().definition_hash != make(sign=-1).definition_hash
    assert make().definition_hash != make(needs=("y",)).definition_hash
    assert make().definition_hash != make(params={"k": 3}).definition_hash


def test_backtest_factor_missingness_does_not_redefine_benchmark():
    rows = []
    for month in pd.period_range("2018-01", periods=60, freq="M"):
        for asset_id in range(100):
            good = asset_id >= 50
            rows.append({
                "ym": month,
                "asset_id": asset_id,
                "signal": float(asset_id) if good else np.nan,
                "fwd_mid": .10 if good else -.10,
                "market_cap": 100.0,
                "_eligible": True,
            })
    result = gate.backtest(pd.DataFrame(rows), "signal", "fwd_mid", min_months=24)
    assert result is not None
    # Fixed benchmark is all 100 names (0%); the old implementation benchmarked
    # only the 50 non-missing good names and incorrectly produced zero alpha.
    assert result["gross"] == pytest.approx(120.0)


def _silver_prices() -> pd.DataFrame:
    rows = []
    dates = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"])
    for asset_id, closes in ((1, [100, 110, 121]), (2, [100, 90, 80])):
        for age, (trade_date, close) in enumerate(zip(dates, closes), 1):
            rows.append({
                "asset_id": asset_id, "Code": f"A{asset_id}", "Name": f"종목{asset_id}",
                "instrument_type": "common_stock", "listed_from": None, "listed_to": None,
                "trade_date": trade_date, "close": close, "adj_close": close,
                "total_return_close": close, "trading_value": 1e9, "market_cap": 1e11,
                "shares": 1000, "market": "KOSPI", "adv20": 1e9, "age_days": age,
                "first_seen": dates[0], "dataset_start": dates[0], "quality_run_id": "q",
            })
    return pd.DataFrame(rows)


def test_panel_uses_total_return_and_only_terminalizes_inactive_assets():
    frame = _silver_prices()
    # Asset 2 disappears before the sample end and is treated as inactive.
    frame = frame[~((frame["asset_id"] == 2) & (frame["trade_date"] > pd.Timestamp("2024-01-31")))]
    panel = from_silver_frame(frame, verbose=False)
    returns = forward_returns(panel, terminal=-1.0)
    asset1 = panel.monthly["asset_id"].eq(1)
    asset2 = panel.monthly["asset_id"].eq(2)
    assert returns[asset1].dropna().iloc[0] == pytest.approx(.10)
    assert returns[asset2].iloc[0] == -1.0


def test_total_return_is_required():
    frame = _silver_prices()
    frame.loc[0, "total_return_close"] = np.nan
    with pytest.raises(RuntimeError, match="total_return_close"):
        from_silver_frame(frame, verbose=False)


def test_by_multiple_testing_updates_pending_check_and_verdict():
    result = gate.Result(
        factor="x", definition_hash="hash", metrics={"ic_p_investable": 1e-6},
        checks=[gate.Check("T4.3", "다중검정 FDR", False)],
    )
    gate.apply_multiple_testing([result])
    assert result.metrics["fdr_qvalue"] <= gate.TH["fdr_q"]
    assert result.verdict == gate.Verdict.PROMOTE


def test_composite_rank_signals_are_rejected_but_single_ratio_is_allowed():
    def composite(frame):
        first_rank = frame["market_cap"].rank(pct=True)
        second_rank = frame["adv20"].rank(pct=True)
        return first_rank + second_rank

    def atomic(frame):
        return frame["adv20"] / frame["market_cap"]

    composite_factor = Factor(
        name="composite_x", category="other", hypothesis="합성", predicted_sign=1,
        compute=composite,
    )
    atomic_factor = Factor(
        name="atomic_x", category="other", hypothesis="단일 비율", predicted_sign=1,
        compute=atomic,
    )
    assert composite_factor.composite_evidence()
    assert atomic_factor.composite_evidence() == []


def test_return_hurdles_are_not_part_of_ruleset_v3():
    assert gate.RULESET_VERSION == "fr-3.2.0"
    assert "net_alpha" not in gate.TH
    assert "net_ir" not in gate.TH
    assert "dsr_probability" not in gate.TH
    assert gate.TH["min_ic"] == 0.03
    assert gate.TH["min_investable_ic"] == 0.02
    assert gate.TH["min_rank_icir"] == 0.15
    assert gate.TH["oos_ic"] == 0.02
    assert "investable_retention" not in gate.TH
    source = inspect.getsource(gate.evaluate)
    assert 'Check("T2.4"' not in source
    assert '"백테스트 표본", False' not in source
    assert '"전체 IC HAC 유의성"' not in source
    assert '"투자가능 IC 유지율"' not in source
    assert '"투자가능 Rank ICIR 최소요건"' in source


def test_common_research_start_is_fixed_after_financial_warmup():
    assert gate.RESEARCH_START == pd.Period("2018-03", freq="M")
    months = pd.period_range("2017-01", "2018-05", freq="M")
    frame = pd.DataFrame({"ym": months})
    filtered = frame[frame["ym"].ge(gate.RESEARCH_START)]
    assert list(filtered["ym"].astype(str)) == ["2018-03", "2018-04", "2018-05"]


def test_promotion_requires_current_null_calibration():
    result = gate.Result(
        factor="x", definition_hash="hash",
        checks=[gate.Check("T4.3", "다중검정 FDR", True)],
    )
    gate.apply_null_calibration([result], None, data_cutoff="2026-01-31")
    assert result.verdict == gate.Verdict.REJECT
    calibration = pd.DataFrame({
        "ruleset_version": [gate.RULESET_VERSION] * 100,
        "data_cutoff": ["2026-01-31"] * 100,
        "pass": [False] * 100,
    })
    gate.apply_null_calibration([result], calibration, data_cutoff="2026-01-31")
    assert result.verdict == gate.Verdict.PROMOTE


def test_trial_ledger_counts_unique_definitions_and_freezes_oos():
    with tempfile.TemporaryDirectory() as directory:
        ledger = TrialLedger(Path(directory) / "trials.sqlite3")
        months = list(pd.period_range("2015-01", periods=120, freq="M"))
        first = ledger.fixed_oos_start(months)
        extended = months + list(pd.period_range("2025-01", periods=6, freq="M"))
        assert ledger.fixed_oos_start(extended) == first
        assert ledger.summary(["a", "a", "b"]).count == 2


def test_candidate_loader_requires_preregistered_research_spec():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "candidate.py").write_text(
            """
from engine.factors import Factor
FACTOR = Factor(name='candidate_x', category='other', hypothesis='가설',
                predicted_sign=1, compute=lambda d: d['market_cap'])
RESEARCH_SPEC = {
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '기존 팩터와 낮은 상관', 'data_notes': 'PIT 가격'
}
""",
            encoding="utf-8",
        )
        registry = Registry()
        loaded = load_candidates(registry, root)
        assert [factor.name for factor in loaded] == ["candidate_x"]
        assert "candidate_x" in registry


def test_autonomous_cycle_rejects_retested_definition():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        factor = Factor(
            name="candidate_x", category="other", hypothesis="가설", predicted_sign=1,
            compute=lambda frame: frame["market_cap"],
        )
        (root / "history.jsonl").write_text(
            '{"cycle_id":"cycle-0001-candidate_x","factor":"candidate_x",'
            f'"definition_hash":"{factor.definition_hash}"}}\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="이미 평가한 definition hash"):
            research.assert_new_candidate(
                factor, {"strategy_file": "factors/candidates/candidate_x.py"},
                research_dir=root,
            )
