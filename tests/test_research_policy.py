"""Research input floor and maximum-lookback policy regressions."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from engine import gate, research_policy, silver
from engine.factors import Factor, Registry
from engine.panel import Panel, bind_asset_identity
from factors import candidate_loader
from scripts import run as run_script


def _panel(start: str = "2014-10", end: str = "2018-04") -> Panel:
    months = pd.period_range(start, end, freq="M")
    frame = pd.DataFrame({
        "asset_id": 1,
        "Code": "000001",
        "ym": months,
        "trade_date": months.to_timestamp(how="end").normalize(),
        "instrument_type": "common_stock",
        "market": "KOSPI",
        "adj_close": range(100, 100 + len(months)),
        "total_return_close": range(200, 200 + len(months)),
        "fwd_opt": 0.01,
        "fwd_mid": 0.01,
        "fwd_pess": 0.01,
        "f_stale": 999.0,
    })
    panel = Panel(
        frame,
        pd.Series(dtype="datetime64[ns]"),
        meta={
            "source": "RDS public Silver",
            **silver.return_role_contract(),
            "label_return_contract_status": "CERTIFIED",
        },
    )
    bind_asset_identity(panel)
    return panel


def test_raw_identity_scope_is_preserved_but_factor_view_starts_in_2015():
    raw = _panel()
    raw_identity = raw.meta["asset_identity_digest"]

    view = run_script._research_input_panel(raw)

    assert raw.monthly["ym"].min() == pd.Period("2014-10", freq="M")
    assert raw.meta["asset_identity_digest"] == raw_identity
    assert view.monthly["ym"].min() == research_policy.RESEARCH_INPUT_START
    assert "f_stale" not in view.monthly
    assert view.meta["parent_asset_identity_digest"] == raw_identity
    assert view.meta["asset_identity_digest"] != raw_identity


def test_research_view_excludes_preferred_shares_but_raw_identity_keeps_them():
    raw = _panel()
    preferred = raw.monthly.copy()
    preferred["asset_id"] = 2
    preferred["Code"] = "000001P"
    preferred["instrument_type"] = "preferred_stock"
    raw.monthly = pd.concat([raw.monthly, preferred], ignore_index=True)
    bind_asset_identity(raw)

    view = run_script._research_input_panel(raw)

    assert set(raw.monthly["instrument_type"]) == {
        "common_stock", "preferred_stock",
    }
    assert set(view.monthly["instrument_type"]) == {"common_stock"}
    assert set(view.monthly["asset_id"]) == {1}


def test_research_view_excludes_konex_rows():
    raw = _panel()
    konex = raw.monthly.copy()
    konex["asset_id"] = 2
    konex["Code"] = "000002"
    konex["market"] = "KONEX"
    raw.monthly = pd.concat([raw.monthly, konex], ignore_index=True)
    bind_asset_identity(raw)

    view = run_script._research_input_panel(raw)

    assert set(raw.monthly["market"]) == {"KOSPI", "KONEX"}
    assert set(view.monthly["market"]) == {"KOSPI"}


def test_campaign_scope_keeps_pre_2015_rows_for_full_live_identity():
    raw = _panel("2014-10", "2021-04")
    scoped = run_script._scope_discovery_panel(
        raw, data_cutoff="2018-04-30", oos_start="2018-05",
    )

    assert scoped.monthly["ym"].min() == pd.Period("2014-10", freq="M")
    parent_digest = scoped.meta["asset_identity_digest"]
    view = run_script._research_input_panel(scoped)
    assert view.monthly["ym"].min() == pd.Period("2015-01", freq="M")
    assert view.meta["parent_asset_identity_digest"] == parent_digest


def test_factor_compute_cannot_receive_pre_2015_rows():
    raw = _panel()
    observed: list[pd.Period] = []

    def compute(frame):
        observed.append(frame["ym"].min())
        return frame["adj_close"]

    factor = Factor(
        name="input_floor_probe",
        category="other",
        hypothesis="연구 입력 하한 검증",
        predicted_sign=1,
        compute=compute,
    )

    with pytest.raises(ValueError, match="2015-01부터"):
        run_script._ensure_factor_columns(raw, [factor])

    view = run_script._research_input_panel(raw)
    run_script._ensure_factor_columns(view, [factor])
    assert observed
    assert min(observed) == research_policy.RESEARCH_INPUT_START
    assert all(month >= research_policy.RESEARCH_INPUT_START for month in observed)


def test_authoritative_compute_never_exposes_more_than_declared_history():
    view = run_script._research_input_panel(_panel("2015-01", "2018-04"))
    observed_windows: list[tuple[pd.Period, pd.Period]] = []

    def compute(frame):
        months = pd.PeriodIndex(frame["ym"], freq="M")
        observed_windows.append((months.min(), months.max()))
        return frame.groupby("asset_id")["adj_close"].transform("mean")

    factor = Factor(
        name="bounded_runtime_probe",
        category="other",
        hypothesis="선언한 기간 밖 과거정보를 실행 단계에서 차단",
        predicted_sign=1,
        params={"lookback_months": 12},
        compute=compute,
    )

    result = research_policy.compute_factor(factor, view.monthly)

    assert result.index.equals(view.monthly.index)
    assert observed_windows
    assert all(end.ordinal - start.ordinal <= 12 for start, end in observed_windows)
    last = view.monthly["ym"].eq(view.monthly["ym"].max())
    expected = view.monthly.loc[
        view.monthly["ym"].ge(view.monthly["ym"].max() - 12), "adj_close"
    ].mean()
    assert result.loc[last].iloc[0] == pytest.approx(expected)


def test_five_year_seasonality_is_preserved_but_not_registered():
    registry = Registry()
    loaded = candidate_loader.load_candidates(registry)

    assert "annual_seasonality_5y" not in registry
    assert "annual_seasonality_5y" not in candidate_loader.RESEARCH_SPECS
    disabled = candidate_loader.DISABLED_RESEARCH_SPECS[
        "annual_seasonality_5y"
    ]
    assert disabled["max_lookback_months"] == 60
    assert "36개월" in disabled["disabled_reason"]
    assert all(factor.name != "annual_seasonality_5y" for factor in loaded)
    assert Path("factors/candidates/annual_seasonality_5y.py").is_file()
    for name in ("dividend_yield_ttm", "dividend_event_frequency_ttm"):
        assert name not in registry
        assert name in candidate_loader.DISABLED_RESEARCH_SPECS
        assert "historical-vintage/known_at" in (
            candidate_loader.DISABLED_RESEARCH_SPECS[name]["disabled_reason"]
        )


def test_every_registered_existing_candidate_has_resolved_allowed_lookback():
    registry = Registry()
    loaded = candidate_loader.load_candidates(registry)

    horizons = {
        factor.name: research_policy.assert_allowed_lookback(
            name=factor.name, source=factor.source, params=factor.params,
        )
        for factor in loaded
    }
    expected_files = {
        path.stem
        for path in candidate_loader.CANDIDATE_DIR.glob("*.py")
        if not path.name.startswith("_")
    }
    disabled = {
        Path(spec["strategy_file"]).stem
        for spec in candidate_loader.DISABLED_RESEARCH_SPECS.values()
        if Path(spec["strategy_file"]).stem in expected_files
    }
    assert set(horizons) | disabled == expected_files
    assert max(horizons.values()) == 36
    assert horizons["intermediate_momentum_12_7"] == 12


def test_undeclared_time_series_horizon_fails_closed(tmp_path):
    candidate = tmp_path / "undeclared_horizon.py"
    candidate.write_text(
        """
