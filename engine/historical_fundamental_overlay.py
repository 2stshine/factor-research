"""Expiry-aware local replay of an append-only historical revenue dataset.

This is a separate provenance contract, NOT the legacy RDS fundamental query.
No database connection is opened, and no publication/commit is performed.
The v2 overlay only supplements 2015 Q1/Q2/Q3 current-quarter revenue. Unknown
or expired observations become explicit NaN controls for their fiscal key;
later certified base quarters and all stock inputs remain usable.
All revenue, including untouched base years/assets, additionally requires one
statement basis for FY residuals and four-quarter TTM. Other metrics retain the
frozen materializer's exact calculation; this is not their basis certification.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from engine import fundamental_contract as legacy_contract
from engine import fundamentals, silver

VERSION = "historical-revenue-validity-and-basis-overlay-v2"
META_KEY = "historical_fundamental_overlay_contract"
RECEIPT_KEY = "historical_fundamental_overlay_receipt"
PUBLISHER_VERSION = "dart-original-revenue-bounded-pit-v1"
FROZEN_MATERIALIZER_SHA = "136da8ad847ec3510549c881109dacff4cbb406359c4ec8d9c5a7347cff8f1ed"
KST = ZoneInfo("Asia/Seoul")
HASH = re.compile(r"[a-f0-9]{64}\Z")

# Must remain byte-identical to the publisher's bounded-reader query. This is
# not an as-of filter: every validity endpoint is needed to compile barriers.
BOUNDED_LEDGER_SQL = """
SELECT r.* FROM public.fundamental_document_revenue r
JOIN public.fundamental_document_dataset d USING(dataset_version)
JOIN public.dq_run q ON q.run_id=r.quality_run_id AND q.status='CERTIFIED'
WHERE r.dataset_version=%s AND d.quality_run_id=r.quality_run_id
ORDER BY r.asset_id,r.period_end,r.fs_type,r.available_date,r.revision_key
"""
DATASET_METADATA_SQL = """
SELECT d.*,q.status AS dq_status,q.input_fingerprint,q.ruleset_version
FROM public.fundamental_document_dataset d
JOIN public.dq_run q ON q.run_id=d.quality_run_id AND q.status='CERTIFIED'
WHERE d.dataset_version=%s
"""
PAYLOAD_FIELDS = (
    "asset_id", "stock_code", "corp_code", "source", "metric", "statement_type",
    "data_basis", "unit_type", "quantity_semantics", "period_start", "period_end",
    "fiscal_period", "fs_type", "value", "currency", "filing_id", "revision_key",
    "filed", "available_date", "available_at", "valid_until_exclusive", "evidence",
    "observation_key",
)
DEFAULT_FIELDS = {"source": "DART_DOCUMENT", "metric": "revenue", "statement_type": "IS",
    "data_basis": "STANDARDIZED", "unit_type": "currency", "quantity_semantics": "FLOW_CURRENT_QUARTER",
    "currency": "KRW"}
POINT = ("asset_id", "period_end", "fiscal_period", "metric")
EXACT = (*POINT, "fs_type", "revision_key")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def source_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def query_source_sha256():
    return hashlib.sha256(BOUNDED_LEDGER_SQL.encode()).hexdigest()


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _day(value):
    parsed = pd.Timestamp(value)
    _require(pd.notna(parsed) and parsed == parsed.normalize(), "Noncanonical date")
    return parsed.date().isoformat()


def _instant(value):
    parsed = pd.Timestamp(value)
    _require(pd.notna(parsed) and parsed.tzinfo is not None, "Explicit available_at timezone required")
    return parsed.tz_convert(KST).isoformat()


def _payload(raw):
    row = {**DEFAULT_FIELDS, **dict(raw)}
    for field, expected in DEFAULT_FIELDS.items():
        _require(row[field] == expected, "Unsupported overlay source/metric/quantity contract")
    for field in ("period_start", "period_end", "filed", "available_date", "valid_until_exclusive"):
        row[field] = _day(row[field])
    row["available_at"] = _instant(row["available_at"])
    value = Decimal(str(row["value"]))
    _require(value.is_finite() and value >= 0, "Invalid original revenue amount")
    canonical = format(value, ".6f")
    _require(Decimal(canonical) == value, "Overlay numeric precision would be lost")
    row["value"] = canonical
    row["asset_id"] = int(row["asset_id"])
    out = {field: row[field] for field in PAYLOAD_FIELDS}
    out["payload_sha256"] = str(row["payload_sha256"])
    _require(HASH.fullmatch(out["payload_sha256"]) and digest({k: out[k] for k in PAYLOAD_FIELDS}) == out["payload_sha256"],
             "Overlay row payload hash mismatch")
    return out


def bundle_from_rows(rows, metadata):
    """Validate a complete exact-version DQ-certified query result locally."""
    meta = deepcopy(dict(metadata))
    _require(meta.get("dq_status") == "CERTIFIED", "Overlay dataset is not CERTIFIED")
    UUID(str(meta["quality_run_id"]))
    for field in ("manifest_sha256", "bundle_sha256"):
        _require(HASH.fullmatch(str(meta.get(field))), "Missing dataset binding hash")
    _require(meta.get("input_fingerprint") == meta["bundle_sha256"], "Dataset DQ input binding mismatch")
    _require(bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,119}", str(meta.get("dataset_version")))), "Invalid dataset version")
    originals = []
    for raw in rows:
        _require(raw.get("dataset_version") == meta["dataset_version"]
                 and str(raw.get("quality_run_id")) == str(meta["quality_run_id"]), "Observation dataset/DQ binding mismatch")
        originals.append(_payload(raw))
    originals.sort(key=lambda row: row["observation_key"])
    _require(originals and len({r["observation_key"] for r in originals}) == len(originals), "Empty/duplicate overlay observations")
    evidence, blocks = meta["evidence"], meta["blocking_windows"]
    _require(evidence.get("contract_version") == PUBLISHER_VERSION
             and evidence.get("reader_contract") == "ASOF_WINDOW_REQUIRED_NO_UNBOUNDED_FORWARD_FILL"
             and evidence.get("certification_scope") == "SOURCE_ROWS_WITH_BOUNDED_VALIDITY_ONLY"
             and evidence.get("full_history_certified") is False, "Unsupported publisher validity contract")
    _require(evidence.get("review", {}).get("decision") == "ACCEPT", "Reviewed publisher evidence missing")
    _require(digest({"rows": originals, "blocking_windows": blocks, "evidence": evidence}) == meta["bundle_sha256"],
             "Complete dataset bundle hash mismatch")
    return {"dataset_version": meta["dataset_version"], "manifest_sha256": meta["manifest_sha256"],
            "bundle_sha256": meta["bundle_sha256"], "quality_run_id": str(meta["quality_run_id"]),
            "rows": originals, "blocking_windows": deepcopy(blocks), "evidence": deepcopy(evidence),
            "query_source_sha256": query_source_sha256(),
            "metadata_query_sha256": hashlib.sha256(DATASET_METADATA_SQL.encode()).hexdigest(),
            "dq_status": "CERTIFIED", "input_fingerprint": meta["input_fingerprint"]}


def read_bundle(conn, dataset_version):
    """Two fixed SELECTs only; caller owns an already read-only connection."""
    _require(getattr(conn, "read_only", None) is True, "Read-only connection required")
    with conn.cursor() as cursor:
        def fetch(sql):
            cursor.execute(sql, (dataset_version,))
            rows = cursor.fetchall()
            if not rows or isinstance(rows[0], dict):
                return rows
            names = [getattr(column, "name", None) or column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in rows]
        metadata = fetch(DATASET_METADATA_SQL)
        _require(len(metadata) == 1, "Exact certified dataset version unavailable")
        rows = fetch(BOUNDED_LEDGER_SQL)
    return bundle_from_rows(rows, metadata[0])


def _verified_bundle(bundle):
    _require(bundle.get("query_source_sha256") == query_source_sha256()
             and bundle.get("metadata_query_sha256") == hashlib.sha256(DATASET_METADATA_SQL.encode()).hexdigest(),
             "Overlay source query changed")
    metadata = {key: bundle[key] for key in ("dataset_version", "manifest_sha256", "bundle_sha256", "quality_run_id",
                                           "dq_status", "input_fingerprint", "evidence", "blocking_windows")}
    rows = [{**row, "dataset_version": bundle["dataset_version"], "quality_run_id": bundle["quality_run_id"]}
            for row in bundle["rows"]]
    return bundle_from_rows(rows, metadata)


def _semantic(row, fields):
    return tuple(_day(row[field]) if field == "period_end" else int(row[field]) if field == "asset_id"
                 else str(row[field]) for field in fields)


def compile_ledger(base_rows, bundle):
    """Return a NEW replay ledger and provenance; never modify source rows.

    This contract fails on competing nonidentical base revisions for an overlaid fiscal
    point rather than inventing a source priority. Exact observations can be
    reused only when amount and both availability fields agree.
    """
    _require(fundamentals.source_sha256() == FROZEN_MATERIALIZER_SHA, "Frozen financial materializer changed")
    base_provenance = legacy_contract._ledger(base_rows)
    bundle = _verified_bundle(bundle)
    evidence = bundle["evidence"]
    scopes = {scope["scope_id"]: scope for scope in evidence["scopes"]}
    _require(len(scopes) == len(evidence["scopes"]), "Duplicate overlay scope")
    horizon = {corp: (date.fromisoformat(_day(day)) + timedelta(days=1)).isoformat()
               for corp, day in evidence["covered_through_by_corp"].items()}
    points, intervals, overlay = {}, {}, bundle["rows"]
    for row in overlay:
        _require(row["fiscal_period"] in {"Q1", "Q2", "Q3"} and row["fs_type"] in {"CFS", "OFS"}, "Unsupported fiscal scope")
        _require(bool(re.fullmatch(r"[0-9]{14}", row["revision_key"])) and row["filing_id"] == row["revision_key"],
                 "Original receipt revision identity required")
        observation_key = digest([row[k] for k in ("asset_id", "period_end", "fiscal_period", "fs_type", "revision_key", "metric")])
        _require(row["observation_key"] == observation_key, "Original observation key mismatch")
        expected_end = {"Q1": "2015-03-31", "Q2": "2015-06-30", "Q3": "2015-09-30"}[row["fiscal_period"]]
        expected_start = {"Q1": "2015-01-01", "Q2": "2015-04-01", "Q3": "2015-07-01"}[row["fiscal_period"]]
        _require(row["period_end"] == expected_end and row["period_start"] == expected_start, "Overlay outside fixed current-quarter periods")
        sid = row["evidence"]["scope_id"]
        _require(sid in scopes and row["corp_code"] == scopes[sid]["corp_code"]
                 and row["fiscal_period"] == scopes[sid]["quarter"], "Overlay row/scope mismatch")
        expected_available = (date.fromisoformat(row["filed"]) + timedelta(days=1)).isoformat()
        _require(row["available_date"] == expected_available
                 and row["available_at"] == datetime.combine(date.fromisoformat(expected_available), time.min, KST).isoformat(),
                 "Conservative next-day publication policy mismatch")
        _require(row["period_end"] < row["available_date"] < row["valid_until_exclusive"] <= horizon[row["corp_code"]],
                 "Invalid or unbounded overlay validity interval")
        point = _semantic(row, POINT)
        points[point] = row
        interval = (point, row["revision_key"], row["available_date"], row["valid_until_exclusive"])
        intervals.setdefault(interval, []).append(row)
    for values in intervals.values():
        both = len(values) == 2 and {r["fs_type"] for r in values} == {"CFS", "OFS"}
        ofs_only = len(values) == 1 and values[0]["fs_type"] == "OFS"
        if ofs_only:
            row_evidence = values[0]["evidence"]
            status = row_evidence.get("statement_scope_status")
            detail = row_evidence.get("statement_scope_details", {}).get("CFS", {})
            proofs = detail.get("absence_evidence", [])
            ofs_only = (status == {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"}
                and detail.get("absence_proven") is True and isinstance(proofs, list)
                and len(proofs) == 1 and isinstance(proofs[0], dict)
                and proofs[0].get("claim") == "REPORT_EXPLICITLY_DECLARES_CFS_NOT_APPLICABLE"
                and bool(HASH.fullmatch(str(proofs[0].get("xml_sha256"))))
                and bool(HASH.fullmatch(str(proofs[0].get("source_slice_sha256")))))
        _require(both or ofs_only, "Both statement scopes must be resolved or CFS absence source-certified")
    by_point = {}
    for (point, revision, start, end), _ in intervals.items():
        by_point.setdefault(point, []).append((start, end, revision))
    for windows in by_point.values():
        windows.sort()
        _require(all(a[1] <= b[0] for a, b in zip(windows, windows[1:])), "Overlapping approved revision windows")

    controls = {}
    def block(point, when, reason):
        controls.setdefault((point, when), set()).add(reason)
    for point, windows in by_point.items():
        starts = {window[0] for window in windows}
        for _, until, _ in windows:
            if until not in starts:
                block(point, until, "APPROVED_WINDOW_EXPIRED")
    unbound_blocks = []
    mappings = evidence.get("verified_scope_identity_mappings", [])
    for window in bundle["blocking_windows"]:
        sid, start, end = window["scope_id"], _day(window["valid_from"]), _day(window["valid_until_exclusive"])
        _require(sid in scopes and start < end <= horizon[scopes[sid]["corp_code"]], "Invalid blocking window")
        matching = [m for m in mappings if m["scope_id"] == sid and _day(m["valid_from"]) <= start < _day(m["valid_until_exclusive"])]
        if not matching:
            # Expiry of a prior approved identity is already handled above.
            # A never-identified scope must not be attached to a guessed asset.
            unbound_blocks.append({"scope_id": sid, "valid_from": start, "reason": window["reason"]})
            continue
        _require(len({int(m["asset_id"]) for m in matching}) == 1, "Ambiguous blocked-scope identity")
        scope = scopes[sid]
        point = (int(matching[0]["asset_id"]), _day(scope["period_end"]), scope["quarter"], "revenue")
        _require(not any(a < end and start < b for a, b, _ in by_point.get(point, [])), "Blocked and approved windows overlap")
        block(point, start, str(window["reason"]))

    overlay_by_exact = {_semantic(row, EXACT): row for row in overlay}
    _require(len(overlay_by_exact) == len(overlay), "Duplicate exact overlay revision")
    relevant_points = set(points) | {point for point, _ in controls}
    reused, seen_base = set(), set()
    for row in base_rows.loc[base_rows.metric.eq("revenue") & base_rows.period_end.between(pd.Timestamp("2015-01-01"), pd.Timestamp("2015-12-31"))].to_dict("records"):
        if _semantic(row, POINT) not in relevant_points:
            continue
        exact = _semantic(row, EXACT)
        _require(exact not in seen_base, "Duplicate exact base revision")
        seen_base.add(exact)
        _require(exact in overlay_by_exact, "Competing base revision requires explicit source reconciliation")
        other = overlay_by_exact[exact]
        _require(pd.notna(row["value"]) and Decimal(str(row["value"])) == Decimal(other["value"])
                 and _day(row["available_date"]) == other["available_date"]
                 and _instant(row["available_at"]) == other["available_at"]
                 and row["statement_type"] == other["statement_type"], "Exact revision collision mismatch")
        reused.add(exact)
    additions = []
    for row in overlay:
        if _semantic(row, EXACT) in reused:
            continue
        additions.append({**{key: row[key] for key in legacy_contract._LEDGER_REQUIRED if key != "quality_run_id"},
                          "quality_run_id": bundle["quality_run_id"]})
    control_evidence = []
    for (point, when), reasons in sorted(controls.items()):
        details = {**dict(zip(POINT, point)), "available_date": when, "reasons": sorted(reasons)}
        control_evidence.append(details)
        for fs_type in ("CFS", "OFS"):
            additions.append({**dict(zip(POINT, point)), "fs_type": fs_type, "statement_type": "IS", "value": np.nan,
                "available_date": when, "available_at": datetime.combine(date.fromisoformat(when), time.min, KST),
                "revision_key": "~VALIDITY_CONTROL:" + digest({**details, "fs_type": fs_type}),
                "quality_run_id": "DERIVED_VALIDITY_CONTROL:" + bundle["quality_run_id"]})
    merged = pd.concat([base_rows.copy(deep=True), pd.DataFrame(additions)], ignore_index=True)
    for field in ("period_end", "available_date"):
        merged[field] = pd.to_datetime(merged[field])
    provenance = {"schema_version": VERSION, "source": "CERTIFIED_BASE_PLUS_BOUNDED_DOCUMENT_OVERLAY_AND_DERIVED_VALIDITY_CONTROLS",
        "materializer_source_sha256": fundamentals.source_sha256(), "overlay_source_sha256": source_sha256(),
        "base_source_query_sha256": hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest(), "base_ledger": base_provenance,
        "dataset_version": bundle["dataset_version"], "dataset_manifest_sha256": bundle["manifest_sha256"],
        "dataset_bundle_sha256": bundle["bundle_sha256"], "dataset_quality_run_id": bundle["quality_run_id"],
        "overlay_query_sha256": bundle["query_source_sha256"], "overlay_metadata_query_sha256": bundle["metadata_query_sha256"],
        "covered_through_by_corp": evidence["covered_through_by_corp"], "exact_base_observations_reused": len(reused),
        "new_source_observations": len(overlay) - len(reused), "derived_control_rows": len(controls) * 2,
        "validity_controls": control_evidence, "unbound_blocking_scopes_not_guessed": unbound_blocks,
        "source_expiry_applies_to_fiscal_keys_not_entire_panel": True,
        "revenue_statement_basis_guard": {
            "scope": "ALL_REVENUE_ALL_ASSETS_AND_DATES_INCLUDING_EXISTING_BASE",
            "fy_residual": "FY_AND_CONTIGUOUS_Q1_Q2_Q3_REQUIRE_ONE_CFS_OR_OFS_BASIS",
            "ttm": "LATEST_FOUR_CONTIGUOUS_QUARTERS_REQUIRE_ONE_CFS_OR_OFS_BASIS",
            "unknown_or_mixed_basis": "NAN_BARRIER_WITHOUT_SOURCE_VALUE_MODIFICATION",
            "overlay_revision_selection": "EXPLICIT_VALIDITY_INTERVAL_OVERRIDES_EXPIRED_SCOPE_PRIORITY",
            "other_metrics": "FROZEN_MATERIALIZER_UNCHANGED_NOT_BASIS_CERTIFIED_BY_THIS_GUARD",
        },
        "original_source_rows_modified": False, "oos_performance_inspections": 0,
    }
    provenance["compiled_ledger_sha256"] = legacy_contract._frame_digest(merged, sorted(merged.columns),
        ("asset_id", "available_date", "period_end", "fiscal_period", "metric", "fs_type", "revision_key", "quality_run_id"))
    return merged, provenance


def _revenue_snapshot_with_basis(state):
    """Use frozen calendar/value rules, then reject ambiguous/mixed FS basis.

    Basis attaches to the selected original quarter, not to a recomputed value.
    FY residuals need the FY and all three contributing quarters to agree. An
    explicit Q4 retains its own source basis and is not replaced by an FY.
    """
    sanitized = {key: dict(row) for key, row in state.items()}
    for row in sanitized.values():
        if row.get("fs_type") not in {"CFS", "OFS"}:
            row["value"] = np.nan
    series = fundamentals._standalone_flow(sanitized, "revenue")
    by_end, fiscal_years = {}, {}
    for (pe, fp, _), row in sanitized.items():
        if fp == "FY":
            fiscal_years[pe] = row
        else:
            by_end.setdefault(pe, []).append((fp, row))
    basis = {}
    for pe, rows in by_end.items():
        if len(rows) == 1 and rows[0][0] in {"Q1", "Q2", "Q3", "Q4"}:
            row = rows[0][1]
            basis[pe] = row["fs_type"] if np.isfinite(row["value"]) and row["fs_type"] in {"CFS", "OFS"} else None
        else:
            basis[pe] = None
    fy_basis_rejections = 0
    for position, (pe, fp, value) in enumerate(series):
        if pe not in fiscal_years or (len(by_end.get(pe, [])) == 1 and by_end[pe][0][0] == "Q4"):
            continue
        fy = fiscal_years[pe]
        prior = series[max(0, position - 3):position]
        components = [basis.get(row[0]) for row in prior]
        one_basis = (len(prior) == 3 and [row[1] for row in prior] == ["Q1", "Q2", "Q3"]
                     and fy["fs_type"] in {"CFS", "OFS"} and all(item == fy["fs_type"] for item in components))
        basis[pe] = fy["fs_type"] if fp == "Q4" and np.isfinite(value) and one_basis else None
        if fp == "Q4" and np.isfinite(value) and not one_basis:
            fy_basis_rejections += 1
    guarded = [(pe, fp, value if basis.get(pe) is not None else np.nan) for pe, fp, value in series]
    recent = guarded[-4:]
    structurally_valid = len(recent) == 4 and fundamentals.is_contiguous_fiscal_quarters(recent)
    one_basis = structurally_valid and len({basis.get(row[0]) for row in recent}) == 1
    return {"revenue": guarded[-1][2] if guarded else np.nan,
            "revenue_ttm": sum(row[2] for row in recent) if one_basis else np.nan,
            "fy_basis_rejections": fy_basis_rejections,
            "ttm_mixed_basis_rejected": bool(structurally_valid and not one_basis)}


def _guarded_revenue_replay(ledger, bundle, receipt):
    """Replay selected revenue basis, preserving explicit validity barriers.

    Ordinary certified base points keep frozen CFS/date/revision priority.
    Overlaid points use their fully certified interval instead: a later proven
    OFS-only revision may replace an expired CFS, never an unresolved CFS.
    No source observation is edited or assigned a fabricated CFS amount.
    """
    schedule, overlaid_points = {}, set()
    intervals = {}
    for row in bundle["rows"]:
        point = _semantic(row, POINT)
        intervals.setdefault((point, row["available_date"], row["revision_key"]), []).append(row)
    for (point, when, _), rows in intervals.items():
        chosen = next((row for row in rows if row["fs_type"] == "CFS"), rows[0])
        schedule.setdefault((point[0], pd.Timestamp(when)), {})[point] = {
            **chosen, "value": float(chosen["value"]), "period_end": pd.Timestamp(chosen["period_end"]),
            "available_date": pd.Timestamp(when)}
        overlaid_points.add(point)
    for control in receipt["validity_controls"]:
        point = _semantic(control, POINT)
        key = (point[0], pd.Timestamp(control["available_date"]))
        _require(point not in schedule.get(key, {}), "Validity control and approved interval collide")
        schedule.setdefault(key, {})[point] = {**dict(zip(POINT, point)),
            "value": np.nan, "fs_type": "UNRESOLVED", "available_date": key[1],
            "period_end": pd.Timestamp(point[1]), "revision_key": "VALIDITY_BARRIER"}
        overlaid_points.add(point)
    d = ledger.loc[ledger.metric.eq("revenue")].copy()
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.dropna(subset=["period_end", "available_date"])
    d = d.sort_values(["asset_id", "available_date", "revision_key"], kind="stable")
    snapshots = []
    for asset_id, asset_rows in d.groupby("asset_id", sort=False):
        state = {}
        for when, event in asset_rows.groupby("available_date", sort=True):
            changed = False
            for row in event.to_dict("records"):
                if _semantic(row, POINT) in overlaid_points:
                    continue
                key = (pd.Timestamp(row["period_end"]), str(row["fiscal_period"]), "revenue")
                prior = state.get(key)
                if prior is None or fundamentals._priority(row) > fundamentals._priority(prior):
                    state[key], changed = row, True
                elif fundamentals._priority(row) == fundamentals._priority(prior):
                    a, b = row["value"], prior["value"]
                    if row["fs_type"] != prior["fs_type"] or not (a == b or (pd.isna(a) and pd.isna(b))):
                        # Equal-priority conflicting raw facts cannot be selected
                        # by input ordering. A newer revision may resolve them.
                        state[key] = {**prior, "value": np.nan}
                        changed = True
            for point, row in schedule.get((int(asset_id), pd.Timestamp(when)), {}).items():
                state[(pd.Timestamp(point[1]), point[2], "revenue")] = row
                changed = True
            if changed:
                snapshots.append({"asset_id": int(asset_id), "available_date": pd.Timestamp(when),
                                  **_revenue_snapshot_with_basis(state)})
    return pd.DataFrame(snapshots, columns=["asset_id", "available_date", "revenue", "revenue_ttm",
                                          "fy_basis_rejections", "ttm_mixed_basis_rejected"])


def _attach_revenue_guard(frame, guarded):
    """Union event dates and as-of join whole snapshots, never fill a NaN cell."""
    if guarded.empty:
        return frame, {"guarded_revenue_snapshots": 0}
    pieces = []
    for asset_id, source in frame.groupby("asset_id", sort=False):
        revenue = guarded.loc[guarded.asset_id.eq(asset_id)]
        if revenue.empty:
            pieces.append(source)
            continue
        dates = pd.DataFrame({"available_date": pd.concat([source.available_date, revenue.available_date]).drop_duplicates().sort_values()})
        merged = pd.merge_asof(dates, source.drop(columns=["revenue", "revenue_ttm"]).sort_values("available_date"), on="available_date", direction="backward")
        merged = pd.merge_asof(merged, revenue[["available_date", "revenue", "revenue_ttm"]].sort_values("available_date"), on="available_date", direction="backward")
        merged["asset_id"] = int(asset_id)
        pieces.append(merged)
    out = pd.concat(pieces, ignore_index=True).sort_values(["available_date", "asset_id"]).reset_index(drop=True)
    out = out[frame.columns]
    audit = {"guarded_revenue_snapshots": len(guarded),
             "snapshots_with_fy_basis_rejection": int(guarded.fy_basis_rejections.gt(0).sum()),
             "snapshots_with_ttm_mixed_basis_rejection": int(guarded.ttm_mixed_basis_rejected.sum()),
             "added_validity_or_scope_transition_snapshot_dates": len(out) - len(frame)}
    return out, audit


def materialize(base_rows, bundle, *, verbose=False):
    ledger, receipt = compile_ledger(base_rows, bundle)
    frame = fundamentals.materialize_pit(ledger, verbose=verbose)
    guarded = _guarded_revenue_replay(ledger, bundle, receipt)
    frame, receipt["revenue_basis_guard_audit"] = _attach_revenue_guard(frame, guarded)
    receipt["materialized_frame_sha256"] = legacy_contract._materialized_digest(frame)
    receipt["sha256"] = digest(receipt)
    frame.attrs[RECEIPT_KEY] = receipt
    return frame


def bind(panel, base_rows, bundle, *, materialized=None):
    """Verify a new replay before replacing inherited legacy-only metadata.

    Failed verification leaves all parent metadata untouched. Only a successful
    overlay binding removes the incompatible old single-source contract.
    """
    fund = materialize(base_rows, bundle) if materialized is None else materialized
    receipt = deepcopy(fund.attrs.get(RECEIPT_KEY))
    _require(isinstance(receipt, dict), "Expiry-aware overlay materialization receipt required")
    expected_sha = receipt.pop("sha256", None)
    _require(expected_sha == digest(receipt), "Overlay materialization receipt changed")
    _, expected = compile_ledger(base_rows, bundle)
    _require(all(receipt.get(k) == value for k, value in expected.items())
             and receipt["materialized_frame_sha256"] == legacy_contract._materialized_digest(fund), "Overlay replay provenance mismatch")
    features = sorted(fundamentals.PIT_FEATURES)
    base = panel.monthly.drop(columns=[*features, "available_date"], errors="ignore")
    attached = fundamentals.attach(base, fund, features)
    _require(legacy_contract._financial_digest(panel.monthly, features) == legacy_contract._financial_digest(attached, features),
             "Panel is not the expiry-aware financial replay")
    contract = {**receipt, "materialization_receipt_sha256": expected_sha, "financial_features": features,
        "panel_row_count": len(panel.monthly), "financial_frame_sha256": legacy_contract._financial_digest(panel.monthly, features)}
    contract["sha256"] = digest(contract)
    panel.meta.pop(legacy_contract.META_KEY, None)
    panel.meta[META_KEY] = contract
    return deepcopy(contract)


def verify(panel):
    """Verify the overlay branch, including legacy_contract.verify routing."""
    contract = deepcopy(panel.meta.get(META_KEY))
    _require(isinstance(contract, dict) and legacy_contract.META_KEY not in panel.meta, "Unambiguous overlay contract required")
    expected = contract.pop("sha256", None)
    _require(expected == digest(contract) and contract.get("schema_version") == VERSION, "Overlay contract altered")
    _require(contract["materializer_source_sha256"] == fundamentals.source_sha256() == FROZEN_MATERIALIZER_SHA
             and contract["overlay_source_sha256"] == source_sha256()
             and contract["base_source_query_sha256"] == hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest()
             and contract["overlay_query_sha256"] == query_source_sha256()
             and contract["overlay_metadata_query_sha256"] == hashlib.sha256(DATASET_METADATA_SQL.encode()).hexdigest(),
             "Financial overlay methodology/source changed")
    features = sorted(fundamentals.PIT_FEATURES)
    _require(contract["financial_features"] == features and contract["panel_row_count"] == len(panel.monthly)
             and contract["financial_frame_sha256"] == legacy_contract._financial_digest(panel.monthly, features), "Overlay panel content changed")
    receipt = {k: v for k, v in contract.items() if k not in {"materialization_receipt_sha256", "financial_features", "panel_row_count", "financial_frame_sha256"}}
    _require(digest(receipt) == contract["materialization_receipt_sha256"], "Overlay receipt binding changed")
    return {"status": "VERIFIED_EXPIRY_AWARE_OVERLAY_REPLAY", "contract_sha256": expected,
            "dataset_version": contract["dataset_version"], "dataset_bundle_sha256": contract["dataset_bundle_sha256"]}
