"""Two incremental FY measurements; no return-based selection or alpha approval.

Kept separate from v2 so the original 45 definitions/snapshots remain immutable.
Tax is the annual JKP implementation, NOT the quarterly Thomas-Zhang original.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine import reference_library as base, reference_library_v2 as previous
from engine.research_generation import digest

SOURCE_TYPE = "RDS_CERTIFIED_DART_PROFIT_GROWTH_FY_V1"
SOURCE_CONTRACT = "EXACT_EXISTING_DART_FY_CAPTURE_PROFIT_GROWTH_V1"
PIT_STATUS = previous.PIT_STATUS
JKP_COMMIT = "666e8960ed81a664f1e9f189f92925ab2eeffcd5"
JKP_URL = f"https://github.com/bkelly-lab/jkp-data/blob/{JKP_COMMIT}/documentation/documentation.tex"
SPECS = {
    "kr_cfo_assets_change_fy_v1": {
        "name_ko": "영업현금흐름 수익성 개선", "family": "profit_growth", "orientation": 1,
        "columns": ["fy_operating_cash_flow", "fy_total_assets", "prev_fy_operating_cash_flow", "prev_fy_total_assets"],
        "formula": "CFO_t / Assets_t - CFO_prevFY / Assets_prevFY",
        "sql": "CASE WHEN fy_total_assets>0 AND prev_fy_total_assets>0 THEN fy_operating_cash_flow/fy_total_assets-prev_fy_operating_cash_flow/prev_fy_total_assets END",
        "primary": "https://doi.org/10.1111/jofi.12734", "title": "Bouchaud et al. (2019), Sticky Expectations and the Profitability Anomaly",
        "replication_variable": "ocf_at_chg1", "quota_bucket": "other_quant_firm",
        "adaptation": "CFM 관련 연구. JKP 연간 ocf_at_chg1을 DART KRW FY 영업현금흐름·기말총자산으로 측정. 애널리스트 기대 경직성을 측정하거나 인과를 입증하지 않음. 기존 CFO/Assets 수준과 변화는 별개 가설이며 경제적 중복은 후속 spanning 검토 대상.",
    },
    "kr_tax_expense_change_assets_fy_v1": {
        "name_ko": "연간 법인세비용 변화", "family": "tax_information", "orientation": 1,
        "columns": ["fy_income_tax_expense", "prev_fy_income_tax_expense", "fy_total_assets"],
        "formula": "(TaxExpense_t - TaxExpense_prevFY) / Assets_t",
        "sql": "CASE WHEN fy_total_assets>0 THEN (fy_income_tax_expense-prev_fy_income_tax_expense)/fy_total_assets END",
        "primary": "https://doi.org/10.1111/j.1475-679X.2011.00409.x", "title": "Thomas and Zhang (2011), Tax Expense Momentum",
        "replication_variable": "tax_gr1a", "quota_bucket": "academic",
        "adaptation": "JKP의 연간 tax_gr1a 측정. Thomas-Zhang 원문의 분기 전년동기 tax surprise 원식 재현 아님. DART 계속영업 법인세비용을 사용하고 현금납부세금·유효세율과 구별. 한국 수익성 미검증.",
    },
}
FEATURES = sorted({c for spec in SPECS.values() for c in spec["columns"]})
ALL_COLUMNS = [*base._BASE, *FEATURES]


def definitions():
    result = []
    for ref, spec in SPECS.items():
        result.append(dict(id=ref, name_ko=spec["name_ko"], family=spec["family"],
            object_type="STOCK_CHARACTERISTIC", role="MEASUREMENT_CONTROL", alpha_approved=False,
            formula=spec["formula"], orientation=spec["orientation"], required_columns=spec["columns"],
            lookback={"fiscal_basis": "LATEST_AVAILABLE_FY_SAME_FILING_SCOPE_CURRENCY", "prior_fiscal_year_required": True, "maximum_statement_age_days": 550},
            sources=[{"title": spec["title"], "url": spec["primary"], "review_scope": "원문 연구 범위와 원형/연간 복제 차이 확인"},
                     {"title": "JKP author replication documentation", "url": JKP_URL, "review_scope": "고정 커밋의 " + spec["replication_variable"] + " 산식·인용표"}],
            adaptation=spec["adaptation"], evidence_tier="PUBLISHED_PREDICTOR_ADAPTATION",
            quota_bucket=spec["quota_bucket"], readiness={"status": "IMPLEMENTED_REQUIRES_ATTESTATION", "blockers": []}))
    base.validate_catalog(result)
    return result


def prepare(panel):
    if set(panel) != set(ALL_COLUMNS) or not panel.columns.is_unique:
        raise ValueError("Exact profit-growth feature schema required; no labels")
    frame = base._prepare(panel.loc[:, base._BASE])
    values = panel.assign(asset_id=panel.asset_id.astype(str), date=pd.to_datetime(panel.date)).set_index(["asset_id", "date"])
    keys = pd.MultiIndex.from_frame(frame[["asset_id", "date"]])
    for c in FEATURES:
        if not pd.api.types.is_numeric_dtype(values[c]) or pd.api.types.is_bool_dtype(values[c]):
            raise ValueError("Numeric financial input required")
        frame[c] = values[c].reindex(keys).to_numpy(dtype=float, na_value=np.nan)
        if np.isinf(frame[c]).any():
            raise ValueError("Infinite financial input")
    return frame


def input_digest(panel):
    frame = prepare(panel).reindex(sorted(ALL_COLUMNS), axis=1)
    h = hashlib.sha256(json.dumps(list(frame), separators=(",", ":")).encode())
    h.update(pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype="uint64").tobytes())
    return h.hexdigest()


def implementation_hash():
    from engine import reference_financial_inputs, reference_profit_growth_parity
    return digest({Path(m).name: hashlib.sha256(Path(m).read_bytes()).hexdigest()
                   for m in [__file__, base.__file__, reference_financial_inputs.__file__, reference_profit_growth_parity.__file__]})


def calculate(panel, reference_id):
    p = prepare(panel)
    if reference_id == "kr_cfo_assets_change_fy_v1":
        raw = p.fy_operating_cash_flow / p.fy_total_assets.where(p.fy_total_assets > 0) - p.prev_fy_operating_cash_flow / p.prev_fy_total_assets.where(p.prev_fy_total_assets > 0)
    elif reference_id == "kr_tax_expense_change_assets_fy_v1":
        raw = (p.fy_income_tax_expense - p.prev_fy_income_tax_expense) / p.fy_total_assets.where(p.fy_total_assets > 0)
    else:
        raise ValueError("Unknown registered measurement")
    raw = raw.where(np.isfinite(raw))
    return p, raw
