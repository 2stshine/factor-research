import io
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import zipfile

import pytest

from scripts import backfill_dart_statement_corpus as collector
from scripts import stage_dart_statement_corpus as stage


CORP, STOCK, KEY = "00126380", "005930", "synthetic-key-no-live-requests"
ORIGINAL, CORRECTION = "20150817000001", "20160901000002"


def statement(scope="CFS"):
    heading = "연결 손익계산서" if scope == "CFS" else "손익계산서"
    return f'''<TABLE><TR><TD>{heading}</TD></TR>
<TR><TD>제 47 기 반기 2015.01.01 부터 2015.06.30 까지</TD></TR>
<TR><TD>제 46 기 반기 2014.01.01 부터 2014.06.30 까지</TD></TR>
<TR><TD>(단위 : 백만원)</TD></TR></TABLE>
<TABLE><THEAD><TR><TH ROWSPAN="2"> </TH><TH COLSPAN="2">제 47 기 반기</TH><TH COLSPAN="2">제 46 기 반기</TH></TR>
<TR><TH>3개월</TH><TH>누적</TH><TH>3개월</TH><TH>누적</TH></TR></THEAD>
<TR><TD>매출액</TD><TD>1,234</TD><TD>2,000</TD><TD>900</TD><TD>1,800</TD></TR></TABLE>'''


def xml(*, partial=False):
    return (f'<DOCUMENT><DOCUMENT-NAME ACODE="11012">보고서</DOCUMENT-NAME><COMPANY-NAME AREGCIK="{CORP}">테스트</COMPANY-NAME>'
            '<TITLE>III. 재무에 관한 사항</TITLE><TITLE>2. 연결재무제표</TITLE>'
            + ("" if partial else statement()) + '<TITLE>4. 재무제표</TITLE>' + statement("OFS")
            + '<TITLE>IV. 기타</TITLE></DOCUMENT>').encode()


