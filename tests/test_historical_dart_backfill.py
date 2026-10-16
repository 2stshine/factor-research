import io
import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
import zipfile

import pytest

from scripts import backfill_dart_historical_filings as pilot


KEY = "synthetic-secret-not-a-real-key-0123456789"


def zip_body(name="report.xml", body=b"<DOCUMENT>Raw original</DOCUMENT>"):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, body)
    return out.getvalue()


class Response(io.BytesIO):
    status = 200


def listing(ticker="005930", corp="00126380", quarter=0, **overrides):
    window = pilot.WINDOWS[quarter]
    row = {"stock_code": ticker, "corp_code": corp,
           "report_nm": f"{window[3]} ({window[4]})",
           "rcept_no": window[1] + "000001", "rcept_dt": window[1]}
    row.update(overrides)
    return {"status": "000", "total_page": 1, "list": [row]}


def fake_api(request, **kwargs):
    parsed = urlparse(request.full_url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert params["crtfc_key"] == KEY
    if parsed.path.endswith("document.xml"):
        return Response(zip_body())
    ticker = dict((corp, ticker) for ticker, corp in pilot.ISSUERS)[params["corp_code"]]
    quarter = next(i for i, w in enumerate(pilot.WINDOWS) if w[1] == params["bgn_de"])
    assert params["last_reprt_at"] == "N" and params["pblntf_ty"] == "A"
    return Response(json.dumps(listing(ticker, params["corp_code"], quarter)).encode())


def collect(tmp_path, **kwargs):
    return pilot.collect(tmp_path / "pilot", api_key=KEY, opener=fake_api, sleeper=lambda _: None, **kwargs)


def test_fixed_plan_and_complete_pilot(tmp_path):
    result = collect(tmp_path)
    assert result["status"] == "RAW_PILOT_COMPLETE_PIT_UNVERIFIED"
    assert result["calls_across_resume"] == 18
    assert len(result["scopes"]) == 9
    assert not result["pit_certified"] and not result["silver_writes"]
    root = tmp_path / "pilot"
    assert len(list(root.glob("attempts/*/response.json"))) == 9
    assert len(list(root.glob("attempts/*/response.zip"))) == 9
    assert all(KEY.encode() not in p.read_bytes() for p in root.rglob("*") if p.is_file())


def test_resume_verifies_hash_and_makes_no_requests(tmp_path):
    result = collect(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("Resume must not call provider")
    resumed = pilot.collect(tmp_path / "pilot", api_key=KEY, opener=forbidden, sleeper=lambda _: None)
    assert resumed["calls_across_resume"] == result["calls_across_resume"] == 18
    assert resumed["status"] == result["status"]


def test_resume_detects_tampering(tmp_path):
    collect(tmp_path)
    path = tmp_path / "pilot/attempts/001/response.json"
    path.write_bytes(b"corrupted")
    result = collect(tmp_path)
    assert result["failure"] == "CACHED_BODY_SHA_MISMATCH"
    assert result["calls_across_resume"] == 18


@pytest.mark.parametrize("body", [b"{\"status\":\"014\"}", b"<result><status>014</status></result>", b"PKjunk"])
def test_reject_document_errors_and_invalid_zip(body):
    with pytest.raises(pilot.PilotError, match="INVALID_DOCUMENT_ZIP"):
        pilot.validate_zip(body)


@pytest.mark.parametrize("name", ["../evil.xml", "/absolute.xml", "folder/../../evil.xml", "C:/evil.xml", "folder\\evil.xml"])
def test_never_accept_zip_traversal(name):
    with pytest.raises(pilot.PilotError, match="UNSAFE_ZIP_MEMBER"):
        pilot.validate_zip(zip_body(name))


def test_never_select_amendment_as_original():
    data = listing(report_nm="[기재정정]분기보고서 (2015.03)")
    result = pilot.select_original(data, "005930", "00126380", pilot.WINDOWS[0])
    assert result["status"] == "NO_UNIQUE_ORIGINAL"


def test_ambiguous_original_and_pagination_fail_closed():
    data = listing()
    data["list"].append({**data["list"][0], "rcept_no": "20150402000001"})
    assert pilot.select_original(data, "005930", "00126380", pilot.WINDOWS[0])["selected"] is None
    data["total_page"] = 2
    assert pilot.select_original(data, "005930", "00126380", pilot.WINDOWS[0])["status"] == "INCOMPLETE_PAGINATION"


def test_official_date_checked_without_receipt_prefix_inference():
    data = listing(rcept_no="20150402000001", rcept_dt="20150401")
    result = pilot.select_original(data, "005930", "00126380", pilot.WINDOWS[0])
    assert result["selected"]["rcept_dt"] == "20150401"
    with pytest.raises(pilot.PilotError, match="SCOPE_OR_DATE"):
        pilot.select_original(listing(rcept_dt="20160101"), "005930", "00126380", pilot.WINDOWS[0])


def test_call_budget_persists_across_resume(tmp_path):
    first = collect(tmp_path, max_calls=2)
    assert first["failure"] == "REQUEST_OR_BYTE_BUDGET_EXHAUSTED"
    assert first["calls_across_resume"] == 2
    again = collect(tmp_path, max_calls=2)
    assert again["calls_across_resume"] == 2


def test_network_retries_count_and_secret_exception_not_persisted(tmp_path):
    def fail(*args, **kwargs):
        raise URLError("https://example.invalid?crtfc_key=" + KEY)
    result = pilot.collect(tmp_path / "pilot", api_key=KEY, opener=fail, sleeper=lambda _: None)
    assert result["calls_across_resume"] == 3
    assert result["failure"] == "RETRIES_EXHAUSTED"
    assert all(KEY.encode() not in p.read_bytes() for p in (tmp_path / "pilot").rglob("*") if p.is_file())


def test_byte_limit_and_secret_echo_do_not_store_bad_bodies(tmp_path):
    def huge(*args, **kwargs):
        return Response(b"x" * 200)
    result = pilot.collect(tmp_path / "bytes", api_key=KEY, opener=huge, sleeper=lambda _: None, max_bytes=100)
    assert result["response_bytes_across_resume"] == 100
    assert result["failure"] == "RESPONSE_BYTE_BUDGET_EXHAUSTED"
    def echo(*args, **kwargs):
        return Response(KEY.encode())
    result = pilot.collect(tmp_path / "secret", api_key=KEY, opener=echo, sleeper=lambda _: None)
    assert result["failure"] == "SECRET_ECHO_REJECTED"
    assert not list((tmp_path / "secret").glob("attempts/*/response.*"))


def test_interrupted_request_requires_audit(tmp_path):
    collect(tmp_path, max_calls=2)
    (tmp_path / "pilot/attempts/002/outcome.json").unlink()
    with pytest.raises(pilot.PilotError, match="INTERRUPTED_REQUEST"):
        collect(tmp_path, max_calls=2)


def test_budget_increases_and_nonempty_unowned_directory_rejected(tmp_path):
    with pytest.raises(pilot.PilotError):
        pilot.plan(31)
    root = tmp_path / "pilot"
    root.mkdir()
    (root / "existing.txt").write_text("keep")
    with pytest.raises(pilot.PilotError, match="NONEMPTY_OUTPUT"):
        collect(tmp_path)


def test_missing_key_does_not_create_output(tmp_path, monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    with pytest.raises(pilot.PilotError, match="KEY_REQUIRED"):
        pilot.collect(tmp_path / "new")
    assert not (tmp_path / "new").exists()


def test_zip_validation_never_extracts(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Archives must remain raw, never extracted")
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    assert pilot.validate_zip(zip_body())[0]["name"] == "report.xml"
    assert not list(tmp_path.iterdir())
    with pytest.raises(pilot.PilotError, match="XML_MEMBER_MISSING"):
        pilot.validate_zip(zip_body("not-a-report.txt"))


def test_resume_rejects_changed_budget_contract(tmp_path):
    collect(tmp_path, max_calls=2)
    with pytest.raises(pilot.PilotError, match="IMMUTABLE_OBJECT_CONFLICT"):
        collect(tmp_path, max_calls=3)


def test_dry_run_needs_no_key_or_output(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["pilot", "--output", str(tmp_path / "not-created")])
    pilot.main()
    output = json.loads(capsys.readouterr().out)
    assert output["max_unique_list_requests"] == 9
    assert not (tmp_path / "not-created").exists()


def test_exact_official_receipt_slash_member_is_raw_only(monkeypatch):
    receipt = "20150515001379"
    def forbidden(*args, **kwargs):
        raise AssertionError("Receipt compatibility must never extract a ZIP")
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    result = pilot.validate_zip(zip_body(f"/{receipt}.xml"), expected_receipt=receipt)
    assert result[0]["name"] == f"/{receipt}.xml"
    with pytest.raises(pilot.PilotError, match="UNSAFE_ZIP_MEMBER"):
        pilot.validate_zip(zip_body(f"/{receipt}.xml"))
    with pytest.raises(pilot.PilotError, match="UNSAFE_ZIP_MEMBER"):
        pilot.validate_zip(zip_body(f"/{receipt}.xml"), expected_receipt="20150515001380")


@pytest.mark.parametrize("name", [
    "//20150515001379.xml", "/../20150515001379.xml", "/x/20150515001379.xml",
    "/./20150515001379.xml", "/20150515001379.xml/", "\\20150515001379.xml",
    "C:/20150515001379.xml",
])
def test_receipt_member_exception_remains_narrow(name):
    with pytest.raises(pilot.PilotError):
        pilot.validate_zip(zip_body(name), expected_receipt="20150515001379")


def test_official_slash_member_passes_fetch_and_provenance(tmp_path):
    def official_api(request, **kwargs):
        parsed = urlparse(request.full_url)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if parsed.path.endswith("document.xml"):
            return Response(zip_body(f"/{params['rcept_no']}.xml"))
        return fake_api(request, **kwargs)
    result = pilot.collect(tmp_path / "pilot", api_key=KEY, opener=official_api, sleeper=lambda _: None)
    assert result["status"] == "RAW_PILOT_COMPLETE_PIT_UNVERIFIED"
    first = json.loads((tmp_path / "pilot/documents/005930-Q1.json").read_text())
    assert first["members"][0]["name"] == f"/{first['receipt_no']}.xml"
