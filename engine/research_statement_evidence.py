"""Pure, diagnostic-only annual DART CFO/assets evidence pairing.

Input is the complete FY line inventory for the requested year from the
CERTIFIED-filtered public.dart_standardized_statement_line interface, including
other mapped metrics. Omitting filings/metrics can hide a newer incomplete filing;
this function cannot authenticate the extraction or certify its completeness/PIT.
Filings/scopes with no mapped lines are invisible in this source interface.
No factor score, admission decision, return label, I/O or state is produced.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo


DEFINITION_VERSION = "dart-fy-cfo-assets-evidence-v1"
SOURCE_RELATION = "public.dart_standardized_statement_line"
_TARGETS = {"operating_cash_flow": "CF", "total_assets": "BS"}
_LINEAGE = ("filing_id", "filed", "available_at", "revision_key", "quality_run_id",
            "mapping_version", "line_key", "account_id", "statement_type", "metric",
            "metric_candidate_count", "period_end", "business_year", "fs_type",
            "currency", "report_code", "fiscal_period", "source")


def _aware(value):
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return parsed
    except (TypeError, ValueError):
        pass
    return None


def _day(value):
    if isinstance(value, datetime):
        return None
    try:
        return value if isinstance(value, date) else date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _text(value):
    return value is not None and bool(str(value).strip())


def _lineage(row):
    return {key: str(row[key]) if row.get(key) is not None else None
            for key in _LINEAGE}


def _pair(selected, fs_type):
    rows = [row for row in selected if row.get("fs_type") == fs_type]
    reasons = []
    metrics = {}
    for metric, statement in _TARGETS.items():
        candidates = [row for row in rows if row.get("metric") == metric]
        if not candidates:
            reasons.append(f"MISSING_{metric.upper()}")
            continue
        if len(candidates) != 1 or any(
            isinstance(row.get("metric_candidate_count"), bool)
            or row.get("metric_candidate_count") != 1 for row in candidates
        ):
            reasons.append(f"AMBIGUOUS_{metric.upper()}")
            continue
        row = metrics[metric] = candidates[0]
        if row.get("statement_type") != statement:
            reasons.append("STATEMENT_TYPE_MISMATCH")
        if row.get("report_code") != "11011":
            reasons.append("FY_REPORT_CODE_MISMATCH")
        if any(not _text(row.get(key)) for key in
               ("quality_run_id", "mapping_version", "line_key", "account_id")):
            reasons.append("MISSING_LINEAGE")
        filed, period = _day(row.get("filed")), _day(row.get("period_end"))
        available_day = _aware(row["available_at"]).astimezone(ZoneInfo("Asia/Seoul")).date()
        if (filed is None or period is None or period >= available_day
                or filed < period or filed >= available_day):
            reasons.append("INVALID_FILING_DATES")
    if len(metrics) != 2:
        return None, sorted(set(reasons))
    cfo, assets = metrics["operating_cash_flow"], metrics["total_assets"]
    if _day(cfo.get("period_end")) != _day(assets.get("period_end")):
        reasons.append("PERIOD_END_MISMATCH")
    currencies = [row.get("currency") for row in (cfo, assets)]
    if not all(isinstance(value, str) and value.strip() for value in currencies):
        reasons.append("MISSING_CURRENCY")
    elif currencies[0] != currencies[1]:
        reasons.append("CURRENCY_MISMATCH")
    if cfo.get("line_key") == assets.get("line_key"):
        reasons.append("LINE_IDENTITY_CONFLICT")
    cfo_amount, asset_amount = _number(cfo.get("current_amount")), _number(assets.get("current_amount"))
    if cfo_amount is None:
        reasons.append("INVALID_CURRENT_CFO")
    if asset_amount is None or asset_amount <= 0:
        reasons.append("INVALID_POSITIVE_CURRENT_ASSETS")
    # The transform copies thstrm_amount/thstrm_add_amount separately. Neither
    # schema nor mapping supplies an equivalence guarantee for cumulative-only FY.
    cumulative = cfo.get("current_cumulative_amount")
    if cumulative is not None:
        cumulative_amount = _number(cumulative)
        if cumulative_amount is None or cumulative_amount != cfo_amount:
            reasons.append("FY_CFO_AMOUNT_CONTRADICTION")
    if reasons:
        return None, sorted(set(reasons))
    return {
        "period_end": _day(cfo["period_end"]).isoformat(), "currency": currencies[0],
        "operating_cash_flow": str(cfo_amount), "total_assets": str(asset_amount),
        "cfo_lineage": _lineage(cfo), "assets_lineage": _lineage(assets),
    }, []


def pair_annual_cfo_assets(
    rows: Iterable[Mapping], *, business_year: int, as_of: str | datetime,
    eligible_asset_ids: Iterable[int], scope_ref: str,
) -> dict:
    """Pair latest available annual evidence; denominator is the supplied universe.

    Select newest visible standardized filing (available_at, revision_key,
    filing_id) across CFS/OFS for this year; prefer CFS if any mapped CFS line
    exists in that filing. OFS is
    used only when that filing has no CFS lines. Never fall back on invalid pairs.
    Full annual filing inventory, eligibility and extraction scope are caller
    responsibilities. This selection policy does not authenticate their claims.
    Amounts remain exact decimal strings; assets are a stock, never a sum.
    """
    cutoff = _aware(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a timezone-aware timestamp")
    if not isinstance(business_year, int) or isinstance(business_year, bool) or not 1 <= business_year <= 9999:
        raise ValueError("business_year must be an integer year")
    if not isinstance(scope_ref, str) or not scope_ref.strip():
        raise ValueError("scope_ref must be nonempty")
    universe = list(eligible_asset_ids)
    if (any(not isinstance(asset, int) or isinstance(asset, bool) or asset <= 0 for asset in universe)
            or len(set(universe)) != len(universe)):
        raise ValueError("eligible_asset_ids must be unique positive integer asset IDs")
    eligible = set(universe)
    available, invalid = defaultdict(list), defaultdict(set)
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("rows must contain mappings from the standardized interface")
        asset = row.get("asset_id")
        if (asset not in eligible or row.get("source") != "DART"
                or row.get("fiscal_period") != "FY" or row.get("business_year") != business_year):
            continue
        stamp = _aware(row.get("available_at"))
        if stamp is None:
            invalid[asset].add("INVALID_AVAILABILITY")
            continue
        if stamp > cutoff:
            continue  # Before revision, ambiguity, amount or lineage validation.
        if not all(_text(row.get(key)) for key in ("filing_id", "revision_key")):
            invalid[asset].add("MISSING_FILING_IDENTITY")
            continue
        available[asset].append(dict(row))

    pairs, rejects = [], []
    for asset in sorted(eligible):
        records = available[asset]
        base = {"asset_id": asset, "business_year": business_year}
        reasons = sorted(invalid[asset])
        if not records:
            rejects.append({**base, "reasons": reasons or ["NO_AVAILABLE_FY_FILING"]})
            continue
        latest = max(records, key=lambda row: (
            _aware(row["available_at"]), str(row["revision_key"]), str(row["filing_id"])))
        selected = [row for row in records if row["filing_id"] == latest["filing_id"]]
        base.update(filing_id=latest["filing_id"],
                    available_at=_aware(latest["available_at"]).astimezone(timezone.utc).isoformat())
        if len({(_aware(row["available_at"]), row["revision_key"]) for row in selected}) != 1:
            reasons.append("INCONSISTENT_FILING_METADATA")
        if any(row.get("fs_type") not in {"CFS", "OFS"} for row in selected):
            reasons.append("INVALID_FS_TYPE")
        fs_type = "CFS" if any(row.get("fs_type") == "CFS" for row in selected) else "OFS"
        base["fs_type"] = fs_type
        pair, pair_reasons = _pair(selected, fs_type)
        reasons.extend(pair_reasons)
        if reasons:
            rejects.append({**base, "reasons": sorted(set(reasons)),
                            "selected_lineage": sorted((_lineage(row) for row in selected),
                                                       key=lambda row: str(row))})
        else:
            pairs.append({**base, **pair})
    count = len(universe)
    return {
        "definition_version": DEFINITION_VERSION, "purpose": "DIAGNOSTIC_ONLY",
        "source_relation": SOURCE_RELATION, "source_or_completeness_reverified": False,
        "unit_scale_reverified": False,
        "pit_certified": False, "factor_admission": "NOT_ASSESSED",
        "scope": {"scope_ref": scope_ref, "business_year": business_year,
                  "as_of": cutoff.astimezone(timezone.utc).isoformat(), "eligible_asset_ids": sorted(eligible)},
        "policy": {"filing": "LATEST_AVAILABLE_THEN_REVISION_THEN_FILING_ID",
                   "fs_type": "CFS_WITHIN_LATEST_FILING_ELSE_OFS_NO_INVALID_FALLBACK",
                   "amount": "FY_CURRENT_AMOUNT_CFO_CUMULATIVE_IF_PRESENT_MUST_EQUAL",
                   "unit": "SOURCE_NUMERIC_AMOUNTS_NO_SCALING_OR_CURRENCY_CONVERSION",
                   "inventory": "ALL_STANDARDIZED_FY_LINES_FOR_REQUESTED_YEAR_REQUIRED",
                   "unmapped_filing_or_scope": "INVISIBLE_TO_THIS_INTERFACE"},
        "pairs": pairs, "rejects": rejects,
        "coverage": {"eligible_assets": count, "matched_assets": len(pairs),
                     "unmatched_assets": len(rejects),
                     "matched_fraction": len(pairs) / count if count else None,
                     "reason_counts": dict(sorted(Counter(
                         reason for row in rejects for reason in row["reasons"]).items()))},
    }
