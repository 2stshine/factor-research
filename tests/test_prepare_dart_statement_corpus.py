import json

import pandas as pd
import pytest

from scripts.prepare_dart_statement_corpus import prepare


@pytest.fixture
def inputs(tmp_path):
    ledger, identity, out = (tmp_path / name for name in ("ledger.parquet", "identity.json", "plan.json"))
    pd.DataFrame({"asset_id": [1, 2, 3, 4], "metric": ["revenue", "revenue", "net_income", "revenue"],
                  "period_end": pd.to_datetime(["2015-12-31", "2015-03-31", "2015-12-31", "2016-12-31"]),
                  "fiscal_period": ["FY"] * 4}).to_parquet(ledger)
    rows = [{"asset_id": "1", "source": source, "identifier_type": kind, "identifier": value,
             "status": "CERTIFIED"} for source, kind, value in
            [("DART", "corp_code", "00126380"), ("KRX", "ticker", "005930")]]
    identity.write_text(json.dumps({"schema_version": "historical-financial-identity-source-extract-v1",
                                    "read_only": True, "rows": rows}))
    return ledger, identity, out


def test_fixed_december_source_scope_keeps_leading_zero_and_no_certification(inputs):
    result = prepare(*inputs)
    assert result["issuers"] == [{"corp_code": "00126380", "stock_code": "005930", "asset_ids": [1]}]
    assert result["source_asset_count"] == 1
    assert result["identity_status"] == "LOOKUP_HINT_ONLY_HISTORICAL_MAPPING_NOT_CERTIFIED"
    assert result["research_authorized_by_plan"] is False
    assert result["silver_publish_authorized_by_plan"] is False
    assert result["list_end"] == "20230731"


def test_plan_cannot_overwrite(inputs):
    prepare(*inputs)
    with pytest.raises(ValueError, match="immutable"):
        prepare(*inputs)


@pytest.mark.parametrize("change", ["uncertified", "short_ticker", "ambiguous_corp", "not_read_only"])
def test_unresolved_identity_stops_instead_of_silently_selecting_subset(inputs, change):
    ledger, path, out = inputs
    data = json.loads(path.read_text())
    if change == "uncertified":
        data["rows"][0]["status"] = "FAILED"
    elif change == "short_ticker":
        data["rows"][1]["identifier"] = "5930"
    elif change == "ambiguous_corp":
        data["rows"].append({**data["rows"][0], "identifier": "00164779"})
    else:
        data["read_only"] = False
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare(ledger, path, out)
    assert not out.exists()
