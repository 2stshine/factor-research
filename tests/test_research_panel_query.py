"""Structural tests only: these do NOT establish real-DB numeric/identity parity."""
import ast
import hashlib
from pathlib import Path
import re

import pytest

from engine.research_panel_query import deferred_identity_sql


QUERY_SHA256 = "e5f7d557794b313fe8ac4d5d009391374027be3e394d05a90afa94d0d0fe8576"


def original_query():
    tree = ast.parse(Path(__file__).resolve().parents[1].joinpath("engine/silver.py").read_text())
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id == "PRICE_SNAPSHOT_SQL" for target in node.targets))


def test_exact_source_is_preserved_and_all_feature_windows_are_unchanged():
    original = original_query()
    assert hashlib.sha256(original.encode()).hexdigest() == QUERY_SHA256
    rewritten = deferred_identity_sql(original)
    assert original == original_query()
    assert original[original.index("        avg(CASE"):original.index("    FROM public.price_daily p")] in rewritten
    assert original[original.index("), feature_inputs AS ("):original.index('\nSELECT asset_id, "Code"')] in rewritten
    daily_select = rewritten.split("    FROM public.price_daily p", 1)[0]
    assert "i.identifier" not in daily_select and "i.ticker_match_count" not in daily_select
    before = original.rsplit("\nSELECT ", 1)[1].split("\nFROM ", 1)[0]
    after = rewritten.rsplit("\nSELECT ", 1)[1].split("\nFROM ", 1)[0]
    assert after.replace("m.asset_id", "asset_id").replace('i.identifier AS "Code"', '"Code"').replace("i.ticker_match_count", "ticker_match_count") == before


def test_only_lookup_occurs_after_month_selection_with_identical_pit_aggregate():
    rewritten = deferred_identity_sql(original_query())
    assert rewritten.count("JOIN LATERAL (") == 1
    selected = re.search(r"FROM\s+\(\s*SELECT \* FROM monthly WHERE month_rank\s*=\s*1\s*\)\s+m", rewritten)
    assert selected is not None and selected.end() < rewritten.index("JOIN LATERAL (")
    lookup = rewritten[rewritten.index("JOIN LATERAL ("):]
    for expression in ("min(ai.identifier) AS identifier", "count(*) AS ticker_match_count",
                       "ai.asset_id = m.asset_id", "ai.source = 'KRX'",
                       "ai.identifier_type = 'ticker'", "ai.valid_from <= m.trade_date",
                       "(ai.valid_to IS NULL OR ai.valid_to >= m.trade_date)"):
        assert expression in lookup
    assert "p.trade_date" not in lookup and "p.asset_id" not in lookup
    assert ") i ON true" in lookup
    assert "HAVING" not in rewritten.upper() and "DISTINCT" not in rewritten.upper()
    assert rewritten.rstrip().endswith("ORDER BY m.asset_id, m.trade_date")


@pytest.mark.parametrize("alter", [lambda sql: "", lambda sql: sql + " ",
    lambda sql: sql.replace("BETWEEN 19 PRECEDING", "BETWEEN 18 PRECEDING", 1),
    lambda sql: sql.replace("    JOIN LATERAL (", "", 1),
    lambda sql: sql.replace("    JOIN LATERAL (", "    JOIN LATERAL (\n    JOIN LATERAL (", 1)])
def test_changed_missing_duplicated_or_whitespace_modified_source_fails_closed(alter):
    with pytest.raises(ValueError):
        deferred_identity_sql(alter(original_query()))
