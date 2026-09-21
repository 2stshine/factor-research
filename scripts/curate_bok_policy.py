"""Issue a narrow, evidence-bound month-end policy diagnostic input.

Requires exact S3 Bronze and official dated decision documents from
prepare_bok_policy. No general FMP approval, database write or campaign change.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from engine.policy_regime import RULES, monthly_states, reconcile
from engine.regime_inputs import DAY_BOUND, VERSION, digest, read_context, freeze_context, campaign_context
from scripts.prepare_bok_policy import BUCKET, RUN, encode, meeting_links, parse_decision, save, sha
from scripts.fmp_pit_audit import parse_bok_rates


def verify_inputs(root, history_path):
    official_path = root / "official/decisions-v2.json"
    official = json.loads(official_path.read_bytes())
    if official.get("through") != "2026-08-31":
        raise ValueError("Unreviewed calendar cutoff")
    decisions = official["decisions"]
    calendar_dates = []
    evidence = []
    for c in official["calendars"]:
        path = Path(c["path"])
        if sha(path.read_bytes()) != c["sha256"]:
            raise ValueError("Changed official calendar")
        actual = meeting_links(path.read_bytes(), c["year"], official["through"])
        if [x["decision_date"] for x in actual] != c["decision_dates"]:
            raise ValueError("Calendar parsing changed")
        calendar_dates += c["decision_dates"]
        evidence.append({"uri": c["url"], "sha256": c["sha256"], "local_path": str(path.resolve())})
    if sorted(calendar_dates) != [x["decision_date"] for x in decisions]:
        raise ValueError("Incomplete official decision documents")
    for row in decisions:
        path = Path(row["pdf_path"])
        text_path = path.with_suffix(".txt")
        if sha(path.read_bytes()) != row["pdf_sha256"] or sha(text_path.read_bytes()) != row["text_sha256"]:
            raise ValueError("Changed official decision evidence")
        parsed = parse_decision(text_path.read_text(), row["decision_date"])
        if any(row[k] != v for k, v in parsed.items()) or not parsed["document_date_verified"]:
            raise ValueError("Official date/rate extraction mismatch")
        evidence.append({"uri": row["url"], "sha256": row["pdf_sha256"], "local_path": str(path.resolve())})
    # Independent effective-rate table corroborates all changes, including the
    # emergency 2020 announcement whose effective date is the following day.
    history = parse_bok_rates(history_path.read_bytes())
    history_receipt = json.loads(history_path.with_suffix(".html.receipt.json").read_bytes())
    if sha(history_path.read_bytes()) != history_receipt["sha256"]:
        raise ValueError("Rate-history evidence hash mismatch")
    changes = [r for i, r in enumerate(decisions) if i and r["target_rate_pct"] != decisions[i - 1]["target_rate_pct"]]
    used = set()
    for row in changes:
        day = datetime.fromisoformat(row["decision_date"])
        match = [(d, v) for d, v in history if d in {str(day.date()), str((day + timedelta(days=1)).date())}
                 and v == row["target_rate_pct"]]
        if len(match) != 1:
            raise ValueError("Official decision disagrees with independent rate history")
        used.add(match[0])
    expected = {(d, v) for d, v in history if decisions[0]["decision_date"] < d <= official["through"]}
    if used != expected:
        raise ValueError("A historical policy change is not represented by a decision")
    evidence.append({"uri": history_receipt["url"], "sha256": sha(history_path.read_bytes()),
                     "local_path": str(history_path.resolve())})

    bronze_path = root / "bronze_policy.json"
    bronze = json.loads(bronze_path.read_bytes())
    mirror = root / "bronze_mirror"
    def read(uri):
        prefix = f"s3://{BUCKET}/"
        if not uri.startswith(prefix):
            raise ValueError("Wrong S3 bucket")
        path = mirror / uri.removeprefix(prefix)
        body = path.read_bytes()
        receipt = json.loads(path.with_suffix(path.suffix + ".download.json").read_bytes())
        if receipt["s3_uri"] != uri or receipt["sha256"] != sha(body):
            raise ValueError("S3 download receipt mismatch")
        return body
    run = json.loads(read(bronze["run_uri"]))
    if sha(read(bronze["run_uri"])) != bronze["run_sha256"] or run.get("complete") is not True:
        raise ValueError("Bad source run")
    policy, counts = [], Counter()
    for p in run["partitions"]:
        pm_body = read(p["selection_manifest_uri"])
        pm = json.loads(pm_body)
        raw_body, selected_body = read(pm["source_object_uri"]), read(pm["object_uri"])
        rm = json.loads(read(pm["source_object_uri"].rsplit("/", 1)[0] + "/manifest.json"))
        if (sha(raw_body) != pm["source_sha256"] or sha(raw_body) != rm["sha256"]
                or sha(selected_body) != pm["sha256"] or rm["received_at"] != pm["received_at"]
                or rm["status_code"] != 200 or pm["complete"] is not True):
            raise ValueError("Broken source manifest binding")
        raw, selected = json.loads(raw_body), json.loads(selected_body)
        if len(selected) != p["selected_row_count"]:
            raise ValueError("Partition row count changed")
        for x in selected:
            if raw[x["source_row_index"]] != x["payload"]:
                raise ValueError("Changed source row")
            counts[x["series_id"]] += 1
            if x["series_id"] == "KR_POLICY_RATE":
                policy.append({**x, "raw_uri": pm["source_object_uri"], "raw_sha256": pm["source_sha256"],
                    "received_at": rm["received_at"], "selection_sha256": pm["sha256"]})
    if counts != run["rows_by_series"] or sum(counts.values()) != run["selected_row_count"] or policy != bronze["policy_rows"]:
        raise ValueError("Derived policy evidence does not reproduce exact S3 source")
    evidence += [{"uri": str(p.resolve()), "sha256": sha(p.read_bytes())} for p in (official_path, bronze_path)]
    evidence.append({"uri": bronze["run_uri"], "sha256": bronze["run_sha256"]})
    return decisions, policy, evidence, {"official_decisions": len(decisions), "rate_changes_corroborated": len(changes),
        "s3_partitions_verified": len(run["partitions"]), "s3_selected_rows_verified": sum(counts.values())}


def build(root, history_path, reviewer):
    out = root / "silver"
    if out.exists():
        raise FileExistsError("Use a new version; curated Silver is immutable")
    decisions, policy, evidence, checks = verify_inputs(root, history_path)
    resolved = reconcile(decisions, policy)
    rows = monthly_states(decisions)
    source = {"context_id": "KR_POLICY_DIRECTION_3M", "source_id": "bok-fmp-announced-target-monthend-201501-202608-v1",
        "kind": "macro_state", "macro_type": "policy_rate", "frequency": "MONTH_END",
        "value_semantics": "ANNOUNCED_POLICY_TARGET", "known_at_semantics": DAY_BOUND,
        "states": ["TIGHTENING", "UNCHANGED", "EASING"], "classification_rules": RULES,
        "storage_layer": "SILVER", "storage_mode": "LOCAL_IMMUTABLE_ARTIFACT_NOT_RDS",
        "source_precedence": "Official dated decision values/dates; every 2015+ FMP actual independently agrees. 2014 warm-up from BOK only.",
        "scope": {"start_month": "2015-01", "end_month": "2026-08", "intraday_allowed": False,
                  "factor_feature_allowed": False, "raw_fmp_timestamp_approved": False,
                  "estimate_previous_fields_approved": False}, "rows": rows}
    checks.update(fmp_rows=len(policy), reconciled_decisions=len(resolved),
        duplicate_excess_resolved=sum(x["duplicate_excess"] for x in resolved),
        provider_calendar_dates_corrected=sum(x["provider_calendar_dates_corrected"] for x in resolved),
        monthly_rows=len(rows), monthly_states=dict(Counter(x["state"] for x in rows)),
        official_values_match_all_fmp_actual=True, exact_s3_snapshot_verified=True,
        policy_value_revision_basis="Dated official decision targets, not present-day statistical estimates",
        availability_basis=DAY_BOUND, bronze_mutated=False, rds_written=False, campaign_modified=False,
        monthly_classification_rule_sha256=digest(RULES), compiler_sha256=sha(Path(__file__).read_bytes()))
    save(out / "resolved_decisions.json", encode(resolved))
    save(out / "checks.json", encode(checks))
    evidence += [{"uri": str(p.resolve()), "sha256": sha(p.read_bytes())}
                 for p in (out / "resolved_decisions.json", out / "checks.json")]
    approval = {"schema_version": "pit-regime-approval-v2", "status": "APPROVED", "source_layer": "SILVER",
        "purpose": "DIAGNOSTIC_ONLY", "source_id": source["source_id"], "source_sha256": digest(source),
        "pit_approved": True, "historical_backtest_allowed": True,
        "publication_date_verified": True, "historical_availability_verified": True,
        "publication_time_verified": False, "revision_history_verified": True,
        "revision_basis": "DATED_OFFICIAL_POLICY_DECISIONS", "availability_basis": DAY_BOUND,
        "intraday_allowed": False, "factor_feature_allowed": False, "reviewer": reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(), "evidence": evidence,
        "scope": source["scope"], "limitations": [
            "Approval only covers the reconciled announced policy target and fixed month-end diagnostic state.",
            "Exact publication clock is not certified; Korean publication-day end is a conservative knowledge bound.",
            "Official dated policy decisions are reviewed as historical records; cryptographic evidence captured in 2015 is not claimed.",
            "Does not approve raw FMP dates, previous/estimate fields, all other macro series, intraday trading or current production use.",
            "Latest complete approved month is 2026-08; future months require fresh official decision and FMP reconciliation.",
            "Local Silver artifact, not RDS Silver ingestion or an external assurance opinion."]}
    save(out / "approval.json", encode(approval))
    save(out / "context.json", encode({"schema_version": VERSION, "contexts": [{"source": source,
        "approval_file": "approval.json", "approval_sha256": sha((out / "approval.json").read_bytes())}]}))
    # Exercise the real adapter, without creating or reading an actual campaign.
    parsed = read_context(out / "context.json")
    frozen = freeze_context(parsed, data_cutoff="2026-09-20", oos_start="2026-10")
    market, macro, provenance = campaign_context({"diagnostic_regimes": frozen,
        "discovery": {"data_cutoff": "2026-09-20"}, "oos": {"start": "2026-10"}})
    if market is not None or len(macro[source["context_id"]]["rows"]) != len(rows):
        raise ValueError("Real adapter did not preserve approved diagnostic input")
    save(out / "wiring_check.json", encode({"mode": "STANDALONE_INPUT_VALIDATION_NO_CAMPAIGN_CREATED",
        "macro_rows_received": len(rows), "last_signal_month": provenance["last_signal_month"],
        "market_index_available": False, "factor_returns_evaluated": False, "provenance": provenance}))
    print(json.dumps(checks, ensure_ascii=False))
    print("CONTEXT", (out / "context.json").resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--rate-history", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    build(args.input, args.rate_history, args.reviewer)
