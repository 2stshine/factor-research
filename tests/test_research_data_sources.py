import hashlib
import json
from pathlib import Path
import socket
import time

import pytest

from engine import research_data_sources as ds
from scripts.research_data_sources import main


def requirement(**changes):
    return {"requirement_id": "attention-v1", "question_id": "delayed-reaction", "research_question": "Does attention distinguish delayed response?", "discriminates": "Attention mechanism versus liquidity explanation", "variables": ["attention"], "market": "KRX", "frequency": "monthly", "start_date": "2020-01-31", "end_date": "2020-02-29", **changes}


def source(**changes):
    return {"source_id": "official-v1", "title": "Official historical attention release", "url": "https://example.com/releases.csv", "provenance_url": "https://example.com/methodology", "format": "csv", "market": "KRX", "frequency": "monthly", "pit_status": "verified", "pit_evidence": "Original release archive checked by reviewer; fixture only", **changes}


def review(**changes):
    return {"reviewer": "independent-fixture-reviewer", "authorization_reference": "test-fixture-only", "license_reference": "fixture-created-for-unit-test", "public_download_permitted": True, "research_use_permitted": True, "pit_approved": True, **changes}


RAW = b"observation_date,known_at,attention\n2020-01-31,2020-02-03T09:00:00+09:00,3\n2020-02-29,2020-03-02T09:00:00+09:00,5\n"


def transport(raw=RAW, mime="text/csv"):
    return lambda url, cap, deadline: (200, {"content-type": mime}, raw)


@pytest.fixture
def case(tmp_path):
    path = ds.create_requirement(tmp_path, requirement())
    ds.register_source(path, source())
    ds.review_source(path, "official-v1", review())
    return path


def test_end_to_end_retains_known_at_and_provenance(case):
    capture = ds.fetch_source(case, "official-v1", transport=transport())
    snapshot = ds.validate_artifact(case, capture["artifact_id"])
    assert snapshot["research_readable"]
    assert snapshot["pit_status"] == "verified"
    assert snapshot["hypothesis_verdict"] == "NO_EVIDENCE"
    loaded = ds.load_snapshot(case, snapshot["snapshot_id"], as_of="2020-02-10T00:00:00Z")
    assert len(loaded["rows"]) == 1
    assert loaded["rows"][0]["attention"] == "3"
    assert snapshot["source_url"] == source()["url"]
    assert capture["sha256"] == hashlib.sha256(RAW).hexdigest()
    assert "not_db" in capture["storage_layer"]


@pytest.mark.parametrize("url", ["http://example.com/a.csv", "https://localhost/a", "https://127.0.0.1/a", "https://10.0.0.2/a", "https://169.254.169.254/latest", "https://[::1]/a", "https://[::ffff:127.0.0.1]/a", "https://example.local/a", "https://name:password@example.com/a", "https://example.com:444/a", "https://example.com/a?api_key=SECRET", "https://example.com/a?%74oken=SECRET", "https://example.com/oauth/device", "https://example.com/signin", "https://example.com/a#fragment", "https://example.com/\nheader"])
def test_unsafe_urls_rejected(url):
    with pytest.raises(ds.DataSourceError):
        ds.check_url(url)


def test_dns_mixed_public_private_rejected():
    def resolver(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ["8.8.8.8", "127.0.0.1"]]
    with pytest.raises(ds.DataSourceError, match="non-public"):
        ds.resolve_public("https://example.com/a", resolver)


def test_dns_public_is_pinned_result():
    resolver = lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
    assert ds.resolve_public("https://example.com/a?version=1", resolver) == ("example.com", 443, "/a?version=1", ["8.8.8.8"])


def test_dns_wait_is_bounded():
    def blocked(*args, **kwargs):
        time.sleep(0.05)
        return []
    with pytest.raises(ds.DataSourceError, match="DNS"):
        ds.resolve_public("https://example.com/a", blocked, timeout_seconds=0.001)


