"""Render the observed admission overlay, never invent strategy performance."""
import argparse
from collections import Counter
from pathlib import Path

from engine.phenomenon_reference_collection import read_collection_program
from engine.research_generation import digest, _immutable
from scripts.publish_reference_expansion import load_json

ROOT = Path(__file__).resolve().parents[1]
STATUS_KO = {"ADMITTED": "입고 가능", "NEEDS_DATA": "자료 보강 필요", "REJECTED": "입고 거절",
             "UNVERIFIED_SNAPSHOT_ONLY": "동결 원본 진단만 완료"}


def render(report, readiness=None):
    if report.get("admission_sha256") != digest({k: v for k, v in report.items() if k != "admission_sha256"}):
        raise ValueError("Admission digest mismatch")
    if readiness and readiness["program_sha256"] != report["program_sha256"]:
        raise ValueError("Readiness report is for another program")
    rows = report["decisions"]
    live = report["live_database_verified"] and report["origin"] == "OBSERVED"
    lines = ["# 레퍼런스 입고 평가 결과", "",
             "**실제 Gold 전 행 대조 완료.**" if live else "**동결 원본 진단 또는 합성 검사이며 실제 입고 확정이 아니다.**", "",
             f"- 대상: {len(rows):,}개 측정값, {sum(r['rows'] for r in rows):,}행.",
             "- 입고는 연구용 측정값 사용 허용이다. 알파·실거래 승인과 다르다.",
             "- 수익률은 입고 평가에 사용하지 않았다. 기존 Gold 값은 변경하지 않았다.",
             "- PIT_ASSUMED: 최초 발표 빈티지를 독립적으로 입증했다는 뜻이 아니다.", "",
             "| 입고 상태 | 개수 |", "| --- | ---: |"]
    for status, count in sorted(Counter(r["status"] for r in rows).items()):
        lines.append(f"| {STATUS_KO[status]} | {count} |")
    lines.extend(["", "## 전략 평가 상태", "",
                  "이 보고서는 입고 결과다. 실제 수익률 기반 전략 선택 결과는 포함하지 않는다."])
    if readiness:
        lines.extend(["", f"실제 DB 준비 상태 확인 시각: {readiness['observed_at']}", ""])
        for item in readiness["blockers"]:
            lines.append(f"- `{item['code']}`: {item.get('reason') or item['note']}")
    lines.extend(["", "## 108개 평가 내역" if len(rows) == 108 else "## 평가 내역", "",
                  "종목 수는 해당 지표에서 관측된 고유 종목 수이고, 관측 월 수는 지표 전체의 월 수다.",
                  "모든 종목이 해당 월 수만큼 존재한다는 뜻이 아니며, KRX 전체 대비 커버리지도 아니다.", "",
                  "| 지표 | 분류 | 상태 | 관측 월 | 종목 수 | 최초 월말 | 최신 월말 | 사유 |",
                  "| --- | --- | --- | ---: | ---: | --- | --- | --- |"])
    for row in sorted(rows, key=lambda r: (r["family"] or "", r["reference_id"])):
        reason = "; ".join(row["errors"] + row["data_gaps"] + row["warnings"]) or "기준 충족"
        name = row["name_ko"].replace("|", " / ")
        lines.append(f"| {name}<br>`{row['reference_id']}` | {row['family']} | {STATUS_KO[row['status']]} | {row['observed_months']} | {row['assets']:,} | {row['first_date']} | {row['latest_date']} | {reason} |")
    lines.extend(["", "## 고정 연결", "", f"- Program: `{report['program_sha256']}`",
                  f"- Admission: `{report['admission_sha256']}`", "",
                  "별도의 전략 결과가 없는데 입고 가능을 ‘성과 검증 완료’로 해석하지 않는다.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", required=True)
    parser.add_argument("--readiness")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = load_json(args.admission)
    program, _, _ = read_collection_program(ROOT)
    if program["program_sha256"] != report["program_sha256"]:
        raise ValueError("Report does not describe the active program")
    body = render(report, load_json(args.readiness) if args.readiness else None)
    _immutable(args.output, body.encode())
    print({"output": str(args.output), "references": len(report["decisions"]), "status": report["status"]})
