"""Independent adversarial source replay checks; synthetic values, no outcomes/API."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine import fundamentals
from engine import historical_fundamental_overlay as overlay
from scripts.build_historical_revenue_panel import replace_financials
from tests.test_build_historical_revenue_panel import parent
from tests.test_historical_fundamental_overlay import (
    asof, base, base_row, bundle, ofs_original, original,
)


def attached(frame, dates, assets=None):
    dates = pd.to_datetime(dates)
    panel = pd.DataFrame({"asset_id": assets if assets is not None else [1] * len(dates),
                          "trade_date": dates, "ym": dates.to_period("M")})
    return fundamentals.attach(panel, frame, sorted(fundamentals.PIT_FEATURES))


@pytest.mark.parametrize("metric", ["revenue", "total_assets"])
def test_builder_must_reject_a_different_base_ledger_from_parent(metric):
    old = parent()
    raw = base()
    raw.loc[raw.metric.eq(metric), "value"] = "999"
    # A separate DQ-certified source is not automatically the exact frozen
    # base that produced this parent. No incidental financial rewrite allowed.
    with pytest.raises(ValueError, match="(?i)(base|ledger|source|parent)"):
        replace_financials(old, raw, bundle())


def test_builder_discards_precomputed_factor_scores_without_mutating_parent():
    old = parent()
    old.monthly["f_synthetic_old_revenue_score"] = [123.0, 456.0, 789.0]
    before = deepcopy(old)
    new = replace_financials(old, base(), bundle())
    assert not any(str(column).startswith("f_") for column in new.monthly)
    pd.testing.assert_frame_equal(old.monthly, before.monthly)
    assert old.meta == before.meta


def test_late_first_filing_is_not_backdated_to_its_fiscal_quarter():
    rows = [original(q, fs, filed="2017-05-01" if q == "Q3" else None)
            for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    frame = overlay.materialize(base(), bundle(rows))
    values = attached(frame, ["2016-03-31", "2017-04-30", "2017-05-01", "2017-05-02"])
    assert values.revenue_ttm.iloc[:3].isna().all()
    assert values.revenue_ttm.iloc[3] == 100


def test_future_restatement_changes_neither_prior_values_nor_prior_availability():
    old_rows = [original(q, fs) for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    revised = [original(q, fs, until="2017-06-02" if q == "Q2" else "2023-08-01")
               for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    revised += [original("Q2", fs, value="25", filed="2017-06-01") for fs in ("CFS", "OFS")]
    dates = ["2015-12-31", "2016-03-31", "2017-05-31", "2017-06-01"]
    before = attached(overlay.materialize(base(), bundle(old_rows)), dates)
    after = attached(overlay.materialize(base(), bundle(revised)), dates)
    pd.testing.assert_frame_equal(before, after)


def test_two_competing_revisions_same_publication_day_fail_closed():
    rows = [original(q, fs) for q in ("Q1", "Q3") for fs in ("CFS", "OFS")]
    rows += [original("Q2", fs, revision="20150801000001") for fs in ("CFS", "OFS")]
    rows += [original("Q2", fs, revision="20150801000002", value="25") for fs in ("CFS", "OFS")]
    with pytest.raises(ValueError, match="Overlapping approved revision"):
        overlay.materialize(base(), bundle(rows))


def test_zero_length_same_day_earlier_revision_cannot_enter_replay():
    rows = [original(q, fs, until="2015-08-02" if q == "Q2" else "2023-08-01")
            for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    with pytest.raises(ValueError, match="validity interval"):
        overlay.compile_ledger(base(), bundle(rows))


def test_unbound_later_block_does_not_allow_known_previous_row_to_live_forever():
    rows = [original(q, fs, until="2016-06-02" if q == "Q2" else "2023-08-01")
            for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    blocks = [{"scope_id":"Q2", "valid_from":"2016-06-02",
               "valid_until_exclusive":"2023-08-01", "reason":"IDENTITY_UNRESOLVED"}]
    frame = overlay.materialize(base(), bundle(rows, blocks, mapping=False))
    values = attached(frame, ["2016-05-31", "2016-06-30", "2023-07-31"])
    assert values.revenue_ttm.iloc[0] == 100
    assert values.revenue_ttm.iloc[1:].isna().all()
    receipt = frame.attrs[overlay.RECEIPT_KEY]
    assert len(receipt["unbound_blocking_scopes_not_guessed"]) == 1
    assert any(c["available_date"] == "2016-06-02" for c in receipt["validity_controls"])


def test_ofs_replacement_after_expired_cfs_is_not_backdated_and_keeps_nan_gap():
    rows = [original(q, fs, until="2016-06-02")
            for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows += [ofs_original(q, filed="2016-08-01") for q in ("Q1", "Q2", "Q3")]
    raw = pd.DataFrame([{**base_row(), "fs_type":"OFS"}, base_row(metric="total_assets", value="500")])
    values = attached(overlay.materialize(raw, bundle(rows)),
                      ["2016-03-31", "2016-06-30", "2016-08-01", "2016-08-02"])
    assert values.revenue_ttm.iloc[:3].isna().all()
    assert values.revenue_ttm.iloc[3] == 100
    assert values.total_assets.eq(500).all()


def test_whole_snapshot_join_never_cell_fills_a_missing_non_revenue_flow():
    net_income = [base_row("2015-03-31", "Q1", "2015-05-01", "net_income", "7"),
                  base_row("2015-03-31", "Q1", "2016-04-01", "net_income", np.nan)]
    raw = pd.concat([base(), pd.DataFrame(net_income)], ignore_index=True)
    rows = [original(q, fs, until="2016-06-02")
            for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows += [ofs_original(q, filed="2016-07-01") for q in ("Q1", "Q2", "Q3")]
    dates = ["2016-03-31", "2016-04-30", "2016-06-30", "2016-07-31"]
    expected = attached(fundamentals.materialize_pit(raw, verbose=False), dates)
    actual = attached(overlay.materialize(raw, bundle(rows)), dates)
    fields = sorted(set(fundamentals.PIT_FEATURES) - {"revenue", "revenue_ttm"})
    pd.testing.assert_frame_equal(actual[fields], expected[fields])
    assert actual.net_income.iloc[0] == 7
    assert actual.net_income.iloc[1:].isna().all()


def test_future_source_amount_and_basis_cannot_change_other_assets():
    other = [{**base_row(f"2018-{end}", f"Q{i}", f"2019-0{i}-01", value="25"), "asset_id":2}
             for i,end in enumerate(("03-31", "06-30", "09-30", "12-31"), 1)]
    raw = pd.concat([base(), pd.DataFrame(other)], ignore_index=True)
    initial = overlay.materialize(raw, bundle())
    rows = [original(q, fs, until="2020-06-02")
            for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows += [ofs_original(q, value="123456", filed="2020-06-01") for q in ("Q1", "Q2", "Q3")]
    later = overlay.materialize(raw, bundle(rows))
    dates = ["2019-04-30", "2020-06-30", "2023-08-31"]
    pd.testing.assert_frame_equal(attached(initial, dates, [2]*3), attached(later, dates, [2]*3))
    assert asof(later.loc[later.asset_id.eq(2)], "2020-06-30").revenue_ttm == 100


def test_input_row_permutation_does_not_select_a_different_revision_or_basis():
    raw = base()
    baseline = overlay.materialize(raw, bundle())
    for seed in range(4):
        shuffled = raw.sample(frac=1, random_state=seed).reset_index(drop=True)
        rows = [original(q, fs) for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
        rows = pd.Series(rows).sample(frac=1, random_state=seed).tolist()
        observed = overlay.materialize(shuffled, bundle(rows))
        pd.testing.assert_frame_equal(baseline, observed)