def test_encoded_auth_endpoint_rejected():
    with pytest.raises(ds.DataSourceError):
        ds.check_url("https://example.com/%6fauth/device")


def test_redirect_to_private_is_rejected_before_second_call():
    seen = []
    def redirect(url, cap, deadline):
        seen.append(url)
        return 302, {"location": "https://127.0.0.1/admin"}, b""
    with pytest.raises(ds.DataSourceError):
        ds.download_public("https://example.com/a", 100, transport=redirect)
    assert seen == ["https://example.com/a"]


def test_public_redirect_records_provenance():
    def redirect(url, cap, deadline):
        if url.endswith("/a"):
            return 302, {"location": "/b"}, b""
        return 200, {"content-type": "text/csv"}, RAW
    result = ds.download_public("https://example.com/a", 1000, transport=redirect)
    assert result["redirects"] == ["https://example.com/a"]
    assert result["final_url"] == "https://example.com/b"


def test_redirect_limit():
    def redirect(url, cap, deadline):
        return 302, {"location": url + "a"}, b""
    with pytest.raises(ds.DataSourceError, match="redirects"):
        ds.download_public("https://example.com/a", 100, transport=redirect)


def test_no_fetch_without_explicit_review(tmp_path):
    path = ds.create_requirement(tmp_path, requirement())
    ds.register_source(path, source())
    with pytest.raises(ds.DataSourceError, match="permission"):
        ds.fetch_source(path, "official-v1", transport=transport())
    assert ds.packet(path)["fetches_used"] == 0


def test_unknown_licence_cannot_be_silently_approved(case):
    with pytest.raises(ds.DataSourceError):
        ds.review_source(case, "official-v1", {"public_download_permitted": True})


def test_revocation_invalidates_snapshot(case):
    capture = ds.fetch_source(case, "official-v1", transport=transport())
    snap = ds.validate_artifact(case, capture["artifact_id"])
    ds.review_source(case, "official-v1", review(research_use_permitted=False))
    with pytest.raises(ds.DataSourceError, match="revoked"):
        ds.load_snapshot(case, snap["snapshot_id"])


def test_artifact_tampering_detected(case):
    capture = ds.fetch_source(case, "official-v1", transport=transport())
    snap = ds.validate_artifact(case, capture["artifact_id"])
    path = case / "objects" / capture["sha256"]
    path.chmod(0o644)
    path.write_bytes(RAW.replace(b",3", b",99"))
    with pytest.raises(ds.DataSourceError, match="hash mismatch"):
        ds.load_snapshot(case, snap["snapshot_id"])


def test_snapshot_tampering_detected(case):
    capture = ds.fetch_source(case, "official-v1", transport=transport())
    snap = ds.validate_artifact(case, capture["artifact_id"])
    path = case / "objects" / snap["snapshot_id"]
    path.chmod(0o644)
    path.write_text("{}")
    with pytest.raises(ds.DataSourceError, match="hash mismatch"):
        ds.load_snapshot(case, snap["snapshot_id"])


def test_history_tampering_detected(case):
    path = case / "events.jsonl"
    path.write_text(path.read_text().replace("Official historical", "Altered historical"))
    with pytest.raises(ds.DataSourceError, match="history"):
        ds.packet(case)


