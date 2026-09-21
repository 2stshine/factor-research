"""Plan, prepare, critique and save an agent review; no automatic LLM calls.

python -m scripts.lesson_review plan --output plan.json
python -m scripts.lesson_review prepare --record CAMPAIGN/EPOCH/FACTOR --output review.json
python -m scripts.lesson_review critique --input review.json --output critique.json
python -m scripts.lesson_review save --input review.json --critic critique.json
Evidence commands recheck current release state; plan reads no results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.lesson_evidence import digest, review_template, validate_review
from engine.scientist_review import (
    ANALYST_PROMPT, CRITIC_PROMPT, augment_template, critique_template, plan_template,
)
from scripts.candidate_lessons import evidence_packet_path, refresh_candidate_lessons
from scripts.lessons import _atomic_write_text, read_jsonl


def current_evidence(root: Path, record_id: str):
    rows = refresh_candidate_lessons(root)
    record = next((r for r in rows if r["record_id"] == record_id), None)
    if record is None or record["visibility"] != "RELEASED_QUALITATIVE":
        raise ValueError("No currently released evidence for this record")
    packet = json.loads(evidence_packet_path(root, record["evidence_packet"]["sha256"]).read_text(encoding="utf-8"))
    if digest(packet) != record["evidence_packet"]["sha256"]:
        raise ValueError("Evidence packet hash mismatch")
    return record, packet


def save_review(root: Path, review: dict):
    record, packet = current_evidence(root, review["record_id"])
    validate_review(review, record, packet)
    target = root / "memory/candidate_lessons.jsonl"
    # Retain every accepted review version, including later superseded reviews.
    archive = root / "memory/lesson_reviews" / f"{digest(review)}.json"
    if archive.exists():
        if digest(json.loads(archive.read_text(encoding="utf-8"))) != digest(review):
            raise ValueError("Archived review hash mismatch")
    else:
        _atomic_write_text(archive, json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    rows = read_jsonl(target)
    for row in rows:
        if row["record_id"] == review["record_id"]:
            row["review"] = review
            row["review_validation"] = "CURRENT"
    _atomic_write_text(target, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))
    # Existing batch/context refresh calls this same generation path.
    from scripts.knowledge import refresh_knowledge
    if (root / "KNOWLEDGE.md").exists():
        refresh_knowledge(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("research"))
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Create a preregistration template without reading results")
    plan.add_argument("--output", type=Path, required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--record", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--scientist", action="store_true", help="Use analyst/critic review also for legacy aggregate evidence")
    save = commands.add_parser("save")
    save.add_argument("--input", type=Path, required=True)
    save.add_argument("--critic", type=Path, help="Accepted critique bound to this exact draft")
    critique = commands.add_parser("critique")
    critique.add_argument("--input", type=Path, required=True)
    critique.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(plan_template(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print("Complete this and add it as RESEARCH_SPEC['mechanism_plan'] before registration.")
    elif args.command == "prepare":
        record, packet = current_evidence(args.root, args.record)
        template = review_template(record, packet)
        if args.scientist:
            template = augment_template(template)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(template, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print("Reviewer-only evidence:", record["evidence_packet"]["path"])
        print("Review draft:", args.output)
        charts = packet["diagnostics"].get("charts", {})
        if charts.get("status") == "AVAILABLE":
            directory = args.output.parent / (args.output.stem + "_figures")
            directory.mkdir(exist_ok=False)
            for chart in charts["data"]:
                with (directory / (chart["id"] + ".svg")).open("x", encoding="utf-8") as handle:
                    handle.write(chart["svg"])
            print("Reviewer-only figures:", directory)
        if "scientist_version" in template:
            print(ANALYST_PROMPT)
    elif args.command == "critique":
        draft = json.loads(args.input.read_text(encoding="utf-8"))
        record, packet = current_evidence(args.root, draft["record_id"])
        validate_review(draft, record, packet, require_critic=False)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(critique_template(draft, packet), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(CRITIC_PROMPT)
        print("Reviewer-only evidence:", record["evidence_packet"]["path"])
    else:
        review = json.loads(args.input.read_text(encoding="utf-8"))
        if args.critic:
            review["critic"] = json.loads(args.critic.read_text(encoding="utf-8"))
        save_review(args.root, review)
        print("Review validated and saved; existing KNOWLEDGE refreshed if present.")


if __name__ == "__main__":
    main()
