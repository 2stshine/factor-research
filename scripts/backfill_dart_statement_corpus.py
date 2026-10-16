"""Bounded receipt-addressed DART corpus, not a financial/PIT certification.

Plan: python -m scripts.backfill_dart_statement_corpus --manifest FILE --output DIR
Run:  the same command with --apply; authentication comes only from DART_API_KEY.
No database, cloud writes, ZIP extraction, or historical-value substitution.
The original nine-report pilot and its staged output are never modified.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from scripts import backfill_dart_historical_filings as pilot


SCHEMA = "dart-statement-corpus-v1"
MAX_CALLS = 12_000
MAX_BYTES = 2_147_483_648
MAX_DOCUMENTS = 8_000
MAX_SINGLE_RESPONSE_BYTES = 100 * 1024 * 1024
WORKERS = 4
REQUEST_INTERVAL = 0.25
MAX_ATTEMPTS_PER_FETCH = 4
PAGE_COUNT = 100
QUARTERS = {"Q1": ("분기보고서", "03"), "Q2": ("반기보고서", "06"), "Q3": ("분기보고서", "09")}
ENDPOINTS = {
    "list.json": "https://opendart.fss.or.kr/api/list.json",
    "document.xml": "https://opendart.fss.or.kr/api/document.xml",
    "main.do": "https://dart.fss.or.kr/dsaf001/main.do",
}
LIMITATIONS = [
    "RAW_CORPUS_ONLY: no financial parser, Silver/Gold writes or input certification",
    "TITLE_GROUP_IS_NOT_A_VERIFIED_CORRECTION_FAMILY",
    "OFFICIAL_RECEIPT_DATE_IS_DATE_ONLY_NOT_AN_INTRADAY_PUBLICATION_TIMESTAMP",
    "FIRST_PUBLICATION_AND_HISTORICAL_IDENTITY_REQUIRE_SEPARATE_VERIFICATION",
    "Post-list_end revisions are outside the frozen historical as-of scope",
    "Current correction markers/issuer display metadata must not become historical features",
]


class CorpusError(RuntimeError):
    """Fixed, secret-free diagnostic codes only."""


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def put(path: Path, body: bytes):
    try:
        pilot._put(path, body)
    except pilot.PilotError:
        raise CorpusError("IMMUTABLE_STORAGE_CONFLICT_OR_UNSAFE_PATH") from None


def read_json(path: Path) -> dict:
    try:
        return pilot._read_json(path)
    except pilot.PilotError:
        raise CorpusError("INVALID_OR_UNSAFE_CHECKPOINT") from None


def valid_date(value) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        return False
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return False
    return True


def load_manifest(path: Path | str) -> tuple[dict, str]:
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise CorpusError("UNSAFE_MANIFEST_PATH")
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw)
    except (OSError, ValueError):
        raise CorpusError("INVALID_MANIFEST_JSON") from None
    required = {"issuers", "fiscal_year", "quarters", "list_start", "list_end", "identity_source_sha256",
                "corpus_id", "max_calls", "max_bytes", "max_documents"}
    optional = {"schema_version", "fiscal_calendar_scope", "identity_status", "issuer_count",
                "research_authorized_by_plan", "silver_publish_authorized_by_plan", "source_asset_count",
                "source_ledger_sha256", "universe_policy"}
    if not isinstance(manifest, dict) or not required <= set(manifest) or set(manifest) - required - optional:
        raise CorpusError("INVALID_MANIFEST_FIELDS")
    if "schema_version" in manifest and manifest["schema_version"] != "dart-statement-corpus-plan-v1":
        raise CorpusError("INVALID_MANIFEST_SCHEMA_VERSION")
    for field in ("research_authorized_by_plan", "silver_publish_authorized_by_plan"):
        if field in manifest and manifest[field] is not False:
            raise CorpusError("RAW_PLAN_CANNOT_AUTHORIZE_RESEARCH_OR_SILVER")
    for field in ("fiscal_calendar_scope", "identity_status", "universe_policy"):
        if field in manifest and (not isinstance(manifest[field], str) or len(manifest[field]) > 2000):
            raise CorpusError("INVALID_MANIFEST_METADATA")
    if "source_ledger_sha256" in manifest and (not isinstance(manifest["source_ledger_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", manifest["source_ledger_sha256"])):
        raise CorpusError("INVALID_SOURCE_LEDGER_SHA256")
    if manifest["fiscal_year"] != 2015 or type(manifest["fiscal_year"]) is not int:
        raise CorpusError("ONLY_2015_FISCAL_SCOPE_SUPPORTED")
    quarters = manifest["quarters"]
    if (not isinstance(quarters, list) or not quarters or any(q not in QUARTERS for q in quarters)
            or len(set(quarters)) != len(quarters)):
        raise CorpusError("INVALID_QUARTERS")
    if (not valid_date(manifest["list_start"]) or not valid_date(manifest["list_end"])
            or manifest["list_start"] != "20150101" or manifest["list_end"] != "20230731"):
        raise CorpusError("INVALID_FIXED_DISCLOSURE_WINDOW")
    if not isinstance(manifest["corpus_id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,100}", manifest["corpus_id"]):
        raise CorpusError("INVALID_CORPUS_ID")
    if not isinstance(manifest["identity_source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", manifest["identity_source_sha256"]):
        raise CorpusError("INVALID_IDENTITY_SOURCE_SHA256")
    for field, ceiling in (("max_calls", MAX_CALLS), ("max_bytes", MAX_BYTES), ("max_documents", MAX_DOCUMENTS)):
        if type(manifest[field]) is not int or not 1 <= manifest[field] <= ceiling:
            raise CorpusError("INVALID_OR_EXCESSIVE_CORPUS_BUDGET")
    issuers = manifest["issuers"]
    if not isinstance(issuers, list) or not issuers:
        raise CorpusError("EMPTY_ISSUER_SCOPE")
    corps, assets = set(), set()
    for item in issuers:
        if not isinstance(item, dict) or set(item) != {"corp_code", "stock_code", "asset_ids"}:
            raise CorpusError("INVALID_ISSUER_FIELDS")
        corp, stock = item["corp_code"], item["stock_code"]
        if (not isinstance(corp, str) or not re.fullmatch(r"[0-9]{8}", corp)
                or not isinstance(stock, str) or not re.fullmatch(r"[0-9]{6}", stock)):
            raise CorpusError("INVALID_ISSUER_IDENTITY")
        if corp in corps:
            raise CorpusError("DUPLICATE_ISSUER_IDENTITY")
        corps.add(corp)
        ids = item["asset_ids"]
        if (not isinstance(ids, list) or not ids or any(type(a) not in (str, int) or str(a).strip() == "" for a in ids)
                or len(set(map(str, ids))) != len(ids)):
            raise CorpusError("INVALID_ASSET_IDS")
        if assets.intersection(map(str, ids)):
            raise CorpusError("ASSET_ID_ASSIGNED_TO_MULTIPLE_ISSUERS")
        assets.update(map(str, ids))
    for field, expected in (("issuer_count", len(issuers)), ("source_asset_count", len(assets))):
        if field in manifest and (type(manifest[field]) is not int or manifest[field] != expected):
            raise CorpusError("MANIFEST_SCOPE_COUNT_MISMATCH")
    return manifest, sha(raw)


def plan(manifest_path, *, collect_correction_main=False) -> dict:
    manifest, digest = load_manifest(manifest_path)
    return {"schema_version": SCHEMA, "manifest": manifest, "manifest_sha256": digest,
            "collector_sha256": sha(Path(__file__).read_bytes()),
            "zip_validator_sha256": sha(Path(pilot.__file__).read_bytes()),
            "collect_correction_main": bool(collect_correction_main),
            "max_concurrency": WORKERS, "max_requests_per_second": 4,
            "max_single_response_bytes": MAX_SINGLE_RESPONSE_BYTES,
            "max_attempts_per_fetch": MAX_ATTEMPTS_PER_FETCH,
            "budget_includes_all_endpoints_retries_and_resumes": True,
            "pit_certified": False, "silver_writes": False, "gold_writes": False,
            "lineage_status": "UNVERIFIED", "limitations": LIMITATIONS}


@contextmanager
def locked(root: Path):
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise CorpusError("UNSAFE_OUTPUT_PATH")
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".corpus.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise CorpusError("CORPUS_LOCK_EXISTS_REVIEW_BEFORE_RESUME") from None
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink()


def _json_body(body: bytes) -> dict:
    try:
        value = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise CorpusError("INVALID_LIST_JSON") from None
    if not isinstance(value, dict):
        raise CorpusError("INVALID_LIST_SHAPE")
    status = value.get("status")
    if status not in {"000", "013"}:
        raise CorpusError("PROVIDER_REQUEST_LIMIT" if status == "020" else
                          "PROVIDER_AUTH_ERROR" if status in {"010", "011", "012", "901"} else "LIST_PROVIDER_ERROR")
    if status == "000" and not isinstance(value.get("list"), list):
        raise CorpusError("INVALID_LIST_ROWS")
    if status == "013" and value.get("list") not in (None, []):
        raise CorpusError("NO_DATA_STATUS_WITH_ROWS")
    return value


def validate_body(endpoint, params, body):
    if endpoint == "list.json":
        _json_body(body)
    elif endpoint == "document.xml":
        # Provider errors are sometimes XML or JSON with HTTP 200. Never save
        # that body as a ZIP or continue thousands of requests after quota/auth.
        if len(body) <= 262_144 and not body.startswith(b"PK"):
            status_match = re.search(rb"<status>\s*([0-9]{3})\s*</status>", body)
            status = status_match.group(1).decode() if status_match else None
            if status is None:
                try:
                    error_json = json.loads(body)
                    status = error_json.get("status") if isinstance(error_json, dict) else None
                except (ValueError, UnicodeError):
                    pass
            if status == "020":
                raise CorpusError("PROVIDER_REQUEST_LIMIT")
            if status in {"010", "011", "012", "901"}:
                raise CorpusError("PROVIDER_AUTH_ERROR")
            if status in {"013", "014"}:
                raise CorpusError("DOCUMENT_PROVIDER_NO_FILE")
        try:
            pilot.validate_zip(body, expected_receipt=params["rcept_no"])
        except pilot.PilotError as exc:
            # These are fixed diagnostic codes, never provider text or URLs.
            raise CorpusError(str(exc)) from None
    elif endpoint == "main.do":
        if not body.strip() or b"<html" not in body.lower():
            raise CorpusError("INVALID_OFFICIAL_MAIN_HTML")
        # A raw HTML response does not prove the selected receipt or lineage.
    else:
        raise CorpusError("UNSUPPORTED_ENDPOINT")


class Transport:
    """One global rate gate, durable attempt budget and response-byte budget."""

    def __init__(self, root, manifest, api_key, *, opener=urlopen, sleeper=time.sleep, monotonic=time.monotonic):
        self.root, self.manifest, self.key = root, manifest, api_key
        self.opener, self.sleeper, self.monotonic = opener, sleeper, monotonic
        self.state_lock = threading.Lock()
        self.gate_lock = threading.Lock()
        self.next_request = 0.0
        self.calls = self.bytes = 0
        self.halted = None
        self.endpoint_counts = {key: 0 for key in ENDPOINTS}
        self.success_counts = {key: 0 for key in ENDPOINTS}
        for index, request in enumerate(sorted((root / "attempts").glob("*/request.json")), 1):
            if request.parent.name != f"{index:06d}":
                raise CorpusError("ATTEMPT_LEDGER_GAP")
            if not request.with_name("outcome.json").is_file():
                raise CorpusError("INTERRUPTED_REQUEST_REQUIRES_AUDIT_BEFORE_RESUME")
            safe_request, outcome = read_json(request), read_json(request.with_name("outcome.json"))
            endpoint = safe_request.get("endpoint")
            amount = outcome.get("received_bytes")
            if endpoint not in ENDPOINTS or type(amount) is not int or amount < 0:
                raise CorpusError("INVALID_ATTEMPT_LEDGER")
            self.calls += 1
            self.bytes += amount
            self.endpoint_counts[endpoint] += 1
            if outcome.get("status") == "VALID_RAW_RESPONSE":
                self.success_counts[endpoint] += 1
        if self.calls > manifest["max_calls"] or self.bytes > manifest["max_bytes"]:
            raise CorpusError("CHECKPOINT_BUDGET_EXCEEDED")

    def cache_key(self, endpoint, params):
        return sha(encoded({"endpoint": endpoint, "params": params}))

    def cached(self, endpoint, params):
        path = self.root / "objects" / (self.cache_key(endpoint, params) + ".json")
        if not path.exists():
            return None
        meta = read_json(path)
        if meta.get("endpoint") != endpoint or meta.get("params") != params:
            raise CorpusError("CACHED_REQUEST_SCOPE_MISMATCH")
        relative = PurePosixPath(str(meta.get("body_path") or ""))
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative) or ":" in str(relative):
            raise CorpusError("UNSAFE_CACHE_BODY_PATH")
        body_path = self.root / relative
        if body_path.is_symlink() or any(p.is_symlink() for p in body_path.parents) or not body_path.is_file():
            raise CorpusError("CACHED_BODY_MISSING_OR_UNSAFE")
        if body_path.stat().st_size != meta.get("bytes") or body_path.stat().st_size > self.manifest["max_bytes"]:
            raise CorpusError("CACHED_BODY_SHA_MISMATCH")
        body = body_path.read_bytes()
        if sha(body) != meta.get("sha256"):
            raise CorpusError("CACHED_BODY_SHA_MISMATCH")
        validate_body(endpoint, params, body)
        return body, meta

    def reserve(self, endpoint, params):
        with self.gate_lock:
            delay = self.next_request - self.monotonic()
            if delay > 0:
                self.sleeper(delay)
            with self.state_lock:
                if self.halted:
                    raise CorpusError(self.halted)
                if self.calls >= self.manifest["max_calls"] or self.bytes >= self.manifest["max_bytes"]:
                    self.halted = "REQUEST_OR_BYTE_BUDGET_EXHAUSTED"
                    raise CorpusError(self.halted)
                self.calls += 1
                self.endpoint_counts[endpoint] += 1
                directory = self.root / "attempts" / f"{self.calls:06d}"
                request = {"endpoint": endpoint, "params": params, "requested_at": now()}
                put(directory / "request.json", encoded(request))
            self.next_request = max(self.next_request, self.monotonic()) + REQUEST_INTERVAL
        return directory, request

    def fetch(self, endpoint, params):
        if endpoint not in ENDPOINTS or "crtfc_key" in params:
            raise CorpusError("UNSAFE_REQUEST_CONFIGURATION")
        cached = self.cached(endpoint, params)
        if cached is not None:
            return cached
        for attempt in range(MAX_ATTEMPTS_PER_FETCH):
            if attempt:
                self.sleeper(min(2 ** (attempt - 1), 16))
            directory, safe_request = self.reserve(endpoint, params)
            error, http_status, size, chunks = None, None, 0, []
            try:
                query_params = params if endpoint == "main.do" else {**params, "crtfc_key": self.key}
                request = Request(ENDPOINTS[endpoint] + "?" + urlencode(query_params),
                                  headers={"User-Agent": "TeamAlpha-historical-statement-corpus/1"})
                with self.opener(request, timeout=90) as response:
                    http_status = getattr(response, "status", 200)
                    if http_status != 200:
                        raise CorpusError("HTTP_STATUS_ERROR")
                    while True:
                        # Serialize bounded read chunks, not the HTTP requests. This
                        # prevents simultaneous readers from spending the same bytes.
                        with self.state_lock:
                            allowance = self.manifest["max_bytes"] - self.bytes
                            if allowance <= 0:
                                self.halted = "RESPONSE_BYTE_BUDGET_EXHAUSTED"
                                raise CorpusError(self.halted)
                            per_response = MAX_SINGLE_RESPONSE_BYTES - size
                            if per_response <= 0:
                                raise CorpusError("SINGLE_RESPONSE_BYTE_LIMIT_EXCEEDED")
                            chunk = response.read(min(65_536, allowance, per_response))
                            if len(chunk) > allowance:
                                raise CorpusError("READER_EXCEEDED_REQUESTED_BYTE_LIMIT")
                            self.bytes += len(chunk)
                            size += len(chunk)
                        if not chunk:
                            break
                        chunks.append(chunk)
            except HTTPError as exc:
                http_status, error = exc.code, "HTTP_STATUS_ERROR"
                exc.close()
            except CorpusError as exc:
                error = str(exc)
            except Exception:
                error = "NETWORK_READ_ERROR"
            body = b"".join(chunks)
            if error is None:
                if any(secret in body for secret in (self.key.encode(), quote(self.key).encode())):
                    error = "SECRET_ECHO_REJECTED"
                else:
                    try:
                        validate_body(endpoint, params, body)
                    except CorpusError as exc:
                        error = str(exc)
            received = now()
            outcome = {"received_at": received, "received_bytes": size,
                       "http_status": http_status, "status": error or "VALID_RAW_RESPONSE"}
            if error is None:
                suffix = {"list.json": "json", "document.xml": "zip", "main.do": "html"}[endpoint]
                body_path = directory / ("response." + suffix)
                put(body_path, body)
                meta = {**safe_request, "received_at": received, "bytes": size, "sha256": sha(body),
                        "body_path": body_path.relative_to(self.root).as_posix()}
                put(directory / "outcome.json", encoded({**outcome, "sha256": sha(body)}))
                put(self.root / "objects" / (self.cache_key(endpoint, params) + ".json"), encoded(meta))
                with self.state_lock:
                    self.success_counts[endpoint] += 1
                return body, meta
            put(directory / "outcome.json", encoded(outcome))
            if error in {"PROVIDER_REQUEST_LIMIT", "PROVIDER_AUTH_ERROR", "LIST_PROVIDER_ERROR", "SECRET_ECHO_REJECTED"} or http_status in {401, 403}:
                with self.state_lock:
                    self.halted = error
            if error != "NETWORK_READ_ERROR" and not (http_status == 429 or (http_status is not None and 500 <= http_status <= 599)):
                raise CorpusError(error) from None
        raise CorpusError("RETRIES_EXHAUSTED")


def target_quarter(report_name, manifest):
    if not isinstance(report_name, str):
        return None
    for quarter in manifest["quarters"]:
        title, month = QUARTERS[quarter]
        if re.fullmatch(r"(?:\[[^\[\]]+\]\s*)*" + title + r"\s*\(\s*2015\." + month + r"\s*\)", report_name.strip()):
            return quarter
    return None


def issuer_disclosures(client, issuer, manifest):
    rows, pages, seen = [], [], set()
    expected_pages = expected_count = None
    page = 1
    while expected_pages is None or page <= expected_pages:
        params = {"corp_code": issuer["corp_code"], "bgn_de": manifest["list_start"], "end_de": manifest["list_end"],
                  "last_reprt_at": "N", "pblntf_ty": "A", "sort": "date", "sort_mth": "asc",
                  "page_no": str(page), "page_count": str(PAGE_COUNT)}
        body, meta = client.fetch("list.json", params)
        payload = _json_body(body)
        pages.append(meta)
        if payload["status"] == "013":
            if page != 1:
                raise CorpusError("INCOMPLETE_PAGINATION_NO_DATA_MIDWAY")
            expected_pages, expected_count = 0, 0
            break
        try:
            actual_page, count, total, per_page = (int(payload[k]) for k in ("page_no", "total_count", "total_page", "page_count"))
        except (KeyError, TypeError, ValueError):
            raise CorpusError("INVALID_PAGINATION_METADATA") from None
        if (actual_page != page or count < 1 or total < 1 or per_page != PAGE_COUNT
                or total != math.ceil(count / PAGE_COUNT)):
            raise CorpusError("INCONSISTENT_PAGINATION_METADATA")
        if expected_pages is None:
            expected_pages, expected_count = total, count
        if (total, count) != (expected_pages, expected_count):
            raise CorpusError("PAGINATION_SNAPSHOT_CHANGED")
        entries = payload["list"]
        if len(entries) != min(PAGE_COUNT, count - (page - 1) * PAGE_COUNT):
            raise CorpusError("INCOMPLETE_PAGINATION_ROW_COUNT")
        for row in entries:
            if not isinstance(row, dict):
                raise CorpusError("INVALID_DISCLOSURE_ROW")
            receipt, received = row.get("rcept_no"), row.get("rcept_dt")
            if (row.get("corp_code") != issuer["corp_code"] or not isinstance(receipt, str)
                    or not re.fullmatch(r"[0-9]{14}", receipt) or not valid_date(received)
                    or not manifest["list_start"] <= received <= manifest["list_end"]):
                raise CorpusError("DISCLOSURE_SCOPE_OR_DATE_MISMATCH")
            if receipt in seen:
                raise CorpusError("DUPLICATE_RECEIPT_ACROSS_LIST_PAGES")
            seen.add(receipt)
            quarter = target_quarter(row.get("report_nm"), manifest)
            if quarter:
                listed_stock = row.get("stock_code")
                identity_status = ("LIST_STOCK_CODE_BLANK" if listed_stock in (None, "") else
                                   "LIST_STOCK_CODE_MATCH" if listed_stock == issuer["stock_code"] else
                                   "LIST_STOCK_CODE_MISMATCH")
                # A present-day list display code is not historical issuer→asset
                # certification. Retain mismatches/blank codes as evidence.
                rows.append({"quarter": quarter, "disclosure": row, "list_source_sha256": meta["sha256"],
                             "list_stock_identity_status": identity_status,
                             "historical_asset_identity_status": "UNVERIFIED"})
        page += 1
    if len(seen) != expected_count:
        raise CorpusError("INCOMPLETE_PAGINATION_TOTAL_COUNT")
    return {**issuer, "status": "DISCLOSURE_LIST_COMPLETE", "all_disclosure_count": len(seen),
            "total_pages": expected_pages, "list_responses": pages, "selected_disclosures": rows,
            "missing_quarters": [q for q in manifest["quarters"] if not any(r["quarter"] == q for r in rows)],
            "lineage_status": "UNVERIFIED"}


def _jobs(items, function):
    """Drain all in-flight jobs before returning; do not discard their ledger."""
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        pending = {pool.submit(function, item): item for item in items}
        for future in as_completed(pending):
            item = pending[future]
            try:
                results.append((item, future.result(), None))
            except CorpusError as exc:
                results.append((item, None, str(exc)))
            except Exception:
                results.append((item, None, "UNEXPECTED_LOCAL_OR_WORKER_ERROR"))
    return results


def collect(manifest_path, output, *, collect_correction_main=False, opener=urlopen,
            sleeper=time.sleep, monotonic=time.monotonic):
    """Collect into a new, caller-named local namespace; never writes a DB."""
    contract = plan(manifest_path, collect_correction_main=collect_correction_main)
    manifest = contract["manifest"]
    api_key = os.environ.get("DART_API_KEY", "").strip()
    if not api_key:
        raise CorpusError("DART_API_KEY_ENVIRONMENT_REQUIRED")
    root = Path(output)
    if root.exists() and not (root / "contract.json").is_file() and any(root.iterdir()):
        raise CorpusError("NONEMPTY_UNOWNED_OUTPUT_DIRECTORY")
    with locked(root):
        put(root / "contract.json", encoded(contract))
        client = Transport(root, manifest, api_key, opener=opener, sleeper=sleeper, monotonic=monotonic)
        result = {"schema_version": SCHEMA, "corpus_id": manifest["corpus_id"],
                  "manifest_sha256": contract["manifest_sha256"], "started_at": now(),
                  "issuers": [], "documents": [], "correction_main_pages": [], "failures": [],
                  "pit_certified": False, "silver_writes": False, "gold_writes": False,
                  "lineage_status": "UNVERIFIED", "limitations": LIMITATIONS}
        for issuer, data, error in _jobs(manifest["issuers"], lambda i: issuer_disclosures(client, i, manifest)):
            if error:
                result["failures"].append({"stage": "list", "corp_code": issuer["corp_code"], "reason": error})
            else:
                result["issuers"].append(data)
        result["issuers"].sort(key=lambda i: i["corp_code"])
        # No documents are requested unless every issuer's list is complete.
        candidates = []
        if not result["failures"]:
            for issuer in result["issuers"]:
                for selected in issuer["selected_disclosures"]:
                    candidates.append({"corp_code": issuer["corp_code"], "stock_code": issuer["stock_code"],
                                       "asset_ids": issuer["asset_ids"], **selected})
            receipts = [c["disclosure"]["rcept_no"] for c in candidates]
            if len(receipts) != len(set(receipts)):
                result["failures"].append({"stage": "selection", "reason": "DUPLICATE_SELECTED_RECEIPT"})
            if len(candidates) > manifest["max_documents"]:
                result["failures"].append({"stage": "selection", "reason": "DOCUMENT_BUDGET_EXCEEDED"})
        if not result["failures"]:
            def document(candidate):
                receipt = candidate["disclosure"]["rcept_no"]
                body, meta = client.fetch("document.xml", {"rcept_no": receipt})
                return {**candidate, "receipt_no": receipt, "official_rcept_dt": candidate["disclosure"]["rcept_dt"],
                        "document": meta, "members": pilot.validate_zip(body, expected_receipt=receipt),
                        "status": "RAW_DOCUMENT_SAVED", "lineage_status": "UNVERIFIED",
                        "historical_first_publication_proven": False, "financial_available_at": None}
            for candidate, data, error in _jobs(candidates, document):
                if error:
                    result["failures"].append({"stage": "document", "receipt_no": candidate["disclosure"]["rcept_no"], "reason": error})
                else:
                    result["documents"].append(data)
            if collect_correction_main:
                corrected_groups = {(c["corp_code"], c["quarter"]) for c in candidates
                                    if "정" in str(c["disclosure"].get("rm") or "")
                                    or re.search(r"\[(?:기재정정|첨부정정|첨부추가|정정명령부과|정정제출요구)\]", c["disclosure"]["report_nm"])}
                main_candidates = [c for c in candidates if (c["corp_code"], c["quarter"]) in corrected_groups]
                for candidate, data, error in _jobs(main_candidates, lambda c: client.fetch("main.do", {"rcpNo": c["disclosure"]["rcept_no"]})):
                    receipt = candidate["disclosure"]["rcept_no"]
                    if error:
                        result["failures"].append({"stage": "correction_main", "receipt_no": receipt, "reason": error})
                    else:
                        result["correction_main_pages"].append({"receipt_no": receipt, "main": data[1],
                                                               "status": "RAW_HTML_ONLY_LINEAGE_UNVERIFIED"})
        result["documents"].sort(key=lambda d: d["receipt_no"])
        result["correction_main_pages"].sort(key=lambda d: d["receipt_no"])
        result["failures"].sort(key=lambda f: json.dumps(f, sort_keys=True))
        result.update(completed_at=now(), calls_across_resume=client.calls, response_bytes_across_resume=client.bytes,
                      endpoint_attempt_counts=dict(client.endpoint_counts), issuer_count=len(manifest["issuers"]),
                      successful_response_counts_across_resume=dict(client.success_counts),
                      complete_issuer_list_count=len(result["issuers"]), selected_document_count=len(candidates),
                      saved_document_count=len(result["documents"]), saved_main_page_count=len(result["correction_main_pages"]),
                      missing_target_scope_count=sum(len(i["missing_quarters"]) for i in result["issuers"]),
                      list_response_count=sum(len(i["list_responses"]) for i in result["issuers"]))
        result["status"] = "RAW_CORPUS_INCOMPLETE_PIT_UNVERIFIED" if result["failures"] else "RAW_CORPUS_COMPLETE_PIT_UNVERIFIED"
        result["target_period_coverage_complete"] = not result["failures"] and result["missing_target_scope_count"] == 0
        run = len(list((root / "runs").glob("*.json"))) + 1
        put(root / "runs" / f"{run:06d}.json", encoded(result))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--collect-correction-main", action="store_true")
    args = parser.parse_args()
    try:
        result = (collect(args.manifest, args.output, collect_correction_main=args.collect_correction_main) if args.apply
                  else plan(args.manifest, collect_correction_main=args.collect_correction_main))
    except CorpusError as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc)}))
        raise SystemExit(2) from None
    if args.apply:
        keys = ("status", "calls_across_resume", "response_bytes_across_resume", "complete_issuer_list_count",
                "selected_document_count", "saved_document_count", "saved_main_page_count", "missing_target_scope_count", "failures")
        print(json.dumps({k: result[k] for k in keys}, ensure_ascii=False, indent=2))
        if result["failures"]:
            raise SystemExit(2)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
