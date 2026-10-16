"""Bounded, receipt-addressed DART raw-document pilot; never writes Silver.

Dry run: python -m scripts.backfill_dart_historical_filings --output PATH
Collect: DART_API_KEY=<environment only> ... --output PATH --apply

Only three fixed issuers and their first three 2015 reports are in scope.
This is not a complete correction ledger, financial parser or PIT certification.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
import zipfile


API_ROOT = "https://opendart.fss.or.kr/api/"
MAX_CALLS = 30
MAX_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
ISSUERS = (("005930", "00126380"), ("000660", "00164779"), ("005380", "00164742"))
WINDOWS = (
    ("Q1", "20150401", "20150630", "분기보고서", "2015.03"),
    ("Q2", "20150701", "20150930", "반기보고서", "2015.06"),
    ("Q3", "20151001", "20151231", "분기보고서", "2015.09"),
)
LIMITATIONS = [
    "RAW_EVIDENCE_ONLY: no financial numbers parsed or written to Silver",
    "PIT_NOT_CERTIFIED: historical values and statement periods not validated",
    "CORRECTION_HISTORY_INCOMPLETE: only three fixed filing-date windows inspected",
    "FIRST_REPORT_WITHIN_WINDOW_ONLY: earlier/later/withdrawn filings may be missing",
    "No comparative amounts backdated, no annual proxy and no factor evaluation",
]


class PilotError(RuntimeError):
    """Safe, fixed diagnostics: never include request URLs or response bodies."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _put(path: Path, body: bytes) -> None:
    """Never replace an existing object, including on resume."""
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise PilotError("SYMLINK_OUTPUT_FORBIDDEN")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise PilotError("IMMUTABLE_OBJECT_CONFLICT")
        return
    with path.open("xb") as target:
        target.write(body)
        target.flush()
        os.fsync(target.fileno())


def _read_json(path: Path) -> dict:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise PilotError("SYMLINK_CHECKPOINT_FORBIDDEN")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError):
        raise PilotError("INVALID_CHECKPOINT_JSON") from None
    if not isinstance(value, dict):
        raise PilotError("INVALID_CHECKPOINT_SHAPE")
    return value


def plan(max_calls: int = MAX_CALLS, max_bytes: int = MAX_BYTES) -> dict:
    if not (1 <= max_calls <= MAX_CALLS and 1 <= max_bytes <= MAX_BYTES):
        raise PilotError("BUDGET_EXCEEDS_FIXED_PILOT_LIMIT")
    return {
        "schema_version": "dart-historical-raw-pilot-v1",
        "issuers": [{"stock_code": ticker, "corp_code": corp} for ticker, corp in ISSUERS],
        "windows": [dict(zip(("quarter", "start", "end", "report_name", "period_label"), w)) for w in WINDOWS],
        "max_calls_including_retries_across_resume": max_calls,
        "max_response_bytes_across_resume": max_bytes,
        "max_unique_list_requests": 9,
        "max_selected_documents": 9,
        "list_page_limit": 1,
        "pit_certified": False,
        "silver_writes": False,
        "limitations": LIMITATIONS,
    }