@pytest.mark.parametrize("raw,expected", [
    (RAW.replace(b"attention", b"different"), "columns"),
    (RAW.replace(b"2020-02-29", b"2020-02-30"), "calendar"),
    (RAW.replace(b"2020-02-03T09:00:00+09:00", b"2020-01-01T09:00:00+09:00"), "known_at"),
    (RAW.replace(b"2020-02-03T09:00:00+09:00", b"2099-01-01T09:00:00+09:00"), "known_at"),
    (RAW.replace(b"2020-02-03T09:00:00+09:00", b"2020-02-03T09:00:00"), "timezone"),
    (RAW.replace(b",3", b",nan"), "nonfinite"),
    (RAW.replace(b",3", b","), "null"),
    (RAW + RAW.splitlines(keepends=True)[1], "duplicate"),
    (b"observation_date,known_at,attention\n", "empty"),
    (RAW.splitlines(keepends=True)[0] + RAW.splitlines(keepends=True)[1], "endpoints"),
])
def test_invalid_schema_dates_values_fail_closed(case, raw, expected):
    capture = ds.fetch_source(case, "official-v1", transport=transport(raw))
    snap = ds.validate_artifact(case, capture["artifact_id"])
    assert not snap["research_readable"]
    assert any(expected in error for error in snap["errors"])
    assert snap["status"] == "UNMET_NO_EVIDENCE"
    with pytest.raises(ds.DataSourceError, match="not research-readable"):
        ds.load_snapshot(case, snap["snapshot_id"])


@pytest.mark.parametrize("pit,allow,ready", [("verified", False, True), ("assumed", False, False), ("assumed", True, True), ("unverified", True, False)])
def test_pit_assumption_is_explicit_not_global(tmp_path, pit, allow, ready):
    path = ds.create_requirement(tmp_path, requirement(allow_pit_assumed=allow))
    ds.register_source(path, source(pit_status=pit))
    ds.review_source(path, "official-v1", review())
    capture = ds.fetch_source(path, "official-v1", transport=transport())
    assert ds.validate_artifact(path, capture["artifact_id"])["research_readable"] is ready


def test_search_and_fetch_budget_counts_failures(tmp_path):
    path = ds.create_requirement(tmp_path, requirement(budget={"searches": 1, "fetches": 1, "bytes": 1000}))
    ds.record_web_search(path, "official data", [])
    with pytest.raises(ds.DataSourceError, match="searches budget"):
        ds.record_web_search(path, "try again", [])
    ds.register_source(path, source())
    ds.review_source(path, "official-v1", review())
    def fail(*args):
        raise OSError("secret=DO_NOT_LOG_ME")
    with pytest.raises(ds.DataSourceError, match="fetch failed"):
        ds.fetch_source(path, "official-v1", transport=fail)
    with pytest.raises(ds.DataSourceError, match="fetches budget"):
        ds.fetch_source(path, "official-v1", transport=transport())
    packet = ds.packet(path)
    assert packet["bytes_charged"] == 1000
    assert "DO_NOT_LOG_ME" not in (path / "events.jsonl").read_text()


def test_process_interruption_keeps_byte_reservation(tmp_path):
    path = ds.create_requirement(tmp_path, requirement(budget={"bytes": 1000}))
    ds.register_source(path, source())
    ds.review_source(path, "official-v1", review())
    def interrupt(*args):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        ds.fetch_source(path, "official-v1", transport=interrupt)
    assert ds.packet(path)["bytes_charged"] == 1000
    with pytest.raises(ds.DataSourceError, match="bytes budget"):
        ds.fetch_source(path, "official-v1", transport=transport())


def test_elapsed_budget_is_checked_before_external_action(tmp_path, monkeypatch):
    created = "2000-01-01T00:00:00+00:00"
    monkeypatch.setattr(ds, "_now", lambda: created)
    path = ds.create_requirement(tmp_path, requirement())
    with pytest.raises(ds.DataSourceError, match="elapsed-time"):
        ds.record_web_search(path, "search", [])


def test_repeat_capture_same_source_is_valid(case):
    ds.fetch_source(case, "official-v1", transport=transport())
    capture = ds.fetch_source(case, "official-v1", transport=transport())
    assert ds.validate_artifact(case, capture["artifact_id"])["research_readable"]
    assert ds.packet(case)["bytes_charged"] == 2 * len(RAW)