from engine.factors import Factor

WINDOW = 24

def compute(frame):
    return frame.groupby('asset_id')['adj_close'].shift(WINDOW)

FACTOR = Factor(
    name='undeclared_horizon', category='other', hypothesis='가설',
    predicted_sign=1, params={}, compute=compute,
)
RESEARCH_SPEC = {
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '기존 팩터와 낮은 상관',
    'data_notes': 'PIT 가격',
}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="horizon WINDOW"):
        candidate_loader.load_candidates(Registry(), tmp_path)


def test_active_candidate_cannot_reduce_unbounded_asset_history(tmp_path):
    candidate = tmp_path / "unbounded_asset_mean.py"
    candidate.write_text(
        """
from engine.factors import Factor

LOOKBACK_MONTHS = 12

def compute(frame):
    return frame.groupby('asset_id')['adj_close'].transform('mean')

FACTOR = Factor(
    name='unbounded_asset_mean', category='other', hypothesis='가설',
    predicted_sign=1, params={'lookback_months': LOOKBACK_MONTHS},
    compute=compute,
)
RESEARCH_SPEC = {
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '낮은 상관', 'data_notes': 'PIT 가격',
}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="전체-history"):
        candidate_loader.load_candidates(Registry(), tmp_path)


@pytest.mark.parametrize("group_key", ["fake_ym", "frame['ym'].notna()"])
def test_cross_section_guard_rejects_fake_or_transformed_month_key(
    tmp_path, group_key,
):
    candidate = tmp_path / "fake_month_group.py"
    candidate.write_text(
        f"""
from engine.factors import Factor

def compute(frame):
    fake_ym = frame['asset_id']
    return frame['adj_close'].groupby({group_key}).transform('mean')

FACTOR = Factor(
    name='fake_month_group', category='other', hypothesis='가설',
    predicted_sign=1, params={{}}, compute=compute,
)
RESEARCH_SPEC = {{
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '낮은 상관', 'data_notes': 'PIT 가격',
}}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="전체-history"):
        candidate_loader.load_candidates(Registry(), tmp_path)


