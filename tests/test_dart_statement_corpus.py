import io
import json
from pathlib import Path
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
import zipfile

import pytest

from scripts import backfill_dart_statement_corpus as corpus


KEY = "synthetic-corpus-secret-not-a-real-api-key"


def make_manifest(tmp_path, **changes):
    value = {"issuers": [{"corp_code": "00126380", "stock_code": "005930", "asset_ids": [1]}],
             "fiscal_year": 2015, "quarters": ["Q1", "Q2", "Q3"], "list_start": "20150101",
             "list_end": "20230731", "identity_source_sha256": "a" * 64, "corpus_id": "synthetic-corpus",
             "max_calls": 100, "max_bytes": 1_000_000, "max_documents": 100}
    value.update(changes)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def disclosure(quarter="Q1", *, index=1, **changes):
    title, month = corpus.QUARTERS[quarter]
    row = {"corp_code": "00126380", "stock_code": "005930", "corp_name": "synthetic company",
           "report_nm": f"{title} (2015.{month})", "rcept_dt": f"2015{int(month)+2:02d}15",
           "rcept_no": f"2015{int(month)+2:02d}15{index:06d}", "rm": ""}
    row.update(changes)
    return row


def make_zip(receipt, name=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name or ("/" + receipt + ".xml"), b"<DOCUMENT>raw synthetic</DOCUMENT>")
    return buffer.getvalue()


class Response(io.BytesIO):
    status = 200


class FakeAPI:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [disclosure(q) for q in corpus.QUARTERS]
        self.requests = []
        self.lock = threading.Lock()

    def __call__(self, request, **kwargs):
        parsed = urlparse(request.full_url)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        endpoint = parsed.path.rsplit("/", 1)[1]
        with self.lock:
            self.requests.append((endpoint, params))
        if endpoint != "main.do":
            assert params.pop("crtfc_key") == KEY
        else:
            assert "crtfc_key" not in params
            return Response(b"<html><body>raw only</body></html>")
        if endpoint == "document.xml":
            return Response(make_zip(params["rcept_no"]))
        assert endpoint == "list.json"
        assert params["last_reprt_at"] == "N" and params["pblntf_ty"] == "A"
        assert params["bgn_de"] == "20150101" and params["end_de"] == "20230731"
        if not self.rows:
            return Response(b'{"status":"013","message":"No data"}')
        page = int(params["page_no"])
        selected = self.rows[(page-1)*100:page*100]
        return Response(json.dumps({"status": "000", "page_no": page, "page_count": 100,
                                    "total_count": len(self.rows), "total_page": (len(self.rows)+99)//100,
                                    "list": selected}).encode())


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", KEY)


def run(tmp_path, api=None, **kwargs):
    manifest = kwargs.pop("manifest", None) or make_manifest(tmp_path)
    return corpus.collect(manifest, tmp_path / "corpus", opener=api or FakeAPI(), sleeper=lambda _: None, **kwargs)


def test_collect_and_resume_immutable_without_new_calls(tmp_path):
    first = run(tmp_path)
    assert first["status"] == "RAW_CORPUS_COMPLETE_PIT_UNVERIFIED"
    assert first["calls_across_resume"] == 4
    assert first["endpoint_attempt_counts"] == {"list.json": 1, "document.xml": 3, "main.do": 0}
    assert first["saved_document_count"] == 3 and first["target_period_coverage_complete"]
    assert all(d["financial_available_at"] is None for d in first["documents"])
    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden on completed resume")
    second = run(tmp_path, forbidden)
    assert second["calls_across_resume"] == 4
    assert second["status"] == first["status"]
    assert len(list((tmp_path / "corpus/runs").glob("*.json"))) == 2
    assert all(KEY.encode() not in p.read_bytes() for p in (tmp_path / "corpus").rglob("*") if p.is_file())


def test_plan_has_no_key_network_or_output_requirement(tmp_path, monkeypatch):
    monkeypatch.delenv("DART_API_KEY")
    result = corpus.plan(make_manifest(tmp_path))
    assert result["manifest"]["max_calls"] == 100
    assert result["max_concurrency"] == 4
    assert not (tmp_path / "corpus").exists()
    with pytest.raises(corpus.CorpusError, match="ENVIRONMENT_REQUIRED"):
        corpus.collect(tmp_path / "manifest.json", tmp_path / "corpus")


