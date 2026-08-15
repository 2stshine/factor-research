"""Invariants whose failure can silently reverse a factor decision."""
from __future__ import annotations

import inspect
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine import epochs
from engine import fundamentals as FU
from engine import gate
from engine import implementation
from engine import null as null_engine
from engine import research
from engine import research_policy
from engine import silver
from engine.boundaries import (
    PROSPECTIVE_HOLDOUT_MODE,
    CampaignWindow,
    QUALIFICATION_POLICY,
    validate_manifest,
)
from engine.factors import Factor, Registry
from engine.panel import (
    INVESTABLE_ADV,
    Panel,
    forward_returns,
    from_silver_frame,
    snapshot_digest,
)
from engine.trials import TrialLedger
from factors.candidate_loader import load_candidates
from scripts import research as research_script
from scripts import run as run_script


RETURN_EVIDENCE = {
    "validation_status": "VERIFIED",
    "contract_release": silver.TOTAL_RETURN_CONTRACT_RELEASE,
    "methodology_version": silver.TOTAL_RETURN_METHOD,
    "dividend_treatment": silver.TOTAL_RETURN_DIVIDEND_TREATMENT,
    "quality_run_id": "q",
    "coverage_start": "2015-01-02",
    "coverage_end": "2035-12-31",
    "certified_scope_start": "2015-01-01",
    "certified_markets": ["KOSPI", "KOSDAQ"],
    "price_row_count": 1,
    "asset_count": 1,
    "action_snapshot_run_id": "action-run",
    "action_snapshot_schema_version": silver.TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA,
    "action_snapshot_manifest_sha256": "a" * 64,
    "action_snapshot_body_digest": "b" * 64,
    "pit_scope_contract": silver.TOTAL_RETURN_PIT_SCOPE_CONTRACT,
    "pit_input_action_count": 1,
    "pit_included_action_count": 1,
    "pit_excluded_action_count": 0,
    "source_receipt_row_count": 1,
    "source_receipt_row_digest": "d" * 64,
    "terminal_economic_receipt_count": 1,
    "terminal_economic_receipt_digest": "e" * 64,
    "published_action_count": 1,
    "published_action_row_digest": "f" * 64,
    "published_action_scope_contract": (
        "issuer_cash_ex_plus_manifest_scale_support_v1"
    ),
    "included_cash_action_parity_count": 1,
    "included_cash_action_parity_digest": "1" * 64,
    "cash_scale_source_contract": (
        silver.TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT
    ),
    "cash_scale_source_evidence_count": 0,
    "cash_scale_source_evidence_digest": "3" * 64,
    "cash_scale_source_manifest_sha256": "5" * 64,
    "cash_scale_source_manifest_digest": "6" * 64,
    "cash_scale_support_action_count": 0,
    "cash_scale_support_action_digest": "7" * 64,
    "cash_scale_support_manifest_digest": "8" * 64,
    "cash_scale_support_semantic_group_count": 0,
    "disclosure_observation_contract": (
        silver.TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT
    ),
    "disclosure_mutable_conflict_digest": "2" * 64,
    "research_role": dict(silver.TOTAL_RETURN_RESEARCH_ROLE),
    "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
    "cash_action_count": 1,
    "canonical_event_count": 1,
    "applied_event_count": 1,
    "excluded_event_count": 0,
    "cash_scale_resolution_contract": (
        silver.TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
    ),
    "cash_scale_resolution_row_count": 1,
    "cash_scale_resolution_row_digest": "4" * 64,
    "cash_scale_stable_event_count": 1,
    "cash_scale_changed_event_count": 0,
    "cash_scale_evidence_match_count": 0,
    "cash_scale_adjusted_cash_parity_count": 1,
    "cash_scale_first_listing_exclusion_count": 0,
    "cash_scale_explicit_exclusion_count": 0,
    "cash_scale_adj_close_decimal_places": 4,
    "cash_scale_cash_in_adj_close": False,
    "asset_identity_contract": silver.TOTAL_RETURN_ASSET_IDENTITY_CONTRACT,
    "asset_identity_digest": "c" * 64,
}
RETURN_EVIDENCE["evidence_sha256"] = silver.total_return_evidence_sha256(
    RETURN_EVIDENCE,
)


RETURN_META = {
    **silver.return_role_contract(),
    "label_return_contract_status": "CERTIFIED",
    "return_contract_run_id": "q",
    "return_contract_validation_status": "VERIFIED",
    "return_contract_evidence_sha256": RETURN_EVIDENCE["evidence_sha256"],
    "return_contract_validation_evidence": RETURN_EVIDENCE,
}


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
    empty = FU.materialize_pit(pd.DataFrame(), verbose=False)
    assert FU.PIT_FEATURES.issubset(empty.columns)


def test_q4_derivation_applies_only_to_flow():
    snapshots = FU.materialize_pit(_financial_rows(), verbose=False)
    final = snapshots.iloc[-1]
    assert final["total_assets"] == pytest.approx(514.5)
    assert final["revenue"] == pytest.approx(300.9 - 71.9 - 74.1 - 79.1)
    assert final["revenue_ttm"] == pytest.approx(300.9)


def test_pit_materialization_does_not_depend_on_database_row_order():
    rows = _financial_rows()
    expected = FU.materialize_pit(rows, verbose=False)
    shuffled = FU.materialize_pit(
        rows.sample(frac=1.0, random_state=20260808), verbose=False,
    )

    pd.testing.assert_frame_equal(shuffled, expected)


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
                "total_return_close": close if age == 1 else close + 2,
                "trading_value": 1e9, "market_cap": 1e11,
                "shares": 1000, "market": "KOSPI", "adv20": 1e9, "age_days": age,
                "first_seen": dates[0], "dataset_start": dates[0], "quality_run_id": "q",
                "total_return_quality_run_id": "q",
                "amihud_illiquidity_1m": None if age == 1 else 1e-12,
                "amihud_observations_1m": age - 1,
                "daily_volatility_252d": None if age < 3 else .01,
                "daily_return_observations_252d": age - 1,
                "max_daily_return_1m": None if age == 1 else .10,
                "max_daily_return_observations_1m": age - 1,
                "price_high_252d": max(closes[:age]),
                "price_high_observations_252d": age,
            })
    frame = pd.DataFrame(rows)
    frame.attrs["return_contract"] = {
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "status": "CERTIFIED",
        "quality_run_id": "q",
        "validation_evidence": dict(RETURN_EVIDENCE),
    }
    frame.attrs["return_roles"] = silver.return_role_contract()
    return frame


def _monthly_panel(start: str, end: str) -> Panel:
    months = pd.period_range(start, end, freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "Code": "000001",
        "ym": months,
        "trade_date": months.to_timestamp(how="end").normalize(),
        "adj_close": np.arange(len(months), dtype=float) + 100.0,
        "total_return_close": np.arange(len(months), dtype=float) + 200.0,
        "instrument_type": "common_stock",
    })
    return Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta={"source": "RDS public Silver", **RETURN_META},
    )


def _start_campaign(
    root: Path,
    campaign_id: str = "campaign-001",
    *,
    discovery_data_cutoff: str = "2023-06-30",
    snapshot_cutoff: str = "2026-07-31",
    min_oos_months: int = 36,
    planned_epoch_count: int = 1,
):
    closure_cutoff = str(
        (pd.Timestamp(snapshot_cutoff).to_period("M") + 1)
        .to_timestamp(how="end").normalize().date()
    )
    return epochs.start_campaign(
        root,
        campaign_id,
        discovery_data_cutoff=discovery_data_cutoff,
        snapshot_cutoff=snapshot_cutoff,
        snapshot_digest="a" * 64,
        discovery_snapshot_digest="b" * 64,
        snapshot_asset_identity_digest="c" * 64,
        discovery_asset_identity_digest="d" * 64,
        closure_asset_identity_digest="e" * 64,
        closure_asset_identity_cutoff=closure_cutoff,
        min_oos_months=min_oos_months,
        planned_epoch_count=planned_epoch_count,
    )


def _strategy_sha(factor: Factor) -> str:
    return hashlib.sha256(
        f"{factor.name}:{factor.definition_hash}".encode("utf-8")
    ).hexdigest()


def _strategy_digests(factors: list[Factor]) -> dict[str, str]:
    return {factor.name: _strategy_sha(factor) for factor in factors}


def _net_income_ratio(frame):
    return frame["net_income_ttm"] / frame["total_liabilities"]


def _pretax_income_ratio(frame):
    return frame["pretax_income_ttm"] / frame["total_liabilities"]


def _input_feasibility(factors: list[Factor], snapshot_digest: str = "b" * 64):
    return research_policy.input_feasibility_artifact(
        factors,
        snapshot_digest=snapshot_digest,
        signal_start=str(gate.RESEARCH_START),
        signal_end="2023-05",
        metrics={
            factor.name: {"coverage": 1.0, "monthly_coverage_p10": 1.0}
            for factor in factors
        },
        minimum_coverage=gate.TH["coverage"],
        minimum_monthly_p10=gate.TH["monthly_coverage_p10"],
    )


def _batch_orthogonality(factors: list[Factor]):
    names = sorted(factor.name for factor in factors)
    return {
        "schema_version": "gold-batch-orthogonality-v1",
        "policy": "lexical_first_independent_of_research_outcomes_v1",
        "threshold": gate.TH["max_gold_corr"],
        "minimum_comparison_months": gate.TH["min_gold_corr_months"],
        "candidate_factors": names,
        "pairs": [
            {
                "left": left,
                "right": right,
                "median_absolute_spearman": 0.0,
                "comparison_months": gate.TH["min_gold_corr_months"],
                "conflict": False,
            }
            for index, left in enumerate(names)
            for right in names[index + 1:]
        ],
        "survivors": names,
        "suppressed": [],
    }


def _conflicting_batch_orthogonality(factors: list[Factor]):
    names = sorted(factor.name for factor in factors)
    assert len(names) == 2
    return {
        "schema_version": "gold-batch-orthogonality-v1",
        "policy": "lexical_first_independent_of_research_outcomes_v1",
        "threshold": gate.TH["max_gold_corr"],
        "minimum_comparison_months": gate.TH["min_gold_corr_months"],
        "candidate_factors": names,
        "pairs": [{
            "left": names[0], "right": names[1],
            "median_absolute_spearman": .95,
            "comparison_months": gate.TH["min_gold_corr_months"],
            "conflict": True,
        }],
        "survivors": [names[0]],
        "suppressed": [{
            "factor": names[1], "kept_factor": names[0],
            "reason": "batch_signal_correlation_above_threshold",
        }],
    }


def _implementation_evidence(factor: Factor, campaign: dict) -> dict:
    months = pd.period_range(
        gate.RESEARCH_START,
        pd.Period(campaign["discovery"]["signal_end"], freq="M"),
        freq="M",
    )
    python_frame = pd.DataFrame({
        "asset_id": np.arange(len(months), dtype=int) + 1,
        "as_of_date": months.to_timestamp(how="end").normalize(),
        "value": np.arange(len(months), dtype=float) + 1.0,
    })
    sql_frame = python_frame.copy()
    sql_frame["rank"] = 1
    spec = {
        "sql": f"implementations/gold/factors/{factor.name}.sql",
        "predicted_sign": factor.predicted_sign,
        "research_definition_hash": factor.definition_hash,
        "value_contract": "raw_value_direction_adjusted_rank_v1",
    }
    return implementation.compare_parity(
        factor,
        python_frame,
        sql_frame,
        implementation_uri=f"repo://factor-research/{spec['sql']}",
        implementation_sha256="c" * 64,
        manifest_spec=spec,
        discovery_signal_start=gate.RESEARCH_START,
        discovery_signal_end=campaign["discovery"]["signal_end"],
        discovery_snapshot_digest=campaign["snapshot"]["discovery_input_digest"],
        strategy_sha256=_strategy_sha(factor),
    )


def _binding_from_evidence(row: dict) -> dict:
    keys = (
        "factor", "definition_hash", "strategy_sha256", "predicted_sign", "value_contract",
        "implementation_uri", "implementation_sha256", "manifest_entry_digest",
    )
    return {key: row[key] for key in keys}


