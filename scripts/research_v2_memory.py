"""Audited retrieval/usage for reviewed v2 lessons; legacy memory is never read."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from engine.research_memory_v2 import MemoryCapability, MemoryStore, canonical
from engine.research_v2_release import NAMESPACE, load_bundle, public_filter
from engine.research_memory_transfer import (activate_production_release, approve_transfer, load_active_memory,
    prepare_campaign_context, record_campaign_usage, require_campaign_memory_usage,
    transfer_template, validate_transfer_proposal, write_artifact)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["retrieve", "usage", "transfer-template", "transfer-propose",
        "transfer-review", "campaign-context", "campaign-usage", "campaign-check", "activate-production"])
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--key")
    parser.add_argument("--case")
    parser.add_argument("--query")
    parser.add_argument("--research-as-of")
    parser.add_argument("--usage-file", type=Path)
    parser.add_argument("--pointer", type=Path, default=Path("research/v2/active-memory.json"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--target-scope", type=Path)
    parser.add_argument("--source-revision")
    parser.add_argument("--author")
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--critic", type=Path)
    parser.add_argument("--transfer-approval", type=Path, action="append", default=[])
    parser.add_argument("--context", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command not in {"retrieve", "usage"}:
        def read(path, label):
            if path is None:
                parser.error(f"{label} is required")
            return json.loads(path.read_text())
        if args.command == "activate-production":
            if args.release_root is None:
                parser.error("--release-root is required")
            value = activate_production_release(args.pointer, args.release_root, repo_root=args.repo_root)
        elif args.command.startswith("transfer-"):
            active = load_active_memory(args.pointer, repo_root=args.repo_root)
            if args.command == "transfer-template":
                if not args.source_revision or not args.author:
                    parser.error("--source-revision and --author are required")
                value = transfer_template(active, args.source_revision, read(args.target_scope, "--target-scope"), author=args.author)
            elif args.command == "transfer-propose":
                value = read(args.proposal, "--proposal")
                validate_transfer_proposal(active, value)
            else:
                value = approve_transfer(active, read(args.proposal, "--proposal"), read(args.critic, "--critic"))
        else:
            if not args.task_id:
                parser.error("--task-id is required")
            if args.command == "campaign-context":
                if not args.query or not args.research_as_of:
                    parser.error("--query and explicit --research-as-of are required")
                value = prepare_campaign_context(args.pointer, repo_root=args.repo_root,
                    target_scope=read(args.target_scope, "--target-scope"), task_id=args.task_id,
                    query=args.query, research_as_of=args.research_as_of, transfer_approvals=args.transfer_approval)
            elif args.command == "campaign-usage":
                if not args.key:
                    parser.error("--key is required")
                decisions = read(args.usage_file, "--usage-file")
                if set(decisions) != {"used", "rejected"}:
                    parser.error("Campaign usage schema must contain exactly used and rejected maps")
                value = record_campaign_usage(args.pointer, read(args.context, "--context"), **decisions,
                    actor=args.task_id, key=args.key, repo_root=args.repo_root)
            else:
                value = require_campaign_memory_usage(args.pointer, read(args.context, "--context"),
                    expected_scope=read(args.target_scope, "--target-scope"), task_id=args.task_id, repo_root=args.repo_root)
        if args.output:
            write_artifact(args.output, value)
        print(canonical(value))
        return
    if args.database is None or args.release_root is None or not args.task_id or not args.key:
        parser.error("--release-root, --database, --task-id and --key are required for source retrieval/usage")
    if not args.database.is_file():
        raise SystemExit("An activated v2 database is required; no implicit empty store")
    memory = MemoryStore(args.database, namespace=NAMESPACE, public_filter=public_filter(args.release_root))
    if args.command == "retrieve":
        bundle = load_bundle(args.release_root)
        if args.case not in bundle["cases"] or not args.query:
            raise SystemExit("Exact historical source-case scope and nonempty query required")
        accepted = json.loads((args.release_root / "accepted" / f"{args.case}.json").read_text())
        scope = accepted["envelope"]["scope"]
        now = datetime.now(timezone.utc)
        capability = MemoryCapability(capability_id=args.task_id, namespace=NAMESPACE, scope=scope,
            allowed_evidence_ids=(accepted["envelope"]["evidence_id"],), expires_at=(now + timedelta(minutes=5)).isoformat())
        value = memory.retrieve(args.query, scope=scope, research_as_of=args.research_as_of or now.isoformat(),
            capability=capability, task_id=args.task_id, key=args.key)
    else:
        if args.usage_file is None:
            raise SystemExit("Explicit used/rejected decisions are required")
        decisions = json.loads(args.usage_file.read_text())
        if set(decisions) != {"receipt_id", "used", "rejected"}:
            raise SystemExit("Unexpected usage schema")
        value = memory.record_usage(**decisions, actor=args.task_id, key=args.key)
    print(canonical(value))


if __name__ == "__main__":
    main()
