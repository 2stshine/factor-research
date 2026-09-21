"""Synthetic contract tests only; no live KIS/DB calls or PIT approval."""
from contextlib import AbstractContextManager
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import audit_kis_pit_evidence as audit_module


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    files = {
        "pipeline/silver/kis_flows.py": (
            "observed = max(datetime.fromisoformat(r['fetched_at'])\n"
            "'historical_revision_risk': True\n"
            "'availability_basis': 'POLICY_ASSUMPTION'\n"
        ),
        "pipeline/silver_quality/migrations/015_kis_market_flows.sql": (
            "k.first_observed_at <= cutoff AND k.research_available_at <= cutoff\n"
            "PRIMARY KEY (asset_id, trade_date, venue, kind, revision, first_observed_at)"
        ),
        "docs/kis-market-flows.md": "Synthetic fixture. Not historical source evidence.\n",
    }
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return tmp_path


def test_fingerprint_binds_exact_bytes_and_resolved_path(tmp_path):
    path = tmp_path / "evidence.bin"
    body = b"\x00\xff\r\nsource\n"
    path.write_bytes(body)
    assert audit_module.fingerprint(path) == {
        "path": str(path.resolve()), "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
    }
    path.write_bytes(body + b"x")
    assert audit_module.fingerprint(path)["sha256"] != hashlib.sha256(body).hexdigest()


def test_code_contract_pass_is_explicitly_not_data_proof(source_root):
    checks, evidence = audit_module.source_checks(source_root)
    assert len(checks) == 6
    assert all(c["passed"] for c in checks)
    assert {c["kind"] for c in checks} == {"CODE_CONTRACT_NOT_DATA_PROOF"}
    assert len(evidence) == 3
    assert all(audit_module.fingerprint(Path(e["path"])) == e for e in evidence)


def test_live_false_never_calls_database_even_when_code_passes(source_root, monkeypatch):
    def forbidden():
        raise AssertionError("Unexpected live database access")
    monkeypatch.setattr(audit_module, "database_summary", forbidden)
    report = audit_module.audit(source_root, live=False)
    assert report["database"] == {"status": "NOT_QUERIED", "rows_examined": None}
    assert report["confirmed"]
    assert report["status"] == "HISTORICAL_VINTAGE_UNPROVEN"
    assert report["historical_pit_approved"] is False
    assert report["approval_changed"] is False
    assert not any(report["mutations"].values())


def test_contract_failure_cannot_claim_confirmed_protections(source_root):
    path = source_root / "pipeline/silver/kis_flows.py"
    path.write_text(path.read_text().replace("'historical_revision_risk': True", "'historical_revision_risk': False"))
    report = audit_module.audit(source_root)
    assert sum(c["passed"] for c in report["code_checks"]) == 5
    assert report["confirmed"] == []
    assert not report["historical_pit_approved"]


def test_missing_source_is_error_not_positive_evidence(tmp_path):
    with pytest.raises(FileNotFoundError):
        audit_module.source_checks(tmp_path)


@pytest.mark.parametrize("exception", [RuntimeError, SystemExit])
def test_database_error_redacts_message_and_prints_nothing(exception, monkeypatch, capsys):
    from engine import silver

    def unavailable(*, read_only):
        assert read_only is True
        raise exception("password=DO_NOT_OUTPUT_THIS postgres://secret-user@private-endpoint")

    monkeypatch.setattr(silver, "connect", unavailable)
    result = audit_module.database_summary()
    assert result["status"] == "CONNECTION_OR_QUERY_UNAVAILABLE"
    assert result["error_class"] == exception.__name__
    assert result["error_details_redacted"] is True
    assert result["rows_examined"] is None
    assert "DO_NOT_OUTPUT_THIS" not in json.dumps(result)
    assert "private-endpoint" not in json.dumps(result)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


class FakeCursor(AbstractContextManager):
    def __init__(self, *, table_exists=True, query_error=False):
        self.executed = []
        self.table_exists = table_exists
        self.query_error = query_error
        self.description = []

    def __exit__(self, *args):
        return False

    def execute(self, sql):
        self.executed.append(sql)
        if sql == audit_module.SUMMARY_SQL:
            if self.query_error:
                raise RuntimeError("SECRET_QUERY_ERROR")
            self.description = [SimpleNamespace(name="rows"), SimpleNamespace(name="provider_time_unknown")]

    def fetchone(self):
        if "to_regclass" in self.executed[-1]:
            return ("kis_market_observation" if self.table_exists else None,)
        return (10, 10)

    def fetchall(self):
        return [("INVESTOR", "KRX", 10)]


class FakeConnection(AbstractContextManager):
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def cursor(self):
        return self.fake_cursor

    def __exit__(self, *args):
        return False


def install_connection(monkeypatch, cursor):
    from engine import silver

    def connect(*, read_only):
        assert read_only is True
        return FakeConnection(cursor)

    monkeypatch.setattr(silver, "connect", connect)


def test_missing_table_is_zero_examined_not_certification(monkeypatch):
    cursor = FakeCursor(table_exists=False)
    install_connection(monkeypatch, cursor)
    assert audit_module.database_summary() == {"status": "TABLE_NOT_PRESENT", "rows_examined": 0}
    assert audit_module.SUMMARY_SQL not in cursor.executed


def test_live_aggregate_success_still_cannot_approve_pit(source_root, monkeypatch):
    cursor = FakeCursor()
    install_connection(monkeypatch, cursor)
    report = audit_module.audit(source_root, live=True)
    assert report["database"]["status"] == "READ_ONLY_AGGREGATES_VERIFIED"
    assert report["database"]["rows_examined"] == 10
    assert report["database"]["does_not_prove_first_release_values"] is True
    assert report["historical_pit_approved"] is False
    assert report["approval_changed"] is False
    assert report["status"] == "HISTORICAL_VINTAGE_UNPROVEN"
    assert cursor.executed[0] == "SET LOCAL statement_timeout='30000ms'"
    assert all(q.lstrip().startswith(("SET LOCAL", "SELECT")) for q in cursor.executed)


def test_query_failure_after_connect_is_redacted(monkeypatch, capsys):
    cursor = FakeCursor(query_error=True)
    install_connection(monkeypatch, cursor)
    report = audit_module.database_summary()
    assert report["status"] == "CONNECTION_OR_QUERY_UNAVAILABLE"
    assert "SECRET_QUERY_ERROR" not in json.dumps(report)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