def test_panel_labels_use_total_return_and_only_terminalize_inactive_assets():
    frame = _silver_prices()
    # Asset 2 disappears before the sample end and is treated as inactive.
    frame = frame[~((frame["asset_id"] == 2) & (frame["trade_date"] > pd.Timestamp("2024-01-31")))]
    panel = from_silver_frame(frame, verbose=False)
    returns = forward_returns(panel, terminal=-1.0)
    asset1 = panel.monthly["asset_id"].eq(1)
    asset2 = panel.monthly["asset_id"].eq(2)
    # adj_close moves 10%, while the certified ex-post total-return label moves
    # 12%; forward labels must use the latter and candidate features the former.
    assert returns[asset1].dropna().iloc[0] == pytest.approx(.12)
    assert returns[asset2].iloc[0] == -1.0


def test_total_return_is_required():
    frame = _silver_prices()
    frame.loc[0, "total_return_close"] = np.nan
    with pytest.raises(RuntimeError, match="total_return_close"):
        from_silver_frame(frame, verbose=False)


def test_total_return_methodology_contract_is_required():
    missing = _silver_prices()
    missing.attrs.clear()
    with pytest.raises(RuntimeError, match="방법론 계약"):
        from_silver_frame(missing, verbose=False)

    stale = _silver_prices()
    stale.attrs["return_contract"]["methodology_version"] = "price_only_v0"
    with pytest.raises(RuntimeError, match="인증 기준과 다릅니다"):
        from_silver_frame(stale, verbose=False)


def test_panel_snapshot_digest_binds_values_and_terminal_membership():
    panel = from_silver_frame(_silver_prices(), verbose=False)
    original = snapshot_digest(panel)
    changed_values = Panel(panel.monthly.copy(), panel.dead.copy(), dict(panel.meta))
    changed_values.monthly.loc[0, "total_return_close"] += 1.0
    assert snapshot_digest(changed_values) != original
    changed_dead = Panel(panel.monthly.copy(), panel.dead.copy(), dict(panel.meta))
    changed_dead.dead.loc[999] = pd.Timestamp("2024-01-31")
    assert snapshot_digest(changed_dead) != original


def test_campaign_discovery_scope_honors_exact_cutoff_and_oos_boundary():
    panel = from_silver_frame(_silver_prices(), verbose=False)
    panel.monthly["f_leaked_full_sample"] = 1.0
    scoped = run_script._scope_discovery_panel(
        panel, data_cutoff="2024-02-29", oos_start="2024-03",
    )
    assert scoped.monthly["ym"].max() == pd.Period("2024-02", freq="M")
    assert scoped.monthly["trade_date"].max() == pd.Timestamp("2024-02-29")
    assert "f_leaked_full_sample" not in scoped.monthly
    assert scoped.meta["label_return_methodology"] == silver.TOTAL_RETURN_METHOD
    assert scoped.meta["feature_price_field"] == "adj_close"
    assert scoped.meta["label_return_contract_status"] == "CERTIFIED"
    with pytest.raises(ValueError, match="정확히 재현"):
        run_script._scope_discovery_panel(
            panel, data_cutoff="2024-02-15", oos_start="2024-03",
        )


def test_confirmation_scope_discards_months_after_fixed_oos_label():
    partial = _monthly_panel("2020-12", "2024-01")
    with pytest.raises(ValueError, match="다음 달"):
        run_script._scope_confirmation_panel(
            partial, data_cutoff="2020-12-31",
            oos_start="2021-01", oos_end="2023-12",
        )
    panel = _monthly_panel("2020-12", "2024-03")
    panel.meta.update({"source": "RDS public Silver", **RETURN_META})
    panel.monthly["f_leaked_full_sample"] = 1.0
    scoped = run_script._scope_confirmation_panel(
        panel, data_cutoff="2020-12-31",
        oos_start="2021-01", oos_end="2023-12",
    )
    assert scoped.monthly["ym"].max() == pd.Period("2024-01", freq="M")
    assert scoped.meta["confirmation_closure_month"] == "2024-02"
    assert scoped.meta["closure_asset_identity_cutoff"] == "2024-02-29"
    assert scoped.meta["label_return_methodology"] == silver.TOTAL_RETURN_METHOD
    assert scoped.meta["feature_price_field"] == "adj_close"
    assert scoped.meta["label_return_contract_status"] == "CERTIFIED"
    assert "f_leaked_full_sample" not in scoped.monthly


def test_legacy_full_panel_gate_and_publish_cannot_bypass_campaign_scope():
    with pytest.raises(SystemExit, match="봉인 OOS"):
        run_script.cmd_gate(SimpleNamespace(factor=None))
    with pytest.raises(SystemExit, match="비활성화"):
        run_script.cmd_publish(SimpleNamespace())
    with pytest.raises(ValueError, match="snapshot digest"):
        run_script._evaluate(
            SimpleNamespace(factor=None),
            phase="discovery",
            data_cutoff="2023-06-30",
            oos_start="2023-07",
        )


def test_discovery_snapshot_digest_is_checked_before_database_or_factor_evaluation(
    monkeypatch,
):
    panel = _monthly_panel("2018-03", "2020-12")
    monkeypatch.setattr(run_script, "load_registry", lambda: None)
    monkeypatch.setattr(run_script, "_load", lambda: panel)

    with pytest.raises(ValueError, match="discovery Silver snapshot"):
        run_script._evaluate(
            SimpleNamespace(factor=None),
            phase="discovery",
            data_cutoff="2020-12-31",
            oos_start="2021-01",
            discovery_snapshot_digest="0" * 64,
            discovery_asset_identity_digest="1" * 64,
        )


@pytest.mark.parametrize("oos_end", ["2023-11", "2024-01"])
def test_confirmation_scope_rejects_35_and_37_signal_months(oos_end):
    panel = _monthly_panel("2020-12", "2024-03")
    with pytest.raises(ValueError, match="정확히 36 signal개월"):
        run_script._scope_confirmation_panel(
            panel, data_cutoff="2020-12-31",
            oos_start="2021-01", oos_end=oos_end,
        )


def test_campaign_window_separates_discovery_and_oos_signal_return_support():
    window = CampaignWindow.from_completed_snapshot(
        discovery_data_cutoff="2023-06-30",
        snapshot_cutoff="2026-07-31",
        oos_months=36,
    )
    assert window.discovery_signal_end == pd.Period("2023-05", freq="M")
    assert window.discovery_return_end == pd.Period("2023-06", freq="M")
    assert window.oos_signal_start == pd.Period("2023-07", freq="M")
    assert window.oos_signal_end == pd.Period("2026-06", freq="M")
    assert window.oos_return_end == pd.Period("2026-07", freq="M")
    assert window.closure_month == pd.Period("2026-08", freq="M")
    assert window.discovery_return_end < window.oos_signal_start


def test_campaign_snapshot_boundary_handles_partial_and_lagged_silver():
    panel = _monthly_panel("2015-01", "2026-08")
    window = research_script._campaign_snapshot_boundary(
        panel, as_of_date="2026-08-07",
    )
    assert window.snapshot_cutoff == "2026-06-30"
    assert window.discovery_data_cutoff == "2023-05-31"
    assert str(window.oos_signal_start) == "2023-06"
    assert str(window.oos_signal_end) == "2026-05"

    window = research_script._campaign_snapshot_boundary(
        panel, as_of_date="2026-09-15",
    )
    assert window.snapshot_cutoff == "2026-07-31"
    assert window.discovery_data_cutoff == "2023-06-30"
    assert str(window.oos_signal_start) == "2023-07"

    late_current_month = research_script._campaign_snapshot_boundary(
        panel, as_of_date="2026-08-20",
    )
    assert late_current_month.snapshot_cutoff == "2026-06-30"
    assert late_current_month.closure_month == pd.Period("2026-07", freq="M")


def test_prospective_campaign_boundary_reserves_only_future_signals():
    panel = _monthly_panel("2015-01", "2026-08")
    window = research_script._prospective_campaign_boundary(
        panel, as_of_date="2026-08-07",
    )

    assert window.mode == PROSPECTIVE_HOLDOUT_MODE
    assert window.snapshot_cutoff == "2026-07-31"
    assert window.discovery_signal_end == pd.Period("2026-06", freq="M")
    assert window.oos_signal_start == pd.Period("2026-09", freq="M")
    assert window.oos_signal_end == pd.Period("2029-08", freq="M")
    assert window.oos_return_end == pd.Period("2029-09", freq="M")


def test_prospective_campaign_stays_pristine_and_historical_reuse_is_labeled(
    tmp_path,
):
    exposure_dir = tmp_path / "oos-exposures"
    exposure_dir.mkdir()
    (exposure_dir / "old-audit.json").write_text(json.dumps({
        "exposure_id": "old-audit",
        "signal_start": "2023-06",
        "signal_end": "2026-05",
        "return_end": "2026-06",
    }), encoding="utf-8")
    historical_path = _start_campaign(tmp_path, "campaign-historical")
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    assert historical["oos"]["evidence_class"] == "HISTORICAL_REUSED_WINDOW"
    assert historical["oos"]["prior_exposure_ids"] == ["old-audit"]
    historical["status"] = "CLOSED_NO_QUALIFIED"
    historical["oos"]["status"] = "NOT_USED"
    historical_path.write_text(json.dumps(historical), encoding="utf-8")

    path = epochs.start_campaign(
        tmp_path,
        "campaign-prospective",
        discovery_data_cutoff="2026-07-31",
        snapshot_cutoff="2026-07-31",
        snapshot_digest="a" * 64,
        discovery_snapshot_digest="b" * 64,
        snapshot_asset_identity_digest="c" * 64,
        discovery_asset_identity_digest="d" * 64,
        mode=PROSPECTIVE_HOLDOUT_MODE,
        oos_start="2026-09",
    )
    campaign = json.loads(path.read_text(encoding="utf-8"))
    window = validate_manifest(campaign, expected_oos_months=36)

    assert window.mode == PROSPECTIVE_HOLDOUT_MODE
    assert campaign["oos"]["start"] == "2026-09"
    assert campaign["oos"]["signal_end"] == "2029-08"
    assert campaign["snapshot"]["completed_month"] == "2026-07"


def test_campaign_snapshot_boundary_rejects_truncated_prior_month():
    panel = _monthly_panel("2015-01", "2026-08")
    panel.monthly.loc[
        panel.monthly["ym"].eq(pd.Period("2026-07", freq="M")),
        "trade_date",
    ] = pd.Timestamp("2026-07-10")

    with pytest.raises(ValueError, match="월말까지 적재"):
        research_script._campaign_snapshot_boundary(
            panel,
            as_of_date="2026-09-15",
        )


def test_campaign_snapshot_boundary_rejects_future_silver_month():
    panel = from_silver_frame(_silver_prices(), verbose=False)
    with pytest.raises(ValueError, match="미래"):
        research_script._campaign_snapshot_boundary(
            panel, as_of_date="2024-02-15",
        )


def test_current_ready_snapshot_ends_oos_return_in_2026_06():
    panel = _monthly_panel("2015-01", "2026-08")
    window = research_script._campaign_snapshot_boundary(
        panel, as_of_date="2026-08-07",
    )

    assert window.discovery_signal_end == pd.Period("2023-04", freq="M")
    assert window.discovery_return_end == pd.Period("2023-05", freq="M")
    assert window.oos_signal_start == pd.Period("2023-06", freq="M")
    assert window.oos_signal_end == pd.Period("2026-05", freq="M")
    assert window.oos_return_end == pd.Period("2026-06", freq="M")


def test_scoped_panel_recomputes_terminal_labels_without_future_reappearance():
    months = pd.period_range("2020-12", "2024-03", freq="M")
    rows = [{
        "asset_id": 1,
        "Code": "000001",
        "trade_date": month.to_timestamp(how="end").normalize(),
        "ym": month,
        "adj_close": 100.0 + index,
        "total_return_close": 200.0 + index,
    } for index, month in enumerate(months)]
    for index, month in enumerate(pd.PeriodIndex(["2023-12", "2024-03"], freq="M")):
        rows.append({
            "asset_id": 2,
            "Code": "000002",
            "trade_date": month.to_timestamp(how="end").normalize(),
            "ym": month,
            "adj_close": 100.0 + index,
            "total_return_close": 200.0 + index,
        })
    panel = Panel(
        pd.DataFrame(rows), pd.Series(dtype="datetime64[ns]"),
        meta={"source": "RDS public Silver", **RETURN_META},
    )
    scoped = run_script._scope_confirmation_panel(
        panel, data_cutoff="2020-12-31",
        oos_start="2021-01", oos_end="2023-12",
    )
    disappeared = scoped.monthly["asset_id"].eq(2)
    assert scoped.monthly.loc[disappeared, "fwd_mid"].iloc[0] == -.50


