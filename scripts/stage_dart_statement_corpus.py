"""Offline corpus/lineage/revenue staging; never grants PIT or DB approval.

Read a completed receipt-addressed corpus. Persist a new immutable output
directory with stage, corpus, lineage and a SHA-addressed artifact index.
--allow-incomplete is diagnostic only and is explicitly nonpublishable.
No API, database, cloud writes, ZIP extraction or outcome inspection.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import importlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from engine import dart_historical_revenue_parser as parser
from scripts import backfill_dart_statement_corpus as collector
from scripts import backfill_dart_historical_filings as pilot


SCHEMA = "dart-historical-revenue-staging-v1"
PERIODS = {"Q1": ("2015-01-01", "2015-03-31"), "Q2": ("2015-04-01", "2015-06-30"),
           "Q3": ("2015-07-01", "2015-09-30")}


class StageError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def require(condition, reason):
    if not condition:
        raise StageError(reason)


def safe_read(root, relative):
    part = PurePosixPath(str(relative))
    require(not part.is_absolute() and ".." not in part.parts and "\\" not in str(part) and ":" not in str(part), "UNSAFE_ARTIFACT_PATH")
    path = root / part
    require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "MISSING_OR_UNSAFE_ARTIFACT")
    return path.read_bytes()


def iso(value):
    require(collector.valid_date(value), "INVALID_OFFICIAL_RECEIPT_DATE")
    return datetime.strptime(value, "%Y%m%d").date().isoformat()


class Sources:
    def __init__(self, root):
        self.root = root
        self.index = {}
        self.generated = {}

    def add(self, body, relative, source_root="corpus"):
        digest = collector.sha(body)
        self.index.setdefault(digest, {"root": source_root, "path": relative, "bytes": len(body)})
        return digest

    def raw(self, relative):
        body = safe_read(self.root, relative)
        self.add(body, relative)
        return body

    def implementation(self, body, name):
        relative = "source/" + collector.sha(body) + "-" + name
        self.generated[relative] = body
        self.add(body, relative, "output")

    def response(self, meta, endpoint, params):
        require(meta.get("endpoint") == endpoint and meta.get("params") == params, "SOURCE_REQUEST_SCOPE_MISMATCH")
        body = self.raw(meta["body_path"])
        require(len(body) == meta.get("bytes") and collector.sha(body) == meta.get("sha256"), "SOURCE_RESPONSE_SHA_MISMATCH")
        request_path = str(PurePosixPath(meta["body_path"]).with_name("request.json"))
        request_raw = self.raw(request_path)
        request = json.loads(request_raw)
        require(request.get("endpoint") == endpoint and request.get("params") == params
                and request.get("requested_at") == meta.get("requested_at"), "RAW_REQUEST_METADATA_MISMATCH")
        outcome_raw = self.raw(str(PurePosixPath(meta["body_path"]).with_name("outcome.json")))
        outcome = json.loads(outcome_raw)
        require(outcome.get("status") == "VALID_RAW_RESPONSE" and outcome.get("received_bytes") == len(body)
                and outcome.get("sha256") == collector.sha(body), "RAW_RESPONSE_OUTCOME_MISMATCH")
        return body, collector.sha(request_raw)


class FamilySelector(HTMLParser):
    """Official family/attachment options, preserving exact option anchors."""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text = text
        self.lines = [0] + [m.end() for m in re.finditer("\n", text)]
        self.counts = {"family": 0, "att": 0}
        self.selector = None
        self.option = None
        self.options = []

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "select" and attributes.get("id") in self.counts:
            require(self.selector is None, "NESTED_OFFICIAL_SELECTOR")
            self.selector = attributes["id"]
            self.counts[self.selector] += 1
        elif tag == "option" and self.selector:
            require(self.option is None, "UNTERMINATED_SELECTOR_OPTION")
            value = attributes.get("value") or ""
            receipt = re.search(r"(?:^|[?&])rcpNo=([0-9]{14})(?:&|$)", value, re.I)
            dcm = re.search(r"(?:^|[?&])dcmNo=([0-9]+)(?:&|$)", value, re.I)
            self.option = {"selector": self.selector, "receipt_no": receipt.group(1) if receipt else None,
                           "dcm_no": dcm.group(1) if dcm else None, "selected": "selected" in attributes,
                           "title": attributes.get("title") or "", "parts": [], "start": self.source_offset()}

    def handle_data(self, data):
        if self.option is not None:
            self.option["parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self.option is not None:
            end = self.text.find(">", self.source_offset()) + 1
            require(end > 0, "UNTERMINATED_SELECTOR_OPTION")
            item = self.option
            item["text"] = " ".join("".join(item.pop("parts")).split())
            item["raw_anchor"] = self.text[item.pop("start"):end]
            if item["receipt_no"]:
                self.options.append(item)
            self.option = None
        elif tag == "select" and self.selector:
            require(self.option is None, "UNTERMINATED_SELECTOR_OPTION")
            self.selector = None


def parse_family(body, receipt):
    text, decoding = parser.decode_document(body)
    html = FamilySelector(text)
    html.feed(text)
    html.close()
    require(html.counts == {"family": 1, "att": 1} and html.option is None and html.selector is None,
            "MISSING_OR_AMBIGUOUS_OFFICIAL_SELECTORS")
    family = [o for o in html.options if o["selector"] == "family"]
    attachments = [o for o in html.options if o["selector"] == "att"]
    ids = [o["receipt_no"] for o in family]
    require(ids and len(ids) == len(set(ids)) and ids == sorted(ids, reverse=True), "INVALID_OFFICIAL_FAMILY_ORDER")
    require(all(o["dcm_no"] is None for o in family) and all(o["dcm_no"] for o in attachments), "FAMILY_ATTACHMENT_KIND_MISMATCH")
    require(len({(o["receipt_no"], o["dcm_no"]) for o in attachments}) == len(attachments), "DUPLICATE_ATTACHMENT_SELECTOR_KEY")
    chosen = [o for o in html.options if o["selected"]]
    require(len(chosen) == 1 and chosen[0]["receipt_no"] == receipt, "OFFICIAL_VIEWER_SELECTED_DIFFERENT_RECEIPT")
    views = set(re.findall(r"viewDoc\(\s*[\"']" + re.escape(receipt)
                          + r"[\"']\s*,\s*[\"']([0-9]+)[\"']\s*,\s*[\"']0[\"']\s*,\s*[\"']0[\"']\s*,\s*[\"']0[\"']\s*,\s*[\"']([A-Za-z0-9_.-]+)[\"']", text))
    require(len(views) == 1, "MISSING_OR_AMBIGUOUS_EXACT_VIEWER_TARGET")
    dcm, dtd = next(iter(views))
    if chosen[0]["selector"] == "att":
        require(chosen[0]["dcm_no"] == dcm, "ATTACHMENT_VIEWER_TARGET_MISMATCH")
    return {"family": family, "attachments": attachments, "current_selector": chosen[0]["selector"],
            "dcm_no": dcm, "dtd": dtd, "decoding": decoding, "sha256": collector.sha(body)}


def relevant_quarter(name):
    compact = re.sub(r"\s+", "", str(name or ""))
    found = [q for q, (title, month) in collector.QUARTERS.items() if title in compact and "2015." + month in compact]
    return found[0] if len(found) == 1 else None


def explicit_option_date(option):
    # Use a date actually displayed in the official selector, never rcept_no[:8].
    candidates = set(re.findall(r"(?<![0-9])((?:19|20)[0-9]{2})[.\-/]([0-9]{2})[.\-/]([0-9]{2})(?![0-9])",
                                option["text"]))
    if len(candidates) != 1:
        return None
    try:
        return date(*map(int, next(iter(candidates)))).isoformat()
    except ValueError:
        return None


def lineage_scope(issuer, quarter, events_rows, all_receipts, mains, documents, horizon):
    start, end = PERIODS[quarter]
    sid = issuer["corp_code"] + ":2015:" + quarter
    ordered = sorted(events_rows, key=lambda r: (r["rcept_dt"], r["rcept_no"]))
    ids = [r["rcept_no"] for r in ordered]
    needs_family = (len(ids) > 1 or any("정정" in r["report_nm"] or "첨부추가" in r["report_nm"]
                                     or "철회" in r["report_nm"] or "정" in str(r.get("rm") or "") for r in ordered))
    family_results, family_errors, local_errors, outside = {}, [], defaultdict(list), []
    if needs_family:
        for receipt in ids:
            if receipt not in mains:
                local_errors[receipt].append("OFFICIAL_FAMILY_HTML_MISSING")
                continue
            try:
                family_results[receipt] = parse_family(mains[receipt], receipt)
            except (StageError, parser.ParseError) as exc:
                local_errors[receipt].append(str(exc))
        sequences = {tuple(o["receipt_no"] for o in f["family"]) for f in family_results.values()}
        if len(sequences) > 1:
            family_errors.append("OFFICIAL_FAMILY_SEQUENCES_DISAGREE")
        for receipt, evidence in family_results.items():
            for option in evidence["family"] + evidence["attachments"]:
                member = option["receipt_no"]
                if member in ids:
                    continue
                if member in all_receipts:
                    local_errors[receipt].append("OFFICIAL_FAMILY_MEMBER_NOT_CLASSIFIED_IN_SCOPE:" + member)
                    continue
                displayed = explicit_option_date(option)
                if displayed and displayed > horizon:
                    outside.append({"receipt_no": member, "official_selector_display_date": displayed,
                                    "reason": "POST_HORIZON_SELECTOR_DEPENDENCY_NOT_USED_FOR_VALUES",
                                    "artifact_sha256": evidence["sha256"], "text": option["raw_anchor"]})
                else:
                    local_errors[receipt].append("UNDATED_OR_IN_HORIZON_FAMILY_MEMBER_MISSING:" + member)
    events = []
    previous = None
    for row in ordered:
        receipt, name = row["rcept_no"], row["report_nm"]
        kind, reason, proof = "UNRESOLVED", None, None
        current = family_results.get(receipt)
        if family_errors or local_errors.get(receipt):
            reason = "OFFICIAL_FAMILY_EVIDENCE_INCOMPLETE_OR_CONFLICTING"
        elif iso(row["rcept_dt"]) < end:
            reason = "FILING_PRECEDES_PERIOD_END"
        elif collector.target_quarter(name, {"quarters": [quarter]}) is None:
            reason = "UNSUPPORTED_TARGET_REPORT_TITLE"
        elif current and current["current_selector"] == "att":
            reason = "ATTACHMENT_ONLY_DIRECT_ECONOMIC_PARENT_UNPROVEN"
        elif previous is None:
            if "정정" in name or "철회" in name or "첨부추가" in name:
                reason = "ORIGINAL_RECEIPT_NOT_PROVEN"
            elif current and current["family"][-1]["receipt_no"] != receipt:
                reason = "LIST_ORIGINAL_IS_NOT_OFFICIAL_FAMILY_ROOT"
            else:
                kind = "ORIGINAL"
        elif current and ("정정" in name or "철회" in name):
            family_ids = [o["receipt_no"] for o in current["family"]]
            position = family_ids.index(receipt) if receipt in family_ids else -1
            if position < 0 or position + 1 >= len(family_ids) or family_ids[position + 1] != previous:
                reason = "DIRECT_PREVIOUS_REVISION_NOT_PROVEN"
            else:
                parent = current["family"][position + 1]
                proof = {"artifact_sha256": current["sha256"], "text": parent["raw_anchor"],
                         "method": "EXACT_OFFICIAL_FAMILY_ADJACENCY_AFTER_SELECTOR_AND_SCOPE_CHECK"}
                kind = "WITHDRAWAL" if "철회" in name else "CORRECTION"
        else:
            reason = "MULTIPLE_ORIGINALS_OR_UNPROVEN_REVISION_RELATION"
        if kind in {"ORIGINAL", "CORRECTION"} and receipt not in documents:
            kind, reason = "UNRESOLVED", "MISSING_OR_UNSAFE_ORIGINAL_DOCUMENT"
        event = {"receipt_no": receipt, "kind": kind, "official_filed_date": iso(row["rcept_dt"])}
        if reason:
            event["reason"] = reason
        if proof:
            event.update(parent_receipt_no=previous, proof=proof)
        events.append(event)
        previous = receipt
    for index, event in enumerate(events):
        begin = date.fromisoformat(event["official_filed_date"]) + timedelta(days=1)
        until = (date.fromisoformat(events[index + 1]["official_filed_date"]) + timedelta(days=1)
                 if index + 1 < len(events) else date.fromisoformat(horizon) + timedelta(days=1))
        event["valid_from_date"] = begin.isoformat()
        event["valid_until_exclusive"] = until.isoformat()
        event["date_only_availability_policy"] = "NEXT_CALENDAR_DAY_00_00_ASIA_SEOUL_NOT_INTRADAY_CERTIFICATION"
        event["empty_same_day_window"] = until <= begin
    return {"scope_id": sid, "corp_code": issuer["corp_code"], "stock_code": issuer["stock_code"],
            "quarter": quarter, "period_start": start, "period_end": end, "events": events,
            "family_evidence_errors": sorted(set(family_errors)), "family_receipt_errors": dict(local_errors),
            "post_horizon_dependencies": outside,
            "lineage_evidence_status": "UNRESOLVED" if any(e["kind"] == "UNRESOLVED" for e in events) else "BOUNDED_RELATION_EVIDENCE_CHECKED_NOT_PIT_CERTIFIED"}


def selected_parser(version):
    require(version in {"v1", "v2"}, "UNSUPPORTED_PARSER_VERSION")
    if version == "v1":
        return parser
    try:
        return importlib.import_module("engine.dart_historical_revenue_parser_v2")
    except ModuleNotFoundError:
        raise StageError("PARSER_V2_NOT_AVAILABLE") from None


def publication_scope_supported(parsed):
    scopes = parsed["scope_status"]
    return (scopes == {"CFS": "PARSED", "OFS": "PARSED"} or
            (scopes == {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"}
             and parsed.get("cfs_absence_proven") is True and bool(parsed.get("cfs_absence_evidence"))))


def build(root, *, allow_incomplete=False, parser_version="v1"):
    root = Path(root).absolute()
    sources = Sources(root)
    parser_module = selected_parser(parser_version)
    parser_source = Path(parser_module.__file__).read_bytes()
    parser_sha = collector.sha(parser_source)
    stage_source = Path(__file__).read_bytes()
    sources.implementation(stage_source, Path(__file__).name)
    sources.implementation(parser_source, Path(parser_module.__file__).name)
    if parser_version != "v1":
        sources.implementation(Path(parser.__file__).read_bytes(), Path(parser.__file__).name)
    contract_raw = sources.raw("contract.json")
    contract = json.loads(contract_raw)
    require(contract.get("schema_version") == collector.SCHEMA, "WRONG_CORPUS_CONTRACT")
    manifest = contract["manifest"]
    current_source = Path(collector.__file__).read_bytes()
    require(collector.sha(current_source) == contract["collector_sha256"], "FROZEN_COLLECTOR_SOURCE_CHANGED")
    sources.implementation(current_source, "backfill_dart_statement_corpus.py")
    pilot_source = Path(pilot.__file__).read_bytes()
    require(collector.sha(pilot_source) == contract["zip_validator_sha256"], "FROZEN_ZIP_VALIDATOR_CHANGED")
    sources.implementation(pilot_source, "backfill_dart_historical_filings.py")
    runs = sorted((root / "runs").glob("*.json"))
    finished = bool(runs) and not (root / ".corpus.lock").exists()
    if not allow_incomplete:
        require(finished, "CORPUS_COLLECTION_STILL_RUNNING_OR_NO_COMPLETION_RUN")
    run_sha, failed_documents = None, {}
    if runs:
        run_raw = sources.raw(runs[-1].relative_to(root).as_posix())
        run = json.loads(run_raw)
        require(run["manifest_sha256"] == contract["manifest_sha256"], "RUN_MANIFEST_SHA_MISMATCH")
        run_sha = collector.sha(run_raw)
        failed_documents = {f["receipt_no"]: f["reason"] for f in run.get("failures", [])
                            if f.get("stage") == "document" and re.fullmatch(r"[A-Z_]+", str(f.get("reason", "")))}
    objects = {}
    for path in sorted((root / "objects").glob("*.json")):
        raw = sources.raw(path.relative_to(root).as_posix())
        meta = json.loads(raw)
        key = collector.sha(collector.encoded({"endpoint": meta["endpoint"], "params": meta["params"]}))
        require(path.stem == key and key not in objects, "OBJECT_POINTER_KEY_MISMATCH")
        objects[key] = meta
    class OfflineClient:
        def fetch(self, endpoint, params):
            key = collector.sha(collector.encoded({"endpoint": endpoint, "params": params}))
            if key not in objects:
                if endpoint == "document.xml" and params["rcept_no"] in failed_documents:
                    raise collector.CorpusError("COLLECTOR_FAILURE:" + failed_documents[params["rcept_no"]])
                raise collector.CorpusError("OFFLINE_OBJECT_NOT_AVAILABLE")
            meta = objects[key]
            try:
                body, _ = sources.response(meta, endpoint, params)
            except StageError as exc:
                raise collector.CorpusError(str(exc)) from None
            return body, meta
    client = OfflineClient()
    issuer_results, all_receipts, source_pages, blockers = {}, {}, {}, []
    corpus = {"schema_version": "dart-original-corpus-v1", "collector_contract_sha256": collector.sha(contract_raw),
              "source_run_sha256": run_sha, "issuers": [], "documents": []}
    for issuer in manifest["issuers"]:
        corp = issuer["corp_code"]
        try:
            listed = collector.issuer_disclosures(client, issuer, manifest)
            pages, local_receipts, local_sources = [], {}, {}
            for meta in listed["list_responses"]:
                body, request_sha = sources.response(meta, "list.json", meta["params"])
                pages.append({"request_sha256": request_sha, "response_sha256": collector.sha(body)})
                for row in json.loads(body).get("list") or []:
                    receipt = row["rcept_no"]
                    require(receipt not in all_receipts or all_receipts[receipt] == row, "GLOBAL_RECEIPT_IDENTITY_CONFLICT")
                    local_receipts[receipt] = row
                    local_sources[receipt] = collector.sha(body)
            all_receipts.update(local_receipts)
            source_pages.update(local_sources)
            issuer_results[corp] = listed
            corpus["issuers"].append({"corp_code": corp, "covered_from": iso(manifest["list_start"]),
                                      "covered_through": iso(manifest["list_end"]), "pages": pages})
        except (collector.CorpusError, StageError) as exc:
            blockers.append({"stage": "issuer_list", "corp_code": corp, "reason": str(exc)})
    all_lists_complete = len(issuer_results) == len(manifest["issuers"])
    corpus["all_planned_issuer_lists_complete"] = all_lists_complete
    if not allow_incomplete:
        require(all_lists_complete, "PLANNED_ISSUER_LISTS_NOT_COMPLETE")
    documents, parsed_docs, mains, rows, doc_results = {}, {}, {}, [], []
    issuers_by_corp = {i["corp_code"]: i for i in manifest["issuers"]}
    for receipt, official in sorted(all_receipts.items()):
        quarter = relevant_quarter(official["report_nm"])
        if quarter not in manifest["quarters"]:
            continue
        issuer = issuers_by_corp[official["corp_code"]]
        result = {"receipt_no": receipt, "corp_code": issuer["corp_code"], "quarter": quarter}
        try:
            raw_zip, meta = client.fetch("document.xml", {"rcept_no": receipt})
            members = pilot.validate_zip(raw_zip, expected_receipt=receipt)
            xml_members = [m for m in members if m["name"] in {receipt + ".xml", "/" + receipt + ".xml"}]
            require(len(xml_members) == 1, "NO_UNIQUE_RECEIPT_ADDRESSED_XML_MEMBER")
            with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
                xml = archive.read(xml_members[0]["name"])
            parsed = parser_module.parse_document(xml, quarter, issuer["corp_code"])
            require(parsed["parser_source_sha256"] == parser_sha, "PARSER_IMPLEMENTATION_CHANGED_DURING_STAGING")
            doc = {"receipt_no": receipt, "corp_code": issuer["corp_code"], "zip_sha256": collector.sha(raw_zip),
                   "xml_member_name": xml_members[0]["name"], "xml_sha256": collector.sha(xml)}
            corpus["documents"].append(doc)
            documents[receipt], parsed_docs[receipt] = doc, parsed
            evidence = {**doc, "stock_code": issuer["stock_code"], "asset_ids": issuer["asset_ids"], "quarter": quarter,
                        "official_filed_date": iso(official["rcept_dt"]), "filed_date_source": "OpenDART list.json rcept_dt",
                        "list_sha256": source_pages[receipt], "collected_at": meta["received_at"],
                        "zip_relative_path": meta["body_path"], "decoding": parsed.get("decoding"),
                        "xml_issuer_codes": parsed.get("xml_issuer_codes"), "xml_document_form_codes": parsed.get("xml_document_form_codes"),
                        "financial_available_at": None, "original_first_publication_proven": False,
                        "pit_status": "PIT_UNVERIFIED", "input_connected": False,
                        "historical_asset_identity_status": "UNVERIFIED", "parser_source_sha256": parsed["parser_source_sha256"]}
            evidence.update(cfs_absence_proven=parsed.get("cfs_absence_proven", False),
                            cfs_absence_evidence=parsed.get("cfs_absence_evidence", []))
            for value in parsed["rows"]:
                require(evidence["official_filed_date"] >= value["period_end"], "PUBLICATION_PRECEDES_STATEMENT_PERIOD")
                rows.append({**evidence, **value})
            result.update(status=parsed["status"], staged_rows=len(parsed["rows"]), scope_status=parsed["scope_status"],
                          rejections=parsed["rejections"], publication_scope_gate=parsed["publication_scope_gate"],
                          scope_details=parsed.get("scope_details", {}),
                          cfs_absence_proven=parsed.get("cfs_absence_proven", False),
                          cfs_absence_evidence=parsed.get("cfs_absence_evidence", []))
            if not publication_scope_supported(parsed):
                blockers.append({"stage": "parser", "receipt_no": receipt, "reason": parsed["publication_scope_gate"],
                                 "scope_status": parsed["scope_status"], "rejections": parsed["rejections"]})
        except (collector.CorpusError, pilot.PilotError, StageError) as exc:
            result.update(status="REJECTED_SOURCE", staged_rows=0, rejections=[{"reason": str(exc)}])
            blockers.append({"stage": "document", "receipt_no": receipt, "reason": str(exc)})
        doc_results.append(result)
        key = collector.sha(collector.encoded({"endpoint": "main.do", "params": {"rcpNo": receipt}}))
        if key in objects:
            try:
                mains[receipt], _ = sources.response(objects[key], "main.do", {"rcpNo": receipt})
            except StageError as exc:
                blockers.append({"stage": "family_source", "receipt_no": receipt, "reason": str(exc)})
    classifications, grouped = [], defaultdict(list)
    for receipt, official in sorted(all_receipts.items()):
        quarter = relevant_quarter(official["report_nm"])
        relevant = quarter in manifest["quarters"]
        scope_ids = [official["corp_code"] + ":2015:" + quarter] if relevant else []
        classifications.append({"receipt_no": receipt, "scope_ids": scope_ids,
                                "reason": "TARGET_PERIOD_TITLE_REQUIRES_LINEAGE_VERIFICATION" if relevant else "OUTSIDE_FROZEN_2015_INTERIM_PERIODS"})
        if relevant:
            grouped[(official["corp_code"], quarter)].append(official)
    scopes = [lineage_scope(issuers_by_corp[corp], quarter, entries, all_receipts, mains, documents, iso(manifest["list_end"]))
              for (corp, quarter), entries in sorted(grouped.items())]
    lineage = {"schema_version": "dart-original-lineage-v1", "classified_receipts": classifications, "scopes": scopes,
               "pit_certified": False, "source_collection_finished": finished,
               "all_planned_issuer_lists_complete": all_lists_complete}
    events = {e["receipt_no"]: e for s in scopes for e in s["events"]}
    for row in rows:
        event = events[row["receipt_no"]]
        parsed = parsed_docs[row["receipt_no"]]
        row.update(lineage_event_kind=event["kind"], valid_from_date=event["valid_from_date"],
                   valid_until_exclusive=event["valid_until_exclusive"],
                   source_publication_candidate=(finished and all_lists_complete and event["kind"] in {"ORIGINAL", "CORRECTION"}
                                                 and not event["empty_same_day_window"]
                                                 and row["amount_role"] == "CURRENT_QUARTER"
                                                 and publication_scope_supported(parsed)))
    for scope in scopes:
        for event in scope["events"]:
            if event["kind"] in {"UNRESOLVED", "WITHDRAWAL"}:
                blockers.append({"stage": "lineage", "scope_id": scope["scope_id"], **event})
    require(collector.sha(Path(__file__).read_bytes()) == collector.sha(stage_source)
            and collector.sha(Path(parser_module.__file__).read_bytes()) == parser_sha, "IMPLEMENTATION_CHANGED_DURING_STAGING")
    stage = {"schema_version": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(), "source_root": str(root),
             "source_collection_finished": finished, "all_planned_issuer_lists_complete": all_lists_complete,
             "status": "STAGED_PIT_UNVERIFIED" if finished and all_lists_complete else "INCOMPLETE_DIAGNOSTIC_ONLY",
             "staging_script_sha256": collector.sha(stage_source), "parser_source_sha256": parser_sha,
             "parser_module": parser_module.__name__, "parser_version_selection": parser_version,
             "source_contract_sha256": collector.sha(contract_raw), "source_run_sha256": run_sha,
             "rows": rows, "documents": doc_results, "blockers": blockers,
             "staged_row_count": len(rows), "document_count": len(doc_results),
             "parsed_both_scope_documents": sum(d.get("scope_status") == {"CFS": "PARSED", "OFS": "PARSED"} for d in doc_results),
             "parsed_ofs_explicit_cfs_absence_documents": sum(d.get("scope_status") == {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"} for d in doc_results),
             "missing_target_scopes": [{"corp_code": c, "quarter": q} for c in sorted(issuer_results)
                                       for q in manifest["quarters"] if (c, q) not in grouped],
             "lineage_event_counts": dict(Counter(e["kind"] for e in events.values())),
             "source_candidate_current_quarter_rows": sum(r["source_publication_candidate"] and r["amount_role"] == "CURRENT_QUARTER" for r in rows),
             "api_calls": 0, "zip_extractions": 0, "silver_writes": False, "gold_writes": False,
             "pit_certified": False, "certification_changed": False, "official_input_connected": False,
             "counting_note": "CFS/OFS and CURRENT_QUARTER/YTD are separate value cells, not independent quarterly samples; Q1 roles share dates"}
    return stage, corpus, lineage, sources


def write_bundle(root, output, *, allow_incomplete=False, parser_version="v1"):
    output = Path(output).absolute()
    require(not output.exists(), "OUTPUT_NAMESPACE_ALREADY_EXISTS")
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT_NAMESPACE")
    stage, corpus, lineage, sources = build(root, allow_incomplete=allow_incomplete, parser_version=parser_version)
    output.mkdir(parents=True)
    hashes = {}
    for relative, body in sources.generated.items():
        pilot._put(output / relative, body)
    for filename, value in (("staged-revenue.json", stage), ("corpus.json", corpus), ("lineage.json", lineage)):
        body = canonical(value)
        pilot._put(output / filename, body)
        hashes[filename] = sources.add(body, filename, "output")
    index = {"schema_version": "dart-original-artifact-index-v1", "roots": {
        "corpus": str(Path(root).absolute()), "repository": str(Path(__file__).resolve().parent.parent), "output": str(output)},
             "artifacts": sources.index}
    pilot._put(output / "artifact-index.json", canonical(index))
    summary = {"schema_version": "dart-original-staging-bundle-v1", "status": stage["status"], "hashes": hashes,
               "artifact_index_sha256": collector.sha(canonical(index)), "source_collection_finished": stage["source_collection_finished"],
               "all_planned_issuer_lists_complete": stage["all_planned_issuer_lists_complete"],
               "staged_row_count": stage["staged_row_count"], "document_count": stage["document_count"],
               "parsed_both_scope_documents": stage["parsed_both_scope_documents"],
               "parsed_ofs_explicit_cfs_absence_documents": stage["parsed_ofs_explicit_cfs_absence_documents"],
               "missing_target_scope_count": len(stage["missing_target_scopes"]),
               "parser_version_selection": parser_version,
               "source_candidate_current_quarter_rows": stage["source_candidate_current_quarter_rows"],
               "lineage_event_counts": stage["lineage_event_counts"], "blocker_count": len(stage["blockers"]),
               "pit_certified": False, "official_input_connected": False}
    pilot._put(output / "bundle.json", canonical(summary))
    return summary


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--input", type=Path, required=True)
    arguments.add_argument("--output", type=Path, required=True)
    arguments.add_argument("--allow-incomplete", action="store_true")
    arguments.add_argument("--parser-version", choices=("v1", "v2"), default="v1")
    args = arguments.parse_args()
    try:
        summary = write_bundle(args.input, args.output, allow_incomplete=args.allow_incomplete, parser_version=args.parser_version)
    except (StageError, collector.CorpusError, pilot.PilotError) as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc)}))
        raise SystemExit(2) from None
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