def test_asset_rolling_transform_and_month_cross_section_are_allowed(tmp_path):
    rolling = tmp_path / "bounded_asset_mean.py"
    rolling.write_text(
        """
from engine.factors import Factor

WINDOW_MONTHS = 12

def compute(frame):
    return frame.groupby('asset_id')['adj_close'].transform(
        lambda values: values.rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).mean()
    )

FACTOR = Factor(
    name='bounded_asset_mean', category='other', hypothesis='가설',
    predicted_sign=1, params={'window_months': WINDOW_MONTHS}, compute=compute,
)
RESEARCH_SPEC = {
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '낮은 상관', 'data_notes': 'PIT 가격',
}
""",
        encoding="utf-8",
    )
    cross_section = tmp_path / "month_cross_section.py"
    cross_section.write_text(
        """
from engine.factors import Factor

def compute(frame):
    return frame['adj_close'].groupby(frame['ym']).transform('mean')

FACTOR = Factor(
    name='month_cross_section', category='other', hypothesis='가설',
    predicted_sign=1, params={}, compute=compute,
)
RESEARCH_SPEC = {
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '낮은 상관', 'data_notes': 'PIT 가격',
}
""",
        encoding="utf-8",
    )

    loaded = candidate_loader.load_candidates(Registry(), tmp_path)

    assert {factor.name for factor in loaded} == {
        "bounded_asset_mean", "month_cross_section",
    }


def test_over_limit_factor_is_rejected_before_compute_callback_runs():
    calls: list[int] = []

    def compute(frame):
        calls.append(len(frame))
        return frame["adj_close"]

    factor = Factor(
        name="over_limit_callback_probe",
        category="other",
        hypothesis="허용 기간을 넘는 후보는 실행하지 않음",
        predicted_sign=1,
        params={"lookback_months": 60},
        compute=compute,
    )
    view = run_script._research_input_panel(_panel())

    with pytest.raises(ValueError, match="36개월"):
        research_policy.compute_factor(factor, view.monthly)
    assert calls == []