def test_by_multiple_testing_updates_pending_check_and_verdict():
    result = gate.Result(
        factor="x", definition_hash="hash", metrics={"ic_p_investable": 1e-6},
        checks=[gate.Check("T4.3", "다중검정 FDR", None)],
    )
    gate.apply_multiple_testing([result])
    assert result.metrics["fdr_qvalue"] <= gate.TH["fdr_q"]
    assert result.verdict == gate.Verdict.PROMOTE


def test_discovery_evidence_digest_normalizes_numpy_scalars():
    result = gate.Result(
        factor="x", definition_hash="hash",
        metrics={"ic_investable": np.float64(.02)},
        checks=[gate.Check("T1.1", "coverage", np.bool_(True), np.float64(.5))],
    )
    assert len(gate.discovery_evidence_digest(result)) == 64


def test_discovery_candidate_cannot_promote_while_oos_is_sealed():
    result = gate.Result(
        factor="x", definition_hash="hash", metrics={"ic_p_investable": 1e-6},
        labels=["oos_sealed"],
        checks=[gate.Check("T4.3", "다중검정 FDR", None)],
    )
    gate.apply_multiple_testing([result])
    assert result.verdict == gate.Verdict.PROVISIONAL
    assert "discovery_pass" in result.labels
    assert not any(check.name == "고정 OOS IC" for check in result.checks)


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
    assert gate.RULESET_VERSION == "fr-3.14.0"
    assert "net_alpha" not in gate.TH
    assert "net_ir" not in gate.TH
    assert "dsr_probability" not in gate.TH
    assert gate.TH["min_ic"] == 0.03
    assert gate.TH["min_investable_ic"] == 0.03
    assert gate.TH["min_rank_icir"] == 0.15
    assert gate.TH["neutral_ic_retention"] == 0.30
    assert gate.TH["oos_ic"] == 0.02
    assert gate.TH["oos_ic_retention"] == 0.50
    assert gate.TH["max_gold_corr"] == 0.70
    assert gate.TH["min_gold_corr_months"] == 36
    assert gate.TH["candidate_duplicate_corr"] == 0.80
    assert gate.TH["min_oos_months"] == 36
    assert INVESTABLE_ADV == 0.0
    assert "investable_retention" not in gate.TH
    source = inspect.getsource(gate.evaluate)
    assert 'Check("T2.4"' not in source
    assert '"백테스트 표본", False' not in source
    assert '"전체 IC HAC 유의성"' not in source
    assert '"투자가능 IC 유지율"' not in source
    assert '"투자가능 IC HAC 유의성"' not in source
    assert '"투자가능 Rank ICIR 최소요건"' in source
    assert '"T3.4"' not in source
    assert '"sector"' not in inspect.getsource(gate._neutralized_signal)