def zip_bytes(receipt, *, partial=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("/" + receipt + ".xml", xml(partial=partial))
    return buffer.getvalue()


def main_html(receipt, family, *, selected=None, future_date=None):
    selected = selected or receipt
    options = ""
    for member in family:
        visible = future_date if future_date and member not in {ORIGINAL, CORRECTION} else "보고서"
        options += f'<option value="rcpNo={member}"' + (' selected' if member == selected else '') + f'>{visible}</option>'
    return (f'<html><script>viewDoc("{receipt}", "12345", "0", "0", "0", "dart3.xsd");</script>'
            f'<select id="family">{options}</select><select id="att"><option value="null">첨부선택</option></select></html>').encode()


class Response(io.BytesIO):
    status = 200


def make_corpus(tmp_path, monkeypatch, *, corrected=False, partial=False, no_main=False, future=None):
    monkeypatch.setenv("DART_API_KEY", KEY)
    manifest = {"issuers": [{"corp_code": CORP, "stock_code": STOCK, "asset_ids": [1]}], "fiscal_year": 2015,
                "quarters": ["Q2"], "list_start": "20150101", "list_end": "20230731",
                "identity_source_sha256": "a"*64, "corpus_id": "test", "max_calls": 30,
                "max_bytes": 1_000_000, "max_documents": 10}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(json.dumps(manifest).encode())
    listed = [{"corp_code": CORP, "stock_code": STOCK, "report_nm": "반기보고서 (2015.06)",
               "rcept_no": ORIGINAL, "rcept_dt": "20150817", "rm": "정" if corrected or future else ""}]
    if corrected:
        listed.append({**listed[0], "report_nm": "[기재정정]반기보고서 (2015.06)", "rcept_no": CORRECTION, "rcept_dt": "20160901", "rm": ""})
    family = ([future] if future else []) + ([CORRECTION] if corrected else []) + [ORIGINAL]
    def fake(request, **kwargs):
        parsed = urlparse(request.full_url)
        params = {k: v[0] for k,v in parse_qs(parsed.query).items()}
        if parsed.path.endswith("list.json"):
            assert params["crtfc_key"] == KEY
            return Response(json.dumps({"status": "000", "page_no": 1, "page_count": 100,
                                        "total_page": 1, "total_count": len(listed), "list": listed}).encode())
        if parsed.path.endswith("document.xml"):
            return Response(zip_bytes(params["rcept_no"], partial=partial))
        return Response(main_html(params["rcpNo"], family, future_date="2024.03.31" if future else None))
    root = tmp_path / "raw"
    collector.collect(manifest_path, root, collect_correction_main=not no_main,
                      opener=fake, sleeper=lambda _: None)
    return root


def test_complete_original_bundle_and_exact_source_hashes(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch)
    summary = stage.write_bundle(root, tmp_path / "staged")
    assert summary["staged_row_count"] == 4 and summary["source_candidate_current_quarter_rows"] == 2
    assert summary["lineage_event_counts"] == {"ORIGINAL": 1}
    assert summary["status"] == "STAGED_PIT_UNVERIFIED" and not summary["pit_certified"]
    output = json.loads((tmp_path / "staged/staged-revenue.json").read_bytes())
    assert {r["amount_role"] for r in output["rows"]} == {"CURRENT_QUARTER", "CURRENT_YTD"}
    assert all(r["financial_available_at"] is None and not r["input_connected"] for r in output["rows"])
    index = json.loads((tmp_path / "staged/artifact-index.json").read_bytes())
    for digest, item in index["artifacts"].items():
        body = (Path(index["roots"][item["root"]]) / item["path"]).read_bytes()
        assert stage.collector.sha(body) == digest
    with pytest.raises(stage.StageError, match="ALREADY_EXISTS"):
        stage.write_bundle(root, tmp_path / "staged")


def test_official_family_proves_revision_and_bounds_original(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch, corrected=True)
    data, corpus, lineage, sources = stage.build(root)
    assert len(data["rows"]) == 8
    events = lineage["scopes"][0]["events"]
    assert [e["kind"] for e in events] == ["ORIGINAL", "CORRECTION"]
    assert events[1]["parent_receipt_no"] == ORIGINAL
    assert ORIGINAL in events[1]["proof"]["text"]
    assert events[0]["valid_from_date"] == "2015-08-18"
    assert events[0]["valid_until_exclusive"] == "2016-09-02"
    assert events[1]["valid_until_exclusive"] == "2023-08-01"
    assert data["source_candidate_current_quarter_rows"] == 4


def test_matching_titles_without_official_family_never_approve(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch, corrected=True, no_main=True)
    data, _, lineage, _ = stage.build(root)
    assert data["source_candidate_current_quarter_rows"] == 0
    assert {e["kind"] for e in lineage["scopes"][0]["events"]} == {"UNRESOLVED"}
    assert len(data["rows"]) == 8  # Raw parsed evidence remains available for review.


def test_raw_partial_cfs_ofs_does_not_publish_but_preserves_rows(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch, partial=True)
    data, _, _, _ = stage.build(root)
    assert len(data["rows"]) == 2 and data["source_candidate_current_quarter_rows"] == 0
    assert any(b["stage"] == "parser" for b in data["blockers"])


def test_source_sha_tamper_rejected_before_staging(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch)
    next(root.glob("attempts/*/response.json")).write_bytes(b"corrupt")
    with pytest.raises(stage.StageError, match="ISSUER_LISTS_NOT_COMPLETE"):
        stage.build(root)


def test_running_corpus_diagnostic_only(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch)
    (root / ".corpus.lock").write_bytes(b"")
    with pytest.raises(stage.StageError, match="STILL_RUNNING"):
        stage.build(root)
    data, corpus, lineage, _ = stage.build(root, allow_incomplete=True)
    assert data["status"] == "INCOMPLETE_DIAGNOSTIC_ONLY"
    assert not data["source_collection_finished"] and data["source_candidate_current_quarter_rows"] == 0


def test_wrong_receipt_main_selection_rejected():
    with pytest.raises(stage.StageError, match="SELECTED_DIFFERENT"):
        stage.parse_family(main_html(ORIGINAL, [CORRECTION, ORIGINAL], selected=CORRECTION), ORIGINAL)


def test_duplicate_family_receipts_rejected():
    with pytest.raises(stage.StageError):
        stage.parse_family(main_html(ORIGINAL, [ORIGINAL, ORIGINAL]), ORIGINAL)


def test_unknown_family_receipt_not_dated_from_receipt_prefix():
    body = main_html(ORIGINAL, ["20240101000001", ORIGINAL])
    official = {"rcept_no": ORIGINAL, "report_nm": "반기보고서 (2015.06)", "rcept_dt": "20150817", "rm": "정"}
    result = stage.lineage_scope({"corp_code": CORP, "stock_code": STOCK}, "Q2", [official], {ORIGINAL: official},
                                 {ORIGINAL: body}, {ORIGINAL: {}}, "2023-07-31")
    assert result["events"][0]["kind"] == "UNRESOLVED"
    assert "UNDATED_OR_IN_HORIZON" in result["family_receipt_errors"][ORIGINAL][0]


def test_explicit_future_selector_date_excluded_not_backdated(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch, future="20240331000001")
    data, _, lineage, _ = stage.build(root)
    assert lineage["scopes"][0]["events"][0]["kind"] == "ORIGINAL"
    assert lineage["scopes"][0]["post_horizon_dependencies"][0]["official_selector_display_date"] == "2024-03-31"
    assert data["source_candidate_current_quarter_rows"] == 2


def test_unknown_later_revision_closes_previous_window_without_retroactive_erasure():
    rows = [{"rcept_no": ORIGINAL, "report_nm": "반기보고서 (2015.06)", "rcept_dt": "20150817", "rm": "정"},
            {"rcept_no": CORRECTION, "report_nm": "[기재정정]반기보고서 (2015.06)", "rcept_dt": "20160901", "rm": ""}]
    result = stage.lineage_scope({"corp_code": CORP, "stock_code": STOCK}, "Q2", rows,
                                 {r["rcept_no"]:r for r in rows}, {ORIGINAL:main_html(ORIGINAL,[CORRECTION,ORIGINAL])},
                                 {ORIGINAL:{}}, "2023-07-31")
    assert [e["kind"] for e in result["events"]] == ["ORIGINAL", "UNRESOLVED"]
    assert result["events"][0]["valid_until_exclusive"] == "2016-09-02"


def test_same_day_revision_windows_are_empty_not_publishable():
    rows = [{"rcept_no": ORIGINAL, "report_nm": "반기보고서 (2015.06)", "rcept_dt": "20160901", "rm": "정"},
            {"rcept_no": CORRECTION, "report_nm": "[기재정정]반기보고서 (2015.06)", "rcept_dt": "20160901", "rm": ""}]
    mains = {r:main_html(r,[CORRECTION,ORIGINAL]) for r in [ORIGINAL,CORRECTION]}
    result = stage.lineage_scope({"corp_code":CORP,"stock_code":STOCK},"Q2",rows,
                                 {r["rcept_no"]:r for r in rows},mains,{ORIGINAL:{},CORRECTION:{}},"2023-07-31")
    assert result["events"][0]["empty_same_day_window"]
    assert not result["events"][1]["empty_same_day_window"]


def test_corpus_classifies_nontarget_receipts_explicitly(tmp_path, monkeypatch):
    # The relevance function is wider than the downloader, so unusual titles
    # mentioning the exact period cannot be silently dropped from lineage.
    assert stage.relevant_quarter("[철회] 반기보고서 (2015.06)") == "Q2"
    assert stage.relevant_quarter("반기보고서 (2016.06)") is None


def test_absolute_artifact_paths_forbidden(tmp_path):
    with pytest.raises(stage.StageError, match="UNSAFE_ARTIFACT_PATH"):
        stage.safe_read(tmp_path, "/etc/passwd")


def test_explicit_cfs_absence_gate_requires_actual_evidence_and_flag():
    parsed = {"scope_status": {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"},
              "cfs_absence_proven": True, "cfs_absence_evidence": [{"exact_text": "synthetic proof"}]}
    assert stage.publication_scope_supported(parsed)
    assert not stage.publication_scope_supported({**parsed, "cfs_absence_proven": False})
    assert not stage.publication_scope_supported({**parsed, "cfs_absence_evidence": []})
    assert not stage.publication_scope_supported({**parsed, "scope_status": {"CFS": "UNRESOLVED", "OFS": "PARSED"}})


def test_unlisted_parser_module_never_imported():
    with pytest.raises(stage.StageError, match="UNSUPPORTED_PARSER_VERSION"):
        stage.selected_parser("os")


def test_saved_source_code_snapshots_are_hash_bound(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch)
    stage.write_bundle(root, tmp_path / "stage")
    source_files = list((tmp_path / "stage/source").glob("*.py"))
    assert len(source_files) == 4
    for path in source_files:
        assert path.name.startswith(collector.sha(path.read_bytes()))


def test_completed_missing_zip_preserves_provider_failure_and_blocks_window(tmp_path, monkeypatch):
    root = make_corpus(tmp_path, monkeypatch)
    for obj in root.glob("objects/*.json"):
        value = json.loads(obj.read_bytes())
        if value["endpoint"] == "document.xml":
            obj.unlink()
    run_path = next(root.glob("runs/*.json"))
    run = json.loads(run_path.read_bytes())
    run["status"] = "RAW_CORPUS_INCOMPLETE_PIT_UNVERIFIED"
    run["failures"] = [{"stage": "document", "receipt_no": ORIGINAL, "reason": "DOCUMENT_PROVIDER_NO_FILE"}]
    run_path.write_bytes(json.dumps(run).encode())
    data, _, lineage, _ = stage.build(root)
    assert data["source_collection_finished"] and data["all_planned_issuer_lists_complete"]
    assert data["source_candidate_current_quarter_rows"] == 0
    assert data["documents"][0]["rejections"][0]["reason"] == "COLLECTOR_FAILURE:DOCUMENT_PROVIDER_NO_FILE"
    assert lineage["scopes"][0]["events"][0]["kind"] == "UNRESOLVED"


def test_withdrawal_closes_values_without_replacing_amount():
    rows = [{"rcept_no": ORIGINAL, "report_nm": "반기보고서 (2015.06)", "rcept_dt": "20150817", "rm": "정"},
            {"rcept_no": CORRECTION, "report_nm": "[철회]반기보고서 (2015.06)", "rcept_dt": "20160901", "rm": ""}]
    mains = {r:main_html(r,[CORRECTION,ORIGINAL]) for r in [ORIGINAL,CORRECTION]}
    result = stage.lineage_scope({"corp_code":CORP,"stock_code":STOCK},"Q2",rows,
                                 {r["rcept_no"]:r for r in rows},mains,{ORIGINAL:{}},"2023-07-31")
    assert [e["kind"] for e in result["events"]] == ["ORIGINAL", "WITHDRAWAL"]
    assert result["events"][0]["valid_until_exclusive"] == "2016-09-02"


def test_attachment_only_is_not_assumed_to_be_full_economic_revision():
    att = (f'<html><script>viewDoc("{CORRECTION}", "987", "0", "0", "0", "dart3.xsd");</script>'
           f'<select id="family"><option value="rcpNo={ORIGINAL}">보고서</option></select>'
           f'<select id="att"><option value="rcpNo={CORRECTION}&amp;dcmNo=987" selected>첨부</option></select></html>').encode()
    parsed = stage.parse_family(att, CORRECTION)
    assert parsed["current_selector"] == "att"
    row = {"rcept_no": CORRECTION, "report_nm": "[첨부정정]반기보고서 (2015.06)", "rcept_dt": "20160901"}
    original = {"rcept_no": ORIGINAL, "report_nm": "반기보고서 (2015.06)", "rcept_dt": "20150817", "rm": "정"}
    # Keep both official main sequences identical; attachment is a distinct lane.
    orig_main = att.decode().replace(f'viewDoc("{CORRECTION}", "987"', f'viewDoc("{ORIGINAL}", "123"')
    orig_main = orig_main.replace(f'rcpNo={ORIGINAL}">', f'rcpNo={ORIGINAL}" selected>').replace('dcmNo=987" selected', 'dcmNo=987"')
    result = stage.lineage_scope({"corp_code":CORP,"stock_code":STOCK},"Q2",[original,row],
                                 {ORIGINAL:original,CORRECTION:row},{ORIGINAL:orig_main.encode(),CORRECTION:att},
                                 {ORIGINAL:{},CORRECTION:{}},"2023-07-31")
    assert result["events"][0]["kind"] == "ORIGINAL"
    assert result["events"][1]["kind"] == "UNRESOLVED"
    assert result["events"][1]["reason"] == "ATTACHMENT_ONLY_DIRECT_ECONOMIC_PARENT_UNPROVEN"
