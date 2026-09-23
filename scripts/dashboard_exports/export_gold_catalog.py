"""Export sanitized Gold metadata; never reads values or executes research.

Local snapshot (no credentials needed):
  .venv/bin/python scripts/dashboard_exports/export_gold_catalog.py --local
Live metadata, after the existing SSM tunnel and AWS login are available:
  AWS_PROFILE=teamalpha AWS_DEFAULT_REGION=ap-northeast-2 \
    SILVER_DB_HOST_OVERRIDE=localhost SILVER_DB_PORT_OVERRIDE=5432 \
    .venv/bin/python scripts/dashboard_exports/export_gold_catalog.py --live

Only live mode imports the existing read-only connection. It does not start or
stop tunnels, log in, bootstrap schemas, change configuration, or write to RDS.
Failures are redacted and never silently relabeled as a current catalog.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "output/research-dashboard-source/gold-catalog.json"

MEANINGS = {
    "adv20_to_book_equity": "최근 20거래일 평균 거래대금 / 양의 자본총계",
    "asset_to_market": "자산총계 / 양의 시가총액",
    "book_to_market_change_12m": "자본총계/시가총액 비율의 12개월 전 대비 차이",
    "book_to_market_change_6m": "자본총계/시가총액 비율의 6개월 전 대비 차이",
    "capital_stock_growth_18m": "18개월 전 대비 자본금 증가율",
    "capital_stock_to_assets": "자본금 / 양의 자산총계",
    "current_asset_turnover": "최근 12개월 매출 / 양의 유동자산",
    "current_liabilities_to_sales": "유동부채 / 양의 최근 12개월 매출",
    "enterprise_sales_yield_change_6m": "매출/(시가총액+총부채) 비율의 6개월 전 대비 차이; 현금 차감 EV는 아님",
    "idiosyncratic_volatility_24m": "24개월 월수익률에서 전월 시가총액 가중 시장수익으로 설명되지 않는 잔차 변동성",
    "max_daily_return_instability_18m": "월별 최대 일수익률의 18개월 표준편차",
    "max_daily_return_mean_6m": "월별 최대 일수익률의 6개월 평균",
    "net_equity_issuance_price_adjusted_36m": "시가총액/분할조정종가 비율의 36개월 증가율; 가격조정 발행량 대용치",
    "net_income_to_liabilities": "최근 12개월 순이익 / 양의 총부채",
    "net_margin_volatility_12m": "최근 12개월 순이익/매출 비율의 12개월 표준편차",
    "net_working_capital_yield": "(유동자산−유동부채) / 양의 시가총액",
    "nonoperating_burden_margin": "(최근 12개월 영업이익−순이익) / 양의 최근 12개월 매출",
    "operating_earnings_yield": "최근 12개월 영업이익 / 양의 시가총액",
    "pretax_yield_change_6m": "세전이익/시가총액 비율의 6개월 전 대비 차이",
    "price_range_12m": "12개월 월말 분할조정종가의 최고/최저 비율 − 1",
    "realized_daily_volatility_change_24m": "252거래일 일수익률 변동성의 24개월 전 대비 증가율",
    "realized_daily_volatility_instability_6m": "252거래일 일수익률 변동성의 최근 6개월 표준편차",
    "retained_earnings_to_assets_volatility_12m": "이익잉여금/총자산 비율의 12개월 표준편차",
    "retained_earnings_to_equity": "이익잉여금 / 양의 자본총계",
    "revenue_to_noncurrent_assets": "최근 12개월 매출 / 양의 비유동자산",
    "market_leverage": "총부채 / 양의 시가총액",
    "max_daily_return_1m": "최근 한 달 최대 일수익률; 최소 10개 관측",
    "net_equity_issuance_price_adjusted_12m": "시가총액/분할조정종가 비율의 12개월 증가율; 가격조정 발행량 대용치",
    "operating_income_to_current_liabilities": "최근 12개월 영업이익 / 양의 유동부채",
    "operating_income_to_liabilities": "최근 12개월 영업이익 / 양의 총부채",
    "operating_return_on_capital_employed": "최근 12개월 영업이익 / 양의 (총자산−유동부채)",
    "paid_in_capital_ratio": "자본금 / 양의 자본총계",
    "realized_volatility_252d": "최근 252거래일 일수익률 변동성; 최소 126개 관측",
    "return_kurtosis_24m": "분할조정종가 월수익률의 24개월 초과첨도",
    "trading_turnover_20d": "최근 20거래일 평균 거래대금 / 양의 시가총액",
    "turnover_volatility_12m": "평균 거래대금/시가총액 로그 비율의 12개월 표준편차",
}
METRIC_KEYS = (
    "research_start", "evaluation_phase", "ic_full", "ic_investable",
    "ic_std_investable", "rank_icir_investable", "neutral_ic", "months",
    "gross", "cost", "net", "net_ir", "turnover", "oos_start", "oos_end",
    "oos_months", "oos_ic", "oos_ic_retention", "sharpe", "net_sharpe",
    "oos_sharpe", "hac_pvalue", "ic_p_investable", "oos_ic_p",
)
UNITS = {
    "ic_investable": "dimensionless monthly mean Spearman correlation, decimal",
    "oos_ic": "dimensionless monthly mean Spearman correlation, decimal",
    "rank_icir_investable": "monthly mean Rank IC / monthly Rank IC sample SD; NOT annualized",
    "gross": "annualized arithmetic portfolio excess return, percentage points (monthly mean × 12 × 100)",
    "cost": "annualized modeled trading cost, percentage points (monthly mean × 12 × 100)",
    "net": "annualized arithmetic excess return after modeled cost, percentage points; NOT CAGR",
    "net_ir": "annualized excess-return information ratio (monthly mean/SD × sqrt(12)); NOT Sharpe",
    "turnover": "annualized turnover percent (monthly mean one-way turnover × 12 × 100)",
    "months": "valid portfolio diagnostic months; may differ from IC evaluation months",
    "sharpe": "legacy field: exact legacy period/risk-free/cost convention must be separately verified",
}
LIMITATIONS = [
    "APPROVED is a catalog status, not a guarantee of future returns or a portfolio recommendation.",
    "fr-3 uses Rank IC evidence; legacy Sharpe gates and fr-3 Rank IC/Rank ICIR are not interchangeable or one leaderboard.",
    "Portfolio net/gross/cost are annualized arithmetic excess percentage points, not decimal returns or CAGR; net_ir is not Sharpe.",
    "Historical reused OOS is not new independent prospective evidence; preserve each campaign evidence class.",
    "No factor_value rows, sealed results, new backtests, or research evaluations were read or run.",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def finite_metrics(values):
    return {k: v for k in METRIC_KEYS if (v := values.get(k)) is not None
            and isinstance(v, (int, float, str))
            and (not isinstance(v, float) or math.isfinite(v))}


def literal(node, constants):
    if isinstance(node, ast.Name):
        return constants[node.id]
    if isinstance(node, ast.Dict):
        return {literal(k, constants): literal(v, constants) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)):
        return [literal(x, constants) for x in node.elts]
    return ast.literal_eval(node)


def local_definitions():
    index_path = ROOT / "research/memory/factor_index.json"
    index = read(index_path)
    registry = {d["name"]: d for d in index["observed_registry_rows"]}
    result = {}
    for definition in index["definitions"]:
        name = definition["name"]
        if name not in MEANINGS:
            continue
        path = ROOT / definition["source_path"]
        if not path.exists() or sha(path) != definition.get("source_sha256"):
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        constants, factor = {}, None
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            try:
                value = literal(node.value, constants)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = value
            except (ValueError, TypeError, KeyError):
                pass
            if any(isinstance(t, ast.Name) and t.id == "FACTOR" for t in node.targets):
                if isinstance(node.value, ast.Call):
                    factor = {kw.arg: literal(kw.value, constants)
                              for kw in node.value.keywords if kw.arg != "compute"}
        if factor is None or factor.get("name") != name:
            continue
        result[name] = {
            "family": factor.get("family"), "category": factor.get("category"),
            "exploration_domain": factor.get("exploration_domain"),
            "hypothesis": factor.get("hypothesis"), "meaning": MEANINGS[name],
            "definition_hash": registry.get(name, {}).get("definition_hash"),
            "predicted_sign": factor.get("predicted_sign"),
            "params": factor.get("params"), "rebalance_months": factor.get("rebalance_months"),
            "needs": factor.get("needs"), "source_sha256": sha(path),
            "definition_source": relative(path),
            "definition_binding": "LOCAL_INDEX_SOURCE_SHA_VERIFIED; live Gold binding unverified",
        }
    return result


def public_confirmations(names, definitions):
    results = {}
    for path in sorted((ROOT / "research/campaigns").glob("*/manifest.json")):
        manifest = read(path)
        if manifest.get("status") != "REVEALED":
            continue
        qualified = {x["name"]: x for x in manifest.get("qualified_factors", [])}
        targets = set(qualified) & set(names)
        if not targets or not manifest.get("confirmation_result"):
            continue
        result_path = ROOT / manifest["confirmation_result"]
        result = read(result_path)
        if digest(result) != manifest.get("confirmation_result_digest"):
            continue
        for item in result.get("confirmations", []):
            name = item.get("factor")
            if name not in targets or item.get("verdict") != "PROMOTE":
                continue
            definition = definitions.get(name, {})
            if (item.get("definition_hash") != definition.get("definition_hash")
                    or item.get("strategy_sha256") != definition.get("source_sha256")):
                continue
            metrics = finite_metrics(item.get("evaluation", {}).get("metrics", {}))
            results[name] = {
                "performance": metrics,
                "performance_basis": {
                    "period": {
                        "discovery_signal_start": metrics.get("research_start"),
                        "discovery_signal_end": manifest.get("discovery", {}).get("signal_end"),
                        "discovery_return_end": manifest.get("discovery", {}).get("return_end"),
                        "oos_signal_start": result.get("oos_start"),
                        "oos_signal_end": result.get("oos_end"),
                        "oos_return_start": manifest.get("oos", {}).get("return_start"),
                        "oos_return_end": manifest.get("oos", {}).get("return_end"),
                    },
                    "rule": manifest.get("ruleset_version"), "units": UNITS,
                    "evidence_class": manifest.get("oos", {}).get("evidence_class", "NOT_RECORDED"),
                    "revealed_at": result.get("revealed_at"),
                    "campaign_id": manifest.get("campaign_id"),
                    "confirmation_digest_verified": True,
                    "definition_file_sha_verified": True,
                    "portfolio_rule": "Discovery-period long-only top 20% equal-weight diagnostic, fixed investable universe benchmark, declared rebalance_months, modeled commission/impact/tax. Not an OOS portfolio return.",
                    "role": "Published research confirmation metrics; portfolio metrics are diagnostics, not fr-3 promotion criteria.",
                },
                "refs": [relative(path), relative(result_path), "engine/gate.py"],
            }
    return results


def base_row(name, definitions):
    definition = definitions.get(name, {})
    return {
        "name": name, "status": "APPROVED", "current_status_verified": False,
        "family": None, "category": None, "hypothesis": None, "meaning": None,
        "definition_hash": None, **definition,
        "performance": {},
        "performance_basis": {"period": None, "rule": None, "units": UNITS,
                              "evidence_class": "UNAVAILABLE", "role": "No verified matching public performance artifact found."},
        "source_refs": [definition["definition_source"]] if definition else [],
        "limitations": [] if definition else ["Only name/approval-set membership is available in this checkout; definition and hypothesis not verified."],
    }


def local_export():
    manifests = list((ROOT / ".cache/gold-signals").glob("*/manifest.json"))
    if not manifests:
        raise RuntimeError("No local Gold generation metadata")
    path = max(manifests, key=lambda p: p.stat().st_mtime_ns)
    snapshot = read(path)
    generation = snapshot["generation"]
    names = generation["approved_factor_keys"]
    if len(set(names)) != generation["approved_factor_count"]:
        raise RuntimeError("Local approved set count mismatch")
    source = "LOCAL_GOLD_GENERATION_CACHE_NOT_LIVE"
    observed_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    time_basis = "Local cache filesystem write time; database snapshot observation time is not recorded."
    # Public confirmation stores every approved comparator's coverage, but it is
    # an earlier observation and must never be represented as current RDS state.
    for campaign_path in sorted((ROOT / "research/campaigns").glob("*/manifest.json")):
        campaign = read(campaign_path)
        if campaign.get("status") != "REVEALED" or not campaign.get("confirmation_result"):
            continue
        confirmation_path = ROOT / campaign["confirmation_result"]
        confirmation = read(confirmation_path)
        if digest(confirmation) != campaign.get("confirmation_result_digest"):
            continue
        stamp = confirmation.get("revealed_at", "")
        if not stamp or datetime.fromisoformat(stamp) <= datetime.fromisoformat(observed_at):
            continue
        observed_sets = [set(c.get("evaluation", {}).get("metrics", {}).get("gold_signal_comparison_months", {}))
                         for c in confirmation.get("confirmations", [])]
        observed_sets = [s for s in observed_sets if s]
        if not observed_sets or not all(s == observed_sets[0] for s in observed_sets):
            continue
        names = sorted(observed_sets[0])
        path, observed_at = confirmation_path, stamp
        source = "LOCAL_REVEALED_CONFIRMATION_GOLD_COMPARISON_SET_NOT_LIVE"
        time_basis = "Published confirmation timestamp for the prior approved Gold comparison set; current catalog not verified."
    definitions = local_definitions()
    confirmations = public_confirmations(names, definitions)
    rows = []
    for name in sorted(names):
        row = base_row(name, definitions)
        row["approval_evidence"] = source
        if name in confirmations:
            public = confirmations[name]
            row.update({k: v for k, v in public.items() if k != "refs"})
            row["source_refs"].extend(public["refs"])
        else:
            row["limitations"].append("Verified matching disclosed performance is unavailable; no missing number was imputed.")
        row["source_refs"].insert(0, relative(path))
        rows.append(row)
    return {
        "as_of": now(), "source": source,
        "status": "NONLIVE_SNAPSHOT_CURRENT_DB_UNVERIFIED", "is_live": False,
        "catalog_as_of": observed_at,
        "catalog_as_of_basis": time_basis,
        "live_check": {"status": "NOT_CHECKED_BY_LOCAL_EXPORT", "checked_at": None,
                       "preparation_blocker": "AWS SSO token expired during initial preparation; current authentication may have changed.",
                       "reason": "Local export does not query live schema or Gold metadata."},
        "approved_count": len(rows), "source_sha256": sha(path),
        "gold_generation_digest": generation["gold_generation_digest"] if source == "LOCAL_GOLD_GENERATION_CACHE_NOT_LIVE" else None,
        "factors": rows, "limitations": [
            "This is not the current live gold.factor catalog. Changes after the local snapshot are unknown.",
            "Local metadata/source bindings do not certify that live Gold definitions are unchanged.",
            *LIMITATIONS,
        ],
    }


def live_export():
    from engine import silver
    from psycopg.rows import dict_row
    definitions = local_definitions()
    with silver.connect(read_only=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SET LOCAL statement_timeout = '15s'")
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()["transaction_read_only"] != "on":
                raise RuntimeError("Read-only transaction required")
            cur.execute("""SELECT table_schema, table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema='gold' AND table_name IN ('factor','factor_trial')
                ORDER BY table_name, ordinal_position""")
            schema = cur.fetchall()
            cur.execute("SELECT transaction_timestamp() AS as_of")
            as_of = cur.fetchone()["as_of"].isoformat()
            cur.execute("""SELECT factor_key, version, status, description,
                config->>'hypothesis' AS hypothesis,
                config->>'category' AS category,
                config->>'research_definition_hash' AS definition_hash,
                config->'params' AS params,
                config->'needs' AS needs,
                config->>'predicted_sign' AS predicted_sign,
                config->>'rebalance_months' AS rebalance_months,
                config->>'confirmation_evidence_grade' AS evidence_grade,
                evaluation->>'ruleset_version' AS ruleset,
                evaluation->>'campaign_id' AS campaign_id,
                evaluation->>'data_cutoff' AS data_cutoff,
                evaluation->'metrics' AS metrics
                FROM gold.factor WHERE status='APPROVED' ORDER BY factor_key,version""")
            metadata = cur.fetchall()
    rows = []
    confirmations = public_confirmations([r["factor_key"] for r in metadata], definitions)
    for item in metadata:
        name = item["factor_key"]
        row = base_row(name, definitions)
        matching = row.get("definition_hash") == item["definition_hash"] and item["definition_hash"] is not None
        if not matching:
            for key in ("family", "meaning", "params", "needs", "exploration_domain"):
                row[key] = None
            row["limitations"].append("Local definition does not have a matching live research_definition_hash; local meaning withheld.")
        metrics = finite_metrics(item["metrics"] or {})
        row.update({"version": item["version"], "current_status_verified": True,
                    "status": item["status"], "hypothesis": item["hypothesis"] or item["description"],
                    "category": item["category"], "definition_hash": item["definition_hash"],
                    "params": item["params"], "needs": item["needs"],
                    "predicted_sign": item["predicted_sign"], "rebalance_months": item["rebalance_months"],
                    "definition_binding": "LIVE_HASH_MATCHES_LOCAL_INDEX" if matching else "LIVE_METADATA_ONLY",
                    "performance": metrics,
                    "performance_basis": {"period": {"data_cutoff": item["data_cutoff"],
                                                       "research_start": metrics.get("research_start"),
                                                       "oos_signal_start": metrics.get("oos_start"),
                                                       "oos_signal_end": metrics.get("oos_end")},
                                          "rule": item["ruleset"], "units": UNITS,
                                          "metric_family": "FR3_RANK_IC" if str(item["ruleset"]).startswith("fr-3.") else "LEGACY_OR_UNVERIFIED_RULE",
                                          "campaign_id": item["campaign_id"],
                                          "evidence_class": item["evidence_grade"] or "NOT_RECORDED",
                                          "role": "Live gold.factor evaluation metadata; portfolio diagnostics and IC are distinct."}})
        public = confirmations.get(name)
        if matching and public and public["performance_basis"]["rule"] == item["ruleset"]:
            row["performance_basis"].update(public["performance_basis"])
            row["performance_basis"]["role"] = "Live gold.factor metrics with matching public confirmation provenance."
            row["source_refs"].extend(public["refs"])
        row["source_refs"].insert(0, "gold.factor WHERE status = APPROVED")
        rows.append(row)
    return {"as_of": as_of, "source": "LIVE_RDS_READ_ONLY_METADATA", "status": "LIVE_VERIFIED",
            "is_live": True, "catalog_as_of": as_of, "approved_count": len(rows),
            "schema_inspection": schema, "factors": rows, "limitations": LIMITATIONS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    try:
        payload = live_export() if args.live else local_export()
    except Exception as exc:
        print(json.dumps({"status": "EXPORT_FAILED", "error_type": type(exc).__name__,
                          "details": "Redacted; no credentials or connection strings are printed."}))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "count": payload["approved_count"],
                      "with_performance": sum(bool(x["performance"]) for x in payload["factors"]),
                      "output": relative(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