@pytest.mark.parametrize("changes", [
    {"fiscal_year": 2014}, {"quarters": ["FY"]}, {"quarters": ["Q1", "Q1"]},
    {"list_end": "20261002"}, {"list_start": "20140101"}, {"max_calls": 12001},
    {"max_bytes": 2147483649}, {"max_documents": 8001}, {"max_calls": True},
    {"identity_source_sha256": "bad"}, {"corpus_id": "../unsafe"}, {"issuers": []},
    {"issuers": [{"corp_code": "126380", "stock_code": "005930", "asset_ids": [1]}]},
])
def test_reject_invalid_manifest(tmp_path, changes):
    with pytest.raises(corpus.CorpusError):
        corpus.plan(make_manifest(tmp_path, **changes))


def test_all_pages_no_small_page_limit_and_only_target_periods_downloaded(tmp_path):
    rows = [disclosure(index=i, report_nm="사업보고서 (2022.12)", rcept_dt="20230331") for i in range(1, 202)]
    rows.extend([disclosure("Q1", index=999), disclosure("Q2", index=999), disclosure("Q3", index=999)])
    api = FakeAPI(rows)
    result = run(tmp_path, api)
    assert result["list_response_count"] == 3
    assert result["issuers"][0]["all_disclosure_count"] == 204
    assert result["saved_document_count"] == 3
    assert result["calls_across_resume"] == 6


def test_all_revisions_preserved_not_approved_as_family(tmp_path):
    original = disclosure("Q1", rm="정")
    revision = disclosure("Q1", index=2, report_nm="[기재정정]분기보고서 (2015.03)", rcept_dt="20200331")
    attachment = disclosure("Q1", index=3, report_nm="[첨부정정]분기보고서 (2015.03)", rcept_dt="20210331")
    result = run(tmp_path, FakeAPI([original, revision, attachment]), collect_correction_main=True)
    assert result["saved_document_count"] == result["saved_main_page_count"] == 3
    assert result["lineage_status"] == "UNVERIFIED" and not result["pit_certified"]
    assert result["missing_target_scope_count"] == 2
    assert not result["target_period_coverage_complete"]


def test_main_option_does_not_fetch_uncorrected_scopes(tmp_path):
    result = run(tmp_path, collect_correction_main=True)
    assert result["saved_main_page_count"] == 0
    assert result["calls_across_resume"] == 4


@pytest.mark.parametrize("stock,status", [("", "LIST_STOCK_CODE_BLANK"), ("000001", "LIST_STOCK_CODE_MISMATCH")])
def test_list_display_stock_does_not_drop_corp_receipt(tmp_path, stock, status):
    result = run(tmp_path, FakeAPI([disclosure(stock_code=stock)]))
    assert result["saved_document_count"] == 1
    assert result["documents"][0]["list_stock_identity_status"] == status
    assert result["documents"][0]["historical_asset_identity_status"] == "UNVERIFIED"


def test_official_receipt_date_not_receipt_prefix(tmp_path):
    result = run(tmp_path, FakeAPI([disclosure(rcept_dt="20150516")]))
    assert result["documents"][0]["official_rcept_dt"] == "20150516"
    assert result["documents"][0]["receipt_no"].startswith("20150515")


def test_incomplete_pagination_blocks_all_document_downloads(tmp_path):
    rows = [disclosure(index=i, report_nm="사업보고서 (2022.12)", rcept_dt="20230331") for i in range(1, 102)]
    api = FakeAPI(rows)
    def changing(request, **kwargs):
        response = api(request, **kwargs)
        if "page_no=2" in request.full_url:
            return Response(b'{"status":"013"}')
        return response
    result = run(tmp_path, changing)
    assert result["status"] == "RAW_CORPUS_INCOMPLETE_PIT_UNVERIFIED"
    assert result["failures"][0]["reason"] == "INCOMPLETE_PAGINATION_NO_DATA_MIDWAY"
    assert result["saved_document_count"] == 0


