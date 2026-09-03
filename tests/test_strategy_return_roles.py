"""전략 일별 수익률의 feature/label 경계 계약."""
from __future__ import annotations

import inspect

from strategies import config, daily, data


def test_daily_sql_separates_pit_feature_from_ex_post_label():
    sql = " ".join(daily.DAILY_SQL.split())
    assert "adj_close / prior_adj_close - 1.0 END AS feature_r" in sql
    assert (
        "total_return_close / prior_total_return_close - 1.0 END AS label_r"
        in sql
    )


def test_feature_and_label_use_different_versioned_caches():
    assert daily.FEATURE_CACHE != daily.LABEL_CACHE
    assert "split_adjusted" in daily.FEATURE_CACHE.name
    assert "gross_dividend" in daily.LABEL_CACHE.name


def test_covariance_loader_cannot_fall_back_to_label_cache():
    feature_loader = inspect.getsource(daily.load_daily)
    label_loader = inspect.getsource(daily.load_daily_labels)
    assert "FEATURE_CACHE" in feature_loader
    assert "LABEL_CACHE" not in feature_loader
    assert "LABEL_CACHE" in label_loader


def test_daily_training_uses_label_only_for_forward_target():
    source = inspect.getsource(data.daily_frame)
    assert "label_r = daily_returns.load_daily_labels()" in source
    assert "level = (1.0 + label_r).cumprod()" in source
    assert "valid = label_r.notna()" in source


def test_monthly_feature_level_uses_adjusted_price():
    assert config.StrategyConfig.return_level_col == "adj_close"