def test_discovery_rank_ic_floor_is_three_percent(monkeypatch):
    months = pd.period_range("2020-01", periods=60, freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "ym": months,
        "trade_date": months.to_timestamp(how="end").normalize(),
        "in_universe": True,
        "market_cap": 100.0,
        "adj_close": 100.0,
        "total_return_close": 100.0,
            "adv20": 1.0,
            "market": "KOSPI",
            "instrument_type": "common_stock",
            "f_candidate": 100.0,
        "fwd_opt": 0.0,
        "fwd_mid": 0.0,
        "fwd_pess": 0.0,
    })
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta=dict(RETURN_META),
    )
    factor = Factor(
        name="candidate", category="other", hypothesis="경계값 검사",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    measured_ic = [.03]

    def fake_ic_series(*_args, **_kwargs):
        return pd.Series(np.tile([measured_ic[0] - .05, measured_ic[0] + .05], 30))

    monkeypatch.setattr(gate, "_ic_series", fake_ic_series)
    monkeypatch.setattr(
        gate, "_hac_mean_test",
        lambda _series: (measured_ic[0], 5.0, .001),
    )
    monkeypatch.setattr(gate, "backtest", lambda *_args, **_kwargs: None)

    at_floor = gate.evaluate(factor, panel, frame, phase="discovery")
    for name in ("전체 IC 최소요건", "투자가능 IC 최소요건"):
        check = next(item for item in at_floor.checks if item.name == name)
        assert check.passed is True
        assert check.threshold == ">=0.03"

    measured_ic[0] = .0299
    below = gate.evaluate(factor, panel, frame, phase="discovery")
    for name in ("전체 IC 최소요건", "투자가능 IC 최소요건"):
        assert next(item for item in below.checks if item.name == name).passed is False


def test_invocation_gate_context_is_result_exact():
    months = pd.period_range("2018-03", periods=60, freq="M")
    assets = np.arange(1, 61)
    frame = pd.DataFrame([
        {
            "asset_id": int(asset),
            "ym": month,
            "trade_date": month.to_timestamp(how="end").normalize(),
            "in_universe": True,
            "market_cap": float(asset + 100),
            "adj_close": 100.0,
            "total_return_close": 100.0,
            "adv20": float(asset + 1),
            "market": "KOSPI" if asset % 2 else "KOSDAQ",
            "instrument_type": "common_stock",
            "f_candidate": float(asset + 100),
            "fwd_opt": float(asset) / 1000,
            "fwd_mid": float(asset) / 1000,
            "fwd_pess": float(asset) / 1000,
        }
        for month in months
        for asset in assets
    ])
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"), meta=dict(RETURN_META),
    )
    factor = Factor(
        name="candidate", category="other", hypothesis="context exact parity",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    baseline = gate.evaluate(factor, panel, frame, phase="discovery")
    context = gate.build_evaluation_context(panel, frame, phase="discovery")
    optimized = gate.evaluate(
        factor, panel, frame, phase="discovery", context=context,
    )

    assert research.serialize_result(optimized) == research.serialize_result(baseline)


def test_discovery_defers_only_non_decision_portfolio_diagnostics():
    months = pd.period_range("2018-03", periods=60, freq="M")
    assets = np.arange(1, 61)
    frame = pd.DataFrame([
        {
            "asset_id": int(asset), "ym": month,
            "trade_date": month.to_timestamp(how="end").normalize(),
            "in_universe": True, "market_cap": float(asset + 100),
            "adj_close": 100.0, "total_return_close": 100.0,
            "adv20": float(asset + 1),
            "market": "KOSPI" if asset % 2 else "KOSDAQ",
            "instrument_type": "common_stock",
            "f_candidate": float(asset + 100),
            "fwd_opt": float(asset) / 1000,
            "fwd_mid": float(asset) / 1000,
            "fwd_pess": float(asset) / 1000,
        }
        for month in months for asset in assets
    ])
    panel = Panel(frame, pd.Series(dtype="datetime64[ns]"), meta=dict(RETURN_META))
    factor = Factor(
        name="candidate", category="other", hypothesis="diagnostic deferral",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    context = gate.build_evaluation_context(panel, frame, phase="discovery")
    baseline = gate.evaluate(
        factor, panel, frame, phase="discovery", context=context,
    )
    deferred = gate.evaluate(
        factor, panel, frame, phase="discovery", context=context,
        include_diagnostics=False,
    )
    assert gate.discovery_evidence_digest(deferred) == gate.discovery_evidence_digest(
        baseline
    )
    assert [(c.tier, c.name, c.passed) for c in deferred.checks] == [
        (c.tier, c.name, c.passed) for c in baseline.checks
    ]
    assert "turnover" not in deferred.metrics
    gate.attach_portfolio_diagnostics(
        deferred, factor, panel, frame, context=context,
    )
    for key in ("turnover", "gross", "cost", "net", "net_ir"):
        assert deferred.metrics[key] == pytest.approx(baseline.metrics[key])


def test_internal_null_contract_skips_candidate_t0_but_rejects_drift(monkeypatch):
    months = pd.period_range("2018-03", periods=60, freq="M")
    frame = pd.DataFrame({
        "asset_id": np.arange(len(months)), "ym": months,
        "trade_date": months.to_timestamp(how="end").normalize(),
        "in_universe": True, "market_cap": 100.0, "adj_close": 100.0,
        "total_return_close": 100.0, "adv20": 1.0, "market": "KOSPI",
        "instrument_type": "common_stock", "fwd_opt": 0.0,
        "fwd_mid": 0.0, "fwd_pess": 0.0,
    })
    name = "null_random_0_0"
    frame[f"_raw_{name}"] = np.arange(len(frame), dtype=float)
    frame[f"f_{name}"] = frame[f"_raw_{name}"]
    factor = Factor(
        name=name, family="null_random", category="other",
        hypothesis="합성 귀무", predicted_sign=1,
        params={"kind": "random", "replicate": 0, "candidate": 0, "seed": 7},
        compute=lambda data: data[f"_raw_{name}"],
    )
    panel = Panel(frame, pd.Series(dtype="datetime64[ns]"), meta=dict(RETURN_META))
    contract = gate.certify_internal_null_signal(
        factor, frame, generator_suite="null-v2", kind="random",
        replicate=0, candidate=0, seed=7,
        raw_column=f"_raw_{name}", factor_column=f"f_{name}",
    )
    baseline = gate.evaluate(
        factor, panel, frame, phase="discovery", include_diagnostics=False,
    )
    monkeypatch.setattr(
        gate, "_validate_factor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("candidate T0 must not run for internal null")
        ),
    )
    result = gate.evaluate(
        factor, panel, frame, phase="discovery",
        internal_null_contract=contract, include_diagnostics=False,
    )
    assert all(check.passed is True for check in result.checks if check.tier == "T0")
    assert {
        key: value for key, value in result.metrics.items()
        if key not in {"evaluation_phase", "research_start"}
    } == {
        key: value for key, value in baseline.metrics.items()
        if key not in {"evaluation_phase", "research_start"}
    }
    assert [
        (check.tier, check.name, check.passed, check.value)
        for check in result.checks if not check.tier.startswith("T0")
    ] == [
        (check.tier, check.name, check.passed, check.value)
        for check in baseline.checks if not check.tier.startswith("T0")
    ]
    frame.loc[0, f"f_{name}"] = 999.0
    with pytest.raises(ValueError, match="현재 factor/frame"):
        gate.evaluate(
            factor, panel, frame, phase="discovery",
            internal_null_contract=contract, include_diagnostics=False,
        )


def test_frozen_discovery_result_authentication_skips_recompute_and_detects_tamper(
    tmp_path,
):
    factor = Factor(
        name="candidate", category="other", hypothesis="frozen discovery",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    result = gate.Result(
        factor=factor.name, definition_hash=factor.definition_hash,
        verdict=gate.Verdict.PROVISIONAL,
        metrics={"ic_p_investable": .01, "ic_investable": .04},
        labels=["oos_sealed", "fdr_pending", "portfolio_diagnostics_deferred"],
        checks=[gate.Check("T2.1", "투자가능 IC 최소요건", True, .04)],
    )
    strategy_sha = "c" * 64
    payload = {
        "campaign_id": "campaign-test", "epoch_id": "epoch-test",
        "phase": "discovery", "ruleset_version": gate.RULESET_VERSION,
        "factor": {"name": factor.name, "definition_hash": factor.definition_hash},
        "research_spec": {"strategy_sha256": strategy_sha},
        "evaluation": research.serialize_result(result),
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    raw = path.read_bytes()
    frozen = {
        "factor": factor.name, "definition_hash": factor.definition_hash,
        "strategy_sha256": strategy_sha, "pvalue": .01,
        "evidence_ruleset_version": gate.RULESET_VERSION,
        "discovery_evidence_digest": gate.discovery_evidence_digest(result),
        "discovery_result_artifact": str(path),
        "discovery_result_artifact_sha256": hashlib.sha256(raw).hexdigest(),
    }
    restored = research.load_authenticated_discovery_result(frozen, factor)
    assert research.serialize_result(restored) == research.serialize_result(result)
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="artifact SHA"):
        research.load_authenticated_discovery_result(frozen, factor)


def test_authenticated_discovery_fast_path_uses_no_external_gold_trial_rows():
    assert run_script.research is research
    assert run_script._external_gold_trial_rows(None) == []
    frame = pd.DataFrame({"definition_hash": ["a" * 16, "b" * 16]})
    assert run_script._external_gold_trial_rows(frame) == [
        ("a" * 16, None, None),
        ("b" * 16, None, None),
    ]


def test_confirmation_reuses_authenticated_t0_and_binds_current_signal(monkeypatch):
    months = pd.period_range("2023-07", periods=36, freq="M")
    assets = np.arange(1, 61)
    frame = pd.DataFrame([
        {
            "asset_id": int(asset), "ym": month,
            "trade_date": month.to_timestamp(how="end").normalize(),
            "in_universe": True, "market_cap": float(asset + 100),
            "adj_close": 100.0, "total_return_close": 100.0,
            "adv20": float(asset + 1), "market": "KOSPI",
            "instrument_type": "common_stock",
            "f_candidate": float(asset + 100),
            "fwd_opt": float(asset) / 1000,
            "fwd_mid": float(asset) / 1000,
            "fwd_pess": float(asset) / 1000,
        }
        for month in months for asset in assets
    ])
    panel = Panel(frame, pd.Series(dtype="datetime64[ns]"), meta=dict(RETURN_META))
    factor = Factor(
        name="candidate", category="other", hypothesis="confirmation T0 reuse",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    discovery = gate.Result(
        factor=factor.name, definition_hash=factor.definition_hash,
        checks=gate._validate_factor(factor, frame, "f_candidate"),
    )
    contract = gate.certify_confirmation_signal(factor, frame, discovery)
    monkeypatch.setattr(
        gate, "_validate_factor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("confirmation must not rerun candidate T0")
        ),
    )
    result = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=pd.Period("2023-07", freq="M"),
        oos_end=pd.Period("2026-06", freq="M"),
        data_cutoff="2023-06-30", discovery_ic=.05,
        confirmation_signal_contract=contract,
    )
    assert any(check.name.startswith("동결 Discovery") for check in result.checks)
    frame.loc[0, "f_candidate"] = -999.0
    with pytest.raises(ValueError, match="인증 뒤 변경"):
        gate.evaluate_oos(
            factor, panel, frame,
            oos_start=pd.Period("2023-07", freq="M"),
            oos_end=pd.Period("2026-06", freq="M"),
            data_cutoff="2023-06-30", discovery_ic=.05,
            confirmation_signal_contract=contract,
        )


def test_gold_publication_materializes_sql_once_then_verifies_staging():
    source = inspect.getsource(run_script.publish_revealed_campaign)
    assert source.count("_populate_gold_value_temp(") == 1
    assert '"campaign_gold_values"' in source
    assert '"campaign_gold_verify"' not in source


def test_neutralized_ic_requires_thirty_percent_of_investable_ic(monkeypatch):
    months = pd.period_range("2020-01", periods=60, freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "ym": months,
        "trade_date": months.to_timestamp(how="end").normalize(),
        "in_universe": True,
        "market_cap": 100.0,
        "adj_close": 100.0,
        "total_return_close": 100.0,
            "adv20": 1.0,
            "market": "KOSPI",
            "instrument_type": "common_stock",
            "f_candidate": 100.0,
        "fwd_opt": 0.0,
        "fwd_mid": 0.0,
        "fwd_pess": 0.0,
    })
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta=dict(RETURN_META),
    )
    factor = Factor(
        name="candidate", category="other", hypothesis="중립화 유지율 경계",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    monkeypatch.setattr(
        gate, "_ic_series",
        lambda *_args, **_kwargs: pd.Series(np.tile([.05, .15], 30)),
    )
    monkeypatch.setattr(gate, "backtest", lambda *_args, **_kwargs: None)

    def evaluate_with(neutral_ic):
        measured = iter([.10, .10, neutral_ic])
        monkeypatch.setattr(
            gate, "_hac_mean_test",
            lambda _series: (next(measured), 5.0, .001),
        )
        return gate.evaluate(factor, panel, frame, phase="discovery")

    below = evaluate_with(.02999)
    below_check = next(
        item for item in below.checks if item.name.endswith("IC·유지율")
    )
    assert below.metrics["neutral_ic"] > gate.TH["neutral_ic"]
    assert below.metrics["neutral_ic_retention"] < .30
    assert below_check.passed is False

    at_floor = evaluate_with(.03)
    at_floor_check = next(
        item for item in at_floor.checks if item.name.endswith("IC·유지율")
    )
    assert at_floor.metrics["neutral_ic_retention"] == pytest.approx(.30)
    assert at_floor_check.passed is True


def test_gold_signal_overlap_accepts_point_seven_and_rejects_above(monkeypatch):
    months = pd.period_range("2020-01", periods=60, freq="M")
    asset_ids = np.arange(1, 51)
    frame = pd.DataFrame([
        {
            "asset_id": int(asset_id),
            "ym": month,
            "trade_date": month.to_timestamp(how="end").normalize(),
            "in_universe": True,
            "market_cap": float(asset_id + 100),
            "adj_close": 100.0,
            "total_return_close": 100.0,
                "adv20": float(asset_id + 1),
                "market": "KOSPI",
                "instrument_type": "common_stock",
                "f_candidate": float(asset_id + 100),
            "fwd_opt": 0.0,
            "fwd_mid": 0.0,
            "fwd_pess": 0.0,
        }
        for month in months
        for asset_id in asset_ids
    ])
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta=dict(RETURN_META),
    )
    factor = Factor(
        name="candidate", category="other", hypothesis="Gold 중복 경계",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    monkeypatch.setattr(
        gate, "_ic_series",
        lambda *_args, **_kwargs: pd.Series(
            np.tile([.05, .15], 30), index=months,
        ),
    )
    monkeypatch.setattr(gate, "_hac_mean_test", lambda _series: (.10, 5.0, .001))
    monkeypatch.setattr(gate, "backtest", lambda *_args, **_kwargs: None)
    measured_correlation = [.70]
    monkeypatch.setattr(
        gate.stats, "spearmanr",
        lambda *_args, **_kwargs: SimpleNamespace(statistic=measured_correlation[0]),
    )
    existing = {
        "approved": pd.Series(frame["asset_id"].to_numpy(dtype=float), index=frame.index),
    }

    at_floor = gate.evaluate(
        factor, panel, frame, existing=existing, phase="discovery",
    )
    check = next(item for item in at_floor.checks if item.name == "Gold 신호 직교성")
    assert check.passed is True
    assert at_floor.metrics["max_gold_signal_corr"] == pytest.approx(.70)

    measured_correlation[0] = .7001
    above = gate.evaluate(
        factor, panel, frame, existing=existing, phase="discovery",
    )
    assert next(
        item for item in above.checks if item.name == "Gold 신호 직교성"
    ).passed is False

    unavailable = gate.evaluate(
        factor, panel, frame,
        existing={"approved": pd.Series(np.nan, index=frame.index)},
        phase="discovery",
    )
    unavailable_check = next(
        item for item in unavailable.checks if item.name == "Gold 신호 직교성"
    )
    assert unavailable_check.passed is False
    assert "36개월 미만" in unavailable_check.note

    measured_correlation[0] = .70
    one_month = pd.Series(np.nan, index=frame.index)
    one_month.loc[frame["ym"].eq(months[0])] = frame.loc[
        frame["ym"].eq(months[0]), "asset_id"
    ].to_numpy(dtype=float)
    one_month_result = gate.evaluate(
        factor, panel, frame, existing={"approved": one_month}, phase="discovery",
    )
    one_month_check = next(
        item for item in one_month_result.checks if item.name == "Gold 신호 직교성"
    )
    assert one_month_result.metrics["gold_signal_comparison_months"] == {"approved": 1}
    assert one_month_check.passed is False


def test_approved_catalog_without_values_fails_t5_closed(monkeypatch):
    frame = pd.DataFrame({
        "asset_id": [1, 2],
        "ym": pd.PeriodIndex(["2023-01", "2023-01"], freq="M"),
    })
    monkeypatch.setattr(
        run_script.silver, "load_approved_factor_keys",
        lambda _conn: ["approved_without_values"],
    )
    monkeypatch.setattr(
        run_script.silver, "load_approved_values",
        lambda _conn: pd.DataFrame(
            columns=["factor_key", "asset_id", "as_of_date", "value"]
        ),
    )

    signals = run_script._approved_signals(object(), frame)

    assert list(signals) == ["approved_without_values"]
    assert signals["approved_without_values"].isna().all()


def test_deferred_fdr_is_pending_not_a_false_failure():
    result = gate.Result(
        factor="x", definition_hash="hash",
        metrics={"ic_p_investable": .01},
        labels=["oos_sealed"],
        checks=[gate.Check("T4.3", "다중검정 FDR", None)],
    )
    gate.apply_multiple_testing([result], defer=True)
    assert not result.failed
    assert result.pending[0].name == "다중검정 FDR"
    assert result.verdict == gate.Verdict.PROVISIONAL


def test_discovery_fdr_counts_registered_definitions_without_ic_pvalues():
    result = gate.Result(
        factor="x", definition_hash="hash",
        metrics={"ic_p_investable": .001},
        checks=[gate.Check("T4.3", "다중검정 FDR", None)],
    )
    gate.apply_multiple_testing([result], total_trials=100)
    assert result.metrics["fdr_qvalue"] > gate.TH["fdr_q"]
    assert result.verdict == gate.Verdict.REJECT


def test_oos_pvalues_are_corrected_as_one_qualified_family():
    results = [
        gate.Result(
            factor=name, definition_hash=name,
            metrics={"oos_ic_p": pvalue},
            checks=[
                gate.Check("T4.1", "고정 OOS IC", True),
                gate.Check("T4.3", "다중검정 FDR", True),
            ],
        )
        for name, pvalue in (("a", .06), ("b", .07))
    ]
    gate.apply_oos_multiple_testing(results)
    assert all(result.metrics["oos_fdr_qvalue"] > gate.TH["fdr_q"] for result in results)
    assert all(result.verdict == gate.Verdict.REJECT for result in results)
    assert all(any(check.name == "OOS 다중검정 FDR" for check in result.failed) for result in results)


def test_missing_oos_pvalue_is_an_explicit_not_testable_failure():
    result = gate.Result(
        factor="a", definition_hash="a",
        checks=[
            gate.Check("T4.1", "고정 OOS IC", False),
            gate.Check("T4.3", "다중검정 FDR", True),
        ],
    )
    gate.apply_oos_multiple_testing([result])
    check = next(check for check in result.checks if check.name == "OOS 다중검정 FDR")
    assert check.passed is False
    assert result.metrics["oos_fdr_status"] == "NOT_TESTABLE"
    assert result.metrics["oos_fdr_qvalue"] == 1.0
    assert result.verdict == gate.Verdict.REJECT


def test_oos_early_failure_preserves_the_frozen_window():
    factor = Factor(
        name="broken", category="other", hypothesis="계산 실패", predicted_sign=1,
        compute=lambda frame: frame["missing_input"],
    )
    frame = pd.DataFrame({"asset_id": [1], "ym": [pd.Period("2030-01", freq="M")]})
    panel = Panel(frame, pd.Series(dtype="datetime64[ns]"), meta={})
    result = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=pd.Period("2030-01", freq="M"),
        oos_end=pd.Period("2032-12", freq="M"),
        data_cutoff="2029-12-31",
        discovery_ic=.03,
    )
    assert result.metrics["oos_start"] == "2030-01"
    assert result.metrics["oos_end"] == "2032-12"
    assert result.metrics["oos_months"] == 0
    assert result.tier_failed("T0")


@pytest.mark.parametrize("invalid_ic", [None, np.nan, 0.0, -.01])
def test_confirmation_discovery_ic_preflight_fails_the_whole_batch(invalid_ic):
    valid = gate.Result(
        factor="valid", definition_hash="valid", metrics={"ic_investable": .03},
    )
    invalid = gate.Result(
        factor="invalid", definition_hash="invalid",
        metrics={"ic_investable": invalid_ic},
    )
    with pytest.raises(ValueError, match="부분 OOS 공개"):
        run_script._assert_confirmation_discovery_ics([valid, invalid])
    run_script._assert_confirmation_discovery_ics([valid])


