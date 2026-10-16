"""Read/write publication must preserve v1 compatibility and v2 provenance."""
from copy import deepcopy

import pandas as pd
import pytest

from engine import reference_gold as gold
from engine import reference_library as base
from engine import reference_library_v2 as v2
from engine.research_generation import digest


def fixture(*, expanded=False, financial=False):
    path = v2.CATALOG_PATH if financial else base.CATALOG_PATH
    ref = "kr_roa_fy_v1" if financial else "kr_size_issue_v1"
    definition = next(d for d in base.load_catalog(path) if d["id"] == ref)
    values = pd.DataFrame([dict(reference_id=ref, definition_hash=definition["definition_hash"],
        asset_id="1", stock_code="0037T0", date="2020-01-31",
        known_at="2020-01-31T16:00:00+09:00", value=.1)])
    att = dict(status="CERTIFIED", source_type="RDS_CERTIFIED_KRX_PRICE_ONLY",
               source_version="legacy-source-v1", evidence_sha256="a" * 64, input_sha256="b" * 64)
    if expanded:
        att.update(source_type=v2.SOURCE_TYPE, source_version="a" * 64,
                   source_contract=v2.SOURCE_CONTRACT, pit_status=v2.PIT_STATUS,
                   first_vintage_independently_verified=False,
                   feature_contracts=deepcopy(v2.FEATURE_CONTRACTS),
                   feature_units=deepcopy(v2.FEATURE_UNITS),
                   identity_contract=base.IDENTITY_CONTRACT, scope=base.INPUT_SCOPE)
    parity = dict(passed=True, values_sha256=digest(gold.canonical_values(values)), rows_compared=1,
                  sql_sha256="c" * 64, rtol=1e-10, atol=0,
                  kind="INDEPENDENT_POSTGRES_FORMULAS_SAME_ATTESTED_PRICE_FEATURES")
    validation = dict(value_rows=1, source_version=att["source_version"], input_sha256="b" * 64,
        source_evidence_sha256="a" * 64, role="MEASUREMENT_CONTROL", alpha_approved=False,
        implementation_sha256="d" * 64,
        references=[dict(reference_id=ref, definition_hash=definition["definition_hash"],
                         value_rows=1, status="MEASUREMENT_VALIDATED")])
    return values, definition, att, validation, parity


def build(args):
    values, definition, att, validation, parity = args
    return gold.build_publication(values, [definition], attestation=att, validation=validation, parity=parity)


def rehash(publication):
    publication["dataset_id"] = digest({k: v for k, v in publication.items() if k != "dataset_id"})


def test_original_v1_publication_still_valid_without_new_fields():
    publication, rows = build(fixture())
    assert "pit_status" not in publication["attestation"]
    assert gold.validate_publication(publication, rows) == publication
    assert gold.publish(None, publication, rows)["status"] == "DRY_RUN"


@pytest.mark.parametrize("financial", [True, False])
def test_v2_can_publish_only_explicit_assumed_not_verified_status(financial):
    publication, rows = build(fixture(expanded=True, financial=financial))
    assert publication["attestation"]["pit_status"] == v2.PIT_STATUS
    assert publication["attestation"]["first_vintage_independently_verified"] is False
    assert gold.validate_publication(publication, rows) == publication
    assert not publication["profitability_approved"] and not publication["legacy_gold_used"]


@pytest.mark.parametrize("field,value", [
    ("pit_status", "FIRST_VINTAGE_VERIFIED"), ("pit_status", None),
    ("first_vintage_independently_verified", True), ("first_vintage_independently_verified", 0),
    ("source_contract", "OTHER"), ("identity_contract", "CURRENT_TICKER"),
    ("scope", "ALL_STOCKS"), ("source_version", "bad"),
])
def test_rehashed_v2_metadata_cannot_erase_pit_limitations(field, value):
    publication, rows = build(fixture(expanded=True, financial=True))
    publication["attestation"][field] = value; rehash(publication)
    with pytest.raises(ValueError):
        gold.validate_publication(publication, rows)


def test_v1_label_cannot_publish_financial_measurement():
    with pytest.raises(ValueError):
        build(fixture(financial=True))


def test_rehashed_financial_publication_cannot_downgrade_to_v1_adapter():
    publication, rows = build(fixture(expanded=True, financial=True))
    publication["attestation"]["source_type"] = "RDS_CERTIFIED_KRX_PRICE_ONLY"
    rehash(publication)
    with pytest.raises(ValueError):
        gold.validate_publication(publication, rows)


def test_definition_rehash_does_not_allow_financial_formula_under_original_price_id():
    args = list(fixture())
    definition = deepcopy(args[1]); definition["formula"] = "fy_net_income / fy_total_assets"
    definition["required_columns"] = ["fy_net_income", "fy_total_assets"]
    definition["definition_hash"] = base.definition_hash(definition)
    args[1] = definition
    args[0]["definition_hash"] = definition["definition_hash"]
    args[3]["references"][0]["definition_hash"] = definition["definition_hash"]
    args[4]["values_sha256"] = digest(gold.canonical_values(args[0]))
    with pytest.raises(ValueError):
        build(args)