def test_oversized_or_compressed_download_rejected():
    with pytest.raises(ds.DataSourceError):
        ds.download_public("https://example.com/a", 1, transport=transport())
    with pytest.raises(ds.DataSourceError, match="compressed"):
        ds.download_public("https://example.com/a", 1000, transport=lambda *args: (200, {"content-encoding": "gzip"}, b"bad"))


def test_html_is_not_accepted_as_dataset(case):
    with pytest.raises(ds.DataSourceError, match="fetch failed"):
        ds.fetch_source(case, "official-v1", transport=transport(b"<script>bad</script>", "text/html"))


def test_catalog_is_metadata_only_and_searchable(case, tmp_path):
    catalog = tmp_path / "inventory.json"
    catalog.write_text(json.dumps([{"source_id": "one", "title": "Attention archive", "variables": ["attention"], "url": "https://example.com/data.csv"}]))
    assert ds.search_catalog(case, catalog, "attention")[0]["source_id"] == "one"
    catalog.write_text(json.dumps([{"source_id": "bad", "oos_sharpe": 3}]))
    with pytest.raises(ds.DataSourceError, match="metadata"):
        ds.search_catalog(case, catalog, "bad")


def test_unmet_has_no_negative_hypothesis_inference(case):
    event = ds.mark_unmet(case, "No original-release archive found within budget")
    assert event["payload"]["hypothesis_verdict"] == "NO_EVIDENCE"
    assert "explicit_proxy_requirement" in event["payload"]["next_options"]


def test_proxy_requires_explicit_new_definition(tmp_path):
    with pytest.raises(ds.DataSourceError, match="proxy_definition"):
        ds.create_requirement(tmp_path, requirement(proxy_for="attention-v0"))
    case = ds.create_requirement(tmp_path, requirement(proxy_for="attention-v0", proxy_definition="Turnover as an imperfect attention proxy, also affected by liquidity"))
    assert ds.packet(case)["requirement"]["proxy_for"] == "attention-v0"


def test_local_capture_requires_exact_hash_and_never_changes_source(case, tmp_path):
    file = tmp_path / "data.csv"
    file.write_bytes(RAW)
    with pytest.raises(ds.DataSourceError, match="exact expected SHA"):
        ds.capture_local(case, "official-v1", file)
    ds.register_source(case, source(source_id="local-copy-v1", expected_sha256=hashlib.sha256(RAW).hexdigest()))
    ds.review_source(case, "local-copy-v1", review())
    result = ds.capture_local(case, "local-copy-v1", file)
    assert ds.validate_artifact(case, result["artifact_id"])["research_readable"]
    assert file.read_bytes() == RAW


def test_local_wrong_hash_not_captured(case, tmp_path):
    file = tmp_path / "data.csv"
    file.write_bytes(RAW)
    ds.register_source(case, source(source_id="wrong", expected_sha256="0" * 64))
    ds.review_source(case, "wrong", review())
    with pytest.raises(ds.DataSourceError, match="capture failed"):
        ds.capture_local(case, "wrong", file)


def test_json_supported_with_finite_type_validation(tmp_path):
    case = ds.create_requirement(tmp_path, requirement())
    ds.register_source(case, source(format="json", url="https://example.com/data.json"))
    ds.review_source(case, "official-v1", review())
    rows = [{"observation_date": "2020-01-31", "known_at": "2020-02-01T00:00:00Z", "attention": 3}, {"observation_date": "2020-02-29", "known_at": "2020-03-01T00:00:00Z", "attention": 5}]
    capture = ds.fetch_source(case, "official-v1", transport=transport(json.dumps(rows).encode(), "application/json"))
    snapshot = ds.validate_artifact(case, capture["artifact_id"])
    assert snapshot["research_readable"]
    assert ds.load_snapshot(case, snapshot["snapshot_id"])["rows"][0]["attention"] == 3