def test_common_evaluation_start_keeps_36_month_warmup():
    assert research_policy.COMMON_EVALUATION_START == pd.Period(
        "2018-03", freq="M",
    )
    warmup = (
        research_policy.COMMON_EVALUATION_START.ordinal
        - research_policy.RESEARCH_INPUT_START.ordinal
    )
    assert warmup >= research_policy.MAX_FACTOR_LOOKBACK_MONTHS


def test_t0_policy_checks_have_unique_ids():
    view = run_script._research_input_panel(_panel())
    factor = Factor(
        name="unique_t0_probe",
        category="other",
        hypothesis="T0 검사 식별자 검증",
        predicted_sign=1,
        compute=lambda frame: frame["adj_close"],
    )
    view.monthly["f_unique_t0_probe"] = factor.compute(view.monthly)

    checks = gate._validate_factor(
        factor, view.monthly, "f_unique_t0_probe",
    )
    identifiers = [check.tier for check in checks]
    assert len(identifiers) == len(set(identifiers))


def test_factor_compute_never_receives_forward_labels_or_cached_factors():
    view = run_script._research_input_panel(_panel())
    sensitive = {
        "Name", "Market", "age_days", "amount", "available_date",
        "dataset_start", "first_seen", "in_universe", "instrument_type",
        "is_distress", "is_reit", "is_spac", "listed_from", "listed_to",
        "me_date", "ok_age",
        "ok_common", "ok_market", "ok_price", "quality_run_id", "seasoned",
        "ticker_match_count", "total_return_quality_run_id",
        "total_return_close", "return_close", "close",
        "dividend_cash_ttm", "dividend_event_count_ttm",
    }
    for column in sensitive:
        view.monthly[column] = (
            "common_stock" if column == "instrument_type"
            else "probe" if column == "Name"
            else pd.Timestamp("1995-01-01")
            if column in {
                "available_date", "dataset_start", "first_seen", "listed_from",
                "listed_to", "me_date",
            }
            else True
        )
    observed: set[str] = set()
    observed_attrs: list[dict] = []

    def compute(frame):
        observed.update(map(str, frame.columns))
        observed_attrs.append(dict(frame.attrs))
        return frame["adj_close"]

    factor = Factor(
        name="label_isolation_probe",
        category="other",
        hypothesis="미래수익 레이블 격리 검증",
        predicted_sign=1,
        compute=compute,
    )
    run_script._ensure_factor_columns(view, [factor])

    assert not any(column.startswith("fwd_") for column in observed)
    assert not any(column.startswith("f_") for column in observed)
    assert observed.isdisjoint(sensitive)
    assert "total_return_close" not in observed
    assert "return_close" not in observed
    assert "close" not in observed
    assert "adj_close" in observed
    assert "market" in observed
    assert observed_attrs
    assert all(attrs == {} for attrs in observed_attrs)


@pytest.mark.parametrize("label", ["total_return_close", "return_close"])
def test_candidate_cannot_declare_or_read_label_only_return(label):
    view = run_script._research_input_panel(_panel())
    factor = Factor(
        name=f"label_access_{label}",
        category="other",
        hypothesis="ex-post label 접근 차단 검증",
        predicted_sign=1,
        needs=(label,),
        compute=lambda frame: frame[label],
    )
    view.monthly[f"f_{factor.name}"] = 1.0

    checks = gate._validate_factor(factor, view.monthly, f"f_{factor.name}")

    blocked = next(check for check in checks if check.name == "label 전용 입력 차단")
    assert blocked.passed is False
    assert label in blocked.note
    with pytest.raises(KeyError):
        research_policy.compute_factor(factor, view.monthly)


