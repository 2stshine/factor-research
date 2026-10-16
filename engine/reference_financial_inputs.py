"""Auditable DART annual inputs, not factor outcomes or first-vintage certification.

Extract certified full filing anchors as well as mapped lines: a newer incomplete
filing must not disappear merely because the desired metric is absent. All live
queries run in one caller-owned READ ONLY REPEATABLE READ transaction. Local
checkpoints are immutable completed captures, not resumable cross-vintage queries.
Amounts use provider units without FX conversion; only unambiguous KRW bundles
are usable. Historical values are explicitly PIT_ASSUMED, never PIT verified.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd


VERSION = "dart-annual-reference-input-v1"
ATTACHMENT_VERSION = "dart-annual-reference-attachment-v2-balance-quarantine"
BALANCE_ABSOLUTE_TOLERANCE_KRW = Decimal("1")
BALANCE_RELATIVE_TOLERANCE = Decimal("0.000001")
METRICS = (
    "revenue", "operating_income", "pretax_income", "net_income",
    "comprehensive_income", "total_assets", "current_assets", "noncurrent_assets",
    "total_liabilities", "current_liabilities", "noncurrent_liabilities",
    "total_equity", "capital_stock", "retained_earnings", "cash_and_equivalents",
    "inventories", "trade_and_other_current_receivables", "property_plant_and_equipment",
    "goodwill", "intangibles_excluding_goodwill", "cost_of_revenue", "gross_profit",
    "income_tax_expense", "operating_cash_flow", "investing_cash_flow",
    "financing_cash_flow", "purchase_of_ppe", "purchase_of_intangibles",
)
FLOW_METRICS = frozenset(METRICS[:5] + METRICS[20:])
CORE_SQL = """
SELECT f.asset_id, 'STANDARDIZED_NAME' AS source_kind, f.source, f.period_end,
 f.fiscal_period, f.fs_type, f.statement_type, f.filing_id, f.filed,
 f.available_at, f.accepted_at, f.currency, f.revision_key,
 f.quality_run_id::text, f.metric, f.value::text AS amount,
 NULL::text AS cumulative_amount, NULL::text AS account_id,
 NULL::text AS line_key, 'DART_STANDARDIZED_ACCOUNT_NAME' AS mapping_version,
 '11011'::text AS report_code
FROM public.fundamental f
JOIN public.dq_run q ON q.run_id=f.quality_run_id AND q.status='CERTIFIED'
WHERE f.source='DART' AND f.data_basis='STANDARDIZED' AND f.unit_type='currency'
 AND f.fiscal_period='FY' AND f.asset_id=ANY(%s::bigint[])
 AND f.period_end >= %s::date AND f.available_at <= %s::timestamptz
ORDER BY f.asset_id,f.period_end,f.filing_id,f.fs_type,f.metric,f.revision_key
"""
EXACT_SQL = """
SELECT f.asset_id, 'EXACT_ACCOUNT_ID' AS source_kind, f.source, f.period_end,
 f.fiscal_period, f.fs_type, f.statement_type, f.filing_id, f.filed,
 f.available_at, f.accepted_at, f.currency, f.revision_key,
 f.quality_run_id::text, m.metric, f.current_amount::text AS amount,
 f.current_cumulative_amount::text AS cumulative_amount, f.account_id,
 f.line_key, m.mapping_version, f.report_code
FROM public.fundamental_statement_line f
JOIN public.dart_account_metric_map m
 ON replace(f.account_id,':','_')=m.account_id AND f.statement_type=m.statement_type
JOIN public.dq_run q ON q.run_id=f.quality_run_id AND q.status='CERTIFIED'
WHERE f.source='DART' AND f.fiscal_period='FY' AND f.asset_id=ANY(%s::bigint[])
 AND f.period_end >= %s::date AND f.available_at <= %s::timestamptz
 AND coalesce(btrim(f.account_detail),'') IN ('','-')