def test_entity_calendar_contract_blocks_endpoint_only_coverage(tmp_path):
    case = ds.create_requirement(tmp_path, requirement(entity_column="stock_code", required_entities=["005930", "000660"], expected_dates=["2020-01-31", "2020-02-29"]))
    ds.register_source(case, source())
    ds.review_source(case, "official-v1", review())
    raw = b"observation_date,known_at,attention,stock_code\n2020-01-31,2020-02-03T09:00:00+09:00,3,005930\n2020-02-29,2020-03-02T09:00:00+09:00,5,005930\n"
    capture = ds.fetch_source(case, "official-v1", transport=transport(raw))
    snap = ds.validate_artifact(case, capture["artifact_id"])
    assert not snap["research_readable"]
    assert "required entities not covered" in snap["errors"]
    assert "expected calendar dates missing for requested entities" in snap["errors"]


def test_monthly_calendar_gap_blocks_readiness(tmp_path):
    case = ds.create_requirement(tmp_path, requirement(end_date="2020-03-31", expected_dates=["2020-01-31", "2020-02-29", "2020-03-31"]))
    ds.register_source(case, source())
    ds.review_source(case, "official-v1", review())
    raw = RAW.replace(b"2020-02-29", b"2020-03-31").replace(b"2020-03-02", b"2020-04-02")
    capture = ds.fetch_source(case, "official-v1", transport=transport(raw))
    snap = ds.validate_artifact(case, capture["artifact_id"])
    assert snap["first_date"] == "2020-01-31" and snap["last_date"] == "2020-03-31"
    assert not snap["research_readable"]


def test_json_boolean_is_not_numeric_attention(tmp_path):
    case = ds.create_requirement(tmp_path, requirement())
    ds.register_source(case, source(format="json"))
    ds.review_source(case, "official-v1", review())
    raw = json.dumps([{"observation_date": "2020-01-31", "known_at": "2020-02-01T00:00:00Z", "attention": True}]).encode()
    capture = ds.fetch_source(case, "official-v1", transport=transport(raw, "application/json"))
    snap = ds.validate_artifact(case, capture["artifact_id"])
    assert not snap["research_readable"]
    assert "nonfinite numeric" in snap["errors"][0]


def test_market_frequency_mismatch_blocks_readiness(tmp_path):
    case = ds.create_requirement(tmp_path, requirement())
    ds.register_source(case, source(market="USA", frequency="annual"))
    ds.review_source(case, "official-v1", review())
    capture = ds.fetch_source(case, "official-v1", transport=transport())
    snap = ds.validate_artifact(case, capture["artifact_id"])
    assert not snap["research_readable"]
    assert "source market/frequency metadata does not match requirement" in snap["errors"]


def test_source_cannot_inject_approval_at_registration(tmp_path):
    case = ds.create_requirement(tmp_path, requirement())
    with pytest.raises(ds.DataSourceError, match="approvals are separate"):
        ds.register_source(case, source(research_use_permitted=True))


def test_cli_init_packet_and_unmet(tmp_path, capsys):
    path = tmp_path / "requirement.json"
    path.write_text(json.dumps(requirement()))
    root = tmp_path / "cases"
    assert main(["--root", str(root), "init", "--input", str(path)]) == 0
    case = Path(json.loads(capsys.readouterr().out)["case_dir"])
    assert main(["--root", str(case), "packet"]) == 0
    assert "host_agent_contract" in json.loads(capsys.readouterr().out)
    assert main(["--root", str(case), "unmet", "--reason", "source unavailable"]) == 0
    assert json.loads(capsys.readouterr().out)["payload"]["hypothesis_verdict"] == "NO_EVIDENCE"


@pytest.mark.parametrize("changes", [{"requirement_id": "../escape"}, {"start_date": "2021-01-31"}, {"budget": {"searches": 0}}, {"allow_pit_assumed": "yes"}, {"api_key": "secret"}, {"variables": ["attention", "attention"]}])
def test_invalid_requirement_contract(tmp_path, changes):
    with pytest.raises(ds.DataSourceError):
        ds.create_requirement(tmp_path, requirement(**changes))