def test_oos_requires_absolute_floor_and_half_of_discovery_ic(monkeypatch):
    months = pd.period_range("2030-01", periods=36, freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "ym": months,
        "in_universe": True,
        "market_cap": 100.0,
        "adj_close": 100.0,
        "total_return_close": 100.0,
        "adv20": 1.0,
        "market": "KOSPI",
        "instrument_type": "common_stock",
        "f_candidate": 100.0,
        "fwd_mid": 0.0,
    })
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta=dict(RETURN_META),
    )
    factor = Factor(
        name="candidate", category="other", hypothesis="경계값 검사",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )

    measured_ic = [.0199]
    monkeypatch.setattr(
        gate, "_ic_series", lambda *_args, **_kwargs: pd.Series([0.0] * 36),
    )
    monkeypatch.setattr(
        gate, "_hac_mean_test",
        lambda _series: (measured_ic[0], 5.0, .001),
    )
    below = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=months[0], oos_end=months[-1], data_cutoff="2029-12-31",
        discovery_ic=.03,
    )
    assert next(check for check in below.checks if check.name == "고정 OOS IC").passed is False

    measured_ic[0] = .02
    at_floor = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=months[0], oos_end=months[-1], data_cutoff="2029-12-31",
        discovery_ic=.03,
    )
    assert next(
        check for check in at_floor.checks if check.name == "고정 OOS IC"
    ).passed is True
    assert at_floor.metrics["oos_discovery_ic"] == pytest.approx(.03)
    assert at_floor.metrics["oos_ic_retention"] == pytest.approx(2 / 3)
    assert at_floor.metrics["oos_required_ic"] == pytest.approx(.02)

    measured_ic[0] = .0299
    below_retention = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=months[0], oos_end=months[-1], data_cutoff="2029-12-31",
        discovery_ic=.06,
    )
    assert below_retention.metrics["oos_ic"] > gate.TH["oos_ic"]
    assert below_retention.metrics["oos_ic_retention"] < .50
    assert next(
        check for check in below_retention.checks if check.name == "고정 OOS IC"
    ).passed is False

    measured_ic[0] = .03
    at_retention_floor = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=months[0], oos_end=months[-1], data_cutoff="2029-12-31",
        discovery_ic=.06,
    )
    assert at_retention_floor.metrics["oos_ic_retention"] == pytest.approx(.50)
    assert at_retention_floor.metrics["oos_required_ic"] == pytest.approx(.03)
    assert next(
        check for check in at_retention_floor.checks if check.name == "고정 OOS IC"
    ).passed is True


@pytest.mark.parametrize("discovery_ic", [None, np.nan, 0.0, -.01])
def test_oos_without_valid_discovery_ic_fails_closed(monkeypatch, discovery_ic):
    months = pd.period_range("2030-01", periods=36, freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "ym": months,
        "in_universe": True,
        "market_cap": 100.0,
        "adj_close": 100.0,
        "total_return_close": 100.0,
        "adv20": 1.0,
        "market": "KOSPI",
        "instrument_type": "common_stock",
        "f_candidate": 100.0,
        "fwd_mid": 0.0,
    })
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta=dict(RETURN_META),
    )
    factor = Factor(
        name="candidate", category="other", hypothesis="Discovery IC 계약",
        predicted_sign=1, compute=lambda data: data["market_cap"],
    )
    monkeypatch.setattr(
        gate, "_ic_series", lambda *_args, **_kwargs: pd.Series([0.0] * 36),
    )
    monkeypatch.setattr(gate, "_hac_mean_test", lambda _series: (.03, 5.0, .001))
    result = gate.evaluate_oos(
        factor, panel, frame,
        oos_start=months[0], oos_end=months[-1], data_cutoff="2029-12-31",
        discovery_ic=discovery_ic,
    )
    assert next(
        check for check in result.checks if check.name == "고정 OOS IC"
    ).passed is False
    assert np.isnan(result.metrics["oos_ic_retention"])
    assert np.isnan(result.metrics["oos_required_ic"])


def test_null_calibration_outputs_campaign_family_units(monkeypatch):
    discovery_signals = {}
    events = []

    def fake_evaluate(factor, scoped_panel, scoped_df, **kwargs):
        events.append((factor.name, "discovery"))
        assert kwargs["phase"] == "discovery"
        assert scoped_df["trade_date"].max() == pd.Timestamp("2025-12-31")
        discovery_signals[factor.name] = scoped_df[f"f_{factor.name}"].copy()
        return gate.Result(
            factor=factor.name, definition_hash=factor.definition_hash,
            labels=["oos_sealed"],
            metrics={"ic_p_investable": .001, "ic_investable": .03},
            checks=[
                gate.Check("T4.3", "다중검정 FDR", None),
            ],
        )

    def fake_evaluate_oos(factor, _panel, confirmation_df, **_kwargs):
        events.append((factor.name, "oos"))
        assert _kwargs["discovery_ic"] == .03
        assert confirmation_df["ym"].max() == pd.Period("2029-01", freq="M")
        pd.testing.assert_series_equal(
            discovery_signals[factor.name],
            confirmation_df[f"f_{factor.name}"].reindex(
                discovery_signals[factor.name].index
            ),
        )
        return gate.Result(
            factor=factor.name, definition_hash=factor.definition_hash,
            metrics={"oos_ic_p": .001},
            checks=[gate.Check("T4.1", "고정 OOS IC", True)],
        )

    original_discovery_by = gate.apply_multiple_testing
    original_oos_by = gate.apply_oos_multiple_testing

    def spy_discovery_by(results, **kwargs):
        events.append((results[0].factor, "discovery_by"))
        return original_discovery_by(results, **kwargs)

    def spy_oos_by(results):
        events.append((results[0].factor if results else "none", "oos_by"))
        return original_oos_by(results)

    monkeypatch.setattr(gate, "evaluate", fake_evaluate)
    monkeypatch.setattr(gate, "evaluate_oos", fake_evaluate_oos)
    monkeypatch.setattr(gate, "apply_multiple_testing", spy_discovery_by)
    monkeypatch.setattr(gate, "apply_oos_multiple_testing", spy_oos_by)
    months = pd.period_range("2025-12", "2029-01", freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "ym": months,
        "trade_date": months.to_timestamp(how="end").normalize(),
        "in_universe": True,
        "market_cap": 100.0,
        "adj_close": np.arange(len(months), dtype=float) + 100.0,
        "total_return_close": np.arange(len(months), dtype=float) + 100.0,
        "adv20": 1.0,
    })
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"), meta=dict(RETURN_META),
    )
    output = null_engine.measure(
        panel, n=1, oos_start=pd.Period("2026-01", freq="M"),
        oos_end=pd.Period("2028-12", freq="M"),
        research_data_cutoff="2025-12-31",
        discovery_family_size=2, oos_family_size=2, verbose=False,
    )
    assert len(output) == 4
    assert set(output["kind"]) == {"random", "ar1_095", "ar1_0999", "frozen"}
    assert output["calibration_unit"].eq("null_campaign_family").all()
    assert output["generator_suite"].eq("null-v2").all()
    assert output["qualification_policy"].eq(QUALIFICATION_POLICY).all()
    assert output["neutral_ic_retention_floor"].eq(.30).all()
    assert output["oos_ic_retention_floor"].eq(.50).all()
    assert output["max_gold_signal_corr_threshold"].eq(.70).all()
    assert output["min_gold_signal_corr_months"].eq(36).all()
    assert output["revealed_count"].eq(2).all()
    assert [event for _, event in events] == [
        "discovery", "discovery", "discovery_by", "oos", "oos", "oos_by",
    ] * 4


def test_latest_context_is_a_compact_index_not_a_policy_or_report_copy():
    source = inspect.getsource(research.write_context)
    assert "## Next-loop constraints" not in source
    assert "factor.hypothesis" not in source
    assert "key_result" not in source
    assert 'row.get("report")' in source


def test_latest_context_exposes_unused_pit_inputs_but_not_research_outputs(tmp_path):
    frame = pd.DataFrame({
        "asset_id": [1],
        "ym": [pd.Period("2026-01", freq="M")],
        "capital_stock": [100.0],
        "market": ["KOSPI"],
        "instrument_type": ["common_stock"],
        "fwd_mid": [0.1],
        "f_example": [0.2],
    })
    panel = Panel(
        monthly=frame,
        dead=pd.Series(dtype="datetime64[ns]"),
        meta={"source": "RDS public Silver", **RETURN_META},
    )
    path = research.write_context(panel, Registry(), research_dir=tmp_path)
    context = path.read_text()
    inputs = context.split("## Registered factors", maxsplit=1)[0]
    assert "`capital_stock`" in inputs
    assert "`fwd_mid`" not in inputs
    assert "`f_example`" not in inputs


def test_latest_context_withholds_post_cutoff_history_without_active_campaign(tmp_path):
    (tmp_path / "history.jsonl").write_text(
        json.dumps({
            "cycle_id": "old-full-sample",
            "factor": "old_factor",
            "family": "old_family",
            "ruleset_version": "legacy",
            "data_cutoff": "2026-07-31",
            "verdict": "PROVISIONAL",
            "failed_checks": [],
            "report": "research/runs/old/report.md",
        }) + "\n",
        encoding="utf-8",
    )
    panel = Panel(
        monthly=pd.DataFrame({
            "asset_id": [1],
                "ym": [pd.Period("2023-06", freq="M")],
                "trade_date": [pd.Timestamp("2023-06-30")],
                "market": ["KOSPI"],
                "instrument_type": ["common_stock"],
        }),
        dead=pd.Series(dtype="datetime64[ns]"),
    )

    context = research.write_context(
        panel,
        Registry(),
        research_dir=tmp_path,
        context_cutoff="2023-06-30",
    ).read_text()

    assert "old-full-sample" in context
    assert "WITHHELD_POST_CUTOFF" in context
    assert "research/runs/old/report.md" not in context


def test_common_research_start_is_fixed_after_financial_warmup():
    assert gate.RESEARCH_START == pd.Period("2018-03", freq="M")
    months = pd.period_range("2017-01", "2018-05", freq="M")
    frame = pd.DataFrame({"ym": months})
    filtered = frame[frame["ym"].ge(gate.RESEARCH_START)]
    assert list(filtered["ym"].astype(str)) == ["2018-03", "2018-04", "2018-05"]


