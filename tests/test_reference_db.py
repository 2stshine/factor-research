"""AWS connection wrapper safety; no subprocess or database is contacted."""
import json
import subprocess
import traceback
from types import SimpleNamespace

import pytest

from engine import reference_db as db


URL = "postgresql://fixture_user:NOT_A_REAL_SECRET@fixture.invalid/database"
ENV_KEYS = ("SILVER_DB_URL", "SILVER_DB_SECRET_ID", "AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION")


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(db.silver, "_load_environment", lambda: None)
    monkeypatch.setattr(db.silver, "connect", lambda **kwargs: pytest.fail("DB mock not configured"))
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **kw: pytest.fail("CLI mock not configured"))


def response(payload=None, *, returncode=0, stderr=""):
    if payload is None:
        payload = {"SILVER_DB_URL": URL}
    return SimpleNamespace(returncode=returncode,
                           stdout=json.dumps({"SecretString": json.dumps(payload)}), stderr=stderr)


@pytest.mark.parametrize("read_only", [True, False])
def test_direct_environment_connection_never_calls_aws(monkeypatch, read_only):
    monkeypatch.setenv("SILVER_DB_URL", URL)
    connection = object(); seen = []
    def connect(**kwargs):
        seen.append(kwargs)
        assert db.os.environ["SILVER_DB_URL"] == URL
        return connection
    monkeypatch.setattr(db.silver, "connect", connect)
    assert db.connect(read_only=read_only) is connection
    assert seen == [{"read_only": read_only}]


@pytest.mark.parametrize("old_url", [None, "postgresql://old.invalid/old"])
def test_secret_connection_restores_environment_and_never_prints(monkeypatch, capsys, old_url):
    monkeypatch.setenv("SILVER_DB_SECRET_ID", "fixture-authorized-secret")
    monkeypatch.setenv("AWS_PROFILE", "fixture-profile")
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    if old_url is not None:
        monkeypatch.setenv("SILVER_DB_URL", old_url)
    calls = []; connection = object()
    def run(args, **kwargs):
        calls.append((args, kwargs)); return response()
    def connect(**kwargs):
        assert db.os.environ["SILVER_DB_URL"] == URL
        assert not db.os.environ.get("SILVER_DB_SECRET_ID")
        assert kwargs == {"read_only": True}
        return connection
    monkeypatch.setattr(db.subprocess, "run", run)
    monkeypatch.setattr(db.silver, "connect", connect)
    assert db.connect() is connection
    assert db.os.environ.get("SILVER_DB_URL") == old_url
    assert db.os.environ["SILVER_DB_SECRET_ID"] == "fixture-authorized-secret"
    args, kwargs = calls[0]
    assert args[:3] == ["aws", "secretsmanager", "get-secret-value"]
    assert "fixture-profile" in args and "ap-northeast-2" in args
    assert URL not in str(args)
    assert kwargs == {"capture_output": True, "text": True, "timeout": 45}
    assert capsys.readouterr() == ("", "")


def test_cli_failure_does_not_expose_stderr_or_payload(monkeypatch, capsys):
    monkeypatch.setenv("SILVER_DB_SECRET_ID", "fixture-authorized-secret")
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **kw: response(returncode=1, stderr=URL))
    with pytest.raises(RuntimeError) as error:
        db.connect()
    assert URL not in str(error.value)
    assert db.os.environ.get("SILVER_DB_URL") is None
    assert db.os.environ["SILVER_DB_SECRET_ID"] == "fixture-authorized-secret"
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("payload", [{}, {"SILVER_DB_URL": None}, {"SILVER_DB_URL": 123},
                                      {"SILVER_DB_URL": ""}, [], "secret-not-a-mapping"])
def test_malformed_secret_is_safe_runtime_error_without_environment_changes(monkeypatch, payload):
    monkeypatch.setenv("SILVER_DB_SECRET_ID", "fixture-authorized-secret")
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **kw: response(payload))
    with pytest.raises(RuntimeError) as error:
        db.connect()
    assert "secret-not-a-mapping" not in str(error.value)
    assert db.os.environ.get("SILVER_DB_URL") is None
    assert db.os.environ["SILVER_DB_SECRET_ID"] == "fixture-authorized-secret"


def test_connection_error_cannot_leak_secret_even_via_chained_traceback(monkeypatch):
    monkeypatch.setenv("SILVER_DB_SECRET_ID", "fixture-authorized-secret")
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **kw: response())
    def connect(**kwargs):
        raise ValueError("Connection parse failed: " + URL)
    monkeypatch.setattr(db.silver, "connect", connect)
    try:
        db.connect()
    except RuntimeError:
        assert URL not in traceback.format_exc()
    else:
        pytest.fail("Expected sanitized connection failure")
    assert db.os.environ.get("SILVER_DB_URL") is None
    assert db.os.environ["SILVER_DB_SECRET_ID"] == "fixture-authorized-secret"


def test_timeout_is_bounded_and_reported_without_captured_secret(monkeypatch):
    monkeypatch.setenv("SILVER_DB_SECRET_ID", "fixture-authorized-secret")
    def run(args, **kwargs):
        raise subprocess.TimeoutExpired(args, 45, output=URL, stderr=URL)
    monkeypatch.setattr(db.subprocess, "run", run)
    with pytest.raises(RuntimeError) as error:
        db.connect()
    assert URL not in str(error.value)
    assert db.os.environ.get("SILVER_DB_URL") is None