ORDER BY f.asset_id,f.period_end,f.filing_id,f.fs_type,m.metric,f.line_key
"""
ANCHOR_SQL = """
SELECT DISTINCT f.asset_id, 'FILING_ANCHOR' AS source_kind, f.source, f.period_end,
 f.fiscal_period, f.fs_type, NULL::text AS statement_type, f.filing_id, f.filed,
 f.available_at, NULL::timestamptz AS accepted_at, f.currency, f.revision_key,
 f.quality_run_id::text, NULL::text AS metric, NULL::text AS amount,
 NULL::text AS cumulative_amount, NULL::text AS account_id,
 NULL::text AS line_key, NULL::text AS mapping_version, f.report_code
FROM public.fundamental_statement_line f
JOIN public.dq_run q ON q.run_id=f.quality_run_id AND q.status='CERTIFIED'
WHERE f.source='DART' AND f.fiscal_period='FY' AND f.asset_id=ANY(%s::bigint[])
 AND f.period_end >= %s::date AND f.available_at <= %s::timestamptz
ORDER BY f.asset_id,f.period_end,f.filing_id,f.fs_type
"""
MAPPING_SQL = "SELECT account_id,statement_type,metric,mapping_version FROM public.dart_account_metric_map ORDER BY account_id,statement_type"


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp(value):
    try:
        value = pd.Timestamp(value)
        return value.tz_convert("UTC") if value.tzinfo is not None and not pd.isna(value) else None
    except (ValueError, TypeError):
        return None


def _day(value):
    try:
        result = pd.Timestamp(value)
        if pd.isna(result) or result.tzinfo is not None or result != result.normalize():
            return None
        return result
    except (TypeError, ValueError):
        return None


def _number(value):
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _present(value):
    return value is not None and not pd.isna(value) and bool(str(value).strip())


def _query(conn, sql, params=None):
    # Bound each network response over SSM; SQL result semantics are unchanged.
    with conn.cursor(name="reference_financial_capture") as cursor:
        cursor.execute(sql, params)
        columns = [description.name for description in cursor.description]
        chunks = []
        while rows := cursor.fetchmany(2000):
            chunks.append(pd.DataFrame(rows, columns=columns))
        return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=columns)


def _assert_readonly(conn):
    with conn.cursor() as cursor:
        cursor.execute("SHOW transaction_read_only")
        readonly = cursor.fetchone()[0]
        cursor.execute("SHOW transaction_isolation")
        isolation = cursor.fetchone()[0]
    if readonly != "on" or isolation not in {"repeatable read", "serializable"}:
        raise ValueError("Extraction requires caller-owned READ ONLY REPEATABLE READ transaction")


def capture_annual_ledger(conn, asset_ids, start_period, end_available, checkpoint_dir, *, batch_size=20):
    """Capture all requested assets in ONE transaction, returning a bound manifest.

    Existing nonempty directories are refused. An interrupted capture is not a
    completed dataset and must not be silently resumed from a different snapshot.
    No credentials or connection URLs are serialized.
    """
    requested = list(asset_ids)
    if any(isinstance(item, (bool, np.bool_)) or re.fullmatch(r"[0-9]+", str(item)) is None for item in requested):
        raise ValueError("positive integral asset IDs required")
    assets = sorted(set(int(item) for item in requested))
    if (not assets or any(item <= 0 or item > np.iinfo(np.int64).max for item in assets)
            or not isinstance(batch_size, int) or isinstance(batch_size, bool) or not 1 <= batch_size <= 250):
        raise ValueError("positive asset IDs and batch_size in [1,250] required")
    start, end = _day(start_period), _stamp(end_available)
    if start is None or end is None or start.date() > end.date():
        raise ValueError("start date and aware end timestamp required")
    _assert_readonly(conn)
    root = Path(checkpoint_dir)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError("Capture directory must be empty; cross-snapshot resume is forbidden")
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_current_snapshot()::text, transaction_timestamp()")
        snapshot, captured_at = cursor.fetchone()
        cursor.execute("SET LOCAL statement_timeout='90s'")
        # The wide raw statement table has costly lossy bitmap plans for asset
        # batches. An ordinary indexed scan changes performance, not filtering.
        cursor.execute("SET LOCAL enable_bitmapscan=off")
    mapping = _query(conn, MAPPING_SQL).to_dict("records")
    (root / "mapping.json").write_text(_json(mapping), encoding="utf-8")
    files = [{"path": "mapping.json", "sha256": _sha(root / "mapping.json"), "rows": len(mapping)}]
    source_counts = Counter()
    metric_counts = Counter()
    for offset in range(0, len(assets), batch_size):
        batch = assets[offset:offset + batch_size]
        parts = [_query(conn, sql, (batch, start.date(), end.to_pydatetime()))
                 for sql in (CORE_SQL, EXACT_SQL, ANCHOR_SQL)]
        ledger = pd.concat(parts, ignore_index=True)
        for name in ("period_end", "filed"):
            ledger[name] = ledger[name].map(lambda value: str(value) if _present(value) else None)
        for name in ("available_at", "accepted_at"):
            ledger[name] = ledger[name].map(lambda value: _stamp(value).isoformat() if _stamp(value) is not None else None)
        name = f"ledger-{offset // batch_size:04d}.parquet"
        ledger.to_parquet(root / name, index=False)
        source_counts.update(ledger["source_kind"].value_counts().to_dict())
        metric_counts.update(ledger["metric"].dropna().value_counts().to_dict())
        files.append({"path": name, "sha256": _sha(root / name), "rows": len(ledger), "asset_ids": batch})
        # Append progress only after each durable, hash-bound chunk. This is not
        # permission to reuse partial captures as a completed database snapshot.
        with (root / "progress.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(_json(files[-1]) + "\n")
    manifest = {
        "version": VERSION, "status": "COMPLETE", "pit_status": "PIT_ASSUMED",
        "first_vintage_verified": False, "snapshot": snapshot,
        "captured_at": captured_at.isoformat(), "asset_ids": assets,
        "start_period": start.date().isoformat(), "end_available": end.isoformat(),
        "files": files, "source_row_counts": dict(source_counts),
        "metric_line_counts": dict(metric_counts),
        "query_sha256": {name: hashlib.sha256(sql.encode()).hexdigest() for name, sql in
                         (("core", CORE_SQL), ("exact", EXACT_SQL), ("anchors", ANCHOR_SQL), ("mapping", MAPPING_SQL))},
        "scope": "CERTIFIED_DART_FY_ALL_FILING_VINTAGES_FOR_EXPLICIT_ASSETS",
        "units": "SOURCE_KRW_NO_FX_OR_SCALING",
        "transport": "SERVER_CURSOR_FETCH_2000_ROWS_ASSET_BATCHES",
        "query_settings": {"statement_timeout_seconds": 90, "enable_bitmapscan": False},
    }
    manifest["manifest_sha256"] = hashlib.sha256(_json(manifest).encode()).hexdigest()
    (root / "manifest.json").write_text(_json(manifest), encoding="utf-8")
    return manifest


def verify_capture(checkpoint_dir):
    root = Path(checkpoint_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    supplied = manifest.pop("manifest_sha256", None)
    if supplied != hashlib.sha256(_json(manifest).encode()).hexdigest():
        raise ValueError("Capture manifest hash mismatch")
    manifest["manifest_sha256"] = supplied
    if (manifest.get("version") != VERSION or manifest.get("status") != "COMPLETE"
            or manifest.get("pit_status") != "PIT_ASSUMED"
            or manifest.get("first_vintage_verified") is not False):
        raise ValueError("Capture contract mismatch")
    for item in manifest["files"]:
        name = item["path"]
        if Path(name).name != name or _sha(root / name) != item["sha256"]:
            raise ValueError("Capture artifact hash mismatch")
    return manifest


def read_annual_ledger(conn, asset_ids, start_period, end_available, checkpoint_dir):
    manifest = capture_annual_ledger(conn, asset_ids, start_period, end_available, checkpoint_dir)
    ledger = pd.concat([pd.read_parquet(Path(checkpoint_dir) / item["path"])
                        for item in manifest["files"] if item["path"].endswith(".parquet")], ignore_index=True)
    return ledger, manifest


def _bundle(rows):
    """One filing+period, both scopes; invalid selected scope never falls back."""
    fs = "CFS" if any(row["fs_type"] == "CFS" for row in rows) else "OFS"
    selected = [row for row in rows if row["fs_type"] == fs]
    reasons, values = [], {}
    clocks = {_stamp(row.get("available_at")) for row in selected}
    currencies = {row.get("currency") for row in selected}
    # Existing core uses filed+1 UTC midnight while exact lines use KST
    # midnight. Take the later source clock, never normalize it backwards.
    # A single source with contradictory clocks or conflicting filed dates is
    # not that known timezone-policy difference and remains invalid.
    source_clocks = defaultdict(set)
    for row in selected:
        source_clocks[row.get("source_kind")].add(_stamp(row.get("available_at")))
    if None in clocks or any(len(value) != 1 for value in source_clocks.values()):
        reasons.append("INCONSISTENT_FILING_CLOCK")
    if len({_day(row.get("filed")) for row in selected}) != 1:
        reasons.append("INCONSISTENT_FILED_DATE")
    if currencies != {"KRW"}:
        reasons.append("NON_KRW_OR_CONFLICTING_CURRENCY")
    for row in selected:
        stamp, filed, period = _stamp(row.get("available_at")), _day(row.get("filed")), _day(row.get("period_end"))
        if (row.get("source") != "DART" or row.get("fiscal_period") != "FY"
                or row.get("report_code") != "11011" or row.get("fs_type") not in {"CFS", "OFS"}
                or any(not _present(row.get(key)) for key in ("filing_id", "revision_key", "quality_run_id"))):
            reasons.append("INVALID_FILING_LINEAGE")
        if (stamp is None or filed is None or period is None or filed < period
                or stamp.tz_convert("Asia/Seoul").date() <= filed.date()):
            reasons.append("INVALID_DISCLOSURE_CLOCK")
    invalid, decimal_values = {}, {}
    for metric in METRICS:
        candidates = [row for row in selected if row.get("metric") == metric]
        if not candidates:
            continue
        failures = []
        numbers = []
        # Distinct exact account lines representing the same metric are accepted
        # ONLY when amounts agree exactly (including duplicated IS/CIS totals).
        # This is equal-value reconciliation, not arbitrary statement preference.
        for row in candidates:
            number = _number(row.get("amount"))
            if number is None:
                failures.append("MISSING_OR_NONFINITE_AMOUNT")
            else:
                numbers.append(number)
            if row.get("source_kind") == "EXACT_ACCOUNT_ID":
                if any(not _present(row.get(key)) for key in ("account_id", "line_key", "mapping_version")):
                    failures.append("MISSING_EXACT_LINEAGE")
                cumulative = row.get("cumulative_amount")
                if metric in FLOW_METRICS and _present(cumulative) and _number(cumulative) != number:
                    failures.append("FY_CURRENT_CUMULATIVE_CONFLICT")
            elif row.get("source_kind") != "STANDARDIZED_NAME":
                failures.append("INVALID_METRIC_SOURCE")
        if len(set(numbers)) > 1:
            failures.append("CONFLICTING_METRIC_AMOUNTS")
        if failures:
            invalid[metric] = sorted(set(failures))
        elif numbers:
            number = float(numbers[0])
            if np.isfinite(number):
                values[metric] = number
                decimal_values[metric] = numbers[0]
    balance_equation = {"status": "NOT_ASSESSED_INCOMPLETE_TRIPLET"}
    balance_metrics = ("total_assets", "total_liabilities", "total_equity")
    if all(metric in decimal_values for metric in balance_metrics):
        # This detects internal uncertainty, not a proven source error. Reported
        # amounts may themselves be rounded. Never repair A/L/E, reject negative
        # equity solely for its sign, or backfill a different filing/scope.
        # Check original decimals before float conversion and tolerate 1 KRW or
        # one part per million of absolute assets, whichever is greater.
        with localcontext() as context:
            context.prec = 80  # Source NUMERIC(38,6), including exact subtraction.
            assets, liabilities, equity = (decimal_values[metric] for metric in balance_metrics)
            residual = assets - liabilities - equity
            tolerance = max(BALANCE_ABSOLUTE_TOLERANCE_KRW, abs(assets) * BALANCE_RELATIVE_TOLERANCE)
            uncertain = abs(residual) > tolerance
        balance_equation = {
            "status": "UNCERTAINTY_QUARANTINED" if uncertain else "WITHIN_DECLARED_TOLERANCE",
            "residual_krw": str(residual), "tolerance_krw": str(tolerance),
            "source_error_confirmed": False,
        }
        if uncertain:
            reasons.append("BALANCE_EQUATION_UNCERTAINTY")
    return {"fs_type": fs, "available_at": max(clock for clock in clocks if clock is not None) if clocks - {None} else None,
            "values": values if not reasons else {}, "reasons": sorted(set(reasons)), "metric_reasons": invalid,
            "balance_equation": balance_equation,
            "currency": "KRW" if currencies == {"KRW"} else None,
            "period_end": _day(rows[0]["period_end"]), "filing_id": rows[0]["filing_id"]}


def attach_annual_features(base_panel, ledger, *, max_statement_age_days=550, allow_pit_assumed=True):
    """Attach known annual accounting features to an explicit historical grid.

    Returns only identity plus financial features, not any price/return columns.
    A previous FY means exactly 12 calendar months earlier (month-end preserving),
    not an arbitrary older report or the value seen 12 observation rows earlier.
    """
    if allow_pit_assumed is not True:
        raise ValueError("Historical DART capture is PIT_ASSUMED, not first-vintage verified")
    if not isinstance(max_statement_age_days, int) or not 366 <= max_statement_age_days <= 730:
        raise ValueError("Explicit annual freshness policy must be 366..730 days")
    required = {"asset_id", "date", "stock_code", "market"}
    if not required <= set(base_panel):
        raise ValueError("Historical asset/date/stock_code/market grid required")
    result = base_panel[["asset_id", "date", "stock_code", "market"]].copy().reset_index(drop=True)
    assets = pd.to_numeric(result["asset_id"], errors="raise")
    if (any(isinstance(value, (bool, np.bool_)) for value in result.asset_id)
            or assets.isna().any() or not np.isfinite(assets).all()
            or (assets <= 0).any() or (assets % 1 != 0).any()
            or (assets > np.iinfo(np.int64).max).any()):
        raise ValueError("Positive integral asset identity required")
    result["asset_id"] = assets.astype("int64")
    result["date"] = pd.to_datetime(result["date"])
    if (result.duplicated(["asset_id", "date"]).any()
            or any(not isinstance(code, str) or re.fullmatch(r"[0-9A-Z]{6}", code) is None for code in result.stock_code)
            or not result.market.isin(["KOSPI", "KOSDAQ"]).all()
            or result.date.isna().any() or result.date.dt.tz is not None
            or not result.date.dt.is_month_end.all()
            or not result.date.eq(result.date.dt.normalize()).all()
            or (pd.to_numeric(result.asset_id, errors="coerce") <= 0).any()):
        raise ValueError("Invalid or duplicate historical monthly identity grid")
    count = len(result)
    numeric = {f"{prefix}{metric}": np.full(count, np.nan) for prefix in ("fy_", "prev_fy_") for metric in METRICS}
    meta = {f"{prefix}{name}": [None] * count for prefix in ("fy_", "prev_fy_")
            for name in ("period_end", "fs_type", "filing_id", "available_at", "currency")}
    reasons = ["NO_AVAILABLE_FY_FILING"] * count
    previous_reasons = ["NO_PRIOR_FY"] * count
    all_bundles = defaultdict(list)
    invalid_rows = Counter()
    frame = ledger.copy()
    if not frame.empty:
        if not {"asset_id", "period_end", "filing_id", "available_at", "fiscal_period", "fs_type"} <= set(frame):
            raise ValueError("Ledger contract missing filing metadata")
        for key, group in frame.groupby(["asset_id", "period_end", "filing_id"], dropna=False, sort=False):
            asset, period, filing = key
            period = _day(period)
            if period is None or not _present(filing):
                # Do not hide a possibly newer correction with broken identity.
                raise ValueError("Annual ledger has invalid period or filing identity")
            records = group.to_dict("records")
            if any(row.get("fiscal_period") != "FY" for row in records):
                raise ValueError("Quarterly rows cannot enter annual ledger")
            bundle = _bundle(records)
            if bundle["available_at"] is None:
                # A missing historical clock cannot be silently skipped: doing so
                # could hide a correction. Extraction consumers must repair it.
                raise ValueError("Annual filing has no valid availability clock")
            all_bundles[int(asset)].append(bundle)
    metric_rejects, bundle_rejects = Counter(), Counter()
    for asset, indexes in result.groupby("asset_id", sort=False).groups.items():
        bundles = all_bundles[int(asset)]
        for index in indexes:
            date = result.at[index, "date"]
            cutoff = (date + pd.Timedelta(days=1)).tz_localize("Asia/Seoul").tz_convert("UTC") - pd.Timedelta(nanoseconds=1)
            visible = [bundle for bundle in bundles if bundle["available_at"] <= cutoff]
            if not visible:
                continue
            current = max(visible, key=lambda item: (item["period_end"], item["available_at"], item["filing_id"]))
            age = (date - current["period_end"]).days
            stale = age < 0 or age > max_statement_age_days
            reasons[index] = "STALE_FY" if stale else "|".join(current["reasons"]) or "AVAILABLE"
            prior_end = current["period_end"] - pd.DateOffset(years=1)
            if current["period_end"].is_month_end:
                prior_end = prior_end + pd.offsets.MonthEnd(0)
            prior_candidates = [bundle for bundle in visible if bundle["period_end"] == prior_end]
            previous = max(prior_candidates, key=lambda item: (item["available_at"], item["filing_id"])) if prior_candidates else None
            if previous is not None:
                if previous["fs_type"] != current["fs_type"]:
                    previous_reasons[index] = "PRIOR_FS_SCOPE_MISMATCH"
                    previous = None
                elif previous["currency"] != "KRW" or current["currency"] != "KRW":
                    previous_reasons[index] = "PRIOR_CURRENCY_MISMATCH"
                    previous = None
                else:
                    previous_reasons[index] = "|".join(previous["reasons"]) or "AVAILABLE"
            for prefix, bundle in (("fy_", current), ("prev_fy_", previous)):
                if bundle is None:
                    continue
                for name in ("period_end", "fs_type", "filing_id", "available_at", "currency"):
                    meta[prefix + name][index] = bundle[name]
                if not stale and not current["reasons"]:
                    for metric, value in bundle["values"].items():
                        numeric[prefix + metric][index] = value
                    metric_rejects.update(prefix + metric + ":" + reason for metric, errs in bundle["metric_reasons"].items() for reason in errs)
            bundle_rejects.update(current["reasons"])
    result = pd.concat([result, pd.DataFrame(numeric), pd.DataFrame(meta)], axis=1)
    for prefix in ("fy_", "prev_fy_"):
        result[prefix + "available_at"] = pd.to_datetime(result[prefix + "available_at"], utc=True)
        result[prefix + "period_end"] = pd.to_datetime(result[prefix + "period_end"])
    result["financial_known_at"] = result[["fy_available_at", "prev_fy_available_at"]].max(axis=1)
    result["financial_status"], result["prior_financial_status"] = reasons, previous_reasons
    coverage = {name: int(np.isfinite(values).sum()) for name, values in numeric.items()}
    evidence = {
        "version": VERSION, "attachment_version": ATTACHMENT_VERSION,
        "pit_status": "PIT_ASSUMED", "first_vintage_verified": False,
        "denominator_asset_months": count, "assets": int(result.asset_id.nunique()),
        "max_statement_age_days": max_statement_age_days,
        "feature_nonnull_asset_months": coverage,
        "status_counts": dict(Counter(reasons)), "prior_status_counts": dict(Counter(previous_reasons)),
        "invalid_ledger_rows": dict(invalid_rows), "bundle_rejections": dict(bundle_rejects),
        "metric_rejections": dict(metric_rejects),
        "policy": {
            "clock": "MAX_SOURCE_AVAILABLE_AT_LE_MONTH_END_KST; CORE_UTC_AND_RAW_KST_CLOCKS_PRESERVED; NO_EARLY_REVISIONS",
            "filing": "LATEST_KNOWN_FY_PERIOD_THEN_AVAILABILITY_THEN_FILING_ID",
            "scope": "CFS_WITHIN_LATEST_FILING_ELSE_OFS_NO_INVALID_FALLBACK",
            "previous": "EXACT_PREVIOUS_CALENDAR_FY_END_SAME_FS_AND_KRW",
            "reconciliation": "SAME_FILING_CORE_AND_EXACT_LINES_MUST_AGREE_EXACT_DECIMAL; IS_CIS_EQUAL_ONLY",
            "missing": "NULL_IS_UNKNOWN_NOT_ZERO; NO_METRICWISE_OLDER_FILING_FALLBACK",
            "units": "KRW_ONLY_SOURCE_SCALE_ASSUMED_NO_FX",
            "balance_equation": "COMPLETE_RECONCILED_A_L_E_ONLY; ABS(A-L-E)>MAX(1_KRW,ABS(A)*1e-6)_QUARANTINES_WHOLE_FY_BUNDLE_CURRENT_OR_PRIOR; UNCERTAINTY_NOT_CONFIRMED_ERROR; NEGATIVE_EQUITY_ALONE_NOT_REJECTED",
        },
    }
    return result, evidence


def attach_capture(base_panel, checkpoint_dir, *, max_statement_age_days=550, allow_pit_assumed=True):
    """Memory-bounded attachment; verifies every captured byte before use."""
    manifest = verify_capture(checkpoint_dir)
    # Validate/canonicalize before .isin: string IDs must not silently disappear
    # from an integer asset chunk, nor may 1.5 be truncated to asset 1.
    base_panel, _ = attach_annual_features(base_panel, pd.DataFrame(),
                                          max_statement_age_days=max_statement_age_days,
                                          allow_pit_assumed=allow_pit_assumed)
    base_panel = base_panel[["asset_id", "date", "stock_code", "market"]]
    assets = set(int(value) for value in base_panel.asset_id)
    if not assets <= set(manifest["asset_ids"]):
        raise ValueError("Base contains assets outside captured inventory")
    end = _stamp(manifest["end_available"])
    max_cutoff = (pd.Timestamp(base_panel.date.max()) + pd.Timedelta(days=1)).tz_localize("Asia/Seoul").tz_convert("UTC") - pd.Timedelta(nanoseconds=1)
    if end < max_cutoff:
        raise ValueError("Capture does not include the requested monthly cutoff")
    frames, evidences = [], []
    for item in manifest["files"]:
        if not item["path"].endswith(".parquet"):
            continue
        base = base_panel[base_panel.asset_id.isin(item["asset_ids"])]
        if base.empty:
            continue
        ledger = pd.read_parquet(Path(checkpoint_dir) / item["path"])
        frame, evidence = attach_annual_features(base, ledger, max_statement_age_days=max_statement_age_days,
                                               allow_pit_assumed=allow_pit_assumed)
        frames.append(frame)
        evidences.append(evidence)
    result = pd.concat(frames, ignore_index=True).sort_values(["asset_id", "date"]).reset_index(drop=True)
    if len(result) != len(base_panel) or result.duplicated(["asset_id", "date"]).any():
        raise ValueError("Capture chunks do not cover the exact base grid once")
    merged = dict(evidences[0])
    for key in ("feature_nonnull_asset_months", "status_counts", "prior_status_counts", "invalid_ledger_rows", "bundle_rejections", "metric_rejections"):
        counter = Counter()
        for evidence in evidences:
            counter.update(evidence[key])
        merged[key] = dict(counter)
    merged.update(denominator_asset_months=len(result), assets=int(result.asset_id.nunique()),
                  extraction_manifest_sha256=manifest["manifest_sha256"])
    return result, merged


def monthly_features(conn, base_panel, checkpoint_dir, *, max_statement_age_days=550, allow_pit_assumed=True):
    start = pd.Timestamp(base_panel.date.min()) - pd.Timedelta(days=max_statement_age_days + 366)
    end = (pd.Timestamp(base_panel.date.max()) + pd.Timedelta(days=1)).tz_localize("Asia/Seoul").tz_convert("UTC")
    capture_annual_ledger(conn, base_panel.asset_id.unique(), start.normalize(), end, checkpoint_dir)
    return attach_capture(base_panel, checkpoint_dir, max_statement_age_days=max_statement_age_days,
                          allow_pit_assumed=allow_pit_assumed)
