"""Export provenance-backed Gold discovery order without database access.

Run from any directory:
  .venv/bin/python scripts/dashboard_exports/export_discovery_order.py
  .venv/bin/python scripts/dashboard_exports/export_discovery_order.py --check

Only existing catalog data, outcome-free trial identities, history identities,
epoch registration metadata and static Gold membership caches are projected.
No result/report, confirmation, lesson-evidence, signal-value or DB reads occur.
Approval dates, investment periods, Git dates and filesystem times are never
substituted for a missing research registration timestamp.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
GOLD = "output/research-dashboard-source/gold-catalog.json"
RESEARCH = "output/research-dashboard-source/research-catalog.json"
INDEX = "research/memory/factor_index.json"
HISTORY = "research/history.jsonl"
OUTPUT = "output/research-dashboard-source/discovery-order.json"
KST = ZoneInfo("Asia/Seoul")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def instant(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("A registration timestamp must include its timezone")
    return result.astimezone(timezone.utc)


def order_key(row: dict):
    return (
        row["discovered_at"] is None,
        instant(row["discovered_at"]) if row["discovered_at"] else datetime.max.replace(tzinfo=timezone.utc),
        row["discovery_sequence"] if row["discovery_sequence"] is not None else float("inf"),
        row["name"],
    )


def build_catalog(root: Path = ROOT) -> dict:
    gold = read_json(root / GOLD)
    research_names = {row["factor_name"] for row in read_json(root / RESEARCH)["records"]}
    trials = read_json(root / INDEX)["trials"]
    # Immediately project audit metadata; never propagate the history metrics.
    history = {}
    for line, text in enumerate((root / HISTORY).read_text(encoding="utf-8").splitlines(), 1):
        if not text.strip():
            continue
        row = json.loads(text)
        key = (row.get("factor"), row.get("cycle_id"))
        projected = {key: row.get(key) for key in ("factor", "cycle_id", "campaign_id", "epoch_id", "definition_hash")}
        projected["line"] = line
        if key in history and history[key] != projected:
            raise ValueError(f"Duplicate research history identity: {key}")
        history[key] = projected

    caches = []
    for path in sorted((root / ".cache/gold-signals").glob("*/manifest.json")):
        generation = read_json(path).get("generation", {})
        caches.append((generation.get("approved_factor_count", 0), str(path.relative_to(root)), set(generation.get("approved_factor_keys", []))))
    caches.sort(key=lambda row: (row[0], row[1]))

    factors = []
    for factor in gold["factors"]:
        name = factor["name"]
        observations = []
        for trial in (row for row in trials if row.get("factor") == name):
            cycle = trial["cycle_id"]
            record = history.get((name, cycle))
            if not record or not record.get("campaign_id") or not record.get("epoch_id"):
                continue
            campaign, epoch = record["campaign_id"], record["epoch_id"]
            if any(not re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in (campaign, epoch)):
                raise ValueError(f"Invalid research identity for {name}")
            source = f"research/campaigns/{campaign}/epochs/{epoch}/manifest.json"
            manifest = read_json(root / source)
            candidates = [row for row in manifest.get("candidates", []) if row.get("name") == name and row.get("cycle_id") == cycle]
            if len(candidates) != 1 or candidates[0].get("definition_hash") != trial.get("definition_hash") or record.get("definition_hash") != trial.get("definition_hash"):
                raise ValueError(f"Research identity/definition mismatch: {name}/{cycle}")
            match = re.fullmatch(r"cycle-(\d+)-.+", cycle)
            if not match:
                raise ValueError(f"Invalid cycle sequence: {cycle}")
            observed_at = manifest["created_at"]
            instant(observed_at)
            observations.append({
                "at": observed_at, "sequence": int(match[1]), "cycle": cycle,
                "campaign": campaign, "epoch": epoch, "hash": trial["definition_hash"],
                "refs": [f"{source}#/created_at", f"{source}#/candidates[name={name}]", f"{HISTORY}:{record['line']}", f"{INDEX}#/trials[cycle_id={cycle}]"],
            })
        observations.sort(key=lambda row: (instant(row["at"]), row["sequence"]))
        matching = next((row for row in observations if row["hash"] == factor.get("definition_hash")), None)
        row = {"name": name, "discovered_at": None, "discovery_date": None, "date_precision": "unknown", "discovery_sequence": None}
        if matching:
            row.update({
                "discovered_at": matching["at"],
                "discovery_date": instant(matching["at"]).astimezone(KST).date().isoformat(),
                "date_precision": "timestamp", "basis": "FIRST_OBSERVED_RESEARCH_EPOCH_CREATED_AT",
                "discovery_sequence": matching["sequence"], "cycle_id": matching["cycle"],
                "campaign_id": matching["campaign"], "epoch_id": matching["epoch"],
                "definition_hash": matching["hash"],
                "definition_binding": "CATALOG_AND_RESEARCH_DEFINITION_HASH_MATCH",
                "source_refs": matching["refs"] + ([f"{RESEARCH}#/records[factor_name={name}]"] if name in research_names else []),
            })
        elif observations:
            first = observations[0]
            row.update({
                "basis": "EARLIER_SAME_NAME_RESEARCH_HAS_DIFFERENT_DEFINITION_HASH",
                "definition_hash": factor.get("definition_hash"),
                "definition_binding": "SAME_NAME_ONLY_DEFINITION_MISMATCH",
                "observed_name_first_registered_at": first["at"],
                "observed_name_sequence": first["sequence"],
                "observed_name_definition_hash": first["hash"],
                "source_refs": [f"{GOLD}#/factors[name={name}]"] + first["refs"],
                "limitation": "The historical factor-name registration is not established as the discovery date of the currently cataloged definition.",
            })
        else:
            membership = next((path for _, path, names in caches if name in names), None)
            row.update({
                "basis": "NO_DISCOVERY_OR_CREATION_TIMESTAMP_IN_AVAILABLE_LOCAL_METADATA",
                "definition_binding": "NO_LOCAL_RESEARCH_TRIAL",
                "source_refs": [f"{GOLD}#/factors[name={name}]"] + ([f"{membership}#/generation/approved_factor_keys"] if membership else []),
                "limitation": "Gold membership is observed; available cache manifests contain no discovery, creation, or registration timestamp. Cache file mtime and approval observation time are not discovery dates.",
            })
        factors.append(row)

    factors.sort(key=order_key)
    payload = {
        "schema_version": "gold-discovery-order-v1", "as_of": gold["as_of"],
        "catalog_source": GOLD, "exporter": "scripts/dashboard_exports/export_discovery_order.py",
        "scope": "Historically approved factors in the existing local Gold catalog; no DB query or research evaluation.",
        "date_semantics": "discovered_at is the earliest observed research epoch registration timestamp bound to the factor and catalog definition, not the moment an idea was conceived, evaluation completion, or Gold approval. discovery_date renders that timestamp in Asia/Seoul.",
        "date_timezone": "Asia/Seoul",
        "sequence_semantics": "discovery_sequence is the observed numeric research cycle index; it preserves research execution order for identical registration timestamps.",
        "sort_rule": ["Known discovered_at ascending", "Identical timestamps: discovery_sequence ascending", "Missing discovered_at last", "Remaining ties: name ascending; alphabetical tie-break does not imply chronology"],
        "coverage": {
            "total": len(factors),
            "known_definition_bound_registration_timestamp": sum(row["discovered_at"] is not None for row in factors),
            "unknown": sum(row["discovered_at"] is None for row in factors),
            "unknown_no_local_research_trial": sum(row["definition_binding"] == "NO_LOCAL_RESEARCH_TRIAL" for row in factors),
            "unknown_historical_definition_mismatch": sum(row["definition_binding"] == "SAME_NAME_ONLY_DEFINITION_MISMATCH" for row in factors),
            "released_research_catalog_matches": sum(row["name"] in research_names for row in factors),
        },
        "limitations": [
            "Registration timestamps can be shared by a batch; sequence records execution order, not separate idea-creation times.",
            "The earliest retained research record is not proof that no earlier unrecorded research existed.",
            "Git addition dates describe source versioning and can precede or follow registration; they are not substituted for Discovery.",
            "Factors without matching local research trials remain unknown; available static Gold caches record membership, not dates.",
            "Same-name records with different definition hashes are retained separately and never fill the catalog-definition discovery date.",
            "Approval timestamps remain separate and never fill discovery date.",
        ],
        "method_source": "engine/epochs.py:start_epoch freezes candidate names and definition hashes alongside created_at.",
        "factors": factors,
    }
    validate(payload, gold)
    return payload


def validate(payload: dict, gold: dict) -> None:
    factors = payload["factors"]
    names = [row["name"] for row in factors]
    if len(names) != len(set(names)) or sorted(names) != sorted(row["name"] for row in gold["factors"]):
        raise ValueError("Discovery names must match the Gold catalog exactly once")
    if factors != sorted(factors, key=order_key):
        raise ValueError("Discovery order is inconsistent")
    for row in factors:
        if row["discovered_at"] is None:
            if row["discovery_date"] is not None or row["discovery_sequence"] is not None:
                raise ValueError("Unknown discovery must not carry a sortable date or sequence")
        elif row["definition_binding"] != "CATALOG_AND_RESEARCH_DEFINITION_HASH_MATCH" or row["discovery_sequence"] is None:
            raise ValueError("Known discovery requires an exact definition binding and cycle sequence")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / OUTPUT)
    parser.add_argument("--check", action="store_true", help="Verify the existing artifact matches current source metadata without writing")
    args = parser.parse_args()
    payload = build_catalog()
    if args.check:
        if read_json(args.output) != payload:
            raise SystemExit("Discovery artifact differs from current metadata; regenerate it")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "CHECKED" if args.check else "EXPORTED", "output": str(args.output), "coverage": payload["coverage"]}))


if __name__ == "__main__":
    main()