def test_duplicate_receipts_and_changed_page_metadata_rejected(tmp_path):
    result = run(tmp_path, FakeAPI([disclosure(), disclosure()]))
    assert result["failures"][0]["reason"] == "DUPLICATE_RECEIPT_ACROSS_LIST_PAGES"
    assert result["endpoint_attempt_counts"]["document.xml"] == 0


def test_document_budget_blocks_before_any_zip(tmp_path):
    result = run(tmp_path, manifest=make_manifest(tmp_path, max_documents=2))
    assert result["failures"][0]["reason"] == "DOCUMENT_BUDGET_EXCEEDED"
    assert result["calls_across_resume"] == 1


def test_call_budget_is_shared_and_durable(tmp_path):
    manifest = make_manifest(tmp_path, max_calls=2)
    first = run(tmp_path, manifest=manifest)
    second = run(tmp_path, manifest=manifest)
    assert first["calls_across_resume"] == second["calls_across_resume"] == 2
    assert first["saved_document_count"] == second["saved_document_count"] == 1


def test_byte_budget_exact_and_shared(tmp_path):
    result = run(tmp_path, lambda *a, **k: Response(b"x" * 1000), manifest=make_manifest(tmp_path, max_bytes=100))
    assert result["response_bytes_across_resume"] == 100
    assert result["failures"][0]["reason"] == "RESPONSE_BYTE_BUDGET_EXHAUSTED"
    assert not list((tmp_path / "corpus/attempts").glob("*/response.*"))


@pytest.mark.parametrize("code", [429, 500, 503, 599])
def test_retry_http_429_and_5xx_sanitized(tmp_path, code):
    api = FakeAPI()
    attempts = []
    def transient(request, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, code, "secret=" + KEY, {}, None)
        return api(request, **kwargs)
    result = run(tmp_path, transient)
    assert result["calls_across_resume"] == 5
    assert result["saved_document_count"] == 3
    assert all(KEY.encode() not in p.read_bytes() for p in (tmp_path / "corpus").rglob("*") if p.is_file())


def test_network_retries_capped_and_no_secret_exception(tmp_path):
    def fail(*args, **kwargs):
        raise URLError("secret=" + KEY)
    result = run(tmp_path, fail)
    assert result["calls_across_resume"] == 4
    assert result["failures"][0]["reason"] == "RETRIES_EXHAUSTED"
    assert all(KEY.encode() not in p.read_bytes() for p in (tmp_path / "corpus").rglob("*") if p.is_file())


@pytest.mark.parametrize("bad_body", [b'{"status":"014"}', b"<result><status>014</status></result>", b"PKinvalid"])
def test_error_bodies_never_saved_as_zip(tmp_path, bad_body):
    api = FakeAPI([disclosure()])
    def bad_document(request, **kwargs):
        return Response(bad_body) if "document.xml" in request.full_url else api(request, **kwargs)
    result = run(tmp_path, bad_document)
    assert result["saved_document_count"] == 0
    assert not list((tmp_path / "corpus/attempts").glob("*/response.zip"))


def test_secret_echo_rejected_without_body_storage(tmp_path):
    result = run(tmp_path, lambda *args, **kwargs: Response(KEY.encode()))
    assert result["failures"][0]["reason"] == "SECRET_ECHO_REJECTED"
    assert not list((tmp_path / "corpus/attempts").glob("*/response.*"))


def test_cache_sha_tamper_fails_closed(tmp_path):
    run(tmp_path)
    next((tmp_path / "corpus/attempts").glob("*/response.json")).write_bytes(b"corrupt")
    result = run(tmp_path)
    assert result["failures"][0]["reason"] == "CACHED_BODY_SHA_MISMATCH"
    assert result["calls_across_resume"] == 4


def test_unfinished_reservation_requires_audit(tmp_path):
    run(tmp_path)
    next((tmp_path / "corpus/attempts").glob("*/outcome.json")).unlink()
    with pytest.raises(corpus.CorpusError, match="INTERRUPTED_REQUEST"):
        run(tmp_path)


def test_manifest_and_option_changes_rejected_on_resume(tmp_path):
    run(tmp_path)
    with pytest.raises(corpus.CorpusError, match="IMMUTABLE"):
        run(tmp_path, collect_correction_main=True)


