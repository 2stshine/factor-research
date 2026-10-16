import json
import hashlib
from types import SimpleNamespace

import pytest

from scripts.research_statement_readiness import probe


class Cursor:
    def __init__(self, mode="on"):
        self.mode = mode
        self.query = ""
        self.description = [SimpleNamespace(name="asset_id")]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchone(self):
        return (self.mode,) if self.query.startswith("SHOW") else ("certified fixture view definition",)

    def fetchmany(self, n):
        return []


class Conn:
    def __init__(self, mode="on"):
        self.mode = mode

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def cursor(self):
        return Cursor(self.mode)


def test_empty_actual_rows_not_counted_as_full_coverage(tmp_path):
    path = tmp_path / "probe.json"
    def connect(*, read_only):
        assert read_only is True
        return Conn()
    result = probe(asset_ids=[1, 2], business_year=2024, as_of="2025-06-30T23:59:59+09:00",
                   scope_ref="fixture", output=path, connect=connect)
    assert result["coverage"]["matched_fraction"] == 0
    assert result["factor_evaluated"] is False
    saved = json.loads(path.read_text())
    assert saved["source_extraction"]["query_includes_all_standardized_metrics"]
    assert not saved["source_extraction"]["unmapped_filing_completeness_verified"]
    assert saved["schema_version"] == "dart-fy-cohort-probe-v2"
    source = saved["source_extraction"]
    assert source["view_definition_sha256"] == hashlib.sha256(source["view_definition"].encode()).hexdigest()
    assert source["query_sha256"] == hashlib.sha256(source["query_definition"].encode()).hexdigest()
    assert source["certified_dq_filter"] == "EXPECTED_SOURCE_CONTRACT_NOT_INDEPENDENTLY_VERIFIED"
    for source_path, key in (("scripts/research_statement_readiness.py", "compiler_sha256"),
                      ("engine/research_statement_evidence.py", "bridge_sha256")):
        assert hashlib.sha256(saved["source_snapshot"][source_path].encode()).hexdigest() == saved[key]
    with pytest.raises(FileExistsError):
        probe(asset_ids=[1], business_year=2024, as_of="2025-06-30T00:00:00Z", scope_ref="f",
              output=path, connect=lambda **kwargs: pytest.fail("source touched"))


def test_source_must_be_read_only(tmp_path):
    with pytest.raises(ValueError, match="Read-only"):
        probe(asset_ids=[1], business_year=2024, as_of="2025-06-30T00:00:00Z", scope_ref="f",
              output=tmp_path / "new.json", connect=lambda **kwargs: Conn("off"))


@pytest.mark.parametrize("ids", [[], list(range(1, 102)), [1, 1], [-1]])
def test_cohort_scope_validated_before_connection(tmp_path, ids):
    with pytest.raises(ValueError):
        probe(asset_ids=ids, business_year=2024, as_of="2025-06-30T00:00:00Z", scope_ref="f",
              output=tmp_path / "new.json", connect=lambda **kwargs: pytest.fail("source touched"))
