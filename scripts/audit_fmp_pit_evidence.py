"""Bounded evidence re-review; never grants approval or rewrites upstream data.

This ledger separates local receipt/version safeguards from historical value
vintages.  Web findings are human-reviewed supplements, not offline proofs.
Run: python -m scripts.audit_fmp_pit_evidence
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "output/pit_audit/fmp-20260921"
POLICY = ROOT / "output/regime_inputs/kr-policy-pit-20260920/silver"
UPSTREAM = ROOT.parent / "TeamAlpha-data"
OUT = ROOT / "output/pit_review_20260921"


def digest_bytes(body):
    return hashlib.sha256(body).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def verify_hash(path, expected):
    actual = digest_bytes(Path(path).read_bytes())
    if actual != expected:
        raise ValueError(f"Evidence hash mismatch: {path}")
    return {"path": str(Path(path).resolve()), "sha256": actual}


def verify_prior(prior):
    """Check saved proof bodies, not just the prior verdict labels."""
    document = read_json(prior / "verification.json")
    ids = [r["series_id"] for r in document["series"]]
    if len(ids) != 37 or len(set(ids)) != 37:
        raise ValueError("Expected 37 unique series in this reviewed snapshot")
    if sum(r["rows"] for r in document["series"]) != 47483:
        raise ValueError("Snapshot row-count mismatch")
    checks = [verify_hash(prior / x["file"], x["sha256"]) for x in document["inputs"]]
    bodies = [verify_hash(x["path"], x["sha256"]) for x in document["evidence"]]
    return document, {"summaries": checks, "external_bodies_rehashed": len(bodies)}


def verify_policy(directory):
    from engine.regime_inputs import digest, read_context

    bundle = read_context(directory / "context.json")
    if len(bundle["contexts"]) != 1:
        raise ValueError("Unexpected policy context set")
    source = bundle["contexts"][0]["source"]
    approval = read_json(directory / "approval.json")
    if approval["source_sha256"] != digest(source):
        raise ValueError("Policy approval does not bind source")
    evidence = []
    for item in approval["evidence"]:
        location = item.get("local_path", item["uri"])
        if location.startswith("s3://"):
            location = directory.parent / "bronze_mirror" / urlsplit(location).path.lstrip("/")
        evidence.append(verify_hash(location, item["sha256"]))
    if (approval.get("purpose") != "DIAGNOSTIC_ONLY"
            or approval.get("publication_time_verified") is not False
            or approval.get("intraday_allowed") is not False
            or approval.get("factor_feature_allowed") is not False):
        raise ValueError("Policy review scope changed; manual review required")
    return {
        "existing_approval_only": True,
        "source_id": source["source_id"],
        "context_id": source["context_id"],
        "scope": source["scope"],
        "purpose": approval["purpose"],
        "publication_time_verified": False,
        "publication_date_verified": approval["publication_date_verified"],
        "availability_basis": approval["availability_basis"],
        "source_sha256": approval["source_sha256"],
        "evidence_bodies_rehashed": len(evidence),
        "monthly_rows": len(source["rows"]),
        "raw_fmp_series_approved": False,
    }


def inspect_legacy(source, migration):
    """Static contract evidence, explicitly not a production DB recertification."""
    assignments = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"SYMBOLS", "MATURITIES"}:
                    assignments[target.id] = ast.literal_eval(node.value)
    if set(assignments) != {"SYMBOLS", "MATURITIES"}:
        raise ValueError("Legacy series declarations not found")
    compact = " ".join(migration.split())
    safeguards = {
        "receipt_timestamp_written": "received_at, uri, context.run_id" in source,
        "payload_revision_hash": "revision = hashlib.sha256" in source,
        "insert_does_not_overwrite": "ON CONFLICT DO NOTHING" in source,
        "asof_uses_receipt_cutoff": "r.observed_at<=cutoff" in compact,
        "latest_view_explicitly_ex_post": "backfilled revisions are NOT historical PIT features" in migration,
        "quality_guard_present": "FMP regime observation requires certified quality run" in migration,
    }
    if not all(safeguards.values()):
        raise ValueError("Expected legacy receipt/asof contract changed")
    rows = []
    for symbol, kind in assignments["SYMBOLS"].items():
        rows.append({"series_id": symbol, "kind": kind, "metrics": ["close"]})
    rows.append({"series_id": "US_TREASURY", "kind": "yield", "metrics": list(assignments["MATURITIES"])})
    for row in rows:
        row.update(
            status="HISTORICAL_VINTAGE_NOT_REVIEWED",
            observation_date_semantics="US session / Treasury observation date; not receipt date",
            publication_time_evidence="NOT_ROW_LEVEL_VERIFIED",
            value_vintage_evidence="PAYLOAD_REVISIONS_FROM_ACTUAL_COLLECTION_ONLY",
            system_known_at_evidence="OBSERVED_AT_ASOF_CODE_PRESENT",
            row_level_database_check="NOT_PERFORMED_THIS_REVIEW",
            historical_backtest_approved=False,
            prospective_use="Only actually received records at cutoff; requires deployment/DB validation",
            remaining_requirements=["HISTORICAL_CORRECTION_VINTAGES", "SESSION_OR_RELEASE_AVAILABILITY", "ROW_LEVEL_RECEIPT_VALIDATION"],
        )
    return {"code_safeguards": safeguards, "series": rows,
            "series_count": len(rows), "metric_count": sum(len(r["metrics"]) for r in rows),
            "new_pit_approval": False}


def new_series_review(row):
    symbol, kind = row["series_id"], row["kind"]
    policy = symbol == "KR_POLICY_RATE"
    timing = {
        "cot": "POSITION_ASOF_IS_NOT_PUBLICATION; 13 known delayed report dates per contract",
        "fx": "PROVIDER_EOD_DATE; precise session/DST contract not verified",
        "etf": "US_SESSION_DATE; Korean availability requires next-day/session handling",
        "index": "US_SESSION_DATE; Korean availability and restatement timing not verified",
        "macro": "PROVIDER_UTC_EVENT_TIMESTAMP; not independently verified for every row",
    }[kind]
    vintages = "FIRST_AND_SUBSEQUENT_RELEASE_VERSIONS_NOT_RECONSTRUCTED"
    if kind == "cot":
        vintages = "CURRENT_OFFICIAL_HISTORY_MATCHES; first and revised historical versions not reconstructed"
    if symbol.startswith("KR_CPI"):
        vintages = "DATED_RELEASE_PAGES_COMPARED; pages can be replaced; first-version completeness not established"
    if policy:
        vintages = "SEPARATE_OFFICIAL_POLICY_DECISION_MONTH_END_CONTEXT_APPROVED; raw FMP fields not approved"
    return {
        "series_id": symbol, "kind": kind, "rows": row["rows"],
        "first": row["first"], "latest": row["latest"],
        "status": "EXISTING_DERIVED_CONTEXT_ONLY" if policy else "HISTORICAL_PIT_EVIDENCE_INCOMPLETE",
        "source_integrity": row["source_integrity"],
        "current_value_comparison": row["independent_value_check"],
        "publication_time_evidence": timing,
        "value_vintage_evidence": vintages,
        "system_known_at_evidence": "Actual 2026 receipt retained; prior source-integrity audit bound to raw manifests",
        "raw_series_historical_backtest_approved": False,
        "derived_context_exists": policy,
        "remaining_requirements": list(row["remaining_requirements"]),
        "not_approved_is_not_proven_contamination": True,
    }


def cpi_supplement(prior_rows):
    matches = [r for r in prior_rows if r["series_id"] == "KR_CPI_MOM" and r["reference_month"] == "2024-04"]
    if len(matches) != 1 or matches[0]["fmp_actual"] != 0 or matches[0]["official_value"] != 0.1:
        raise ValueError("CPI case changed; manual source review required")
    return {
        "series_id": "KR_CPI_MOM", "reference_month": "2024-04",
        "fmp_actual": 0.0, "current_mods_headline_actual": 0.1,
        "dated_briefing_actual": 0.0, "briefing_date": "2024-05-02",
        "official_briefing_url": "https://www.korea.kr/news/policyNewsView.do?newsId=156628649",
        "current_release_url": matches[0]["official_url"],
        "finding": "FMP_MATCHES_CURRENTLY_PRESERVED_DATED_OFFICIAL_BRIEFING",
        "interpretation": "The latest official page mismatch is not sufficient evidence of FMP error or look-ahead contamination.",
        "briefing_contains_other_field_correction_notice": True,
        "correction_notice_scope": "Cost-of-living CPI YoY 5.3 to 3.5, not the headline MoM comparison",
        "reviewed_via": "web tool direct page inspection, 2026-09-21 KST",
        "raw_http_body_saved": False,
        "local_fetch_failure": "Sandbox DNS unavailable; successful independent web tool inspection",
        "new_pit_approval": False,
        "remaining_requirements": ["HEADLINE_REVISION_REASON_AND_EFFECTIVE_PUBLICATION_DATE", "ALL_MONTH_FIRST_VERSION_PROVENANCE"],
    }


def alternatives():
    return {
        "review_scope": "Two Korean ALFRED series and official help inspected; no API key or observations fetched",
        "candidates": [
            {"id": "CPALTT01KRM657N", "url": "https://alfred.stlouisfed.org/series?seid=CPALTT01KRM657N",
             "semantics": "OECD Korea monthly CPI growth rate previous period, NSA",
             "latest_observation_shown": "2024-03", "metadata_release_history_starts": "2013-06-03",
             "full_2015_2026_replacement": False,
             "limits": ["Stops before target end date", "Vintage observation coverage not downloaded", "OECD release not necessarily Korean initial release; precision differs"]},
            {"id": "KORPROINDMISMEI", "url": "https://alfred.stlouisfed.org/series?seid=KORPROINDMISMEI",
             "semantics": "OECD Korea total industry excluding construction, monthly seasonally adjusted index",
             "latest_observation_shown": "2024-03", "metadata_release_history_starts": "2011-04-11",
             "full_2015_2026_replacement": False,
             "limits": ["Stops before target end date", "Index vs FMP growth-rate mapping not approved", "Base-year vintage changes require causal transformation"]},
        ],
        "official_help_url": "https://alfred.stlouisfed.org/help",
        "release_date_caveat": "ALFRED may use source release date, provider date, or first FRED availability when earlier dates are unknown",
        "growth_rate_caveat": "Rates derived from rounded index levels can differ from original release rates",
        "initial_release_api_url": "https://fred.stlouisfed.org/docs/api/fred/series_observations.html",
        "initial_release_only_is_insufficient": "Historical latest-known reconstruction also needs later revisions before each decision cutoff",
        "new_source_approved": False,
    }


def build_review(prior=PRIOR, policy=POLICY, upstream=UPSTREAM):
    old, integrity = verify_prior(prior)
    existing_policy = verify_policy(policy)
    source_path = upstream / "pipeline/fmp_regime.py"
    migration_path = upstream / "pipeline/silver_quality/migrations/017_fmp_regime.sql"
    legacy = inspect_legacy(source_path.read_text(), migration_path.read_text())
    series = [new_series_review(r) for r in old["series"]]
    supplement = cpi_supplement(old["cpi_row_checks"])
    mom = next(r for r in series if r["series_id"] == "KR_CPI_MOM")
    mom["current_value_comparison"] = "139_CURRENT_PAGE_MATCHES; APR2024_MATCHES_DATED_OFFICIAL_BRIEFING_NOT_CURRENT_PAGE"
    mom["remaining_requirements"] = [r for r in mom["remaining_requirements"] if r != "RESOLVE_2024_APRIL_0_VS_0_1"]
    mom["remaining_requirements"].append("APR2024_HEADLINE_REVISION_TIMING_AND_REASON")
    for row in series:
        if row["series_id"].startswith("KR_CPI"):
            row["remaining_requirements"] = [
                "USE_VERIFIED_2017_SEPT_OFFICIAL_DATE_IN_NEW_DERIVED_INPUT" if r == "RESOLVE_2017_SEPT_RELEASE_DATE" else r
                for r in row["remaining_requirements"]]
    return {
        "schema_version": "fmp-pit-evidence-review-v1", "review_date_kst": "2026-09-21",
        "scope": "FMP 37 new Bronze series plus 9 legacy pipeline series (20 metrics)",
        "new_series": series, "legacy_pipeline": legacy, "existing_policy_context": existing_policy,
        "integrity": integrity,
        "source_files": [{"path": str(p), "sha256": digest_bytes(p.read_bytes())} for p in
                         (prior / "verification.json", policy / "context.json", policy / "approval.json", source_path, migration_path)],
        "new_cpi_evidence": supplement, "bounded_alternative_review": alternatives(),
        "all_historical_pit_verified": False, "new_historical_approvals": 0,
        "existing_derived_context_approvals": 1,
        "approval_or_source_mutated": False, "database_read_or_write": False,
        "all_pit_requirement_not_achieved": "Historical release vintages not present for 36 new series and 9 legacy series; receipt cutoff code alone does not establish historical public availability.",
        "next_step_priority": [
            "Use only independently approved policy context; show other axes as UNKNOWN/BLOCKED, never backfill with latest values",
            "Complete CPI dated briefing/first-release/correction ledger; the April 2024 finding resolves neither every month nor correction timing",
            "COT actual release/correction calendar plus first-vintage source data; do not use position date + 3 days",
            "FX/ETF/index exact session, correction policy and feature-specific adjustment invariance; no blanket adjusted-price failure",
            "Obtain vendor historical-vintage or original-release archive when bounded public search cannot supply it",
        ],
    }


def render(review):
    counts = Counter(r["kind"] for r in review["new_series"])
    lines = ["# FMP PIT 근거 재심사 — 2026-09-21", "",
             "**전체 역사적 PIT 인증 완료 아님. 신규 승인 0, 기존 정책금리 월말 파생 입력 승인 1개 유지.**",
             "소스 검색을 제한하고 보존된 근거를 재검사했다. 미확인은 오염 확정도, 승인도 아니다.", "",
             "## 이번 확인", "",
             f"- 신규 Bronze 37계열 47,483행: {dict(counts)}.",
             f"- 이전 검증 요약 4개, 공식 원문 {review['integrity']['external_bodies_rehashed']}개 hash 재검사.",
             f"- 정책금리 승인·source 결합 및 근거 {review['existing_policy_context']['evidence_bodies_rehashed']}개 hash 재검사. 월말 140행, 2015-01~2026-08 진단용만.",
             "- 기존 FMP 9 series/20 metric의 실제 수집시각·revision·asof 코드 검토. 실제 RDS 행은 이번에 조회하지 않았다.",
             "- 원본·승인·registry·DB·campaign·OOS 변경 없음. 테스트 통과는 역사적 PIT 인증이 아니다.", "",
             "## 새로 해소한 CPI 단서", "",
             "2024-04 headline CPI 전월비는 FMP 0.0%, 현재 통계기관 자료 0.1%이지만,",
             "[2024-05-02 공식 브리핑](https://www.korea.kr/news/policyNewsView.do?newsId=156628649)은 변동 없음(0.0%)이다.",
             "따라서 이 차이를 FMP 오류 또는 수정 후 값 누출로 단정하지 않는다. 현재 보존된 당시 브리핑과 FMP가 일치한다.",
             "같은 브리핑의 별도 생활물가 지표에는 정정 표시가 있으므로 원문 전체 불변성을 주장하지 않는다.",
             "headline 0.1%의 정정 이유·시점과 다른 월의 최초본은 미확인이다. 신규 사용 승인은 발급하지 않았다.",
             "로컬 HTTP는 DNS 제한으로 원문 저장 실패, web 도구의 공식 페이지 직접 열람은 성공했다.", "",
             "## 3가지 시점을 분리한 판정", "",
             "| 계열 | 행 | 공개시점·값 vintage 증거 | 상태 |", "|---|---:|---|---|"]
    for row in review["new_series"]:
        lines.append(f"| {row['series_id']} | {row['rows']} | {row['publication_time_evidence']}; {row['value_vintage_evidence']} | {row['status']} |")
    lines += ["", "각 계열의 실제 수신시각은 2026년 원본 수집시각이다. 2015년 대상 날짜에 과거 수신시각을 붙이지 않는다.",
              "raw 정책금리 105행 전체가 승인된 것이 아니라, 공식 결정으로 정제한 별도 월말 context만 승인됐다.", "",
              "## 기존 FMP 경로", "",
              "| series | metric 수 | 판정 |", "|---|---:|---|"]
    for row in review["legacy_pipeline"]["series"]:
        lines.append(f"| {row['series_id']} | {len(row['metrics'])} | {row['status']} |")
    lines += ["", "`fmp_regime_asof(cutoff)`는 observed_at 이하만 조회한다. 2026년 백필은 2015년 cutoff에 나타나지 않아야 한다.",
              "이는 수집 이후 재현을 위한 올바른 방어다. 과거 처음 공개된 값/시간을 재구성했다는 뜻은 아니다.",
              "`CERTIFIED`는 shape/date/OHLC 등의 품질 검사이고, 역사적 vintage 인증서가 아니다.", "",
              "## ALFRED 대안의 실제 확인 범위", "",
              "[한국 CPI MoM CPALTT01KRM657N](https://alfred.stlouisfed.org/series?seid=CPALTT01KRM657N)과",
              "[한국 산업생산 KORPROINDMISMEI](https://alfred.stlouisfed.org/series?seid=KORPROINDMISMEI)를 직접 확인했다.",
              "둘 다 표시된 최신 관측은 2024-03이라 목표 전체기간을 바로 대체하지 못한다. 과거 vintage 행은 이번에 내려받지 않았다.",
              "CPI는 OECD 경유 전월비, 산업생산은 계절조정 지수라 FMP 성장률과의 정의·단위 매핑도 필요하다.",
              "[ALFRED 도움말](https://alfred.stlouisfed.org/help)은 발표일을 모르면 공급자 날짜 또는 FRED 최초 가용일을 사용하고,",
              "반올림된 수준에서 계산한 증가율이 원발표 증가율과 다를 수 있다고 설명한다. ALFRED도 무조건 한국 최초발표와 같지 않다.", "",
              "## 완료 조건과 제한", "",
              "최초값만 비교하는 데 그치지 않고 각 판단일 이전에 공개된 최신 수정 버전을 재현해야 한다.",
              "값 변경 없음, 타기관 현재값 일치, 고정 lag, 데이터 보유기간만으로 승인하지 않는다.",
              "역사적 원본이 없는 계열은 vendor vintage/공식 원본 제공이 필요하며, 시간 제한 내 검색 종료를 검증 완료로 바꾸지 않는다.",
              "사용 가능한 축만 연결한 진단 레이어와 전 계열 인증 완료는 별도의 결과다.", "",
              "재현: `.venv/bin/python -m scripts.audit_fmp_pit_evidence` (이미 존재하는 출력은 내용 일치할 때만 허용).", ""]
    return "\n".join(lines)


def write_once(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f"Refusing to overwrite evidence: {path}")
    else:
        path.write_bytes(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    review = build_review()
    write_once(args.output / "fmp_review.json", (json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode())
    write_once(args.output / "fmp_review.md", render(review).encode())
    print(json.dumps({"new_series": len(review["new_series"]), "legacy_series": review["legacy_pipeline"]["series_count"],
                      "new_approvals": 0, "all_historical_pit_verified": False, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
