from scripts.audit_krx_pit_evidence import admission, compare_name_rows, name_flags


def test_spac_rename_changes_historical_admission_but_is_not_rds_count():
    row = {"stock_code": "000001", "historical_name": "테스트스팩", "trade_date": "2015-01-30"}
    result = compare_name_rows([row], {"000001": "테스트회사"})
    assert result["classification_mismatch_rows"] == 1
    assert result["directions"]["historically_excluded_now_admitted"] == 1
    assert result["actual_rds_eligible_impact_count"] is None
    assert result["mismatches"][0]["stock_code"] == "000001"


def test_flags_mirror_existing_name_rules():
    assert name_flags("한화3우B")["preferred"]
    assert name_flags("테스트SPAC")["spac"]
    assert name_flags("테스트리츠")["reit"]
    assert admission(name_flags("삼성전자"))


def test_ordinary_rename_is_not_classification_mismatch():
    result = compare_name_rows([{"stock_code": "001234", "historical_name": "옛회사"}], {"001234": "새회사"})
    assert result["classification_mismatch_rows"] == 0


def test_uniform_future_price_scale_cancels_in_return_not_absolute_level():
    old, new, multiplier = 100.0, 110.0, 0.02
    assert abs((new * multiplier) / (old * multiplier) - new / old) < 1e-12
    assert new * multiplier != new
