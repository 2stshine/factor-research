#!/usr/bin/env python3
"""Audit FMP statement coverage for current KOSPI/KOSDAQ companies.

The company-level universe comes from the official KRX KIND listed-corporation
download. FMP_API_KEY is read from the environment (or the git-ignored .env),
never hardcoded or persisted. Detailed FMP responses are checkpointed per
symbol/endpoint so interrupted runs resume without repeating completed calls.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import random
import re
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Sequence

from dotenv import load_dotenv


KIND_DOWNLOAD = (
    "https://kind.krx.co.kr/corpgeneral/"
    "corpList.do?method=download&searchType=13"
)
KIND_PAGE = (
    "https://kind.krx.co.kr/corpgeneral/"
    "corpList.do?method=loadInitPage&searchType=13"
)
FMP_BASE = "https://financialmodelingprep.com/stable"
SCHEMA = 1

SPECS: tuple[tuple[str, str, str, int], ...] = (
    ("annual_income", "income-statement", "annual", 100),
    ("annual_balance", "balance-sheet-statement", "annual", 100),
    ("annual_cashflow", "cash-flow-statement", "annual", 100),
    ("quarterly_income", "income-statement", "quarter", 200),
    ("quarterly_balance", "balance-sheet-statement", "quarter", 200),
    ("quarterly_cashflow", "cash-flow-statement", "quarter", 200),
)

FIELDS = {
    "income": ("revenue", "operatingIncome", "netIncome", "eps"),
    "balance": (
        "totalAssets",
        "totalLiabilities",
        "totalStockholdersEquity",
        "cashAndCashEquivalents",
    ),
    "cashflow": ("operatingCashFlow", "capitalExpenditure", "freeCashFlow"),
}

BASE_COLUMNS = (
    "stock_code", "company_name", "market", "krx_market_raw", "industry",
    "main_products", "listing_date", "region", "region_source_values",
    "company_type", "is_spac", "is_reit", "is_new_listing_365d",
    "krx_source_row_count", "expected_fmp_symbol", "actual_fmp_symbol",
    "fmp_stock_symbol", "fmp_financial_symbol", "fmp_symbol_match_method",
    "fmp_stock_name", "fmp_stock_exchange", "fmp_stock_exists",
    "fmp_financial_symbol_exists", "details_checked",
    "annual_income_exists", "annual_balance_exists", "annual_cashflow_exists",
    "quarterly_income_exists", "quarterly_balance_exists",
    "quarterly_cashflow_exists", "annual_complete", "quarterly_complete",
)

STAT_COLUMNS = tuple(
    f"{key}_{metric}"
    for key, *_ in SPECS
    for metric in ("first_date", "latest_date", "count", "distinct_date_count")
)

DEPTH_COLUMNS = (
    "annual_first_date", "annual_latest_date", "annual_min_statement_records",
    "annual_history_years", "quarterly_first_date", "quarterly_latest_date",
    "quarterly_min_statement_records", "quarterly_history_years",
    "annual_ge3y", "annual_ge5y", "annual_ge10y", "quarterly_ge3y",
    "quarterly_ge5y", "quarterly_ge10y", "oldest_financial_date",
    "latest_financial_date", "reported_currency_mode",
    "reported_currency_krw_share",
)

ALL_COLUMNS = BASE_COLUMNS + STAT_COLUMNS + DEPTH_COLUMNS

MISSING_COLUMNS = (
    "stock_code", "company_name", "market", "company_type", "listing_date",
    "is_new_listing_365d", "primary_reason", "reason",
    "expected_fmp_symbol", "fmp_symbol",
)

SUMMARY_COLUMNS = (
    "market", "krx_companies", "fmp_stock_symbols",
    "fmp_stock_symbol_coverage_pct", "fmp_financial_symbols",
    "fmp_financial_symbol_coverage_pct", "annual_complete",
    "annual_complete_pct", "quarterly_complete", "quarterly_complete_pct",
    "annual_ge3y", "annual_ge3y_pct", "annual_ge5y", "annual_ge5y_pct",
    "annual_ge10y", "annual_ge10y_pct", "quarterly_ge3y",
    "quarterly_ge3y_pct", "quarterly_ge5y", "quarterly_ge5y_pct",
    "quarterly_ge10y", "quarterly_ge10y_pct", "missing_companies",
    "new_listing_companies", "new_listing_annual_complete",
    "new_listing_annual_complete_pct", "new_listing_quarterly_complete",
    "new_listing_quarterly_complete_pct", "general_companies_ex_spac_reit",
    "general_annual_complete", "general_annual_complete_pct",
    "general_quarterly_complete", "general_quarterly_complete_pct",
    "median_annual_history_years_complete",
    "median_quarterly_history_years_complete",
)

COMPLETENESS_COLUMNS = (
    "market", "period", "statement", "field", "record_count", "null_count",
    "null_rate_pct", "reported_currency_nonnull_count",
    "reported_currency_mode", "reported_currency_mode_count",
    "reported_currency_mode_share_pct", "krw_count", "krw_share_pct",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value: object) -> None:
    atomic_bytes(
        path,
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode(),
    )


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def download(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "factor-research-fmp-korea-coverage/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_kind(checkpoint: Path, refresh: bool, timeout: float) -> tuple[bytes, dict]:
    raw_path = checkpoint / "krx_kind_company_list.xls"
    meta_path = checkpoint / "krx_kind_company_list.meta.json"
    if raw_path.exists() and meta_path.exists() and not refresh:
        raw, meta = raw_path.read_bytes(), read_json(meta_path)
        if meta.get("sha256") == sha256(raw):
            return raw, meta
    raw = download(KIND_DOWNLOAD, timeout)
    if len(raw) < 10_000 or b"<table" not in raw.lower():
        raise RuntimeError("KRX KIND download is invalid")
    meta = {
        "source_url": KIND_DOWNLOAD,
        "fetched_at_utc": now_utc(),
        "sha256": sha256(raw),
        "bytes": len(raw),
    }
    atomic_bytes(raw_path, raw)
    atomic_json(meta_path, meta)
    return raw, meta


class KindTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag.lower() == "tr":
            self.row = []
        elif tag.lower() in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self.cell is not None:
            if self.row is not None:
                self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
            self.cell = None


def parse_kind(raw: bytes, as_of: date) -> tuple[list[dict[str, object]], dict]:
    expected = [
        "회사명", "시장구분", "종목코드", "업종", "주요제품", "상장일",
        "결산월", "대표자명", "홈페이지", "지역",
    ]
    parser = KindTableParser()
    parser.feed(raw.decode("euc-kr"))
    if not parser.rows or parser.rows[0] != expected:
        found = parser.rows[0] if parser.rows else []
        raise RuntimeError(f"unexpected KIND columns: {found}")
    source: list[dict[str, str]] = []
    for values in parser.rows[1:]:
        if len(values) != len(expected):
            continue
        row = dict(zip(expected, values, strict=True))
        if row["시장구분"] not in {"유가", "유가증권", "코스닥"}:
            continue
        code = row["종목코드"].upper().zfill(6)
        if not re.fullmatch(r"[0-9A-Z]{6}", code):
            raise RuntimeError(f"invalid KRX stock code: {code!r}")
        row["종목코드"] = code
        source.append(row)

    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in source:
        market = "KOSPI" if row["시장구분"] in {"유가", "유가증권"} else "KOSDAQ"
        groups[(market, row["종목코드"])].append(row)
    companies = []
    duplicate_groups = 0
    duplicate_rows = 0
    order = lambda item: (0 if item[0][0] == "KOSPI" else 1, item[0][1])
    for (market, code), rows in sorted(groups.items(), key=order):
        if len(rows) > 1:
            duplicate_groups += 1
            duplicate_rows += len(rows) - 1
        names = {row["회사명"] for row in rows if row["회사명"]}
        if len(names) != 1:
            raise RuntimeError(f"conflicting KRX names for {market} {code}: {names}")

        def last(column: str) -> str:
            values = [row[column] for row in rows if row[column]]
            return values[-1] if values else ""

        company_name = next(iter(names))
        listed = date.fromisoformat(last("상장일"))
        regions = list(dict.fromkeys(row["지역"] for row in rows if row["지역"]))
        # Avoid the false positive "메리츠" -> "리츠".
        is_spac = bool(re.search(r"스팩|기업인수목적", company_name))
        is_reit = bool(re.search(r"(?<!메)리츠|부동산투자회사", company_name))
        companies.append({
            "stock_code": code,
            "company_name": company_name,
            "market": market,
            "krx_market_raw": last("시장구분"),
            "industry": last("업종"),
            "main_products": last("주요제품"),
            "listing_date": listed.isoformat(),
            "region": regions[-1] if regions else "",
            "region_source_values": " | ".join(regions),
            "company_type": "SPAC" if is_spac else "REIT" if is_reit else "GENERAL",
            "is_spac": is_spac,
            "is_reit": is_reit,
            "is_new_listing_365d": 0 <= (as_of - listed).days <= 365,
            "krx_source_row_count": len(rows),
        })
    counts = Counter(row["market"] for row in companies)
    audit = {
        "source_rows_kospi_kosdaq": len(source),
        "company_rows_after_code_dedup": len(companies),
        "duplicate_code_groups": duplicate_groups,
        "duplicate_source_rows_removed": duplicate_rows,
        "kospi_companies": counts["KOSPI"],
        "kosdaq_companies": counts["KOSDAQ"],
    }
    return companies, audit


class ApiError(Exception):
    def __init__(self, status: int | None, message: str, retry_after: float = 0):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self, rps: float):
        self.interval = 1 / rps
        self.next_at = 0.0
        self.lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self.lock:
            now = time.monotonic()
            if self.next_at > now:
                await asyncio.sleep(self.next_at - now)
            self.next_at = max(now, self.next_at) + self.interval


class FMP:
    def __init__(self, key: str, rps: float, retries: int, timeout: float):
        self.key, self.retries, self.timeout = key, retries, timeout
        self.limiter = RateLimiter(rps)

    def once(self, endpoint: str, params: dict[str, object]) -> Any:
        query = urllib.parse.urlencode({**params, "apikey": self.key})
        request = urllib.request.Request(
            f"{FMP_BASE}/{endpoint}?{query}",
            headers={"Accept": "application/json", "User-Agent": "factor-research-fmp-korea-coverage/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            retry_after = 0.0
            try:
                retry_after = float(exc.headers.get("Retry-After", "0"))
            except ValueError:
                pass
            body = exc.read(400).decode(errors="replace")
            raise ApiError(exc.code, body or str(exc.reason), retry_after) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ApiError(None, str(exc)) from exc
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(None, "invalid JSON response") from exc
        if isinstance(value, dict):
            for field in ("Error Message", "error", "message"):
                if value.get(field):
                    raise ApiError(400, str(value[field])[:300])
        return value

    async def get(self, endpoint: str, **params: object) -> Any:
        for attempt in range(self.retries + 1):
            await self.limiter.wait()
            try:
                return await asyncio.to_thread(self.once, endpoint, params)
            except ApiError as exc:
                retryable = exc.status in {None, 429} or (
                    exc.status is not None and 500 <= exc.status < 600
                )
                if not retryable or attempt == self.retries:
                    raise
                delay = max(exc.retry_after, min(60.0, 2**attempt))
                await asyncio.sleep(delay + random.random() / 2)
        raise AssertionError("unreachable")


async def cached_list(client: FMP, endpoint: str, root: Path, refresh: bool) -> Any:
    data_path = root / f"fmp_{endpoint}.json"
    meta_path = root / f"fmp_{endpoint}.meta.json"
    if data_path.exists() and meta_path.exists() and not refresh:
        payload = read_json(data_path)
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        if read_json(meta_path).get("sha256") == sha256(canonical):
            return payload
    payload = await client.get(endpoint)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    atomic_bytes(data_path, canonical)
    atomic_json(meta_path, {
        "endpoint": f"{FMP_BASE}/{endpoint}", "fetched_at_utc": now_utc(),
        "sha256": sha256(canonical),
        "record_count": len(payload) if isinstance(payload, list) else None,
    })
    return payload


def stock_list(payload: Any) -> tuple[set[str], dict[str, dict]]:
    if not isinstance(payload, list):
        raise RuntimeError("FMP stock-list is not an array")
    records = {}
    for item in payload:
        if isinstance(item, dict) and item.get("symbol"):
            records.setdefault(str(item["symbol"]).strip().upper(), item)
    if not records:
        raise RuntimeError("FMP stock-list is empty")
    return set(records), records


def financial_list(payload: Any) -> set[str]:
    if not isinstance(payload, list):
        raise RuntimeError("FMP financial-statement-symbol-list is not an array")
    result = set()
    for item in payload:
        raw = item if isinstance(item, str) else item.get("symbol") if isinstance(item, dict) else ""
        if raw:
            result.add(str(raw).strip().upper())
    if not result:
        raise RuntimeError("FMP financial-statement-symbol-list is empty")
    return result


def match(company: dict, stocks: set[str], financials: set[str], records: dict) -> dict:
    code = str(company["stock_code"])
    expected_suffix = ".KS" if company["market"] == "KOSPI" else ".KQ"
    alternate_suffix = ".KQ" if expected_suffix == ".KS" else ".KS"
    expected, alternate = code + expected_suffix, code + alternate_suffix
    candidates = [symbol for symbol in (expected, alternate) if symbol in stocks | financials]
    stock_candidates = [symbol for symbol in candidates if symbol in stocks]
    fin_candidates = [symbol for symbol in candidates if symbol in financials]
    actual = (
        expected if expected in fin_candidates else fin_candidates[0] if fin_candidates
        else expected if expected in stock_candidates else stock_candidates[0] if stock_candidates
        else ""
    )
    stock_symbol = expected if expected in stock_candidates else stock_candidates[0] if stock_candidates else ""
    fin_symbol = expected if expected in fin_candidates else fin_candidates[0] if fin_candidates else ""
    item = records.get(stock_symbol, {})
    return {
        "expected_fmp_symbol": expected,
        "actual_fmp_symbol": actual,
        "fmp_stock_symbol": stock_symbol,
        "fmp_financial_symbol": fin_symbol,
        "fmp_symbol_match_method": (
            "none" if not actual else "expected_exact_crosschecked" if actual == expected
            else "alternate_krx_suffix_from_fmp_lists"
        ),
        "fmp_stock_name": item.get("name") or item.get("companyName") or "",
        "fmp_stock_exchange": item.get("exchangeShortName") or item.get("exchange") or "",
        "fmp_stock_exists": bool(stock_candidates),
        "fmp_financial_symbol_exists": bool(fin_candidates),
    }


def detail_path(root: Path, symbol: str) -> Path:
    return root / "details" / f"{re.sub(r'[^0-9A-Za-z._-]', '_', symbol)}.json"


def load_detail(root: Path, symbol: str) -> dict:
    path = detail_path(root, symbol)
    try:
        value = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError):
        value = {}
    if value.get("schema_version") != SCHEMA or value.get("symbol") != symbol:
        value = {"schema_version": SCHEMA, "symbol": symbol, "responses": {}}
    value.setdefault("responses", {})
    return value


def response_valid(value: Any, endpoint: str, period: str, limit: int) -> bool:
    return (
        isinstance(value, dict) and value.get("endpoint") == endpoint
        and value.get("period") == period and value.get("limit") == limit
        and isinstance(value.get("records"), list)
    )


def detail_complete(root: Path, symbol: str) -> bool:
    responses = load_detail(root, symbol)["responses"]
    return all(response_valid(responses.get(key), endpoint, period, limit) for key, endpoint, period, limit in SPECS)


async def fetch_one(client: FMP, root: Path, symbol: str) -> None:
    path, payload = detail_path(root, symbol), load_detail(root, symbol)
    for key, endpoint, period, limit in SPECS:
        if response_valid(payload["responses"].get(key), endpoint, period, limit):
            continue
        result = await client.get(endpoint, symbol=symbol, period=period, limit=limit)
        if not isinstance(result, list):
            raise RuntimeError(f"non-array FMP response: {symbol} {key}")
        payload["responses"][key] = {
            "endpoint": endpoint, "period": period, "limit": limit,
            "fetched_at_utc": now_utc(), "records": result,
        }
        payload["updated_at_utc"] = now_utc()
        atomic_json(path, payload)


async def fetch_details(client: FMP, root: Path, symbols: Sequence[str], concurrency: int) -> None:
    unique = sorted(set(symbols))
    pending = [symbol for symbol in unique if not detail_complete(root, symbol)]
    print(f"FMP detail checkpoints: {len(unique)-len(pending):,} reusable, {len(pending):,} pending", file=sys.stderr, flush=True)
    queue: asyncio.Queue[str] = asyncio.Queue()
    for symbol in pending:
        queue.put_nowait(symbol)
    completed, lock = 0, asyncio.Lock()

    async def worker() -> None:
        nonlocal completed
        while True:
            try:
                symbol = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await fetch_one(client, root, symbol)
                async with lock:
                    completed += 1
                    if completed % 50 == 0 or completed == len(pending):
                        print(f"FMP detail progress: {completed:,}/{len(pending):,}", file=sys.stderr, flush=True)
            finally:
                queue.task_done()

    async with asyncio.TaskGroup() as group:
        for _ in range(min(concurrency, len(pending))):
            group.create_task(worker())


def record_dates(records: Sequence[dict]) -> list[str]:
    result = set()
    for record in records:
        raw = str(record.get("date") or "")[:10]
        try:
            result.add(date.fromisoformat(raw).isoformat())
        except ValueError:
            pass
    return sorted(result)


def min_text(values: Iterable[object]) -> str:
    clean = sorted(str(value) for value in values if value)
    return clean[0] if clean else ""


def max_text(values: Iterable[object]) -> str:
    clean = sorted(str(value) for value in values if value)
    return clean[-1] if clean else ""


def enrich(row: dict, root: Path) -> dict[str, list[dict]]:
    symbol = str(row["fmp_financial_symbol"])
    responses = load_detail(root, symbol)["responses"] if symbol else {}
    by_key: dict[str, list[dict]] = {}
    stats: dict[str, dict] = {}
    for key, endpoint, period, limit in SPECS:
        value = responses.get(key)
        if symbol and not response_valid(value, endpoint, period, limit):
            raise RuntimeError(f"incomplete checkpoint: {symbol} {key}")
        records = value["records"] if symbol else []
        by_key[key] = records
        dates = record_dates(records)
        stats[key] = {
            "exists": bool(records), "first_date": dates[0] if dates else "",
            "latest_date": dates[-1] if dates else "", "count": len(records),
            "distinct_date_count": len(dates),
        }
        row[f"{key}_exists"] = bool(records)
        for field in ("first_date", "latest_date", "count", "distinct_date_count"):
            row[f"{key}_{field}"] = stats[key][field]
    row["details_checked"] = bool(symbol)
    annual = ("annual_income", "annual_balance", "annual_cashflow")
    quarter = ("quarterly_income", "quarterly_balance", "quarterly_cashflow")
    row["annual_complete"] = all(stats[key]["exists"] for key in annual)
    row["quarterly_complete"] = all(stats[key]["exists"] for key in quarter)
    for prefix, keys, divisor in (("annual", annual, 1), ("quarterly", quarter, 4)):
        if row[f"{prefix}_complete"]:
            count = min(stats[key]["distinct_date_count"] for key in keys)
            row[f"{prefix}_first_date"] = max_text(stats[key]["first_date"] for key in keys)
            row[f"{prefix}_latest_date"] = min_text(stats[key]["latest_date"] for key in keys)
        else:
            count = 0
            row[f"{prefix}_first_date"] = row[f"{prefix}_latest_date"] = ""
        row[f"{prefix}_min_statement_records"] = count
        row[f"{prefix}_history_years"] = round(count / divisor, 2)
        for years in (3, 5, 10):
            row[f"{prefix}_ge{years}y"] = bool(row[f"{prefix}_complete"] and count >= years * divisor)
    dates = [day for records in by_key.values() for day in record_dates(records)]
    row["oldest_financial_date"] = min(dates) if dates else ""
    row["latest_financial_date"] = max(dates) if dates else ""
    currencies = Counter(
        str(record.get("reportedCurrency") or "").strip().upper()
        for records in by_key.values() for record in records
        if str(record.get("reportedCurrency") or "").strip()
    )
    row["reported_currency_mode"] = currencies.most_common(1)[0][0] if currencies else ""
    row["reported_currency_krw_share"] = round(currencies.get("KRW", 0) / sum(currencies.values()), 6) if currencies else ""
    return by_key


def pct(n: int, d: int) -> float:
    return round(n / d * 100, 4) if d else 0.0


def reasons(row: dict) -> list[str]:
    result = []
    if not row["fmp_stock_exists"]:
        result.append("NO_FMP_STOCK_SYMBOL")
    if not row["fmp_financial_symbol_exists"]:
        result.append("NO_FMP_FINANCIAL_SYMBOL")
        return result
    for period, label in (("annual", "ANNUAL"), ("quarterly", "QUARTERLY")):
        for statement, name in (("income", "INCOME"), ("balance", "BALANCE_SHEET"), ("cashflow", "CASH_FLOW")):
            if not row[f"{period}_{statement}_exists"]:
                result.append(f"{label}_{name}_MISSING")
    if row["annual_complete"] and not row["quarterly_complete"]:
        result.append("ANNUAL_EXISTS_QUARTERLY_INCOMPLETE")
    if row["annual_complete"] and not row["annual_ge3y"]:
        result.append("ANNUAL_HISTORY_LT_3Y")
    if row["quarterly_complete"] and not row["quarterly_ge3y"]:
        result.append("QUARTERLY_HISTORY_LT_3Y")
    return result


def build_missing(rows: Sequence[dict]) -> list[dict]:
    output = []
    for row in rows:
        why = reasons(row)
        if why:
            output.append({
                "stock_code": row["stock_code"], "company_name": row["company_name"],
                "market": row["market"], "company_type": row["company_type"],
                "listing_date": row["listing_date"],
                "is_new_listing_365d": row["is_new_listing_365d"],
                "primary_reason": why[0], "reason": ";".join(why),
                "expected_fmp_symbol": row["expected_fmp_symbol"],
                "fmp_symbol": row["actual_fmp_symbol"],
            })
    return output


def select_market(rows: Sequence[dict], market: str) -> list[dict]:
    return list(rows) if market == "TOTAL" else [row for row in rows if row["market"] == market]


def build_summary(rows: Sequence[dict], missing: Sequence[dict]) -> list[dict]:
    missing_keys = {(row["market"], row["stock_code"]) for row in missing}
    output = []
    metrics = (
        ("fmp_stock_symbols", "fmp_stock_exists"),
        ("fmp_financial_symbols", "fmp_financial_symbol_exists"),
        ("annual_complete", "annual_complete"), ("quarterly_complete", "quarterly_complete"),
        ("annual_ge3y", "annual_ge3y"), ("annual_ge5y", "annual_ge5y"),
        ("annual_ge10y", "annual_ge10y"), ("quarterly_ge3y", "quarterly_ge3y"),
        ("quarterly_ge5y", "quarterly_ge5y"), ("quarterly_ge10y", "quarterly_ge10y"),
    )
    for market in ("KOSPI", "KOSDAQ", "TOTAL"):
        group = select_market(rows, market)
        total = len(group)
        result: dict[str, object] = {"market": market, "krx_companies": total}
        for name, field in metrics:
            value = sum(bool(row[field]) for row in group)
            result[name] = value
            result[{"fmp_stock_symbols": "fmp_stock_symbol_coverage_pct", "fmp_financial_symbols": "fmp_financial_symbol_coverage_pct"}.get(name, f"{name}_pct")] = pct(value, total)
        result["missing_companies"] = sum((row["market"], row["stock_code"]) in missing_keys for row in group)
        new = [row for row in group if row["is_new_listing_365d"]]
        result["new_listing_companies"] = len(new)
        for field in ("annual_complete", "quarterly_complete"):
            value = sum(bool(row[field]) for row in new)
            result[f"new_listing_{field}"] = value
            result[f"new_listing_{field}_pct"] = pct(value, len(new))
        general = [row for row in group if not row["is_spac"] and not row["is_reit"]]
        result["general_companies_ex_spac_reit"] = len(general)
        for field in ("annual_complete", "quarterly_complete"):
            value = sum(bool(row[field]) for row in general)
            result[f"general_{field}"] = value
            result[f"general_{field}_pct"] = pct(value, len(general))
        annual_depth = [float(row["annual_history_years"]) for row in group if row["annual_complete"]]
        quarter_depth = [float(row["quarterly_history_years"]) for row in group if row["quarterly_complete"]]
        result["median_annual_history_years_complete"] = round(statistics.median(annual_depth), 2) if annual_depth else ""
        result["median_quarterly_history_years_complete"] = round(statistics.median(quarter_depth), 2) if quarter_depth else ""
        output.append(result)
    return output


def build_completeness(detailed: Sequence[tuple[dict, dict[str, list[dict]]]]) -> list[dict]:
    acc: dict[tuple[str, str, str, str], dict] = defaultdict(
        lambda: {"records": 0, "nulls": 0, "currencies": Counter()}
    )
    for company, by_key in detailed:
        for market in (company["market"], "TOTAL"):
            for key, records in by_key.items():
                period, statement = key.split("_", 1)
                for field in FIELDS[statement]:
                    item = acc[(market, period, statement, field)]
                    item["records"] += len(records)
                    item["nulls"] += sum(record.get(field) is None or record.get(field) == "" for record in records)
                    item["currencies"].update(
                        str(record.get("reportedCurrency") or "").strip().upper()
                        for record in records if str(record.get("reportedCurrency") or "").strip()
                    )
    output = []
    for market in ("KOSPI", "KOSDAQ", "TOTAL"):
        for period in ("annual", "quarterly"):
            for statement in ("income", "balance", "cashflow"):
                for field in FIELDS[statement]:
                    item = acc[(market, period, statement, field)]
                    currencies, count = item["currencies"], sum(item["currencies"].values())
                    mode, mode_count = currencies.most_common(1)[0] if currencies else ("", 0)
                    output.append({
                        "market": market, "period": period, "statement": statement,
                        "field": field, "record_count": item["records"],
                        "null_count": item["nulls"], "null_rate_pct": pct(item["nulls"], item["records"]),
                        "reported_currency_nonnull_count": count,
                        "reported_currency_mode": mode,
                        "reported_currency_mode_count": mode_count,
                        "reported_currency_mode_share_pct": pct(mode_count, count),
                        "krw_count": currencies.get("KRW", 0),
                        "krw_share_pct": pct(currencies.get("KRW", 0), count),
                    })
    return output


def csv_value(value: object) -> object:
    return "true" if value is True else "false" if value is False else value


def write_csv(path: Path, rows: Sequence[dict], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", quoting=csv.QUOTE_ALL, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({column: csv_value(row.get(column, "")) for column in columns})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(md(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def count_pct(value: object, total: int) -> str:
    return f"{int(value):,} ({pct(int(value), total):.2f}%)"


def report(rows: Sequence[dict], missing: Sequence[dict], summary: Sequence[dict], completeness: Sequence[dict], kind_meta: dict, audit: dict, checkpoint: Path) -> str:
    by_market = {row["market"]: row for row in summary}
    top = []
    for market in ("KOSPI", "KOSDAQ", "TOTAL"):
        item, total = by_market[market], int(by_market[market]["krx_companies"])
        top.append((market, f"{total:,}", count_pct(item["fmp_stock_symbols"], total), count_pct(item["annual_complete"], total), count_pct(item["quarterly_complete"], total), count_pct(item["annual_ge5y"], total), count_pct(item["annual_ge10y"], total)))
    lines = [
        "# FMP 한국 KOSPI/KOSDAQ 재무제표 coverage 전수조사", "",
        table(("Market", "KRX companies", "FMP symbols", "Annual complete", "Quarterly complete", ">=5y annual", ">=10y annual"), top), "",
        f"- 생성 시각(UTC): {now_utc()}",
        f"- KRX 원본 취득 시각(UTC): {kind_meta.get('fetched_at_utc', '')}",
        f"- KRX 원본 SHA-256: `{kind_meta.get('sha256', '')}`",
        f"- 체크포인트: `{checkpoint}`",
        "- `FMP symbols`는 FMP `stock-list` 존재 기업 수다. 실제 재무 coverage는 6개 statement 응답으로 별도 판정했다.", "",
        "## Coverage 단계별 결과", "",
    ]
    coverage = []
    for market in ("KOSPI", "KOSDAQ", "TOTAL"):
        item, total = by_market[market], int(by_market[market]["krx_companies"])
        coverage.append((market, count_pct(item["fmp_stock_symbols"], total), count_pct(item["fmp_financial_symbols"], total), count_pct(item["annual_complete"], total), count_pct(item["quarterly_complete"], total), " / ".join(count_pct(item[f"annual_ge{n}y"], total) for n in (3, 5, 10)), " / ".join(count_pct(item[f"quarterly_ge{n}y"], total) for n in (3, 5, 10))))
    lines += [table(("Market", "Symbol", "Financial symbol", "Annual complete", "Quarterly complete", "Annual >=3/5/10y", "Quarterly >=3/5/10y"), coverage), "", "## History depth", ""]
    lines += [table(("Market", "Median annual history (years)", "Median quarterly history (years)"), [(market, by_market[market]["median_annual_history_years_complete"], by_market[market]["median_quarterly_history_years_complete"]) for market in ("KOSPI", "KOSDAQ", "TOTAL")]), "", "연간 N년은 세 재무제표 각각 N개 결산일, 분기 N년은 각각 `4 × N`개 결산일이 있을 때 충족한다.", ""]
    oldest = sorted((row for row in rows if row["oldest_financial_date"]), key=lambda row: row["oldest_financial_date"])[:20]
    lines += ["### 가장 오래된 financial history (상위 20)", "", table(("Market", "Code", "Company", "FMP symbol", "Oldest", "Latest"), [(row["market"], row["stock_code"], row["company_name"], row["actual_fmp_symbol"], row["oldest_financial_date"], row["latest_financial_date"]) for row in oldest]), "", "## 신규상장사 및 SPAC/REIT 영향", ""]
    impact = []
    for market in ("KOSPI", "KOSDAQ", "TOTAL"):
        item = by_market[market]
        nt, gt = int(item["new_listing_companies"]), int(item["general_companies_ex_spac_reit"])
        impact.append((market, nt, count_pct(item["new_listing_annual_complete"], nt), count_pct(item["new_listing_quarterly_complete"], nt), gt, count_pct(item["general_annual_complete"], gt), count_pct(item["general_quarterly_complete"], gt)))
    lines += [table(("Market", "New listings <=365d", "New annual", "New quarterly", "General ex SPAC/REIT", "General annual", "General quarterly"), impact), ""]
    type_rows = []
    for market in ("KOSPI", "KOSDAQ", "TOTAL"):
        group = select_market(rows, market)
        for kind in ("GENERAL", "SPAC", "REIT"):
            subset = [row for row in group if row["company_type"] == kind]
            if subset:
                type_rows.append((market, kind, len(subset), count_pct(sum(bool(row["annual_complete"]) for row in subset), len(subset)), count_pct(sum(bool(row["quarterly_complete"]) for row in subset), len(subset))))
    lines += [table(("Market", "Type", "Companies", "Annual complete", "Quarterly complete"), type_rows), "", "신규상장사는 생성일 기준 365일 이내다. SPAC/REIT는 현재 KIND 회사명 키워드로 플래그했으며 삭제하지 않았다.", "", "## 주요 필드 completeness 및 reportedCurrency", ""]
    lines += [table(("Market", "Period", "Statement", "Field", "Records", "Null rate", "Currency mode", "KRW share"), [(item["market"], item["period"], item["statement"], item["field"], f"{int(item['record_count']):,}", f"{float(item['null_rate_pct']):.2f}%", item["reported_currency_mode"], f"{float(item['krw_share_pct']):.2f}%") for item in completeness]), "", "Null은 키 없음, JSON null, 빈 문자열이다. 0은 정상 값이다. 통화 비중은 reportedCurrency 비-null 레코드가 분모다.", "", "## 누락 기업 요약", "", f"누락/짧은-history 분류 기업: **{len(missing):,}개**", ""]
    reason_counts = Counter(reason for row in missing for reason in row["reason"].split(";"))
    lines += [table(("Reason", "Companies"), sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))), "", "### 누락 기업 전체 목록", "", table(("Market", "Code", "Company", "Type", "Reason", "FMP symbol"), [(row["market"], row["stock_code"], row["company_name"], row["company_type"], row["reason"], row["fmp_symbol"]) for row in missing]), "", "## Universe 및 판정 방법", "", f"- KIND KOSPI/KOSDAQ 원본 행: {audit['source_rows_kospi_kosdaq']:,}", f"- 종목코드 중복 통합 후 기업 수: {audit['company_rows_after_code_dedup']:,}", f"- 중복 종목코드 그룹/제거 행: {audit['duplicate_code_groups']:,} / {audit['duplicate_source_rows_removed']:,}", "- KIND 상장법인목록은 기업 단위 대표 코드를 제공해 우선주/종류주를 별도 기업으로 세지 않으며 ETF·ETN·ELW 목록이 아니다.", "- Expected `.KS`/`.KQ`는 FMP 두 목록과 교차검증했고, 실제 목록의 반대 suffix도 보존했다.", "- 상세 호출은 financial-statement-symbol-list 후보만 수행했다. Annual/quarterly complete는 income·balance·cash flow 실제 응답이 모두 비어 있지 않을 때만 true다.", "", "## Sources", "", f"- KRX KIND: {KIND_PAGE}", f"- KRX KIND download: {KIND_DOWNLOAD}", f"- FMP stock list: {FMP_BASE}/stock-list", f"- FMP financial symbols: {FMP_BASE}/financial-statement-symbol-list", f"- FMP income: {FMP_BASE}/income-statement", f"- FMP balance sheet: {FMP_BASE}/balance-sheet-statement", f"- FMP cash flow: {FMP_BASE}/cash-flow-statement", ""]
    return "\n".join(lines)


def validate(rows: Sequence[dict], missing: Sequence[dict], summary: Sequence[dict], completeness: Sequence[dict]) -> None:
    keys = [(row["market"], row["stock_code"]) for row in rows]
    if len(keys) != len(set(keys)) or any(not re.fullmatch(r"[0-9A-Z]{6}", code) for _, code in keys):
        raise RuntimeError("duplicate or invalid final company keys")
    if {row["market"] for row in summary} != {"KOSPI", "KOSDAQ", "TOTAL"}:
        raise RuntimeError("summary market rows are incomplete")
    total = next(row for row in summary if row["market"] == "TOTAL")
    if int(total["krx_companies"]) != len(rows):
        raise RuntimeError("summary total does not reconcile")
    if len(completeness) != 3 * 2 * sum(map(len, FIELDS.values())):
        raise RuntimeError("field completeness row count is invalid")
    if len(missing) != len({(row["market"], row["stock_code"]) for row in missing}):
        raise RuntimeError("duplicate companies in missing output")


async def run(args: argparse.Namespace) -> None:
    root, out = Path(args.checkpoint_dir).resolve(), Path(args.output_dir).resolve()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    raw, kind_meta = get_kind(root, args.refresh_krx, args.timeout_seconds)
    companies, audit = parse_kind(raw, as_of)
    print(f"KRX companies: KOSPI={audit['kospi_companies']:,}, KOSDAQ={audit['kosdaq_companies']:,}, TOTAL={len(companies):,}", file=sys.stderr, flush=True)
    load_dotenv(dotenv_path=Path(".env"))
    key = os.environ.get("FMP_API_KEY", "").strip()
    if not key:
        raise RuntimeError("FMP_API_KEY is not set")
    client = FMP(key, args.requests_per_second, args.retries, args.timeout_seconds)
    raw_stocks, raw_financials = await asyncio.gather(
        cached_list(client, "stock-list", root, args.refresh_fmp_lists),
        cached_list(client, "financial-statement-symbol-list", root, args.refresh_fmp_lists),
    )
    stocks, stock_records = stock_list(raw_stocks)
    financials = financial_list(raw_financials)
    rows = []
    for company in companies:
        row = dict(company)
        row.update(match(company, stocks, financials, stock_records))
        rows.append(row)
    detail_symbols = [row["fmp_financial_symbol"] for row in rows if row["fmp_financial_symbol_exists"]]
    print(f"FMP lists: stock symbols={len(stocks):,}, financial symbols={len(financials):,}, KRX financial candidates={len(detail_symbols):,}", file=sys.stderr, flush=True)
    await fetch_details(client, root, detail_symbols, args.concurrency)
    detailed = [(row, enrich(row, root)) for row in rows]
    missing = build_missing(rows)
    summary = build_summary(rows, missing)
    completeness = build_completeness(detailed)
    validate(rows, missing, summary, completeness)
    write_csv(out / "fmp_korea_coverage_all.csv", rows, ALL_COLUMNS)
    write_csv(out / "fmp_korea_missing.csv", missing, MISSING_COLUMNS)
    write_csv(out / "fmp_korea_summary.csv", summary, SUMMARY_COLUMNS)
    write_csv(out / "fmp_korea_field_completeness.csv", completeness, COMPLETENESS_COLUMNS)
    atomic_bytes(out / "fmp_korea_coverage_report.md", report(rows, missing, summary, completeness, kind_meta, audit, root).encode())
    print(f"Wrote final outputs to {out}", file=sys.stderr, flush=True)


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--checkpoint-dir", default=".cache/fmp-korea-coverage")
    parser.add_argument("--as-of")
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--requests-per-second", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--refresh-krx", action="store_true")
    parser.add_argument("--refresh-fmp-lists", action="store_true")
    args = parser.parse_args(argv)
    if args.concurrency < 1 or args.requests_per_second <= 0 or args.retries < 0 or args.timeout_seconds <= 0:
        parser.error("concurrency/rate/timeout must be positive and retries non-negative")
    if args.as_of:
        date.fromisoformat(args.as_of)
    return args


def main(argv: Sequence[str] | None = None) -> int:
    try:
        asyncio.run(run(arguments(argv)))
        return 0
    except BaseExceptionGroup as group:
        for error in group.exceptions:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
