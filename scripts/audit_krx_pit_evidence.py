"""Read-only local KRX PIT evidence audit; never grants input approval.

Reads source code and Bronze Parquet only, not campaign caches/results or OOS.
Name comparisons reproduce the upstream last-name-wins rule at ticker level;
they are not a count of affected RDS assets, eligible factor rows, or returns.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pyarrow.parquet as pq


PREFERRED = re.compile(r"(?:\d*우(?:[A-Z])?|우선주)$")
SPAC = re.compile(r"스팩|SPAC", re.I)
INDEX_NAMES = {"코스피": "KOSPI", "코스닥": "KOSDAQ",
               "코스피 200": "KOSPI200", "코스닥 150": "KOSDAQ150"}
KOSDAQ150_LAUNCH_DATE = "2015-07-13"
KOSDAQ150_LAUNCH_SOURCE = "https://www.shinhanfund.com/file/download/fundDocument/210961/description"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def name_flags(name: str) -> dict:
    return {"preferred": bool(PREFERRED.search(name)),
            "spac": bool(SPAC.search(name)), "reit": "리츠" in name}


def admission(flags: dict) -> bool:
    return not any(flags.values())


def compare_name_rows(rows: list[dict], latest: dict[str, str]) -> dict:
    """Compare month-end historical-name rules, retaining all discrepant rows."""
    mismatches = []
    directions = Counter()
    for row in rows:
        current = latest[row["stock_code"]]
        before, after = name_flags(row["historical_name"]), name_flags(current)
        if before == after:
            continue
        change = ("historically_excluded_now_admitted" if not admission(before)
                  and admission(after) else "historically_admitted_now_excluded"
                  if admission(before) and not admission(after)
                  else "classification_changed_admission_unchanged")
        directions[change] += 1
        mismatches.append({**row, "latest_name": current,
                           "historical_flags": before, "latest_flags": after,
                           "classification_effect": change})
    return {"month_end_rows": len(rows),
            "classification_mismatch_rows": len(mismatches),
            "classification_mismatch_tickers": len({r["stock_code"] for r in mismatches}),
            "directions": dict(directions), "mismatches": mismatches,
            "per_flag": {flag: {
                "rows": sum(r["historical_flags"][flag] != r["latest_flags"][flag] for r in mismatches),
                "tickers": len({r["stock_code"] for r in mismatches
                    if r["historical_flags"][flag] != r["latest_flags"][flag]})}
                for flag in ("spac", "reit", "preferred")},
            "flags_are_heuristics_not_verified_legal_classifications": True,
            "actual_rds_eligible_impact_count": None,
            "scope": "ticker-level local Bronze month-ends; no identity/DQ/age/factor gating"}


def code_evidence(repo: Path, upstream: Path) -> dict:
    paths = {"reader": repo / "engine/silver.py", "panel": repo / "engine/panel.py",
             "prices": upstream / "pipeline/silver/prices.py",
             "assets": upstream / "pipeline/silver/assets.py",
             "bronze_index": upstream / "pipeline/bronze/index.py",
             "bronze_stock": upstream / "pipeline/bronze/stock_krxapi.py"}
    evidence = {}
    nodes = {"reader": ["PRICE_SNAPSHOT_SQL"], "panel": ["from_silver_frame"],
             "prices": ["_with_adj_close", "_rescale_history_for_events", "publish"],
             "assets": ["_stock_universe", "prepare", "publish"],
             "bronze_index": ["run"], "bronze_stock": ["run"]}
    snippets = {}
    for key, path in paths.items():
        source = path.read_text()
        tree = ast.parse(source)
        spans = []
        for node in tree.body:
            name = getattr(node, "name", None)
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                name = getattr(node.targets[0], "id", None)
            if name in nodes[key]:
                snippet = ast.get_source_segment(source, node)
                snippets[name] = snippet
                spans.append({"symbol": name, "start": node.lineno,
                              "end": node.end_lineno,
                              "snippet_sha256": hashlib.sha256(snippet.encode()).hexdigest()})
        evidence[key] = {"path": str(path), "sha256": digest(path), "spans": spans}
    sql = snippets["PRICE_SNAPSHOT_SQL"]
    return {"files": evidence, "checks": {
        "price_reader_uses_available_at": "available_at" in sql,
        "price_reader_uses_trade_date_identity_intervals": all(s in sql for s in
             ("ai.valid_from <= p.trade_date", "ai.valid_to >= p.trade_date")),
        "price_reader_uses_current_asset_name": 'a.name AS "Name"' in sql,
        "price_reader_uses_current_instrument_type": "a.instrument_type" in sql,
        "price_adjustment_uses_terminal_scale": 'transform("last")' in snippets["_with_adj_close"],
        "daily_adjustment_updates_prior_rows": "UPDATE price_daily SET adj_close" in snippets["_rescale_history_for_events"],
        "upstream_names_last_value_wins": "names.update" in snippets["_stock_universe"],
    }}


def inspect_bronze(data: Path) -> tuple[dict, list[dict]]:
    inventory = []
    latest = {}
    month_rows = {}
    stock_daily_rows = 0
    stock_date_sets = defaultdict(set)
    # Ordering matches upstream assets._stock_universe: all marcap, then krxapi.
    for source in ("stock/marcap", "stock/krxapi"):
        for path in sorted((data / source).glob("date=*/*.parquet")):
            pf = pq.ParquetFile(path)
            code, name, market = (("Code", "Name", "Market") if source.endswith("marcap")
                                  else ("ISU_CD", "ISU_NM", "MKT_NM"))
            values = pf.read(columns=[code, name, market]).to_pydict()
            day = path.parent.name.removeprefix("date=")
            stock_date_sets[source].add(day)
            inventory.append({"path": str(path), "sha256": digest(path),
                              "rows": pf.metadata.num_rows, "columns": pf.schema_arrow.names})
            for ticker, label, mkt in zip(values[code], values[name], values[market]):
                ticker, label = str(ticker), str(label)
                latest[ticker] = label
                if mkt == "KOSDAQ GLOBAL":
                    mkt = "KOSDAQ"
                if mkt not in {"KOSPI", "KOSDAQ"}:
                    continue
                stock_daily_rows += 1
                key = ticker, day[:7]
                if key not in month_rows or month_rows[key]["trade_date"] <= day:
                    month_rows[key] = {"stock_code": ticker, "historical_name": label,
                        "market": mkt, "trade_date": day, "source_file": str(path)}
    index_rows = defaultdict(list)
    for path in sorted((data / "index/krxapi").glob("date=*/*.parquet")):
        pf = pq.ParquetFile(path)
        inventory.append({"path": str(path), "sha256": digest(path),
                          "rows": pf.metadata.num_rows, "columns": pf.schema_arrow.names})
        values = pf.read(columns=["BAS_DD", "IDX_NM", "CLSPRC_IDX"]).to_pydict()
        for day, name, close in zip(values["BAS_DD"], values["IDX_NM"], values["CLSPRC_IDX"]):
            if name not in INDEX_NAMES:
                continue
            compact = str(day)
            iso = f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"
            try:
                number = float(str(close).replace(",", ""))
            except ValueError:
                number = None
            index_rows[INDEX_NAMES[name]].append({"date": iso, "close": number})
    index_summary = {}
    for name, rows in index_rows.items():
        days = [r["date"] for r in rows]
        months = {d[:7] for d in days}
        index_summary[name] = {"rows": len(rows), "dates": len(set(days)),
            "first_date": min(days), "last_date": max(days), "months": len(months),
            "nonpositive_or_missing_close": sum(r["close"] is None or r["close"] <= 0 for r in rows),
            "historical_pit_approved": False,
            "reason": "Historical publication versions/actual receipt timestamps not in local Parquet; no proof of unchanged first publications."}
        if name == "KOSDAQ150":
            prelaunch = [d for d in days if d < KOSDAQ150_LAUNCH_DATE]
            index_summary[name]["launch_date_review"] = {
                "launch_date": KOSDAQ150_LAUNCH_DATE,
                "source": KOSDAQ150_LAUNCH_SOURCE,
                "evidence_access": "official fund issuer prospectus text in web search; byte copy not preserved",
                "prelaunch_rows": len(prelaunch),
                "complete_months_before_launch": len({d[:7] for d in prelaunch if d[:7] < KOSDAQ150_LAUNCH_DATE[:7]}),
                "implication": "Prelaunch dated values must not be treated as publicly disseminated on their observation dates; publication of any backcast requires separate evidence."}
    time_fields = {"known_at", "available_at", "received_at", "published_at", "observed_at", "vintage"}
    no_timing = sum(not time_fields.intersection(x["columns"]) for x in inventory)
    summary = {"stock_daily_rows_including_cross_source_overlap": stock_daily_rows,
               "stock_date_ranges": {k: {"first": min(v), "last": max(v), "dates": len(v)} for k, v in stock_date_sets.items()},
               "name_classification": compare_name_rows(list(month_rows.values()), latest),
               "index_candidates": index_summary,
               "file_count": len(inventory), "files_without_embedded_version_time_fields": no_timing,
               "file_mtime_used_as_historical_availability": False}
    return summary, inventory


def render(report: dict) -> str:
    b = report["bronze"]
    n = b["name_classification"]
    lines = ["# KRX PIT 증거 감사 — 2026-09-21", "",
        "결론: 현재 코드의 시점 방어 일부는 확인했지만, 역사적 원본 버전 전체를 PIT 승인할 증거는 부족하다. 신규 승인 0개.", "",
        "## 확인된 코드 경로", "",
        "- 종목코드는 거래일별 valid_from/valid_to를 적용한다. 반면 name/instrument_type은 현재 asset 값을 과거 전체에 사용한다.",
        "- price_daily는 동일 asset/source/trade_date 행을 upsert하며, available_at은 기본적으로 거래일 다음날 08:30 KST를 생성한다. 실제 당시 수신 로그는 아니다.",
        "- 연구 가격 조회는 available_at을 조회·필터하지 않는다. 월말 t 즉시 이용과 다음 영업일 이용은 다르며, 실행 cutoff 계약 검증이 필요하다.",
        "- adj_close는 미래 기업행사에 따라 과거 전체가 같은 배율로 재조정될 수 있다. 동일 배율은 비율·수익률에서 상쇄된다. 따라서 수정주가라는 이유만으로 수익률 오염을 판정하지 않았다. 소수점 반올림, 원가격 정정, 절대수준 결합은 별개다.", "",
        "## 실제 로컬 원본 점검", "",
        f"- Parquet {b['file_count']:,}개 SHA-256 보존. 이 중 {b['files_without_embedded_version_time_fields']:,}개에 공개/수신/버전 시각 필드가 없다.",
        f"- KOSPI/KOSDAQ 종목별 월말 {n['month_end_rows']:,}행에서 당시 이름과 최신 이름의 분류규칙을 비교했다.",
        f"- 분류 플래그 차이 {n['classification_mismatch_rows']:,}행 / {n['classification_mismatch_tickers']:,}티커.",
        f"- 차이 방향: `{json.dumps(n['directions'], ensure_ascii=False)}`.",
        f"- 플래그별 차이(중복 가능): `{json.dumps(n['per_flag'], ensure_ascii=False)}`.",
        "- 우선주 정규식은 '신우', '동우', '에코글로우' 같은 이름에도 매칭된다. 위 차이는 기존 규칙의 실제 출력 차이지 법적 종류주 여부 확인이 아니다. 과거 이름으로 단순 교체해 해결하지 않는다.",
        "- 이는 Bronze 티커 단위의 실제 분류 차이다. RDS asset_id 이력, 인증·상장기간 필터를 거친 최종 유니버스 영향 수가 아니며, 팩터 성과는 읽지 않았다.", "",
        "| Index | Rows | First | Last | Months | PIT approved |", "|---|---:|---|---|---:|---|",
    ]
    for name, row in b["index_candidates"].items():
        lines.append(f"| {name} | {row['rows']} | {row['first_date']} | {row['last_date']} | {row['months']} | No |")
    launch = b["index_candidates"].get("KOSDAQ150", {}).get("launch_date_review")
    if launch:
        lines.extend(["", f"KOSDAQ150 추가: 공식 산출 개시일 2015-07-13 이전 {launch['prelaunch_rows']}일 / 완전한 {launch['complete_months_before_launch']}개월의 값이 들어 있다. [공식 운용사 투자설명서]({KOSDAQ150_LAUNCH_SOURCE})의 개시일과 비교한 것으로, 관측일 당시 공표값으로 취급하면 안 된다. 과거 재산출치가 언제 공개됐는지는 별도 확인 대상이다."])
    lines.extend(["", "## 미확인과 필요한 조치", "",
        "1. 실제 RDS 원본의 사후 정정 건수와 영향 수는 미측정이다. 연결 시도는 EndpointConnectionError로 실패했고 비밀값은 출력하지 않았다.",
        "2. 종목 명칭·종류 이력을 source row와 asset_id 구간에 연결해 시점별 분류를 적용한다. 당일 이름을 쓴다고 SPAC 법적 상태가 완벽해지는 것은 아니므로 합병/전환 효력일 확인이 필요하다.",
        "3. 가격/규모 값에는 관측 버전과 실제 수신시각을 남긴다. 과거 자료의 수집시각을 거래일로 소급하지 않는다. 역사적 월말 사용을 승인하려면 당시 공표 이력 또는 동등한 원본 증거를 확보한다.",
        "4. 지수 종가도 공식 과거 조회라는 이유만으로 최초본이라고 승인하지 않는다. 월말 공식 종가의 공표·정정 규칙과 해당 과거 버전을 연결해야 한다.", "",
        "## 제한된 공식 소스 조사", "",
        "- [KRX 지수산출방법](https://index.krx.co.kr/contents/MKD/01/0111/01110600/MKD01110600.jsp): 현재 페이지는 확인했으나 동적 목록에서 2015+ 정정/배포 버전 전수 근거를 확보하지 못했다.",
        "- [KRX IPO 통계 안내](https://data.krx.co.kr/contents/MDC/STAT/issue/MDCSTAT201.jsp): 수정주가는 기준가격 조정비율을 과거에 소급 적용한다고 설명한다. 이는 시장지수 최초본 인증은 아니다.",
        "- [KRX 공매도 안내](https://www.krx.co.kr/contents/SRT/02/02010100/SRT02010100.jsp): T+2 이후 신규·정정 보고로 잔고가 변경될 수 있다고 명시한다. 주가/지수에도 동일 지연을 적용한다는 의미는 아니다.",
        "- 외부 페이지는 웹 도구로 읽은 근거이며 원문 바이트 SHA 보관은 하지 않았다. 이 조사만으로 승인하지 않는다.", "",
        "원본/DB/승인 registry/campaign/Gold 수정 없음. 모든 로컬 입력 파일·검토 코드 해시는 JSON에 포함한다."])
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream", type=Path, default=Path("/Users/mac/Documents/GitHub/TeamAlpha-data"))
    p.add_argument("--output", type=Path, default=Path("output/pit_review_20260921"))
    args = p.parse_args()
    for name in ("krx_review.json", "krx_review.md"):
        if (args.output / name).exists():
            raise SystemExit(f"Refusing to overwrite {args.output / name}")
    bronze, files = inspect_bronze(args.upstream / "data")
    report = {"schema_version": 1, "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "new_pit_approvals": 0, "full_historical_pit_verified": False,
        "code": code_evidence(Path(__file__).resolve().parents[1], args.upstream),
        "bronze": bronze, "input_files": files,
        "db_check": {"status": "UNAVAILABLE", "error_class": "EndpointConnectionError",
                     "note": "Bounded read-only aggregate attempted by reviewer, no query result."},
        "sealed_results_read": False, "db_or_upstream_mutated": False}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "krx_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (args.output / "krx_review.md").write_text(render(report))
    compact = {"files": bronze["file_count"], "name_mismatch_rows": bronze["name_classification"]["classification_mismatch_rows"],
               "name_mismatch_tickers": bronze["name_classification"]["classification_mismatch_tickers"],
               "index_candidates": bronze["index_candidates"], "new_pit_approvals": 0}
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
