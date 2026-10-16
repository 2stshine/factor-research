"""Annual accounting measurements: frozen arithmetic, not alpha selection.

Account interpretation and as-of fiscal matching belong to the authenticated
input adapter. These formulas never infer a fiscal lag from monthly row order.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ID: operator, numerator(s), denominator(s), literature direction.
# Explicit FY and issue-cap labels avoid silently claiming canonical US factors.
FINANCIAL_FORMULAS = {
    'kr_equity_to_issue_cap_fy_v1': ('ratio','fy_total_equity','market_cap',1),
    'kr_earnings_to_issue_cap_fy_v1': ('ratio','fy_net_income','market_cap',1),
    'kr_sales_to_issue_cap_fy_v1': ('ratio','fy_revenue','market_cap',1),
    'kr_cfo_to_issue_cap_fy_v1': ('ratio','fy_operating_cash_flow','market_cap',1),
    'kr_gross_profit_assets_fy_v1': ('ratio','fy_gross_profit','fy_total_assets',1),
    'kr_operating_profit_assets_fy_v1': ('ratio','fy_operating_income','fy_total_assets',1),
    'kr_roa_fy_v1': ('ratio','fy_net_income','fy_total_assets',1),
    'kr_roe_fy_v1': ('ratio','fy_net_income','fy_total_equity',1),
    'kr_cfo_assets_fy_v1': ('ratio','fy_operating_cash_flow','fy_total_assets',1),
    'kr_gross_margin_fy_v1': ('ratio','fy_gross_profit','fy_revenue',1),
    'kr_operating_margin_fy_v1': ('ratio','fy_operating_income','fy_revenue',1),
    'kr_net_margin_fy_v1': ('ratio','fy_net_income','fy_revenue',1),
    'kr_liabilities_assets_fy_v1': ('ratio','fy_total_liabilities','fy_total_assets',-1),
    'kr_current_ratio_fy_v1': ('ratio','fy_current_assets','fy_current_liabilities',1),
    'kr_cash_assets_fy_v1': ('ratio','fy_cash_and_equivalents','fy_total_assets',1),
    'kr_retained_earnings_assets_fy_v1': ('ratio','fy_retained_earnings','fy_total_assets',1),
    'kr_tangibility_fy_v1': ('ratio','fy_property_plant_and_equipment','fy_total_assets',1),
    'kr_working_capital_assets_fy_v1': ('spread_ratio','fy_current_assets','fy_current_liabilities','fy_total_assets',1),
    'kr_cashflow_accruals_fy_v1': ('spread_ratio','fy_net_income','fy_operating_cash_flow','fy_total_assets',-1),
    'kr_asset_growth_fy_v1': ('growth','fy_total_assets','prev_fy_total_assets',-1),
    'kr_sales_growth_fy_v1': ('growth','fy_revenue','prev_fy_revenue',-1),
    'kr_equity_growth_fy_v1': ('growth','fy_total_equity','prev_fy_total_equity',-1),
    'kr_inventory_investment_fy_v1': ('spread_ratio','fy_inventories','prev_fy_inventories','prev_fy_total_assets',-1),
    'kr_receivables_investment_fy_v1': ('spread_ratio','fy_trade_and_other_current_receivables','prev_fy_trade_and_other_current_receivables','prev_fy_total_assets',-1),
    'kr_asset_turnover_change_fy_v1': ('change_ratio','fy_revenue','fy_total_assets','prev_fy_revenue','prev_fy_total_assets',1),
}


def required_columns(reference_id):
    return list(FINANCIAL_FORMULAS[reference_id][1:-1])


def calculate(frame, reference_id):
    spec=FINANCIAL_FORMULAS[reference_id]
    op=spec[0]; columns=spec[1:-1]
    values=[pd.to_numeric(frame[c],errors='raise').astype(float).where(lambda x:np.isfinite(x)) for c in columns]
    if op=='ratio':
        a,b=values; result=a/b.where(b>0)
    elif op=='growth':
        a,b=values; result=(a/b.where(b>0)-1).where(a>=0)
    elif op=='spread_ratio':
        a,b,c=values; result=(a-b)/c.where(c>0)
    elif op=='change_ratio':
        a,b,c,d=values; result=a/b.where(b>0)-c/d.where(d>0)
    else:raise ValueError('Unsupported frozen financial operator')
    return result.where(np.isfinite(result))


def sql_expression(reference_id):
    """Independent SQL arithmetic over the same attested fiscal input fields."""
    spec=FINANCIAL_FORMULAS[reference_id];op=spec[0];columns=spec[1:-1]
    if op=='ratio':
        a,b=columns; return f'CASE WHEN {b}>0 THEN {a}/{b} END'
    if op=='growth':
        a,b=columns; return f'CASE WHEN {b}>0 AND {a}>=0 THEN {a}/{b}-1 END'
    if op=='spread_ratio':
        a,b,c=columns; return f'CASE WHEN {c}>0 THEN ({a}-{b})/{c} END'
    if op=='change_ratio':
        a,b,c,d=columns; return f'CASE WHEN {b}>0 AND {d}>0 THEN {a}/{b}-{c}/{d} END'
    raise ValueError('Unsupported frozen financial operator')