def test_stock_snapshot_fiscal_period_tie_matches_gold_priority():
    common = {
        "asset_id": 1,
        "period_end": "2023-12-31",
        "fs_type": "CFS",
        "available_date": "2024-03-31",
        "metric": "total_assets",
    }
    rows = pd.DataFrame([
        {**common, "fiscal_period": "Q3", "value": 333.0, "revision_key": "a"},
        {**common, "fiscal_period": "FY", "value": 444.0, "revision_key": "b"},
    ])

    snapshots = FU.materialize_pit(rows, verbose=False)

    assert snapshots.iloc[-1]["total_assets"] == 444.0


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
        "oos_start": ["2023-01"] * 100,
        "calibration_unit": ["null_campaign_family"] * 100,
        "generator_suite": ["null-v2"] * 100,
        "qualification_policy": [QUALIFICATION_POLICY] * 100,
        "kind": np.repeat(["random", "ar1_095", "ar1_0999", "frozen"], 25),
        "discovery_family_size": [5] * 100,
        "oos_family_size": [2] * 100,
        "discovery_family_digest": ["family-hash"] * 100,
        "oos_family_digest": ["oos-hash"] * 100,
        "gold_family_digest": ["gold-hash"] * 100,
        "confirmation_snapshot_digest": ["snapshot-hash"] * 100,
        "fdr_q": [gate.TH["fdr_q"]] * 100,
        "research_data_cutoff": ["2022-12-31"] * 100,
        "oos_end": ["2025-12"] * 100,
        "pass": [False] * 100,
    })
    gate.apply_null_calibration(
        [result], calibration, data_cutoff="2026-01-31", oos_start="2023-01",
        discovery_family_size=5, oos_family_size=2,
        discovery_family_digest="family-hash",
        oos_family_digest="oos-hash", gold_family_digest="gold-hash",
        confirmation_snapshot_digest="snapshot-hash",
        research_data_cutoff="2022-12-31", oos_end="2025-12",
        qualification_policy=QUALIFICATION_POLICY,
    )
    assert result.verdict == gate.Verdict.PROMOTE
    preflight = gate.assert_null_calibration(
        calibration, data_cutoff="2026-01-31", oos_start="2023-01",
        discovery_family_size=5, oos_family_size=2,
        discovery_family_digest="family-hash",
        oos_family_digest="oos-hash", gold_family_digest="gold-hash",
        confirmation_snapshot_digest="snapshot-hash",
        research_data_cutoff="2022-12-31", oos_end="2025-12",
        qualification_policy=QUALIFICATION_POLICY,
    )
    assert preflight["null_count"] == 100
    with pytest.raises(ValueError, match="OOS는 아직 계산하지 않았습니다"):
        gate.assert_null_calibration(
            None, data_cutoff="2026-01-31", oos_start="2023-01",
            discovery_family_size=5, oos_family_size=2,
            discovery_family_digest="family-hash",
            oos_family_digest="oos-hash", gold_family_digest="gold-hash",
            confirmation_snapshot_digest="snapshot-hash",
            research_data_cutoff="2022-12-31", oos_end="2025-12",
            qualification_policy=QUALIFICATION_POLICY,
        )
    wrong_boundary = gate.Result(
        factor="y", definition_hash="other",
        checks=[gate.Check("T4.3", "다중검정 FDR", True)],
    )
    gate.apply_null_calibration(
        [wrong_boundary], calibration,
        data_cutoff="2026-01-31", oos_start="2024-01",
        discovery_family_size=5, oos_family_size=2,
        discovery_family_digest="family-hash",
        oos_family_digest="oos-hash", gold_family_digest="gold-hash",
        confirmation_snapshot_digest="snapshot-hash",
        research_data_cutoff="2022-12-31", oos_end="2026-12",
        qualification_policy=QUALIFICATION_POLICY,
    )
    assert wrong_boundary.verdict == gate.Verdict.REJECT
    assert wrong_boundary.metrics["null_count"] == 0

    wrong_family = gate.Result(
        factor="z", definition_hash="third",
        checks=[gate.Check("T4.3", "다중검정 FDR", True)],
    )
    gate.apply_null_calibration(
        [wrong_family], calibration,
        data_cutoff="2026-01-31", oos_start="2023-01",
        discovery_family_size=5, oos_family_size=1,
        discovery_family_digest="family-hash",
        oos_family_digest="oos-hash", gold_family_digest="gold-hash",
        confirmation_snapshot_digest="snapshot-hash",
        research_data_cutoff="2022-12-31", oos_end="2025-12",
        qualification_policy=QUALIFICATION_POLICY,
    )
    assert wrong_family.verdict == gate.Verdict.REJECT
    assert wrong_family.metrics["null_count"] == 0

    wrong_policy = gate.Result(
        factor="policy", definition_hash="policy-hash",
        checks=[gate.Check("T4.3", "다중검정 FDR", True)],
    )
    gate.apply_null_calibration(
        [wrong_policy], calibration,
        data_cutoff="2026-01-31", oos_start="2023-01",
        discovery_family_size=5, oos_family_size=2,
        discovery_family_digest="family-hash",
        oos_family_digest="oos-hash", gold_family_digest="gold-hash",
        confirmation_snapshot_digest="snapshot-hash",
        research_data_cutoff="2022-12-31", oos_end="2025-12",
        qualification_policy="manual-selection-v0",
    )
    assert wrong_policy.verdict == gate.Verdict.REJECT
    assert wrong_policy.metrics["null_count"] == 0

    concentrated = calibration.copy()
    random_rows = concentrated.index[concentrated["kind"].eq("random")][:3]
    concentrated.loc[random_rows, "pass"] = True
    worst_kind = gate.Result(
        factor="w", definition_hash="fourth",
        checks=[gate.Check("T4.3", "다중검정 FDR", True)],
    )
    gate.apply_null_calibration(
        [worst_kind], concentrated,
        data_cutoff="2026-01-31", oos_start="2023-01",
        discovery_family_size=5, oos_family_size=2,
        discovery_family_digest="family-hash",
        oos_family_digest="oos-hash", gold_family_digest="gold-hash",
        confirmation_snapshot_digest="snapshot-hash",
        research_data_cutoff="2022-12-31", oos_end="2025-12",
        qualification_policy=QUALIFICATION_POLICY,
    )
    assert worst_kind.verdict == gate.Verdict.REJECT
    assert worst_kind.metrics["null_family_error_rate"] == pytest.approx(.03)
    assert worst_kind.metrics["null_worst_kind_error_rate"] == pytest.approx(.12)


def test_trial_ledger_counts_unique_definitions_and_freezes_oos():
    with tempfile.TemporaryDirectory() as directory:
        ledger = TrialLedger(Path(directory) / "trials.sqlite3")
        months = list(pd.period_range("2015-01", periods=120, freq="M"))
        first = ledger.fixed_oos_start(months)
        assert first == pd.Period("2022-01", freq="M")
        extended = months + list(pd.period_range("2025-01", periods=6, freq="M"))
        assert ledger.fixed_oos_start(extended) == first
        summary = ledger.summary(["a", "a", "b"])
        assert summary.count == 2
        assert summary.ic_count == 2
        scoped = ledger.summary(
            ["a"], external=[("legacy-gold", None, None)],
            ruleset_version=gate.RULESET_VERSION,
        )
        assert scoped.count == 2
        assert scoped.ic_count == 1


def test_trial_ledger_blocks_reentry_when_history_artifact_is_missing(tmp_path):
    factor = Factor(
        name="ledger_candidate",
        category="other",
        hypothesis="시행 원장 재진입 방지 테스트",
        predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )
    ledger = TrialLedger(tmp_path / "trials.sqlite3")
    ledger.record(
        factor,
        gate.Result(factor=factor.name, definition_hash=factor.definition_hash),
        data_cutoff="2023-06-30",
        ruleset_version=gate.RULESET_VERSION,
    )

    assert factor.definition_hash in ledger.definition_hashes()
    with pytest.raises(ValueError, match="시행 원장"):
        research.assert_new_candidate(
            factor,
            {},
            research_dir=tmp_path / "missing-history",
            attempted_definition_hashes=ledger.definition_hashes(),
        )


