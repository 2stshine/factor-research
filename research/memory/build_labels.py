#!/usr/bin/env python3
"""`labels.jsonl` 을 다시 만든다.

라벨의 **근거는 아래 MAP 하나뿐**이다. 우리 팩터를 공개 분류의 어느 행에 붙였는지가
여기 적혀 있고, 나머지 필드(Cat.Economic·Cat.Data·저자·연도·인용수·JKP 테마)는 전부
그 행에서 상속한다. 라벨을 고치려면 MAP 을 고치고 이 스크립트를 다시 돌린다.

    python research/memory/build_labels.py --signaldoc <경로> --jkp-clusters <경로>

두 CSV 는 라이선스 때문에 이 레포에 없다. 받는 곳은 `references.md` 에 적혀 있다.
  OpenSourceAP/CrossSection       SignalDoc.csv
  bkelly-lab/ReplicationCrisis    GlobalFactors/Cluster Labels.csv

## MAP 읽는 법

    "팩터명": (OSAP Acronym, OSAP 확신, JKP 특성, JKP 확신, variant_of 부모)

확신이 둘 다 `high` 일 때만 레코드가 `confidence: high` 가 된다. 하나라도 `low` 면
근거를 특정하지 못했다는 뜻이고 사람 검토 대상이다. 대응이 없으면 `None` 으로 비운다 —
**지어내지 않는다.**
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESEARCH = REPO / "research"

# 우리 팩터 → 공개 분류의 행. 이 표가 라벨의 유일한 근거다.
#   (OSAP Acronym, OSAP 확신, JKP 특성, JKP 확신, variant_of)
MAP = {
    "low_vol_12m":                   ("RealizedVol", "high", "rvol_21d", "high", None),
    "asset_growth_12m":              ("AssetGrowth", "high", "at_gr1", "high", None),
    "downside_vol_12m":              ("RealizedVol", "low", "betadown_252d", "high", "low_vol_12m"),
    "defensive_value":               ("BM", "low", "be_me", "low", None),
    "solvent_value":                 ("BM", "low", "be_me", "low", None),
    "small_value":                   ("BM", "high", "be_me", "high", None),
    "defensive_small_value":         ("BM", "low", "be_me", "low", "small_value"),
    "high_12m_proximity":            ("High52", "high", "prc_highprc_252d", "high", None),
    "earnings_confirmed_small_value": (None, "low", "be_me", "low", "small_value"),
    "quality_stability":             (None, "low", "qmj_safety", "high", None),
    "profitable_small_value":        (None, "low", "be_me", "low", "small_value"),
    "operating_roa":                 ("OperProf", "high", "op_at", "high", None),
    "net_profit_margin":             (None, "low", "ebit_sale", "low", None),
    "sales_growth_12m":              ("sgr", "high", "sale_gr1", "high", None),
    "operating_roa_change_12m":      (None, "low", "ocf_at_chg1", "high", None),
    "long_term_reversal_36_12":      ("LRreversal", "high", "ret_60_12", "high", None),
    "net_roa":                       ("roaq", "high", "niq_at", "high", None),
    "liability_growth_12m":          ("NetDebtFinance", "low", "debt_gr3", "high", None),
    "asset_turnover_change_12m":     ("ChAssetTurnover", "high", "at_turnover", "low", None),
    "return_skewness_24m":           ("ReturnSkew", "high", "rskew_21d", "high", None),
    "net_equity_issuance_12m":       ("ShareIss1Y", "high", "eqnetis_at", "high", None),
    "operating_roa_volatility_36m":  ("roavol", "low", "ocfq_saleq_std", "high", None),
    "annual_seasonality_5y":         ("MomSeason", "high", "seas_2_5an", "high", None),
    "retained_earnings_to_assets":   (None, "low", "z_score", "low", None),
    "current_ratio":                 ("quick", "low", "z_score", "low", None),
    "nonoperating_burden_to_assets": (None, "low", None, "low", None),
    "max_monthly_return_12m":        ("MaxRet", "high", "rmax1_21d", "high", None),
    "working_capital_accruals_12m":  ("Accruals", "high", "cowc_gr1a", "high", None),
    "earnings_change_to_assets":     ("EarningsSurprise", "low", "niq_at_chg1", "high", None),
    "market_beta_36m":               ("Beta", "high", "beta_60m", "high", None),
    "paid_in_capital_ratio":         (None, "low", None, "low", None),
    "current_liability_concentration": ("Leverage", "low", "at_be", "low", None),
    "trading_turnover_20d":          (None, "low", "turnover_126d", "high", None),
    # cycle-0034~0042
    "net_working_capital_to_assets": ("quick", "low", "z_score", "low", None),
    "operating_return_on_capital_employed": ("OperProf", "low", "ebit_bev", "high", None),
    "operating_margin_change_12m":   (None, "low", "ocf_at_chg1", "low", "operating_roa_change_12m"),
    "posttax_income_conversion":     ("ETR", "low", None, "low", None),
    "noncurrent_asset_encumbrance":  ("Leverage", "low", "at_be", "low", "current_liability_concentration"),
    "turnover_volatility_12m":       (None, "low", "turnover_var_126d", "high", "trading_turnover_20d"),
    "equity_growth_12m":             ("AssetGrowth", "low", "be_gr1a", "high", None),
    "positive_return_share_12m":     (None, "low", None, "low", None),
    "return_kurtosis_24m":           ("ReturnSkew", "low", "rmax1_21d", "low", "return_skewness_24m"),
    # cycle-0043~0053
    "amihud_illiquidity_1m":         ("Illiquidity", "low", "ami_126d", "low", None),
    "dividend_yield_ttm":            ("DivYield", "low", "div12m_me", "high", None),
    "high_52w_price_proximity":      ("High52", "high", "prc_highprc_252d", "high", "high_12m_proximity"),
    "max_daily_return_1m":           ("MaxRet", "high", "rmax1_21d", "high", "max_monthly_return_12m"),
    "net_equity_issuance_price_adjusted_12m":
                                        ("ShareIss1Y", "high", "chcsho_12m", "high", "net_equity_issuance_12m"),
    "realized_volatility_252d":      ("RealizedVol", "low", "rvol_21d", "low", "low_vol_12m"),
    "operating_income_to_liabilities":
                                        ("OperProf", "low", "op_at", "low", "operating_roa"),
    "noncurrent_asset_share":        ("tang", "low", "tangibility", "low", None),
    "dividend_event_frequency_ttm":  ("DivSeason", "low", None, "low", None),
    "intermediate_momentum_12_7":    ("IntMom", "high", "ret_12_7", "high", None),
    "market_leverage":               ("Leverage", "high", "debt_me", "high", None),
}

# OSAP 의 GScholarCites 는 스크래핑 값이라 일부가 실제와 크게 어긋난다.
# Accruals(Sloan 1996)=56 이 확인된 예다. 값은 출처 그대로 두고 의심 표시만 단다.
SUSPECT_CITES = {"Accruals"}

# 앵커가 근사일 때 그 사실을 evidence 에 남긴다. 산식이 아니라 메커니즘으로 붙인 건은
# 읽는 쪽이 근사임을 알아야 재검토가 가능하다.
NOTES = {
    "return_kurtosis_24m":
        "첨도 자체는 JKP·OSAP 무대응, 메커니즘(복권형 수요) 기준 최근접 근사 = rmax1_21d",
    "posttax_income_conversion":
        "OSAP ETR(txt/pi)과 분모가 같고 우리 비율은 1-ETR. JKP 는 비율형 세금 특성이 없어 비움",
    "net_working_capital_to_assets":
        "JKP cowc_gr1a 는 변화량이라 부적합. 완충력 메커니즘 기준 z_score 계열로 근사",
    "operating_margin_change_12m":
        "OSAP 무대응. 변화 축이므로 부모(operating_roa_change_12m)와 같은 Profit Growth 로 정렬",
    "amihud_illiquidity_1m":
        "OSAP·JKP 대응은 같지만 공개 특성의 12개월 창과 달리 최근 1개월 가격충격을 사용",
    "dividend_yield_ttm":
        "OSAP DivYield는 소형주·최근 배당 기반 정의라 근사이고 JKP div12m_me가 더 가까움",
    "net_equity_issuance_price_adjusted_12m":
        "기존 12개월 순발행 정의에서 배당 포함 수익 대신 가격수익을 사용한 변형",
    "realized_volatility_252d":
        "공개 RealizedVol의 1개월 CAPM 잔차 변동성과 달리 252거래일 원수익률 변동성을 사용",
    "operating_income_to_liabilities":
        "영업수익성 계열이지만 총자산 대신 총부채를 분모로 사용",
    "noncurrent_asset_share":
        "OSAP tang·JKP tangibility의 자산구성 메커니즘 근사이며 가중 유동성 산식은 다름",
    "dividend_event_frequency_ttm":
        "OSAP DivSeason은 배당 시점 규칙이고 우리는 최근 12개월 실시 횟수라 근사",
}

# needs 는 재무 컬럼만 선언한다(SKILL.md). 가격·거래 컬럼은 compute 본문에서 읽는다.
TRADE_COLS = {"adv20", "trading_value", "amount", "dolvol"}


def num(row: dict | None, column: str) -> int | None:
    if not row:
        return None
    try:
        return int(float((row.get(column) or "").strip()))
    except ValueError:
        return None


def cat_data_fallback(factor: str) -> tuple[str | None, str | None]:
    """OSAP 매칭이 없을 때 후보 소스에서 데이터 원천을 유도한다."""
    path = REPO / "factors" / "candidates" / f"{factor}.py"
    if not path.exists():
        return None, None
    src = path.read_text(encoding="utf-8")
    declared = re.search(r"needs=\(([^)]*)\)", src)
    needs = [x.strip().strip('"') for x in (declared.group(1) if declared else "").split(",") if x.strip()]
    if needs:
        return "Accounting", "needs_fallback"
    columns = set(re.findall(r'\["([a-zA-Z_0-9]+)"\]', src))
    return ("Trading" if columns & TRADE_COLS else "Price"), "needs_fallback"


def main() -> None:
    ap = argparse.ArgumentParser(description="labels.jsonl 재생성")
    ap.add_argument("--signaldoc", required=True, help="OSAP SignalDoc.csv")
    ap.add_argument("--jkp-clusters", required=True, help="JKP Cluster Labels.csv")
    ap.add_argument("--out", default=str(RESEARCH / "memory" / "labels.jsonl"))
    args = ap.parse_args()

    osap = {r["Acronym"]: r for r in csv.DictReader(open(args.signaldoc, encoding="utf-8-sig"))}
    jkp = {r["characteristic"].strip(): r["cluster"].strip()
           for r in csv.DictReader(open(args.jkp_clusters, encoding="utf-8-sig"))}

    history = [json.loads(l) for l in (RESEARCH / "history.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    missing = [h["factor"] for h in history if h["factor"] not in MAP]
    if missing:
        raise SystemExit("MAP 에 없는 팩터가 있다. 근거를 확인하고 항목을 추가하라:\n  " + "\n  ".join(missing))

    records = []
    for h in history:
        factor = h["factor"]
        acronym, osap_conf, jkp_char, jkp_conf, parent = MAP[factor]
        row = osap.get(acronym) if acronym else None
        cat_data = (row or {}).get("Cat.Data") or None
        source = "osap" if cat_data else None
        if not cat_data:
            cat_data, source = cat_data_fallback(factor)
        records.append({
            "cycle_id": h["cycle_id"],
            "factor": factor,
            "ruleset_version": h.get("ruleset_version"),
            "cat_economic": (row or {}).get("Cat.Economic") or None,
            "cat_data": cat_data,
            "cat_data_source": source,
            "jkp_theme": jkp.get(jkp_char) if jkp_char else None,
            "jkp_evidence": jkp_char,
            "osap_acronym": acronym,
            "paper_authors": (row or {}).get("Authors") or None,
            "paper_year": num(row, "Year"),
            "paper_journal": (row or {}).get("Journal") or None,
            "paper_cites": num(row, "GScholarCites202509"),
            "paper_cites_suspect": bool(row and row.get("Acronym") in SUSPECT_CITES),
            "variant_of": parent,
            "analysis": None,
            "confidence": "high" if (osap_conf == "high" and jkp_conf == "high") else "low",
            "evidence": f"runs/{h['cycle_id']}/report.md; factors/candidates/{factor}.py"
                        + (f"; 근사: {NOTES[factor]}" if factor in NOTES else ""),
        })

    Path(args.out).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    low = sum(1 for r in records if r["confidence"] == "low")
    print(f"wrote {len(records)} records to {args.out}  (high {len(records)-low} / low {low})")


if __name__ == "__main__":
    main()