@pytest.mark.parametrize(
    "feature",
    sorted(research_policy.UNCERTIFIED_PIT_FEATURE_COLUMNS),
)
def test_candidate_cannot_declare_or_directly_read_uncertified_dividend_feature(
    feature: str,
):
    view = run_script._research_input_panel(_panel())
    view.monthly[feature] = 1.0
    factor = Factor(
        name=f"uncertified_{feature}",
        category="other",
        hypothesis="historical-vintage 계약 없는 배당 feature 차단 검증",
        predicted_sign=1,
        needs=(feature,),
        compute=lambda frame: frame[feature],
    )
    view.monthly[f"f_{factor.name}"] = 1.0

    checks = gate._validate_factor(factor, view.monthly, f"f_{factor.name}")
    blocked = next(
        check for check in checks if check.name == "label 전용 입력 차단"
    )

    assert blocked.passed is False
    assert feature in blocked.note
    with pytest.raises(KeyError):
        research_policy.compute_factor(factor, view.monthly)
    undeclared = Factor(
        name=f"undeclared_{feature}",
        category="other",
        hypothesis="needs 미선언 배당 feature 직접 접근 차단 검증",
        predicted_sign=1,
        compute=lambda frame: frame[feature],
    )
    with pytest.raises(KeyError):
        research_policy.compute_factor(undeclared, view.monthly)


def test_unresolved_hidden_horizon_cannot_borrow_another_declared_param():
    source = """
def compute(frame):
    short = frame.groupby('asset_id')['adj_close'].shift(LOOKBACK_MONTHS)
    return short + frame.groupby('asset_id')['adj_close'].shift(WINDOW_60)
"""
    with pytest.raises(ValueError, match="WINDOW_60"):
        research_policy.factor_lookback_months(
            source=source, params={"lookback_months": 1},
        )


def test_causal_gate_rejects_composed_history_beyond_36_months():
    view = run_script._research_input_panel(_panel("2015-01", "2022-12"))

    def compute(frame):
        shifted = frame.groupby("asset_id")["adj_close"].shift(24)
        return shifted.groupby(frame["asset_id"]).transform(
            lambda values: values.rolling(24, min_periods=24).mean()
        )

    factor = Factor(
        name="composed_lookback_probe",
        category="other",
        hypothesis="합성 시계열 연산 상한 검증",
        predicted_sign=1,
        params={"lookback_months": 24},
        compute=compute,
    )
    view.monthly["f_composed_lookback_probe"] = (
        research_policy.compute_factor(factor, view.monthly)
    )
    checks = gate._validate_factor(
        factor, view.monthly, "f_composed_lookback_probe",
    )
    causal = next(check for check in checks if check.name == "36개월 인과성")
    assert causal.passed is False
    assert "36개월" in causal.note


def test_runtime_window_neutralizes_full_history_expression_in_every_month():
    view = run_script._research_input_panel(_panel("2015-01", "2024-12"))

    def compute(frame):
        full_history_mean = frame.groupby("asset_id")["adj_close"].transform(
            "mean"
        )
        clean_recent = pd.PeriodIndex(frame["ym"], freq="M") >= pd.Period(
            "2021-01", freq="M",
        )
        return frame["adj_close"].where(clean_recent, full_history_mean)

    factor = Factor(
        name="older_branch_leak_probe",
        category="other",
        hypothesis="과거 분기에서만 전체-history를 보는 우회 검증",
        predicted_sign=1,
        compute=compute,
    )
    reference = research_policy.compute_factor(factor, view.monthly)

    passed, note = research_policy.causal_lookback_check(
        factor, view.monthly, reference,
    )

    assert passed is True
    assert "36개월" in note