def test_no_data_is_complete_list_but_incomplete_target_coverage(tmp_path):
    result = run(tmp_path, FakeAPI([]))
    assert result["status"] == "RAW_CORPUS_COMPLETE_PIT_UNVERIFIED"
    assert result["missing_target_scope_count"] == 3
    assert not result["target_period_coverage_complete"]
    assert result["calls_across_resume"] == 1


def test_global_gate_spaces_requests_with_shared_clock(tmp_path):
    manifest, _ = corpus.load_manifest(make_manifest(tmp_path))
    elapsed = [0.0]
    def sleep(seconds):
        elapsed[0] += seconds
    client = corpus.Transport(tmp_path / "transport", manifest, KEY, sleeper=sleep, monotonic=lambda: elapsed[0])
    times = []
    for page in range(4):
        client.reserve("list.json", {"page_no": str(page)})
        times.append(elapsed[0])
    assert times == [0, 0.25, 0.5, 0.75]


@pytest.mark.parametrize("body,reason", [
    (b'<result><status>020</status></result>', 'PROVIDER_REQUEST_LIMIT'),
    (b'{"status":"020"}', 'PROVIDER_REQUEST_LIMIT'),
    (b'<result><status>010</status></result>', 'PROVIDER_AUTH_ERROR'),
    (b'{"status":"901"}', 'PROVIDER_AUTH_ERROR'),
])
def test_document_quota_auth_body_classified_without_persistence(body, reason):
    with pytest.raises(corpus.CorpusError, match=reason):
        corpus.validate_body("document.xml", {"rcept_no": "20150515000001"}, body)


@pytest.mark.parametrize("code", ["010", "020", "901"])
def test_provider_quota_and_auth_halt_shared_collector(tmp_path, code):
    manifest, _ = corpus.load_manifest(make_manifest(tmp_path))
    calls = []
    def limited(request, **kwargs):
        calls.append(1)
        return Response(json.dumps({"status": code, "message": "do not store provider messages"}).encode())
    client = corpus.Transport(tmp_path / "transport", manifest, KEY, opener=limited, sleeper=lambda _: None)
    with pytest.raises(corpus.CorpusError):
        client.fetch("list.json", {"page_no": "1"})
    with pytest.raises(corpus.CorpusError):
        client.fetch("list.json", {"page_no": "2"})
    assert len(calls) == client.calls == 1


def test_per_response_limit_prevents_unbounded_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "MAX_SINGLE_RESPONSE_BYTES", 100)
    result = run(tmp_path, lambda *a, **k: Response(b"x" * 1000))
    assert result["response_bytes_across_resume"] == 100
    assert result["failures"][0]["reason"] == "SINGLE_RESPONSE_BYTE_LIMIT_EXCEEDED"


def test_failed_later_issuer_preserves_actual_partial_list_counts(tmp_path):
    # Successful pages remain budgeted even when logical pagination later fails.
    rows = [disclosure(index=i, report_nm="사업보고서 (2022.12)", rcept_dt="20230331") for i in range(1, 102)]
    api = FakeAPI(rows)
    def broken(request, **kwargs):
        return Response(b'{"status":"013"}') if "page_no=2" in request.full_url else api(request, **kwargs)
    result = run(tmp_path, broken)
    assert result["successful_response_counts_across_resume"]["list.json"] == 2
    assert result["endpoint_attempt_counts"]["list.json"] == 2


def test_explicit_safe_manifest_metadata_is_frozen(tmp_path):
    result = corpus.plan(make_manifest(tmp_path, schema_version="dart-statement-corpus-plan-v1", issuer_count=1,
                                      source_asset_count=1, source_ledger_sha256="b"*64,
                                      research_authorized_by_plan=False, silver_publish_authorized_by_plan=False,
                                      identity_status="LOOKUP_HINT_ONLY_HISTORICAL_MAPPING_NOT_CERTIFIED"))
    assert result["manifest"]["source_ledger_sha256"] == "b"*64
    assert not result["silver_writes"]


@pytest.mark.parametrize("changes", [{"issuer_count": 2}, {"source_asset_count": True},
                                     {"silver_publish_authorized_by_plan": True}, {"unknown_option": True}])
def test_optional_metadata_never_expands_authority_or_scope(tmp_path, changes):
    with pytest.raises(corpus.CorpusError):
        corpus.plan(make_manifest(tmp_path, **changes))
