"""Read-only export of already released, authenticated reviewer evidence.

Run from the repository root with:
    .venv/bin/python scripts/dashboard_exports/export_research_catalog.py

This does not refresh research memory, evaluate candidates, connect to a DB,
reveal OOS, or publish Gold. Only the output JSON is written. Pending records
are counted before any result/evidence read and their contents are not exported.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from engine import epochs
from engine.lesson_evidence import build_packet, digest, portable_provenance, validate_review
from scripts.candidate_lessons import reviewed_text


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe(value):
    """Remove local locators and accidentally embedded connection information."""
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()
                if k.lower() not in {"password", "passwd", "api_key", "token", "dsn",
                                     "database_url", "db_host", "connection_string"}}
    if isinstance(value, list):
        return [safe(v) for v in value]
    if isinstance(value, str):
        value = value.replace(str(REPO) + "/", "")
        value = re.sub(r"/(?:Users|home)/[^\s\"'<>]+", "[local path omitted]", value)
        value = re.sub(r"(?:postgres(?:ql)?|mysql)://[^\s\"'<>]+", "[connection omitted]", value)
        value = re.sub(r"[A-Za-z0-9.-]+\.rds\.amazonaws\.com", "[internal host omitted]", value)
    return value


def phase_checks(packet, phase):
    return [{"evidence_id": e["id"], **e["data"]} for e in packet["evidence"]
            if e["kind"] == "GATE_OBSERVATION" and e.get("phase") == phase]


def scalar_metrics(packet, phase):
    for entry in packet["evidence"]:
        if entry["id"] == f"{phase}.metrics":
            return entry["data"]
    return None


def compact_regimes(section):
    if not section or "data" not in section:
        return section or {"status": "NOT_COLLECTED"}
    data = section["data"]
    result = {k: v for k, v in section.items() if k != "data"}
    result.update({k: v for k, v in data.items() if k not in {"monthly", "macro_views"}})
    result["phase"] = "discovery"
    result["presentation"] = {"primary_view": "regime", "secondary_views": [
        "trend_long", "trend_short", "volatility_long", "volatility_short", "regime_detail"],
        "selection_basis": "SAMPLE_INTERPRETABILITY_NOT_BEST_PERFORMANCE",
        "detail_states_are_exploratory": True, "macro_cross_product": False}
    result["evidence_id"] = "diagnostic.discovery.regime_comparison"
    result["monthly"] = data.get("monthly", [])
    result["macro_views"] = {}
    for name, view in data.get("macro_views", {}).items():
        # Performance is identical to the common diagnostic monthly table.
        # Keep only state alignment here, preserving every month and UNKNOWN.
        compact = {k: v for k, v in view.items() if k != "monthly"}
        compact["monthly_states"] = [
            {"month": r["month"], "effective_month": r.get("effective_month"),
             "state": r.get("state", "UNKNOWN")} for r in view.get("monthly", [])
        ]
        result["macro_views"][name] = compact
    result["units"] = {
        "rank_ic": "rank correlation coefficient (dimensionless)",
        "top_minus_bottom": "next-month return fraction; multiply by 100 for percent",
        "ci95": "same unit as the associated estimate",
        "n_months": "signal months", "n_episodes": "calendar-contiguous observed runs; not independent replications",
        "n_joint_usable_episodes": "observed state occurrences with joint usable outcomes; UNKNOWN does not create a new occurrence",
    }
    return result


def compact_diagnostics(packet):
    output = {}
    for name, section in packet.get("diagnostics", {}).items():
        if name == "regime_comparison":
            continue
        if name == "charts":
            output[name] = {
                "status": section["status"], "payload_omitted": "SVG omitted; numeric tables retained",
                "limitations": section.get("limitations", []),
                "visual_inspection": "Not inferred from chart generation",
            }
        else:
            output[name] = section
    return output


def export(root, as_of):
    memory_path = root / "memory/candidate_lessons.jsonl"
    memory_bytes = memory_path.read_bytes()
    ledger = [json.loads(s) for s in memory_bytes.decode().splitlines() if s.strip()]
    unique, conflict = {}, set()
    for record in ledger:
        rid = record["record_id"]
        if rid in unique and unique[rid] != record:
            conflict.add(rid)
        unique[rid] = record
    campaigns = {p.parent.name: read_json(p) for p in sorted((root / "campaigns").glob("*/manifest.json"))}
    record_counts = Counter(r["evidence"]["campaign"] for r in unique.values())
    confirmations, release_reason = {}, {}
    for cid in sorted({r["evidence"]["campaign"] for r in unique.values()
                       if r.get("visibility") == "RELEASED_QUALITATIVE"}):
        campaign = campaigns.get(cid, {})
        if campaign.get("status") == "CLOSED_NO_QUALIFIED":
            confirmations[cid] = {}
        elif campaign.get("status") == "REVEALED" and campaign.get("oos", {}).get("status") == "REVEALED":
            try:
                # Existing exact-set/protocol/digest authentication is read-only.
                confirmations[cid] = {r["factor"]: r for r in epochs.load_confirmation(root, cid)["confirmations"]}
            except (ValueError, OSError, KeyError):
                release_reason[cid] = "CURRENT_CONFIRMATION_AUTHENTICATION_FAILED"
        else:
            release_reason[cid] = "CAMPAIGN_NOT_RELEASED"

    records, withheld = [], Counter()
    for rid, record in sorted(unique.items()):
        # This decision precedes opening any raw result or evidence packet.
        if rid in conflict:
            withheld["CONFLICTING_LEDGER_IDENTITY"] += 1
            continue
        if record.get("visibility") != "RELEASED_QUALITATIVE":
            withheld[record.get("visibility", "UNRELEASED")] += 1
            continue
        cid, eid, name = rid.split("/", 2)
        if cid not in confirmations:
            withheld[release_reason.get(cid, "CAMPAIGN_NOT_FOUND")] += 1
            continue
        campaign = campaigns[cid]
        try:
            epoch = epochs.load_epoch(root, cid, eid)
            if epoch.get("status") != "CLOSED":
                raise ValueError("EPOCH_NOT_CLOSED")
            candidate = next(c for c in epoch["candidates"] if c["name"] == name)
            provenance = portable_provenance(record["evidence"])
            cycle = candidate["cycle_id"]
            if (cid, eid, cycle, candidate["definition_hash"]) != (
                provenance["campaign"], provenance["epoch"], provenance["cycle"], provenance["definition_hash"]
            ) or Path(cycle).name != cycle:
                raise ValueError("IDENTITY_MISMATCH")
            result_path = root / "runs" / cycle / "result.json"
            raw_bytes = result_path.read_bytes()
            payload = json.loads(raw_bytes)
            factor = payload["factor"]
            if (payload.get("campaign_id"), payload.get("epoch_id"), factor.get("name"), factor.get("definition_hash")) != (
                cid, eid, name, candidate["definition_hash"]
            ):
                raise ValueError("SOURCE_BINDING_MISMATCH")
            artifact_sha = hashlib.sha256(raw_bytes).hexdigest()
            expected_sha = candidate.get("discovery_result_artifact_sha256")
            if (expected_sha or "mechanism_study" in payload) and expected_sha != artifact_sha:
                raise ValueError("FROZEN_ARTIFACT_HASH_MISMATCH")
            packet_sha = record["evidence_packet"]["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", packet_sha):
                raise ValueError("INVALID_PACKET_HASH")
            packet = read_json(root / "memory/lesson_evidence" / f"{packet_sha}.json")
            if digest(packet) != packet_sha or packet.get("record_id") != rid:
                raise ValueError("EVIDENCE_PACKET_HASH_MISMATCH")
            final = confirmations[cid].get(name)
            # Rebuild in memory, retaining legacy provenance if required. No writes.
            rebuilt = build_packet(record, payload, final, schema_version=packet["schema_version"])
            if digest(rebuilt) != packet_sha:
                raise ValueError("CURRENT_SOURCE_PACKET_MISMATCH")
            all_checks = phase_checks(packet, "discovery") + phase_checks(packet, "confirmation")
            fresh_validation = {
                "checks": [{"check": str(c.get("tier", "")), "name": str(c.get("name", "")),
                            "status": "PASS" if c.get("passed") is True else "FAIL" if c.get("passed") is False else "UNVERIFIED"}
                           for c in all_checks],
                "phase": "confirmation" if final else "discovery",
                "verdict": final.get("verdict") if final else candidate.get("verdict"),
            }
            if fresh_validation != record["validation"]:
                raise ValueError("CURRENT_VALIDATION_MISMATCH")
            basis = hashlib.sha256(json.dumps({
                "validation": fresh_validation, "evidence": record["evidence"], "packet_sha256": packet_sha,
            }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            if basis != record.get("review_basis"):
                raise ValueError("CURRENT_REVIEW_BASIS_MISMATCH")
        except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
            reason = str(exc) if str(exc).isupper() and len(str(exc)) < 80 else "AUTHENTICATION_FAILED"
            withheld[reason] += 1
            continue

        review = None
        review_status = "UNREVIEWED"
        if record.get("review"):
            try:
                validate_review(record["review"], record, packet)
                if reviewed_text(record) is None:
                    raise ValueError("qualitative memory review not current")
                review = record["review"]
                review_status = "REVIEWED_CURRENT"
            except (ValueError, TypeError, KeyError):
                review_status = "STALE_OR_INVALID_REVIEW_WITHHELD"
        performance = {}
        for phase in ("discovery", "confirmation"):
            metrics = scalar_metrics(packet, phase)
            if metrics is None:
                continue
            performance[phase] = {
                "evidence_id": f"{phase}.metrics", "stored_evaluation_phase": metrics.get("evaluation_phase"),
                "metrics": metrics, "checks": phase_checks(packet, phase),
                "discovery_signal_period": {"start": metrics.get("research_start"), "end": campaign.get("discovery", {}).get("signal_end")},
                "period_kind": "FROZEN_ELIGIBLE_SIGNAL_WINDOW; missing observations are not filled",
                "oos_signal_period": ({"start": metrics.get("oos_start"), "end": metrics.get("oos_end"),
                                       "n_months": metrics.get("oos_months")} if metrics.get("oos_start") else None),
                "scope_note": "oos_* metrics use the fixed confirmation signal window (except oos_discovery_ic, the Discovery reference); IC/neutral/portfolio metrics use the frozen Discovery window. Stored phase full does not make gross/cost/net OOS returns.",
            }
        h = record["hypothesis_and_calculation"]
        regimes = compact_regimes(packet.get("diagnostics", {}).get("regime_comparison"))
        # Legacy coarse output omits unseen states; preserve the reviewer-authenticated
        # zero-observation annotation without manufacturing estimates or intervals.
        if review and review.get("regime_review", {}).get("coarse_absent_states"):
            regimes["reviewed_absent_coarse_states"] = review["regime_review"]["coarse_absent_states"]
        records.append({
            "record_id": rid, "factor_name": name, "campaign_id": cid, "epoch_id": eid,
            "family": record.get("family"), "ruleset": record.get("ruleset"),
            "visibility": "RELEASED_QUALITATIVE", "review_status": review_status,
            "definition": {
                **h, "name": name, "predicted_sign": factor.get("predicted_sign"),
                "rebalance_months": factor.get("rebalance_months"), "category": factor.get("category"),
                "exploration_domain": factor.get("exploration_domain"),
                "calculation_summary": h.get("hypothesis") or factor.get("hypothesis"),
                "meaning_status": "PREREGISTERED_HYPOTHESIS_NOT_VERIFIED_CAUSE",
                "research_spec": payload.get("research_spec", {}),
            },
            "validation": {**record["validation"], "discovery_verdict": candidate.get("verdict"),
                           "confirmation_verdict": final.get("verdict") if final else None,
                           "confirmation_status": "EVALUATED" if final else "NOT_EVALUATED",
                           "qualification_status": candidate.get("qualification_status"),
                           "qualification_reason": candidate.get("qualification_reason"),
                           "failed_checks": [c for c in all_checks if c.get("passed") is False]},
            "performance": performance,
            "review": review,
            "unreviewed_notice": None if review else "기계 검사 사실만 있으며 경제적 원인과 일반 교훈은 아직 검토되지 않았습니다.",
            "diagnostics": compact_diagnostics(packet),
            "regimes": regimes,
            "scientist": packet.get("scientist"),
            "review_contract": packet.get("review_contract"),
            "provenance": {**provenance, "result": f"research/{provenance['result']}",
                           "packet_path": f"research/memory/lesson_evidence/{packet_sha}.json",
                           "packet_sha256": packet_sha, "packet_schema": packet["schema_version"],
                           "source_sha256": packet["source_sha256"], "discovery_artifact_sha256": artifact_sha,
                           "frozen_discovery_artifact_hash_present": bool(expected_sha),
                           "authentication": "CURRENT_RELEASE_STATE_AND_EXACT_PACKET_REBUILD",
                           "review_basis": record["review_basis"]},
        })

    released_by_campaign = Counter(r["campaign_id"] for r in records)
    campaign_output = []
    for cid, campaign in campaigns.items():
        public = bool(released_by_campaign[cid])
        item = {
            "campaign_id": cid, "status": campaign.get("status"), "created_at": campaign.get("created_at"),
            "finalized_at": campaign.get("finalized_at"), "ruleset": campaign.get("ruleset_version"),
            "protocol_version": campaign.get("protocol_version"), "ledger_records": record_counts[cid],
            "released_records": released_by_campaign[cid], "withheld_records": record_counts[cid] - released_by_campaign[cid],
            "release_status": "RELEASED" if public else "WITHHELD_OR_NO_LEDGER_RECORDS",
            "manifest": f"research/campaigns/{cid}/manifest.json",
        }
        if public:
            item.update({
                "discovery": campaign.get("discovery"),
                "oos": {k: v for k, v in campaign.get("oos", {}).items() if k in {
                    "mode", "status", "start", "signal_end", "return_start", "return_end",
                    "min_months", "revealed_at", "evidence_class", "prior_exposure_ids"}},
                "implementation_verified_at": campaign.get("implementation_verified_at"),
                "gold_publication_status": campaign.get("gold_publication_status", "NOT_STATED_IN_CAMPAIGN"),
                "confirmation_result_digest": campaign.get("confirmation_result_digest"),
            })
        campaign_output.append(item)

    metric_dictionary = {
        "gross": {"unit": "annualized percentage points", "scope": "discovery_portfolio", "meaning": "Mean monthly long-only portfolio return minus eligible-universe benchmark, multiplied by 12 × 100; not cumulative wealth or OOS return."},
        "cost": {"unit": "annualized percentage points", "scope": "discovery_portfolio", "meaning": "Mean modeled monthly transaction cost × 12 × 100."},
        "net": {"unit": "annualized percentage points", "scope": "discovery_portfolio", "meaning": "gross minus cost; benchmark-relative, not absolute return."},
        "turnover": {"unit": "annualized percent", "scope": "discovery_portfolio", "meaning": "Mean monthly one-way turnover × 12 × 100."},
        "net_ir": {"unit": "annualized dimensionless ratio", "scope": "discovery_portfolio", "meaning": "Mean monthly net excess return / sample standard deviation × sqrt(12)."},
        "rank_icir_investable": {"unit": "dimensionless, not annualized", "scope": "discovery", "meaning": "Mean monthly rank IC / monthly rank IC standard deviation."},
        "ic_full": {"unit": "rank correlation coefficient", "scope": "discovery_full_universe"},
        "ic_investable": {"unit": "rank correlation coefficient", "scope": "discovery_investable_universe"},
        "neutral_ic": {"unit": "rank correlation coefficient", "scope": "discovery_neutralized"},
        "oos_ic": {"unit": "rank correlation coefficient", "scope": "fixed_oos_signal_window"},
        "oos_discovery_ic": {"unit": "rank correlation coefficient", "scope": "discovery_reference"},
        "oos_ic_retention": {"unit": "ratio, not percent", "scope": "oos_ic / discovery_ic"},
        "months": {"unit": "months", "scope": "discovery_portfolio_usable_months"},
        "oos_months": {"unit": "months", "scope": "fixed_oos_usable_months"},
        "*_p/*pvalue/*qvalue": {"unit": "probability in [0,1]", "meaning": "Test p-value or adjusted q-value as labeled; exploratory diagnostics are not extra gates."},
        "*_t": {"unit": "test statistic"},
        "*_retention": {"unit": "ratio, not percent"},
        "*_error_rate/missing_return_rate": {"unit": "fraction in [0,1]"},
        "null_*": {"scope": "campaign calibration metadata; not a return period"},
    }
    for key in ("ic_p_full", "ic_p_investable", "neutral_ic_p", "oos_ic_p", "hac_pvalue", "fdr_qvalue", "oos_fdr_qvalue"):
        metric_dictionary[key] = {"unit": "probability in [0,1]", "scope": "fixed_oos" if key.startswith("oos_") else "discovery"}
    for key in ("ic_t_full", "ic_t_investable", "neutral_ic_t", "oos_ic_t", "hac_t"):
        metric_dictionary[key] = {"unit": "test statistic", "scope": "fixed_oos" if key.startswith("oos_") else "discovery"}
    for key in ("ic_retention", "neutral_ic_retention"):
        metric_dictionary[key] = {"unit": "ratio, not percent", "scope": "discovery"}
    for key in ("ic_std_investable", "max_gold_signal_corr", "oos_required_ic"):
        metric_dictionary[key] = {"unit": "correlation coefficient", "scope": "fixed_oos_threshold" if key.startswith("oos_") else "discovery"}
    for key in ("missing_return_rate", "null_family_error_rate", "null_worst_kind_error_rate"):
        metric_dictionary[key] = {"unit": "fraction in [0,1]", "scope": "discovery_portfolio" if key == "missing_return_rate" else "campaign_calibration"}
    for key in ("n_trials", "null_count", "null_discovery_family_size", "null_oos_family_size"):
        metric_dictionary[key] = {"unit": "count", "scope": "campaign_trial_ledger_or_calibration"}
    metric_dictionary["gold_signal_comparison_months"] = {"unit": "months per comparator", "scope": "discovery"}
    result = {
        "schema_version": "private-research-catalog-v1", "as_of": as_of,
        "audience": "PRIVATE_TERMINAL_RESEARCH_REVIEWER_ONLY",
        "counts": {
            "ledger_records": len(ledger), "unique_record_ids": len(unique),
            "released_records": len(records), "withheld_records": sum(withheld.values()),
            "withheld_by_reason": dict(withheld), "reviewed_records": sum(r["review"] is not None for r in records),
            "unreviewed_records": sum(r["review"] is None for r in records),
            "campaigns": len(campaigns), "campaigns_with_released_records": len(released_by_campaign),
            "verdicts": dict(Counter(r["validation"]["verdict"] for r in records)),
            "regime_records": sum(r["regimes"].get("status") in {"AVAILABLE", "PARTIAL"} for r in records),
            "macro_regime_records": sum(bool(r["regimes"].get("macro_views")) for r in records),
        },
        "source": {"ledger": "research/memory/candidate_lessons.jsonl", "ledger_file_sha256": hashlib.sha256(memory_bytes).hexdigest(),
                   "exporter": "scripts/dashboard_exports/export_research_catalog.py", "read_only_research": True,
                   "metric_definition_source": "engine/gate.py:backtest,evaluate"},
        "metric_dictionary": metric_dictionary,
        "limitations": [
            "Pending/unreleased records are counted only; their raw results and evidence packets are not read by this exporter.",
            "Only existing reviewed lessons are published as interpretations. Unreviewed candidates retain their failures, definitions and released numerical evidence.",
            "No fresh evaluation, refresh, database access, OOS reveal or Gold mutation was performed.",
            "Reused historical windows are not independent prospective validation. A PROMOTE verdict does not prove a cause or profitable implementation.",
            "Monthly regime returns are Discovery diagnostic groups reformed monthly, not implemented holdings. All collected states, zero-support states and UNKNOWN are retained.",
            "PIT_ASSUMED inputs remain explicitly assumed; verified policy-rate input and assumed market/macro input are distinct.",
            "Legacy frozen artifact hashes may be absent; existing source identity and exact content-addressed packet rebuild are still checked.",
            "Source paths are repository-relative provenance, not public web links. No private local paths or connection details are exported.",
        ],
        "campaigns": campaign_output, "records": records,
    }
    registry = root / "regime_sources.json"
    if registry.exists():
        from scripts.regime_snapshot import snapshot
        # Source-only preview is not retrofitted to any frozen research record.
        preview = snapshot(registry, as_of=str(as_of)[:10])
        result["regime_input_snapshot"] = {k: v for k, v in preview.items() if k != "contexts"}
        result["regime_input_snapshot"]["contexts"] = [
            {k: v for k, v in context.items() if k != "rows"} for context in preview["contexts"]]
    return safe(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, default=REPO / "output/research-dashboard-source/research-catalog.json")
    args = parser.parse_args()
    result = export(REPO / "research", args.as_of)
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    if re.search(r"/Users/|/home/|\.rds\.amazonaws\.com|postgres(?:ql)?://", encoded):
        raise ValueError("Private locator survived sanitation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    output_path = args.output.resolve()
    output_label = str(output_path.relative_to(REPO)) if output_path.is_relative_to(REPO) else str(output_path)
    print(json.dumps({"output": output_label, "bytes": len(encoded.encode()),
                      "counts": result["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