@contextmanager
def _locked(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".collector.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise PilotError("COLLECTOR_LOCK_EXISTS_REVIEW_BEFORE_RESUME") from None
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink()


def validate_list(body: bytes) -> dict:
    try:
        value = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise PilotError("INVALID_LIST_JSON") from None
    if not isinstance(value, dict) or value.get("status") not in {"000", "013"}:
        raise PilotError("LIST_PROVIDER_ERROR")
    if value.get("status") == "000" and not isinstance(value.get("list"), list):
        raise PilotError("INVALID_LIST_ROWS")
    return value


def validate_zip(body: bytes, *, expected_receipt: str | None = None) -> list[dict]:
    """Validate raw ZIP members without extracting or normalizing their names.

    Official legacy DART ZIPs sometimes name their sole document member
    ``/<receipt>.xml``.  Only that exact requested-receipt form is accepted as
    raw evidence; it is never interpreted as a writable filesystem path.
    """
    if expected_receipt is not None and not re.fullmatch(r"\d{14}", expected_receipt):
        raise PilotError("INVALID_EXPECTED_DOCUMENT_RECEIPT")
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > 10000:
                raise PilotError("INVALID_ZIP_MEMBER_COUNT")
            if sum(x.file_size for x in infos) > MAX_UNCOMPRESSED_BYTES:
                raise PilotError("ZIP_UNCOMPRESSED_BUDGET_EXCEEDED")
            if not any(x.filename.lower().endswith(".xml") and not x.is_dir() for x in infos):
                raise PilotError("DOCUMENT_XML_MEMBER_MISSING")
            for item in infos:
                member = PurePosixPath(item.filename)
                raw_receipt_member = (
                    expected_receipt is not None
                    and item.filename == f"/{expected_receipt}.xml"
                )
                if ((member.is_absolute() and not raw_receipt_member)
                        or ".." in member.parts or "\\" in item.filename
                        or ":" in item.filename or stat.S_ISLNK(item.external_attr >> 16)
                        or item.flag_bits & 1):
                    raise PilotError("UNSAFE_ZIP_MEMBER")
            if archive.testzip() is not None:
                raise PilotError("ZIP_CRC_FAILURE")
            return [{"name": x.filename, "bytes": x.file_size, "crc": x.CRC} for x in infos]
    except PilotError:
        raise
    except Exception:
        raise PilotError("INVALID_DOCUMENT_ZIP") from None


def select_original(payload: dict, ticker: str, corp: str, window: tuple) -> dict:
    quarter, start, end, title, period = window
    try:
        pages = int(payload.get("total_page") or 0)
    except (TypeError, ValueError):
        raise PilotError("INVALID_LIST_PAGE_COUNT") from None
    if pages > 1:
        return {"status": "INCOMPLETE_PAGINATION", "selected": None}
    target = re.compile(r"(?:\[[^\]]+\]\s*)*" + re.escape(title) + r"\s*\(\s*" + re.escape(period) + r"\s*\)")
    exact = re.compile(re.escape(title) + r"\s*\(\s*" + re.escape(period) + r"\s*\)")
    matched = []
    seen = set()
    for row in payload.get("list") or []:
        if not isinstance(row, dict):
            raise PilotError("INVALID_DISCLOSURE_ROW")
        name = str(row.get("report_nm") or "").strip()
        if not target.fullmatch(name):
            continue
        receipt, received = str(row.get("rcept_no") or ""), str(row.get("rcept_dt") or "")
        if (row.get("corp_code") != corp or row.get("stock_code") != ticker
                or not re.fullmatch(r"\d{14}", receipt) or not re.fullmatch(r"\d{8}", received)
                or not start <= received <= end):
            raise PilotError("DISCLOSURE_SCOPE_OR_DATE_MISMATCH")
        try:
            datetime.strptime(received, "%Y%m%d")
        except ValueError:
            raise PilotError("INVALID_OFFICIAL_RECEIPT_DATE") from None
        if receipt in seen:
            raise PilotError("DUPLICATE_DISCLOSURE_RECEIPT")
        seen.add(receipt)
        matched.append(row)
    originals = [r for r in matched if exact.fullmatch(str(r["report_nm"]).strip())]
    return {
        "status": "SELECTED" if len(originals) == 1 else "NO_UNIQUE_ORIGINAL",
        "selected": originals[0] if len(originals) == 1 else None,
        "matching_disclosures": matched,
        "selection_rule": "Exactly one non-amended matching title in the fixed filing window",
        "quarter": quarter,
        "historical_first_publication_proven": False,
    }


@dataclass
class Collector:
    root: Path
    api_key: str
    max_calls: int = MAX_CALLS
    max_bytes: int = MAX_BYTES
    opener: object = urlopen
    sleeper: object = time.sleep
    interval: float = 1.0

    def __post_init__(self):
        self.calls = self.received_bytes = 0
        attempts = sorted((self.root / "attempts").glob("*/request.json"))
        for expected, request_path in enumerate(attempts, 1):
            if request_path.parent.name != f"{expected:03d}":
                raise PilotError("ATTEMPT_LEDGER_GAP")
            outcome_path = request_path.with_name("outcome.json")
            if not outcome_path.exists():
                raise PilotError("INTERRUPTED_REQUEST_REQUIRES_AUDIT_BEFORE_RESUME")
            outcome = _read_json(outcome_path)
            amount = outcome.get("received_bytes")
            if type(amount) is not int or amount < 0:
                raise PilotError("INVALID_ATTEMPT_BYTE_ACCOUNTING")
            self.received_bytes += amount
            self.calls += 1
        if self.calls > self.max_calls or self.received_bytes > self.max_bytes:
            raise PilotError("CHECKPOINT_BUDGET_EXCEEDED")

    def cached(self, key: str, endpoint: str, params: dict) -> tuple[bytes, dict] | None:
        pointer = self.root / "objects" / f"{key}.json"
        if not pointer.exists():
            return None
        meta = _read_json(pointer)
        if meta.get("endpoint") != endpoint or meta.get("params") != params:
            raise PilotError("CACHED_REQUEST_SCOPE_MISMATCH")
        relative = PurePosixPath(str(meta.get("body_path") or ""))
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
            raise PilotError("INVALID_CACHED_BODY_PATH")
        path = self.root / relative
        if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
                or not path.is_file()):
            raise PilotError("CACHED_BODY_MISSING")
        if path.stat().st_size != meta.get("bytes") or path.stat().st_size > self.max_bytes:
            raise PilotError("CACHED_BODY_SHA_MISMATCH")
        body = path.read_bytes()
        if len(body) != meta.get("bytes") or _sha(body) != meta.get("sha256"):
            raise PilotError("CACHED_BODY_SHA_MISMATCH")
        return body, meta

    def fetch(self, key: str, endpoint: str, params: dict) -> tuple[bytes, dict]:
        if endpoint not in {"list.json", "document.xml"} or "crtfc_key" in params:
            raise PilotError("UNSAFE_REQUEST_CONFIGURATION")
        cached = self.cached(key, endpoint, params)
        if cached is not None:
            return cached
        for retry in range(3):
            if self.calls >= self.max_calls or self.received_bytes >= self.max_bytes:
                raise PilotError("REQUEST_OR_BYTE_BUDGET_EXHAUSTED")
            self.calls += 1
            directory = self.root / "attempts" / f"{self.calls:03d}"
            requested = _now()
            safe_request = {"endpoint": endpoint, "params": params, "requested_at": requested}
            _put(directory / "request.json", _json_bytes(safe_request))
            self.sleeper(self.interval * (2 ** retry))
            chunks, size, error, http_status = [], 0, None, None
            budget = self.max_bytes - self.received_bytes
            try:
                query = urlencode({**params, "crtfc_key": self.api_key})
                request = Request(API_ROOT + endpoint + "?" + query, headers={"User-Agent": "TeamAlpha-raw-filing-pilot/1"})
                with self.opener(request, timeout=60) as response:
                    http_status = getattr(response, "status", 200)
                    if http_status != 200:
                        raise PilotError("HTTP_STATUS_ERROR")
                    while True:
                        if size >= budget:
                            raise PilotError("RESPONSE_BYTE_BUDGET_EXHAUSTED")
                        chunk = response.read(min(65536, budget - size))
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > budget:
                            raise PilotError("RESPONSE_BYTE_BUDGET_EXHAUSTED")
                        chunks.append(chunk)
            except HTTPError as exc:
                http_status = exc.code
                error = "HTTP_STATUS_ERROR"
            except PilotError as exc:
                error = str(exc)
            except Exception:
                error = "NETWORK_READ_ERROR"
            self.received_bytes += size
            body = b"".join(chunks)
            if error is None:
                if any(secret in body for secret in (self.api_key.encode(), quote(self.api_key).encode())):
                    error = "SECRET_ECHO_REJECTED"
                else:
                    try:
                        if endpoint == "list.json":
                            validate_list(body)
                        else:
                            validate_zip(body, expected_receipt=params.get("rcept_no"))
                    except PilotError as exc:
                        error = str(exc)
            received = _now()
            outcome = {
                "received_at": received, "received_bytes": size,
                "http_status": http_status, "status": error or "VALID_RAW_RESPONSE",
            }
            if error is None:
                suffix = "response.json" if endpoint == "list.json" else "response.zip"
                path = directory / suffix
                _put(path, body)
                meta = {**safe_request, "received_at": received, "bytes": len(body),
                        "sha256": _sha(body), "body_path": path.relative_to(self.root).as_posix()}
                _put(directory / "outcome.json", _json_bytes({**outcome, "sha256": _sha(body)}))
                _put(self.root / "objects" / f"{key}.json", _json_bytes(meta))
                return body, meta
            _put(directory / "outcome.json", _json_bytes(outcome))
            if error != "NETWORK_READ_ERROR" and http_status not in {429, 500, 502, 503, 504}:
                raise PilotError(error) from None
        raise PilotError("RETRIES_EXHAUSTED")