def test_trial_ledger_never_rewrites_first_observation(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.sqlite3")
    factor = Factor(
        name="candidate_x", category="other", hypothesis="가설",
        predicted_sign=1, compute=lambda frame: frame["market_cap"],
    )
    first = gate.Result(
        factor=factor.name, definition_hash=factor.definition_hash,
        verdict=gate.Verdict.PROVISIONAL,
        metrics={"ic_p_investable": .01, "net_ir": .2},
    )
    second = gate.Result(
        factor=factor.name, definition_hash=factor.definition_hash,
        verdict=gate.Verdict.REJECT,
        metrics={"ic_p_investable": .90, "net_ir": -1.0},
    )
    ledger.record(factor, first, data_cutoff="2026-01-31", ruleset_version="first")
    ledger.record(factor, second, data_cutoff="2027-01-31", ruleset_version="second")
    original = ledger.summary(ruleset_version="first")
    collision = ledger.summary(
        external=[(factor.definition_hash, None, None)], ruleset_version="first",
    )
    rewritten = ledger.summary(ruleset_version="second")
    assert original.pvalues == ((factor.definition_hash, .01),)
    assert collision.pvalues == original.pvalues
    assert rewritten.pvalues == ()


def test_candidate_loader_requires_preregistered_research_spec():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "candidate.py").write_text(
            """
from engine.factors import Factor

def compute(frame):
    return frame['market_cap']

FACTOR = Factor(name='candidate_x', category='other', hypothesis='가설',
                predicted_sign=1, compute=compute)
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


def test_candidate_batch_policy_blocks_family_formula_retests_and_low_diversity():
    net = Factor(
        name="net_variant", family="income_coverage", category="quality",
        hypothesis="세후이익", predicted_sign=1,
        needs=("net_income_ttm", "total_liabilities"),
        compute=_net_income_ratio,
    )
    pretax = Factor(
        name="pretax_variant", family="pretax_coverage", category="quality",
        hypothesis="세전이익", predicted_sign=1,
        needs=("pretax_income_ttm", "total_liabilities"),
        compute=_pretax_income_ratio,
    )
    formula = research_policy.candidate_batch_policy([net, pretax])
    assert "no_same_formula_variants_in_batch" in {
        row["rule"] for row in formula["violations"]
    }

    retest = research_policy.candidate_batch_policy(
        [pretax], existing_factors=[net],
    )
    assert retest["violations"][0]["rule"] == (
        "no_structural_retest_of_attempted_registry"
    )

    same_family = research_policy.candidate_batch_policy([
        net,
        Factor(
            name="same_family", family="income_coverage", category="value",
            hypothesis="같은 family", predicted_sign=1,
            compute=lambda frame: frame["market_cap"],
        ),
    ])
    assert "one_candidate_per_economic_family" in {
        row["rule"] for row in same_family["violations"]
    }

    narrow = [
        Factor(
            name=f"narrow_{index}", family=f"family_{index}",
            category="quality" if index < 3 else "value",
            hypothesis=str(index), predicted_sign=1,
            params={"candidate": index},
            compute=lambda frame: frame["market_cap"],
        )
        for index in range(5)
    ]
    artifact = research_policy.candidate_batch_policy(narrow)
    assert "minimum_mechanism_category_diversity" in {
        row["rule"] for row in artifact["violations"]
    }


def test_input_feasibility_fails_before_epoch_registration(tmp_path):
    factor = Factor(
        name="sparse_candidate", category="other", hypothesis="희소 입력",
        predicted_sign=1, compute=lambda frame: frame["market_cap"],
    )
    _start_campaign(tmp_path)
    failed = research_policy.input_feasibility_artifact(
        [factor], snapshot_digest="b" * 64,
        signal_start=str(gate.RESEARCH_START), signal_end="2023-05",
        metrics={factor.name: {"coverage": .49, "monthly_coverage_p10": .29}},
        minimum_coverage=gate.TH["coverage"],
        minimum_monthly_p10=gate.TH["monthly_coverage_p10"],
    )
    with pytest.raises(ValueError, match="입력 커버리지 사전검사"):
        epochs.start_epoch(
            tmp_path, "campaign-001", "epoch-001", [factor],
            strategy_digests=_strategy_digests([factor]),
            input_feasibility=failed,
        )
    assert epochs.load_campaign(tmp_path, "campaign-001")["epochs"] == []


def test_failure_bucket_distinguishes_wrong_sign_from_input_and_integrity():
    assert epochs._failure_bucket({"failed_tiers": ["T1.2"]}) == (
        "WRONG_SIGN_OR_NO_EDGE"
    )
    assert epochs._failure_bucket({"failed_tiers": ["T1.1"]}) == (
        "DATA_OR_INPUT_FEASIBILITY"
    )
    assert epochs._failure_bucket({"failed_tiers": ["T1.3"]}) == (
        "DATA_OR_INTEGRITY"
    )


def test_epoch_lifecycle_auto_qualifies_candidates_and_seals_oos(tmp_path):
    first = Factor(
        name="candidate_a", family="family_a", category="other",
        hypothesis="가설 A", predicted_sign=1, compute=lambda frame: frame["market_cap"],
    )
    second = Factor(
        name="candidate_b", family="family_b", category="other",
        hypothesis="가설 B", predicted_sign=-1, compute=lambda frame: frame["market_cap"],
    )
    campaign_path = _start_campaign(tmp_path)
    campaign = json.loads(campaign_path.read_text())
    assert campaign["oos"]["status"] == "SEALED"
    assert campaign["snapshot"]["data_cutoff"] == "2026-07-31"
    assert campaign["oos"]["start"] == "2023-07"
    assert campaign["discovery"] == {
        "data_cutoff": "2023-06-30",
        "signal_end": "2023-05", "return_end": "2023-06",
    }
    assert campaign["oos"]["signal_end"] == "2026-06"
    assert campaign["oos"]["required_data_month"] == "2026-07"
    assert campaign["oos"]["earliest_data_month"] == "2026-08"
    assert campaign["qualification_policy"] == QUALIFICATION_POLICY

    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", [first, second],
        strategy_digests=_strategy_digests([first, second]),
        input_feasibility=_input_feasibility([first, second]),
    )
    epochs.assert_candidate_ready(
        tmp_path, "campaign-001", "epoch-001", first,
        strategy_sha256=_strategy_sha(first),
    )
    changed = Factor(
        name="candidate_a", family="family_a", category="other",
        hypothesis="바뀐 가설", predicted_sign=1, compute=lambda frame: frame["market_cap"],
    )
    with pytest.raises(ValueError, match="정의가 변경"):
        epochs.assert_candidate_ready(
            tmp_path, "campaign-001", "epoch-001", changed,
            strategy_sha256=_strategy_sha(first),
        )

    qualified = gate.Result(
        factor=first.name, definition_hash=first.definition_hash,
        verdict=gate.Verdict.PROVISIONAL,
        metrics={"ic_p_investable": .001},
        labels=["oos_sealed", "discovery_pass"],
    )
    rejected = gate.Result(
        factor=second.name, definition_hash=second.definition_hash,
        verdict=gate.Verdict.REJECT,
        checks=[gate.Check("T2.1", "전체 IC 최소요건", False)],
        labels=["oos_sealed"],
    )
    epochs.mark_evaluated(
        tmp_path, "campaign-001", "epoch-001", first, qualified,
        strategy_sha256=_strategy_sha(first),
        report="research/runs/cycle-a/report.md", strongest_relationship=None,
    )
    with pytest.raises(ValueError, match="평가하지 않은"):
        epochs.close_epoch(tmp_path, "campaign-001", "epoch-001")
    epochs.mark_evaluated(
        tmp_path, "campaign-001", "epoch-001", second, rejected,
        strategy_sha256=_strategy_sha(second),
        report="research/runs/cycle-b/report.md",
        strongest_relationship={"factor": "old", "abs_median_spearman": .91},
    )
    reflection, reflection_json = epochs.close_epoch(
        tmp_path, "campaign-001", "epoch-001"
    )
    assert "OOS 상태: **SEALED**" in reflection.read_text()
    reflection_payload = json.loads(reflection_json.read_text())
    assert reflection_payload["duplicates"] == ["candidate_b"]
    assert reflection_payload["discovery_fdr_status"] == "PENDING_UNTIL_CAMPAIGN_FINALIZE"
    epochs.finalize_campaign(
        tmp_path, "campaign-001",
        batch_orthogonality=_batch_orthogonality([first]),
    )
    finalized = epochs.load_campaign(tmp_path, "campaign-001")
    assert finalized["status"] == "AWAITING_IMPLEMENTATION"
    assert [row["name"] for row in finalized["qualified_factors"]] == ["candidate_a"]
    assert finalized["qualified_factors"][0]["strategy_sha256"] == _strategy_sha(first)
    fdr = json.loads(Path(finalized["discovery_multiple_testing"]).read_text())
    assert fdr["method"] == "Benjamini-Yekutieli"
    assert fdr["qualification_policy"] == QUALIFICATION_POLICY
    assert fdr["results"][0]["status"] == "PASS"
    assert fdr["family_digest"] == finalized["discovery_family_digest"]
    assert epochs.load_discovery_multiple_testing(
        tmp_path, "campaign-001",
    )["family_digest"] == finalized["discovery_family_digest"]
    tampered = json.loads(json.dumps(fdr))
    tampered["results"][0]["qvalue"] = .99
    Path(finalized["discovery_multiple_testing"]).write_text(
        json.dumps(tampered), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="artifact 무결성"):
        epochs.load_discovery_multiple_testing(tmp_path, "campaign-001")
    Path(finalized["discovery_multiple_testing"]).write_text(
        json.dumps(fdr), encoding="utf-8",
    )
    campaign_path = tmp_path / "campaigns/campaign-001/manifest.json"
    authentic_campaign = json.loads(campaign_path.read_text())
    manually_selected = json.loads(json.dumps(authentic_campaign))
    manually_selected["qualified_factors"] = []
    manually_selected["oos_family_digest"] = epochs._family_digest([])
    campaign_path.write_text(json.dumps(manually_selected), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact 무결성"):
        epochs.load_discovery_multiple_testing(tmp_path, "campaign-001")
    campaign_path.write_text(json.dumps(authentic_campaign), encoding="utf-8")
    evidence = _implementation_evidence(first, finalized)
    with pytest.raises(ValueError, match="자동 통과 후보 전체"):
        epochs.record_implementation_verification(
            tmp_path, "campaign-001", [],
        )
    artifact = epochs.record_implementation_verification(
        tmp_path, "campaign-001", [evidence],
    )
    assert artifact.exists()
    binding = [_binding_from_evidence(evidence)]
    changed_binding = [dict(binding[0], implementation_sha256="d" * 64)]
    with pytest.raises(ValueError, match="변경됐습니다"):
        epochs.assert_reveal_ready(
            tmp_path, "campaign-001", "2026-08-15",
            snapshot_digest="a" * 64,
            current_bindings=changed_binding,
        )
    changed_strategy_binding = [dict(binding[0], strategy_sha256="f" * 64)]
    with pytest.raises(ValueError, match="변경됐습니다"):
        epochs.assert_reveal_ready(
            tmp_path, "campaign-001", "2026-08-15",
            snapshot_digest="a" * 64,
            current_bindings=changed_strategy_binding,
        )
    with pytest.raises(ValueError, match="snapshot digest"):
        epochs.assert_reveal_ready(
            tmp_path, "campaign-001", "2026-08-15",
            snapshot_digest="f" * 64,
            current_bindings=binding,
        )
    with pytest.raises(ValueError, match="아직 정확한 36개월"):
        epochs.assert_reveal_ready(
            tmp_path, "campaign-001", "2026-07-31",
            snapshot_digest="a" * 64,
            current_bindings=binding,
        )
    with pytest.raises(ValueError, match="너무 이릅니다"):
        epochs.assert_reveal_ready(
            tmp_path, "campaign-001", "2026-08-03",
            snapshot_digest="a" * 64,
            current_bindings=binding,
        )
    ready = epochs.assert_reveal_ready(
        tmp_path, "campaign-001", "2026-08-15",
        snapshot_digest="a" * 64,
        current_bindings=binding,
    )
    assert ready["qualified_factors"][0]["definition_hash"] == first.definition_hash


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("discovery", "return_end", "2023-07"),
        ("oos", "signal_end", "2026-07"),
        ("oos", "required_data_month", "2026-08"),
        ("oos", "earliest_data_month", "2026-09"),
    ],
)
def test_campaign_boundary_tampering_is_rejected(tmp_path, section, field, value):
    campaign_path = _start_campaign(tmp_path)
    campaign = json.loads(campaign_path.read_text())
    campaign[section][field] = value
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    with pytest.raises(ValueError, match="경계 무결성"):
        epochs.assert_reveal_ready(
            tmp_path, "campaign-001", "2026-08-15",
            snapshot_digest="a" * 64,
            current_bindings=[],
        )


def test_campaign_enforces_oos_floor_and_nonoverlapping_active_holdouts(tmp_path):
    with pytest.raises(ValueError, match="현재 ruleset 고정값 36"):
        _start_campaign(tmp_path, "campaign-short", min_oos_months=35)
    _start_campaign(tmp_path, "campaign-001")
    with pytest.raises(ValueError, match="봉인 OOS 기간이 겹칩니다"):
        _start_campaign(tmp_path, "campaign-002")
    second = _start_campaign(
        tmp_path,
        "campaign-003",
        discovery_data_cutoff="2020-05-31",
        snapshot_cutoff="2023-06-30",
    )
    assert second.exists()


def test_campaign_freezes_epoch_count_and_allows_only_one_open_epoch(tmp_path):
    _start_campaign(tmp_path, planned_epoch_count=2)
    first = Factor(
        name="candidate_a", family="family_a", category="other",
        hypothesis="가설 A", predicted_sign=1, params={"candidate": "a"},
        compute=lambda frame: frame["market_cap"],
    )
    second = Factor(
        name="candidate_b", family="family_b", category="other",
        hypothesis="가설 B", predicted_sign=1, params={"candidate": "b"},
        compute=lambda frame: frame["market_cap"],
    )
    third = Factor(
        name="candidate_c", family="family_c", category="other",
        hypothesis="가설 C", predicted_sign=1, params={"candidate": "c"},
        compute=lambda frame: frame["market_cap"],
    )
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", [first],
        strategy_digests=_strategy_digests([first]),
        input_feasibility=_input_feasibility([first]),
    )
    with pytest.raises(ValueError, match="동시에 둘 이상의 epoch"):
        epochs.start_epoch(
            tmp_path, "campaign-001", "epoch-002", [second],
            strategy_digests=_strategy_digests([second]),
            input_feasibility=_input_feasibility([second]),
        )
    result = gate.Result(
        factor=first.name, definition_hash=first.definition_hash,
        verdict=gate.Verdict.REJECT,
    )
    epochs.mark_evaluated(
        tmp_path, "campaign-001", "epoch-001", first, result,
        strategy_sha256=_strategy_sha(first),
        report="research/runs/a/report.md", strongest_relationship=None,
    )
    epochs.close_epoch(tmp_path, "campaign-001", "epoch-001")
    with pytest.raises(ValueError, match="사전 고정한 epoch 수"):
        epochs.finalize_campaign(
            tmp_path, "campaign-001", batch_orthogonality=_batch_orthogonality([]),
        )
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-002", [second],
        strategy_digests=_strategy_digests([second]),
        input_feasibility=_input_feasibility([second]),
    )
    second_result = gate.Result(
        factor=second.name, definition_hash=second.definition_hash,
        verdict=gate.Verdict.REJECT,
    )
    epochs.mark_evaluated(
        tmp_path, "campaign-001", "epoch-002", second, second_result,
        strategy_sha256=_strategy_sha(second),
        report="research/runs/b/report.md", strongest_relationship=None,
    )
    epochs.close_epoch(tmp_path, "campaign-001", "epoch-002")
    with pytest.raises(ValueError, match="사전 고정한 epoch 수"):
        epochs.start_epoch(
            tmp_path, "campaign-001", "epoch-003", [third],
            strategy_digests=_strategy_digests([third]),
            input_feasibility=_input_feasibility([third]),
        )


def test_reverse_creation_order_cannot_overlap_signal_and_forward_return(tmp_path):
    _start_campaign(tmp_path, "campaign-later")
    with pytest.raises(ValueError, match="봉인 OOS 기간이 겹칩니다"):
        _start_campaign(
            tmp_path,
            "campaign-earlier",
            discovery_data_cutoff="2022-05-31",
            snapshot_cutoff="2025-06-30",
        )


def test_campaign_can_close_without_qualified_factors_instead_of_optional_stopping(tmp_path):
    factor = Factor(
        name="candidate_a", category="other", hypothesis="가설", predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )
    _start_campaign(tmp_path)
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", [factor],
        strategy_digests=_strategy_digests([factor]),
        input_feasibility=_input_feasibility([factor]),
    )
    rejected = gate.Result(
        factor=factor.name, definition_hash=factor.definition_hash,
        verdict=gate.Verdict.REJECT,
        checks=[gate.Check("T2.1", "투자가능 IC 최소요건", False)],
    )
    epochs.mark_evaluated(
        tmp_path, "campaign-001", "epoch-001", factor, rejected,
        strategy_sha256=_strategy_sha(factor),
        report="research/runs/candidate_a/report.md", strongest_relationship=None,
    )
    epochs.close_epoch(tmp_path, "campaign-001", "epoch-001")
    epochs.finalize_campaign(
        tmp_path, "campaign-001", batch_orthogonality=_batch_orthogonality([]),
    )
    campaign = epochs.load_campaign(tmp_path, "campaign-001")
    assert campaign["status"] == "CLOSED_NO_QUALIFIED"
    assert campaign["qualified_factors"] == []
    assert campaign["oos"]["status"] == "NOT_USED"


def test_campaign_finalize_auto_qualifies_every_discovery_pass(tmp_path):
    factors = [
        Factor(
            name=name, family=name, category="other", hypothesis=name,
            predicted_sign=1, params={"candidate": name},
            compute=lambda frame: frame["market_cap"],
        )
        for name in ("candidate_a", "candidate_b", "candidate_c")
    ]
    _start_campaign(tmp_path)
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", factors,
        strategy_digests=_strategy_digests(factors),
        input_feasibility=_input_feasibility(factors),
    )
    for factor, pvalue in zip(factors, (.01, .02, .90), strict=True):
        result = gate.Result(
            factor=factor.name, definition_hash=factor.definition_hash,
            verdict=gate.Verdict.PROVISIONAL,
            metrics={"ic_p_investable": pvalue},
            labels=["oos_sealed", "fdr_pending"],
            checks=[gate.Check("T4.3", "다중검정 FDR", None)],
        )
        epochs.mark_evaluated(
            tmp_path, "campaign-001", "epoch-001", factor, result,
            strategy_sha256=_strategy_sha(factor),
            report=f"research/runs/{factor.name}/report.md",
            strongest_relationship=None,
        )
    epochs.close_epoch(tmp_path, "campaign-001", "epoch-001")
    epoch = epochs.load_epoch(tmp_path, "campaign-001", "epoch-001")
    assert [row["fdr_status"] for row in epoch["candidates"]] == [
        "PENDING", "PENDING", "PENDING",
    ]
    epochs.finalize_campaign(
        tmp_path, "campaign-001",
        batch_orthogonality=_batch_orthogonality(factors[:2]),
    )
    epoch = epochs.load_epoch(tmp_path, "campaign-001", "epoch-001")
    assert [row["fdr_status"] for row in epoch["candidates"]] == ["PASS", "PASS", "FAIL"]
    assert [row["verdict"] for row in epoch["candidates"]] == [
        "PROVISIONAL", "PROVISIONAL", "REJECT",
    ]
    campaign = epochs.load_campaign(tmp_path, "campaign-001")
    assert [row["name"] for row in campaign["qualified_factors"]] == [
        "candidate_a", "candidate_b",
    ]
    assert campaign["qualification_policy"] == QUALIFICATION_POLICY


def test_campaign_suppresses_batch_duplicate_before_implementation(tmp_path):
    factors = [
        Factor(
            name=name, family=name, category="other", hypothesis=name,
            predicted_sign=1, params={"candidate": name},
            compute=lambda frame: frame["market_cap"],
        )
        for name in ("alpha_candidate", "beta_candidate")
    ]
    _start_campaign(tmp_path)
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", factors,
        strategy_digests=_strategy_digests(factors),
        input_feasibility=_input_feasibility(factors),
    )
    for factor in factors:
        epochs.mark_evaluated(
            tmp_path, "campaign-001", "epoch-001", factor,
            gate.Result(
                factor=factor.name, definition_hash=factor.definition_hash,
                verdict=gate.Verdict.PROVISIONAL,
                metrics={"ic_p_investable": .001},
            ),
            strategy_sha256=_strategy_sha(factor),
            report=f"research/runs/{factor.name}/report.md",
            strongest_relationship=None,
        )
    epochs.close_epoch(tmp_path, "campaign-001", "epoch-001")
    epochs.finalize_campaign(
        tmp_path, "campaign-001",
        batch_orthogonality=_conflicting_batch_orthogonality(factors),
    )
    campaign = epochs.load_campaign(tmp_path, "campaign-001")
    assert [row["name"] for row in campaign["qualified_factors"]] == [
        "alpha_candidate",
    ]
    artifact = epochs.load_discovery_multiple_testing(
        tmp_path, "campaign-001",
    )
    statuses = {
        row["factor"]: row["qualification_status"]
        for row in artifact["results"]
    }
    assert statuses == {
        "alpha_candidate": "QUALIFIED",
        "beta_candidate": "SUPPRESSED_BATCH_CORRELATION",
    }

    current_history = {
            "cycle_id": "candidate_a", "factor": "candidate_a",
            "family": "candidate_a", "ruleset_version": gate.RULESET_VERSION,
            "campaign_id": "campaign-001", "data_cutoff": "2023-06-30",
            "verdict": "PROVISIONAL", "failed_checks": [],
            "report": "research/runs/candidate_a/report.md",
        }
    exposed_history = {
        "cycle_id": "old-full-sample", "factor": "old_factor",
        "family": "old_family", "ruleset_version": "legacy",
        "data_cutoff": "2026-07-31", "verdict": "PROVISIONAL",
        "failed_checks": [], "report": "research/runs/old/report.md",
    }
    (tmp_path / "history.jsonl").write_text(
        json.dumps(current_history) + "\n" + json.dumps(exposed_history) + "\n",
        encoding="utf-8",
    )
    panel = Panel(
        monthly=pd.DataFrame({
            "asset_id": [1], "ym": [pd.Period("2023-06", freq="M")],
            "trade_date": [pd.Timestamp("2023-06-30")],
                "adj_close": [1.0], "total_return_close": [1.0],
                "market_cap": [100.0], "adv20": [10.0],
                "trading_value": [10.0], "shares": [1.0], "market": ["KOSPI"],
                "instrument_type": ["common_stock"],
        }),
        dead=pd.Series(dtype="datetime64[ns]"),
        meta={"source": "RDS public Silver", **RETURN_META},
    )
    context = research.write_context(panel, Registry(), research_dir=tmp_path).read_text()
    assert "| `candidate_a` | `candidate_a` | `candidate_a` |" in context
    assert "| `fr-3.14.0` | PROVISIONAL | - |" in context
    assert "old-full-sample" in context
    assert "WITHHELD_POST_CUTOFF" in context
    assert "research/runs/old/report.md" not in context


def test_campaign_fdr_is_identical_when_epoch_order_is_reversed(tmp_path):
    pvalues = {"candidate_a": .01, "candidate_b": .02}

    def run_campaign(root, order):
        _start_campaign(root, planned_epoch_count=len(order))
        factors = {}
        for index, name in enumerate(order, 1):
            factor = Factor(
                name=name, family=name, category="other", hypothesis=name,
                predicted_sign=1, params={"candidate": name},
                compute=lambda frame: frame["market_cap"],
            )
            factors[name] = factor
            epoch_id = f"epoch-{index:03d}"
            epochs.start_epoch(
                root, "campaign-001", epoch_id, [factor],
                strategy_digests=_strategy_digests([factor]),
                input_feasibility=_input_feasibility([factor]),
            )
            result = gate.Result(
                factor=name, definition_hash=factor.definition_hash,
                verdict=gate.Verdict.PROVISIONAL,
                metrics={"ic_p_investable": pvalues[name]},
                checks=[gate.Check("T4.3", "다중검정 FDR", None)],
            )
            epochs.mark_evaluated(
                root, "campaign-001", epoch_id, factor, result,
                strategy_sha256=_strategy_sha(factor),
                report=f"research/runs/{name}/report.md",
                strongest_relationship=None,
            )
            epochs.close_epoch(root, "campaign-001", epoch_id)
        epochs.finalize_campaign(
            root, "campaign-001",
            batch_orthogonality=_batch_orthogonality(list(factors.values())),
        )
        campaign = epochs.load_campaign(root, "campaign-001")
        artifact = json.loads(Path(campaign["discovery_multiple_testing"]).read_text())
        return {
            "qvalues": {row["factor"]: row["qvalue"] for row in artifact["results"]},
            "qualified": [row["name"] for row in campaign["qualified_factors"]],
            "artifact_digest": campaign["discovery_multiple_testing_digest"],
        }

    forward = run_campaign(tmp_path / "forward", ("candidate_a", "candidate_b"))
    reverse = run_campaign(tmp_path / "reverse", ("candidate_b", "candidate_a"))
    assert forward == reverse


def test_epoch_16_campaign_is_read_only_under_epoch_17(tmp_path):
    factor = Factor(
        name="candidate_a", category="other", hypothesis="가설", predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )
    campaign_path = _start_campaign(tmp_path)
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", [factor],
        strategy_digests=_strategy_digests([factor]),
        input_feasibility=_input_feasibility([factor]),
    )
    campaign = json.loads(campaign_path.read_text())
    campaign["protocol_version"] = "epoch-1.6"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    with pytest.raises(ValueError, match="protocol"):
        epochs.assert_candidate_ready(
            tmp_path, "campaign-001", "epoch-001", factor,
            strategy_sha256=_strategy_sha(factor),
        )


def test_epoch_16_finalized_evidence_is_publish_compatible_but_not_reopened(tmp_path):
    factor = Factor(
        name="candidate_a", family="family_a", category="other",
        hypothesis="가설", predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )
    campaign_path = _start_campaign(tmp_path)
    epochs.start_epoch(
        tmp_path, "campaign-001", "epoch-001", [factor],
        strategy_digests=_strategy_digests([factor]),
        input_feasibility=_input_feasibility([factor]),
    )
    epochs.mark_evaluated(
        tmp_path, "campaign-001", "epoch-001", factor,
        gate.Result(
            factor=factor.name, definition_hash=factor.definition_hash,
            verdict=gate.Verdict.PROVISIONAL,
            metrics={"ic_p_investable": .001},
        ),
        strategy_sha256=_strategy_sha(factor),
        report="research/runs/candidate_a/report.md",
        strongest_relationship=None,
    )
    epochs.close_epoch(tmp_path, "campaign-001", "epoch-001")
    epochs.finalize_campaign(
        tmp_path, "campaign-001",
        batch_orthogonality=_batch_orthogonality([factor]),
    )
    campaign = epochs.load_campaign(tmp_path, "campaign-001")
    evidence = _implementation_evidence(factor, campaign)
    implementation_path = epochs.record_implementation_verification(
        tmp_path, "campaign-001", [evidence],
    )

    campaign = json.loads(campaign_path.read_text())
    implementation_payload = json.loads(implementation_path.read_text())
    campaign["protocol_version"] = "epoch-1.6"
    campaign["ruleset_version"] = "fr-3.13.0"
    implementation_payload["protocol_version"] = "epoch-1.6"
    implementation_payload["ruleset_version"] = "fr-3.13.0"
    campaign["implementation_verification_digest"] = epochs._payload_digest(
        implementation_payload
    )
    implementation_path.write_text(
        json.dumps(implementation_payload), encoding="utf-8",
    )
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")

    with pytest.raises(ValueError, match="protocol"):
        epochs.load_implementation_verification(tmp_path, "campaign-001")
    loaded = epochs.load_implementation_verification(
        tmp_path, "campaign-001",
        current_bindings=[_binding_from_evidence(evidence)],
        finalized_publication=True,
    )
    assert loaded["protocol_version"] == "epoch-1.6"

    campaign["status"] = "REVEALED"
    campaign["oos"]["status"] = "REVEALED"
    campaign["oos"]["revealed_at"] = "2026-08-15T00:00:00Z"
    confirmation = {
        "protocol_version": "epoch-1.6",
        "campaign_id": "campaign-001",
        "revealed_at": campaign["oos"]["revealed_at"],
        "oos_start": campaign["oos"]["start"],
        "oos_end": campaign["oos"]["signal_end"],
        "confirmations": [{
            "factor": factor.name,
            "definition_hash": factor.definition_hash,
            "strategy_sha256": _strategy_sha(factor),
            "verdict": "PROMOTE",
        }],
    }
    confirmation_path = tmp_path / "campaigns/campaign-001/confirmation/result.json"
    confirmation_path.parent.mkdir(parents=True, exist_ok=True)
    confirmation_path.write_text(json.dumps(confirmation), encoding="utf-8")
    campaign["confirmation_result"] = str(confirmation_path)
    campaign["confirmation_result_digest"] = epochs._payload_digest(confirmation)
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    assert epochs.load_confirmation(
        tmp_path, "campaign-001"
    )["protocol_version"] == "epoch-1.6"

    campaign["ruleset_version"] = "fr-3.12.0"
    campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
    with pytest.raises(ValueError, match="게시 호환"):
        epochs.load_confirmation(tmp_path, "campaign-001")


def test_batch_gold_orthogonality_keeps_lexical_first_without_outcomes():
    months = pd.period_range("2020-01", periods=36, freq="M")
    assets = np.arange(40)
    frame = pd.DataFrame({
        "ym": np.repeat(months, len(assets)),
        "asset_id": np.tile(assets, len(months)),
    })
    alpha = pd.Series(np.tile(assets, len(months)), index=frame.index, dtype=float)
    beta = alpha.copy()
    rng = np.random.default_rng(20260815)
    gamma = pd.Series(
        np.concatenate([rng.permutation(assets) for _ in months]),
        index=frame.index,
        dtype=float,
    )
    result = gate.batch_signal_orthogonality(
        frame,
        {"gamma": gamma, "beta": beta, "alpha": alpha},
        eligible=pd.Series(True, index=frame.index),
    )
    assert result["candidate_factors"] == ["alpha", "beta", "gamma"]
    assert result["survivors"] == ["alpha", "gamma"]
    assert result["suppressed"] == [{
        "factor": "beta",
        "kept_factor": "alpha",
        "reason": "batch_signal_correlation_above_threshold",
    }]
    conflict = next(
        row for row in result["pairs"]
        if (row["left"], row["right"]) == ("alpha", "beta")
    )
    assert conflict["comparison_months"] == 36
    assert conflict["median_absolute_spearman"] == pytest.approx(1.0)
    assert conflict["conflict"] is True


def test_batch_gold_orthogonality_fails_closed_below_36_comparison_months():
    months = pd.period_range("2020-01", periods=35, freq="M")
    frame = pd.DataFrame({
        "ym": np.repeat(months, 40),
    })
    values = pd.Series(np.tile(np.arange(40), len(months)), index=frame.index)
    with pytest.raises(ValueError, match="비교월이 부족"):
        gate.batch_signal_orthogonality(
            frame,
            {"alpha": values, "beta": values},
            eligible=pd.Series(True, index=frame.index),
        )
