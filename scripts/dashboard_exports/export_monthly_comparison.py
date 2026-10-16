"""Allowlisted public readiness export. Never substitute historical performance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from strategies.comparison_contract import canonical_manifest_hash
from strategies.run_monthly_comparison import read_json, save_new


def export(catalog_path, plan_path, readiness_path, audit_path, prior_path, output):
    catalog, envelope, ready, audit, prior = map(read_json, (
        catalog_path, plan_path, readiness_path, audit_path, prior_path))
    plan = envelope["plan"]
    plan_hash = canonical_manifest_hash(plan)
    if plan_hash != envelope.get("plan_sha256") or plan_hash != ready.get("plan_sha256"):
        raise ValueError("Plan/readiness identity mismatch")
    catalog_hash = hashlib.sha256(Path(catalog_path).read_bytes()).hexdigest()
    if catalog_hash != plan["catalog"]["sha256"]:
        raise ValueError("Frozen catalog changed")
    if catalog["prior_snapshot_sha256"] != hashlib.sha256(Path(prior_path).read_bytes()).hexdigest():
        raise ValueError("Historical comparison source changed")
    if ready["status"] != "BLOCKED_MISSING_EXECUTION_INPUTS" or ready["real_performance_computed"] is not False:
        raise ValueError("This exporter publishes readiness only, not performance")
    if audit["as_of"] != catalog["approval_verified_at"] or audit["read_only"] is not True:
        raise ValueError("Audit/catalog provenance mismatch")
    bindings = [{"factor_id": r["name"], "definition_hash": r["definition_hash"]} for r in catalog["factors"]]
    if bindings != plan["factor_bindings"] or len(bindings) != ready["factor_count"]:
        raise ValueError("Factor exact set mismatch")
    historical = {r["name"]: r for r in prior["factors"]}
    factors = []
    for row in catalog["factors"]:
        old_hash = historical[row["name"]].get("definition_hash")
        factors.append({key: row[key] for key in (
            "name", "version", "status", "frequency", "definition_hash", "implementation_hash",
            "predicted_sign", "lookback_translation")} | {
            "historical_definition_hash": old_hash,
            "historical_binding": "UNKNOWN" if not old_hash else
                "MATCH" if old_hash == row["definition_hash"] else "CHANGED",
            "comparison_status": "NOT_COMPUTED",
        })
    checks = [
        {"id": "identity", "label": "현재 승인 버전·정의 연결", "status": "READY",
         "detail": f"{len(factors)}개 모두 DB에서 확인하고 버전·정의·SQL 해시를 동결했습니다."},
        {"id": "plan", "label": "비교 설계·봉인 구간 보호", "status": "READY",
         "detail": "4개 방식과 기간을 고정했습니다. 실행 전 봉인 구간을 다시 검사합니다."},
        {"id": "scores", "label": "월말 점수·종목군·시가총액", "status": "PENDING",
         "detail": "Gold 값의 방향을 중복 적용하지 않습니다. 원천 가용시각과 월말 표본 연결이 필요합니다."},
        {"id": "calendar", "label": "월초 첫 세션·개장시각", "status": "PENDING",
         "detail": "특별 개장일을 포함한 첫 거래일 시각의 검증 입력이 필요합니다."},
        {"id": "asset_returns", "label": "주식 시가→시가 총수익", "status": "PENDING",
         "detail": "종가 총수익 인증과 별개입니다. 배당락일 진입 권리·기업행사·상폐를 대사해야 합니다."},
        {"id": "market_returns", "label": "동일 구간 시장 TR", "status": "PENDING",
         "detail": "KRX300 TR의 시가→시가 입력이 미연결입니다. 가격지수나 ETF로 대신 채우지 않았습니다."},
    ]
    result = {
        "schema_version": "public-monthly-comparison-readiness-v1",
        "comparison_id": Path(plan_path).parent.name,
        "as_of": catalog["approval_verified_at"], "registered_at": envelope["registered_at"],
        "status": ready["status"], "real_performance_computed": False,
        "independent_oos": False, "orders_submitted": False, "actual_fill_verified": False,
        "plan_sha256": plan_hash, "catalog_sha256": catalog_hash,
        "factor_count": len(factors), "planned_comparisons": len(factors) * len(plan["variants"]),
        "completed_comparisons": 0, "decision_start": plan["bounds"]["decision_start"],
        "decision_end": plan["bounds"]["decision_end"], "return_support_end": plan["bounds"]["return_support_end"],
        "variants": plan["variants"], "benchmark_policy": plan["benchmark_policy"],
        "costs": plan["costs"], "checks": checks, "factors": factors,
        "return_contracts": [{k: r[k] for k in (
            "source", "asset_type", "field_name", "methodology_version", "status",
            "coverage_start", "coverage_end", "certified_at")} for r in audit["return_contracts"]],
        "historical_definition_changed": sum(r["historical_binding"] == "CHANGED" for r in factors),
        "historical_definition_unknown": sum(r["historical_binding"] == "UNKNOWN" for r in factors),
        "limitations": ["과거 연구의 IC·OOS·수익률은 현재 일별 정의의 검증 결과가 아닙니다.",
                        "현재 승인 집합을 과거에 적용하는 개발용 비교이며 독립 OOS가 아닙니다.",
                        "현재 승인 사실은 과거 시점에도 승인되었다는 의미가 아닙니다.",
                        "비용은 기존 연구 가정이며 실제 체결·세법·운용규모별 충격 인증이 아닙니다."],
        "source_links": [{"label": "KRX 총수익지수 안내 (지수 존재 확인; 입력 확보와 별개)",
                          "url": "https://index.krx.co.kr/contents/MKD/03/0306/03060600/MKD03060600.jsp"}],
    }
    save_new(output, result)
    return {"status": result["status"], "factors": len(factors), "published_performance": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "plan", "readiness", "audit", "prior", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.catalog, args.plan, args.readiness, args.audit, args.prior, args.output)))