def collect(output: Path, *, api_key: str | None = None, max_calls: int = MAX_CALLS,
            max_bytes: int = MAX_BYTES, opener=urlopen, sleeper=time.sleep) -> dict:
    contract = plan(max_calls, max_bytes)
    api_key = api_key if api_key is not None else os.environ.get("DART_API_KEY", "")
    if not api_key.strip():
        raise PilotError("DART_API_KEY_REQUIRED_IN_ENVIRONMENT")
    root = output.absolute()
    if root.exists() and not (root / "plan.json").exists() and any(root.iterdir()):
        raise PilotError("NONEMPTY_OUTPUT_WITHOUT_PILOT_PLAN")
    with _locked(root):
        _put(root / "plan.json", _json_bytes(contract))
        client = Collector(root, api_key, max_calls, max_bytes, opener, sleeper)
        scopes = []
        try:
            for ticker, corp in ISSUERS:
                for window in WINDOWS:
                    quarter, start, end, _, _ = window
                    key = f"{ticker}-{quarter}"
                    params = {"corp_code": corp, "bgn_de": start, "end_de": end,
                              "last_reprt_at": "N", "pblntf_ty": "A", "sort": "date",
                              "sort_mth": "asc", "page_no": "1", "page_count": "100"}
                    body, list_meta = client.fetch(f"list-{key}", "list.json", params)
                    selection = select_original(validate_list(body), ticker, corp, window)
                    selection.update(stock_code=ticker, corp_code=corp, list_sha256=list_meta["sha256"])
                    _put(root / "selections" / f"{key}.json", _json_bytes(selection))
                    result = {"stock_code": ticker, "quarter": quarter, "status": selection["status"]}
                    if selection["selected"] is not None:
                        selected = selection["selected"]
                        raw, document_meta = client.fetch(f"document-{key}", "document.xml", {"rcept_no": selected["rcept_no"]})
                        archive = {"receipt_no": selected["rcept_no"], "official_rcept_dt": selected["rcept_dt"],
                                   "list_sha256": list_meta["sha256"], "document": document_meta,
                                   "members": validate_zip(raw, expected_receipt=selected["rcept_no"]),
                                   "pit_certified": False, "limitations": LIMITATIONS}
                        _put(root / "documents" / f"{key}.json", _json_bytes(archive))
                        result.update(status="RAW_DOCUMENT_SAVED", receipt_no=selected["rcept_no"],
                                      official_rcept_dt=selected["rcept_dt"], sha256=document_meta["sha256"])
                    scopes.append(result)
            failure = None
        except PilotError as exc:
            failure = str(exc)
        complete = len(scopes) == 9 and all(x["status"] == "RAW_DOCUMENT_SAVED" for x in scopes)
        summary = {"schema_version": contract["schema_version"], "recorded_at": _now(),
                   "status": "RAW_PILOT_COMPLETE_PIT_UNVERIFIED" if complete else "RAW_PILOT_INCOMPLETE",
                   "failure": failure, "calls_across_resume": client.calls,
                   "response_bytes_across_resume": client.received_bytes, "scopes": scopes,
                   "pit_certified": False, "silver_writes": False, "limitations": LIMITATIONS}
        run_number = len(list((root / "runs").glob("*.json"))) + 1
        _put(root / "runs" / f"{run_number:03d}.json", _json_bytes(summary))
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Make bounded official API requests; default is plan only")
    parser.add_argument("--max-calls", type=int, default=MAX_CALLS)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args()
    try:
        result = (collect(args.output, max_calls=args.max_calls, max_bytes=args.max_bytes)
                  if args.apply else plan(args.max_calls, args.max_bytes))
    except PilotError as exc:
        parser.exit(2, f"DART pilot stopped: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.apply and result["status"] != "RAW_PILOT_COMPLETE_PIT_UNVERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