def test_candidate_module_cannot_import_filesystem_or_read_cache(tmp_path):
    candidate = tmp_path / "cache_reader.py"
    candidate.write_text(
        """
from pathlib import Path
from engine.factors import Factor

LEAK = Path('.cache/panel.pkl').read_bytes()

def compute(frame):
    return frame['adj_close']

FACTOR = Factor(
    name='cache_reader', category='other', hypothesis='가설',
    predicted_sign=1, params={}, compute=compute,
)
RESEARCH_SPEC = {
    'thesis': '가설', 'mechanism': '메커니즘', 'falsification': '반증',
    'expected_relationship': '낮은 상관', 'data_notes': 'PIT',
}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="허용되지 않은 import"):
        candidate_loader.load_candidates(Registry(), tmp_path)


def test_conditional_future_shift_is_rejected_before_runtime_branching():
    source = """
def compute(frame):
    if len(frame) > 10_000:
        return frame.groupby('asset_id')['adj_close'].shift(-1)
    return frame['adj_close']
"""
    with pytest.raises(ValueError, match="미래 행"):
        research_policy.factor_lookback_months(source=source, params={})


def test_nested_negative_shift_is_rejected_even_for_disabled_definition():
    source = """
def compute(frame):
    return frame.groupby('asset_id')['adj_close'].shift(2 * -1)
"""
    with pytest.raises(ValueError, match="미래 행"):
        research_policy.factor_lookback_months(
            source=source,
            params={"history_years": 5, "months_per_year": 12},
        )


@pytest.mark.parametrize(
    "source",
    [
        """
from engine.factors import *
def compute(frame):
    return frame['adj_close']
FACTOR = Factor(name='escape_probe', category='other', hypothesis='가설', predicted_sign=1, compute=compute)
RESEARCH_SPEC = {'thesis':'가설','mechanism':'m','falsification':'f','expected_relationship':'e','data_notes':'d'}
""",
        """
from engine.factors import Factor, REGISTRY
def compute(frame):
    return frame['adj_close']
FACTOR = Factor(name='escape_probe', category='other', hypothesis='가설', predicted_sign=1, compute=compute)
RESEARCH_SPEC = {'thesis':'가설','mechanism':'m','falsification':'f','expected_relationship':'e','data_notes':'d'}
""",
        """
import pandas as pd
from engine.factors import Factor
def compute(frame):
    reader = pd.read_pickle
    return reader('.cache/panel.pkl')
FACTOR = Factor(name='escape_probe', category='other', hypothesis='가설', predicted_sign=1, compute=compute)
RESEARCH_SPEC = {'thesis':'가설','mechanism':'m','falsification':'f','expected_relationship':'e','data_notes':'d'}
""",
        """
import pandas as pd
from engine.factors import Factor
def compute(frame):
    return getattr(pd, 'read_pickle')('.cache/panel.pkl')
FACTOR = Factor(name='escape_probe', category='other', hypothesis='가설', predicted_sign=1, compute=compute)
RESEARCH_SPEC = {'thesis':'가설','mechanism':'m','falsification':'f','expected_relationship':'e','data_notes':'d'}
""",
        """
from engine.factors import Factor
def compute(frame):
    import os
    return frame['adj_close']
FACTOR = Factor(name='escape_probe', category='other', hypothesis='가설', predicted_sign=1, compute=compute)
RESEARCH_SPEC = {'thesis':'가설','mechanism':'m','falsification':'f','expected_relationship':'e','data_notes':'d'}
""",
    ],
)
def test_candidate_loader_rejects_import_and_call_alias_escapes(tmp_path, source):
    (tmp_path / "escape_probe.py").write_text(source, encoding="utf-8")
    with pytest.raises(ValueError):
        candidate_loader.load_candidates(Registry(), tmp_path)


def test_candidate_strategy_sha_binds_exact_executed_file_bytes(tmp_path):
    source = """from engine.factors import Factor

def compute(frame):
    return frame['adj_close']

FACTOR = Factor(name='sha_probe', category='other', hypothesis='가설', predicted_sign=1, compute=compute)
RESEARCH_SPEC = {'thesis':'가설','mechanism':'m','falsification':'f','expected_relationship':'e','data_notes':'d'}
"""
    body = source.replace("\n", "\r\n").encode("utf-8")
    path = tmp_path / "sha_probe.py"
    path.write_bytes(body)

    loaded = candidate_loader.load_candidates(Registry(), tmp_path)

    assert [factor.name for factor in loaded] == ["sha_probe"]
    assert candidate_loader.RESEARCH_SPECS["sha_probe"]["strategy_sha256"] == (
        hashlib.sha256(body).hexdigest()
    )
