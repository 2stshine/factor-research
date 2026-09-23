"""Stage and save human/agent-written lesson reviews without research reruns.

prepare --records allowlist.json --output-dir NEW_DIRECTORY
save --manifest NEW_DIRECTORY/manifest.json --submissions submissions.json

An allowlist is {"record_ids": ["campaign/epoch/factor", ...]}. Submissions are
{"items": [{"record_id": "...", "review_path": "analyst.json",
"critic_path": "critic.json", "analyst_agent_id": "...", "critic_agent_id": "..."}]}.
Paths are relative to the submissions file. Submit a subset for a small batch.
Each JSON must be independently authored after reading its exact packet. This
module generates empty templates only, never findings, ACCEPTs, or model calls.

One writer and one normal release-authentication refresh per invocation. The
refresh itself may regenerate factual records/packets even when later review
validation fails, but no reviews are adopted before ALL submissions validate.
The existing exporter alone reads raw results/confirmation for authentication.
This module reads only released packets; source files are stat-fingerprinted.

flock serializes batch writers. Fingerprints detect intervening non-cooperating
writers; do not concurrently run legacy save/research/context commands. A crash
can leave a recovery journal: fail closed and inspect it, never auto-approve.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from engine.lesson_evidence import digest, review_template, validate_review
from engine.scientist_review import augment_template
from scripts.candidate_lessons import evidence_packet_path, refresh_candidate_lessons
from scripts.lessons import _atomic_write_text, read_jsonl

VERSION = "lesson-review-batch-v1"


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _source_fingerprint(root):
    """Metadata only: never inspect raw result/OOS content outside exporter."""
    paths = set()
    for name in ("campaigns", "runs", "oos-exposures"):
        paths.update(p for p in (root / name).rglob("*") if p.is_file())
    paths.update(p for p in root.glob("*") if p.is_file() and p.suffix in {".json", ".jsonl"})
    paths.update(p for p in (root.parent / "factors").rglob("*.py") if p.is_file())
    paths.update(p for p in (root / "memory").glob("literature.json") if p.is_file())
    result = {}
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError("Symlinked research source is not supported by batch review")
        stat = path.stat()
        result[str(path.relative_to(root.parent))] = [
            stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns,
        ]
    return result


@contextmanager
def _writer(root):
    memory = root / "memory"
    memory.mkdir(parents=True, exist_ok=True)
    with (memory / ".lesson_review_batch.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another batch review writer is active") from exc
        try:
            if (memory / ".lesson_review_batch_transaction.json").exists():
                raise ValueError("Unfinished batch transaction: inspect recovery journal first")
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _ids(values):
    if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x for x in values):
        raise ValueError("Provide a nonempty explicit record allowlist")
    if len(set(values)) != len(values):
        raise ValueError("Duplicate record identity")
    return sorted(values)


def _authenticated(root):
    before = _source_fingerprint(root)
    records = refresh_candidate_lessons(root)
    if before != _source_fingerprint(root):
        raise ValueError("Research inputs changed during authentication")
    ids = [r["record_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate authenticated record identity")
    return {r["record_id"]: r for r in records}, before


def _released_packet(root, record):
    if record.get("visibility") != "RELEASED_QUALITATIVE":
        raise ValueError("Record is not currently released")
    path = evidence_packet_path(root, record["evidence_packet"]["sha256"])
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("Packet must be a local content-addressed file")
    raw = path.read_bytes()
    packet = json.loads(raw)
    if digest(packet) != record["evidence_packet"]["sha256"] or packet.get("record_id") != record["record_id"]:
        raise ValueError("Released packet hash/record mismatch")
    return packet, path, hashlib.sha256(raw).hexdigest()


def _already_reviewed(record):
    # Never replace even a stale historical REVIEWED object through this backlog tool.
    return record.get("review", {}).get("status") == "REVIEWED"


def prepare_batch(root, record_ids, output_dir):
    root, output_dir = Path(root).resolve(), Path(output_dir).resolve()
    requested = _ids(record_ids)
    if output_dir.exists() or output_dir.is_relative_to(root):
        raise ValueError("Use a new output directory outside the research root")
    with _writer(root):
        current, sources = _authenticated(root)
        entries, templates, watched = [], [], {}
        ledger = root / "memory/candidate_lessons.jsonl"
        watched[ledger] = _sha(ledger)
        for index, rid in enumerate(requested, 1):
            record = current.get(rid)
            if record is None or _already_reviewed(record):
                raise ValueError(f"Record unavailable/already reviewed: {rid}")
            packet, path, file_sha = _released_packet(root, record)
            watched[path] = file_sha
            filename = f"{index:04d}.analyst-template.json"
            entries.append({"record_id": rid, "packet_sha256": digest(packet),
                            "packet_path": str(path.relative_to(root)),
                            "review_basis": record["review_basis"], "template_path": filename})
            templates.append(augment_template(review_template(record, packet)))
        manifest = {"version": VERSION, "research_root": str(root), "entries": entries,
                    "source_fingerprint": sources, "prepared_ledger_sha256": watched[ledger]}
        manifest["manifest_sha256"] = digest(manifest)
        _check_guard(root, sources, watched)
        output_dir.mkdir(parents=True, exist_ok=False)
        # Manifest is the ready marker, written only after all templates exist.
        for entry, template in zip(entries, templates):
            with (output_dir / entry["template_path"]).open("x", encoding="utf-8") as handle:
                handle.write(_json(template))
        with (output_dir / "manifest.json").open("x", encoding="utf-8") as handle:
            handle.write(_json(manifest))
        return manifest


def _check_guard(root, sources, watched):
    if sources != _source_fingerprint(root) or any(_sha(p) != sha for p, sha in watched.items()):
        raise ValueError("Inputs changed before commit; no reviews adopted")


def _commit(root, mutable, immutable, guard):
    """Stage complete files, rollback ordinary I/O failures; journal crashes.

    Ledger is replaced last and is the adoption commit point. All new archives
    are create-only hard links. Existing immutable archives are never rewritten.
    A process crash is not a multi-file atomic commit: the journal deliberately
    blocks further batches until recovery, rather than pretending success.
    """
    memory = root / "memory"
    journal = memory / ".lesson_review_batch_transaction.json"
    stage = Path(tempfile.mkdtemp(prefix=".lesson-review-", dir=memory))
    backups, replaced, created = {}, [], []
    planned = []
    journal_created = False
    try:
        for index, (path, text) in enumerate([*immutable.items(), *mutable.items()]):
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Refuse symlinked review output")
            staged = stage / f"{index}.new"
            _atomic_write_text(staged, text)
            if path.exists():
                staged.chmod(stat.S_IMODE(path.stat().st_mode))
            if path in mutable:
                backup = stage / f"{index}.before"
                if path.exists():
                    backup.write_bytes(path.read_bytes())
                    backup.chmod(stat.S_IMODE(path.stat().st_mode))
                    backups[path] = backup
                else:
                    backups[path] = None
            planned.append((path, staged, path in immutable))
        guard({})
        _atomic_write_text(journal, _json({"version": VERSION, "stage": str(stage),
            "mutable": [{"path": str(p), "backup": str(b) if b else None} for p, b in backups.items()],
            "immutable": [str(p) for p in immutable], "state": "PREPARED"}))
        journal_created = True
        for path, staged, is_immutable in planned:
            if is_immutable:
                os.link(staged, path)  # Fails if another process created the name.
                created.append(path)
        written = {}
        guard(written)  # Recheck after staging/archiving, immediately before adoption.
        for path, staged, is_immutable in planned:
            if not is_immutable:
                guard(written)
                os.replace(staged, path)
                replaced.append(path)
                written[path] = hashlib.sha256(mutable[path].encode()).hexdigest()
        guard(written)
        journal.unlink()
        journal_created = False
    except BaseException:
        # Do not delete/overwrite a third party's new value on rollback.
        try:
            for path in reversed(replaced):
                expected = hashlib.sha256(mutable[path].encode()).hexdigest()
                if _sha(path) != expected:
                    raise RuntimeError("Concurrent output change during rollback; inspect recovery journal")
                if backups[path] is None:
                    path.unlink()
                else:
                    os.replace(backups[path], path)
            for path in reversed(created):
                if _sha(path) != hashlib.sha256(immutable[path].encode()).hexdigest():
                    raise RuntimeError("Concurrent archive change during rollback; inspect recovery journal")
                path.unlink()
            if journal_created:
                journal.unlink()
                journal_created = False
        except BaseException:
            # Keep journal + backups if recovery itself failed.
            raise
        raise
    finally:
        if not journal_created:
            for path in stage.iterdir():
                path.unlink()
            stage.rmdir()


def save_batch(root, manifest_path, submissions_path):
    root = Path(root).resolve()
    manifest_path, submissions_path = Path(manifest_path).resolve(), Path(submissions_path).resolve()
    if any(path.is_relative_to(root) for path in (manifest_path, submissions_path)):
        raise ValueError("Batch manifests/submissions must stay outside raw research storage")
    with _writer(root):
        watched = {p: _sha(p) for p in (manifest_path, submissions_path)}
        manifest, submissions = _read(manifest_path), _read(submissions_path)
        unsigned = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
        if (manifest.get("version") != VERSION or manifest.get("research_root") != str(root)
                or manifest.get("manifest_sha256") != digest(unsigned)):
            raise ValueError("Invalid batch manifest identity/hash")
        _ids([e["record_id"] for e in manifest["entries"]])
        allowed = {e["record_id"]: e for e in manifest["entries"]}
        items = submissions.get("items")
        if not isinstance(items, list):
            raise ValueError("Submissions require items")
        _ids([item["record_id"] for item in items])
        if not set(item["record_id"] for item in items).issubset(allowed):
            raise ValueError("Submission outside prepared allowlist")
        if manifest["source_fingerprint"] != _source_fingerprint(root):
            raise ValueError("Research inputs changed since preparation; prepare again")
        current, sources = _authenticated(root)
        if sources != manifest["source_fingerprint"]:
            raise ValueError("Research inputs changed since preparation")
        ledger = root / "memory/candidate_lessons.jsonl"
        watched[ledger] = _sha(ledger)
        all_rows = read_jsonl(ledger)
        if len({r["record_id"] for r in all_rows}) != len(all_rows):
            raise ValueError("Duplicate ledger identity")
        ledger_by_id = {r["record_id"]: r for r in all_rows}
        reviews, receipt_items, immutable = {}, [], {}
        for item in sorted(items, key=lambda x: x["record_id"]):
            rid, entry = item["record_id"], allowed[item["record_id"]]
            record = current.get(rid)
            if record is None or _already_reviewed(record):
                raise ValueError(f"Record unavailable/already reviewed: {rid}")
            if ledger_by_id.get(rid) != record:
                raise ValueError("Authenticated record/ledger mismatch")
            packet, packet_path, file_sha = _released_packet(root, record)
            watched[packet_path] = file_sha
            if (record["review_basis"] != entry["review_basis"] or digest(packet) != entry["packet_sha256"]
                    or entry["packet_path"] != str(packet_path.relative_to(root))):
                raise ValueError("Prepared packet/basis changed")
            analyst, critic_agent = item.get("analyst_agent_id"), item.get("critic_agent_id")
            if not all(isinstance(x, str) and x.strip() for x in (analyst, critic_agent)) or analyst == critic_agent:
                raise ValueError("Separate actual analyst and critic agent identities are required")
            paths = [(submissions_path.parent / item[key]).resolve() for key in ("review_path", "critic_path")]
            if any(path.is_relative_to(root) for path in paths):
                raise ValueError("Submitted drafts/critics must not point into raw research storage")
            if paths[0] == paths[1]:
                raise ValueError("Separate analyst and critic JSON files are required")
            for path in paths:
                watched[path] = _sha(path)
            review, critic = _read(paths[0]), _read(paths[1])
            if "critic" in review or review.get("record_id") != rid or "scientist_version" not in review:
                raise ValueError("Provide an individual scientist analysis and separate critique")
            review = {**review, "critic": critic}
            validate_review(review, record, packet)  # Includes exact independent-critic hash binding.
            sha = digest(review)
            archive = root / "memory/lesson_reviews" / f"{sha}.json"
            if archive.is_symlink() or not archive.resolve().is_relative_to(root):
                raise ValueError("Refuse symlinked review archive")
            if archive.exists():
                watched[archive] = _sha(archive)
                if digest(_read(archive)) != sha:
                    raise ValueError("Archived review hash mismatch")
            else:
                immutable[archive] = _json(review)
            reviews[rid] = review
            receipt_items.append({"record_id": rid, "review_sha256": sha,
                                  "packet_sha256": digest(packet), "analyst_agent_id": analyst,
                                  "critic_agent_id": critic_agent})
        updated = deepcopy(all_rows)
        for row in updated:
            if row["record_id"] in reviews:
                row.update(review=reviews[row["record_id"]], review_validation="CURRENT")
        updated_by_id = {r["record_id"]: r for r in updated}
        # Only freshly authenticated records reach candidate-facing KNOWLEDGE.
        released_rows = [updated_by_id[rid] for rid in current]
        mutable = {}
        knowledge = root / "KNOWLEDGE.md"
        if knowledge.exists():
            from scripts.knowledge import _knowledge_parts, _render_knowledge
            from scripts.factor_memory import INDEX_FILE, _json as index_json, _sources
            index_path = root / INDEX_FILE
            watched[knowledge], watched[index_path] = _sha(knowledge), _sha(index_path)
            parts = _knowledge_parts(root)
            if parts["index"]["source_hashes"] != _sources(root):
                raise ValueError("Stale factor index render inputs")
            mutable[index_path] = index_json(parts["index"])
            mutable[knowledge] = _render_knowledge(parts, released_rows)
        mutable[ledger] = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for r in updated)
        receipt = {"version": VERSION, "manifest_sha256": manifest["manifest_sha256"],
                   "items": receipt_items, "independence_note": "Agent identities are host attestations, not scientific validation."}
        receipt_path = root / "memory/lesson_review_batches" / f"{digest(receipt)}.json"
        if receipt_path.exists():
            if digest(_read(receipt_path)) != digest(receipt):
                raise ValueError("Batch receipt hash mismatch")
            watched[receipt_path] = _sha(receipt_path)
        else:
            immutable[receipt_path] = _json(receipt)
        _commit(root, mutable, immutable, lambda written: _check_guard(root, sources, {**watched, **written}))
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("research"))
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--records", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    save = commands.add_parser("save")
    save.add_argument("--manifest", type=Path, required=True)
    save.add_argument("--submissions", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_batch(args.root, _read(args.records)["record_ids"], args.output_dir)
        print(f"Prepared {len(result['entries'])} empty scientist templates; no reviews approved.")
    else:
        result = save_batch(args.root, args.manifest, args.submissions)
        print(f"Saved {len(result['items'])} individually validated analyst/critic reviews.")


if __name__ == "__main__":
    main()
