"""Bounded, read-only live SQL/Python parity on fixed certified ledger inputs.

This diagnostic reads no prices, returns, OOS results, or Gold. Its only database
calculation is parameterized SELECT/WITH over supplied raw financial revisions.
Selection is the first three asset IDs, two fixed FLOW metrics and three fixed
historical timestamps, declared here before any numerical comparison.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from engine import fundamental_sql, fundamentals, silver
from engine.research_memory_transfer import write_artifact
from scripts.repair_fundamental_panel import file_sha, task_connection


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON_SHA = "136da8ad847ec3510549c881109dacff4cbb406359c4ec8d9c5a7347cff8f1ed"
AS_OF_DATES = ("2017-06-30", "2020-06-30", "2023-06-30")
METRICS = ("revenue", "net_income")
START = "2015-01-01"
END = "2023-06-30"
RTOL = 1e-12
ATOL = 1e-8


def _json_sha(value):
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, default=str).encode()
    return hashlib.sha256(body).hexdigest()


def _number(value):
    return None if value is None or pd.isna(value) else float(value)


def _equal(left, right):
    if left is None or right is None:
        return left is None and right is None
    return bool(np.isclose(left, right, rtol=RTOL, atol=ATOL))


def validate(source_directory, output, *, profile="teamalpha"):
    source_directory = Path(source_directory).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Parity output already exists; append a new explicit version instead")
    if not output.is_relative_to(ROOT / "research" / "v2"):
        raise ValueError("Parity output must remain under research/v2")
    artifact = {
        "schema_version": "certified-ledger-live-financial-sql-parity-v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING", "scope": "FLOW latest standalone and TTM only",
        "selection_policy": "Ascending first three source-ledger asset_ids, without inspecting values",
        "metrics": list(METRICS), "as_of_dates": list(AS_OF_DATES),
        "available_date_start": START, "available_date_end": END,
        "numeric_comparison": {"rtol": RTOL, "atol": ATOL, "nulls_must_match": True},
        "methodology_version": fundamentals.FUNDAMENTAL_METHODOLOGY_VERSION,
        "python_source_sha256": fundamentals.source_sha256(),
        "sql_diagnostic_version": fundamental_sql.SQL_DIAGNOSTIC_VERSION,
        "sql_text_sha256": fundamental_sql.sql_sha256(),
        "validation_script_sha256": file_sha(Path(__file__)),
        "read_only": True, "statement_timeout_seconds": 60,
        "return_evaluations": 0, "oos_reads": 0, "gold_reads": 0, "gold_writes": 0,
        "source_data_modified": False, "frozen_artifacts_modified": False,
        "historical_first_vintage_verified": False,
        "full_ledger_parity_claim": False, "stock_or_sue_parity_claim": False,
        "limitations": [
            "Three preselected assets and two FLOW metrics are bounded sample evidence, not full-ledger parity.",
            "Certified source binding does not independently verify original filing vintages.",
            "SQL fiscal-calendar admissibility is structural, not fiscal-calendar certification.",
            "SQL receives raw revisions only; Python-computed financial values are never SQL parameters.",
            "Latest standalone value and TTM are compared; balance-sheet and SUE outputs are outside scope.",
        ],
    }
    stage = "SOURCE_PROVENANCE"
    try:
        if fundamentals.source_sha256() != EXPECTED_PYTHON_SHA:
            raise ValueError("Frozen Python materializer changed")
        receipt_path = source_directory / "source-receipt.json"
        parquet_path = source_directory / "certified-financial-rows.parquet"
        receipt = json.loads(receipt_path.read_text())
        if (
            receipt.get("schema_version") != "certified-financial-ledger-extract-v1"
            or receipt.get("read_only") is not True
            or receipt.get("isolation") != "REPEATABLE_READ"
            or receipt.get("parquet_sha256") != file_sha(parquet_path)
            or receipt.get("query_sha256") != hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest()
            or receipt.get("metrics") != sorted(fundamentals.ALL_METRICS)
            or receipt.get("row_count") != pq.ParquetFile(parquet_path).metadata.num_rows
        ):
            raise ValueError("Certified ledger provenance mismatch")
        identifiers = pd.read_parquet(parquet_path, columns=["asset_id"])
        all_ids = sorted(int(value) for value in identifiers.asset_id.unique())
        if len(all_ids) != receipt.get("asset_count") or len(all_ids) < 3:
            raise ValueError("Source asset population changed or is too small")
        asset_ids = all_ids[:3]
        del identifiers
        columns = ["asset_id", "period_end", "fiscal_period", "fs_type", "available_date",
                   "metric", "value", "revision_key", "quality_run_id"]
        selected = pd.read_parquet(parquet_path, columns=columns, filters=[
            ("asset_id", "in", asset_ids), ("metric", "in", list(METRICS)),
            ("available_date", ">=", pd.Timestamp(START)),
            ("available_date", "<=", pd.Timestamp(END)),
        ]).sort_values(["asset_id", "available_date", "period_end", "metric", "revision_key"])
        if not selected.quality_run_id.notna().all():
            raise ValueError("Selected rows lack certified quality provenance")
        if not set(selected.quality_run_id).issubset(receipt["quality_run_ids"]):
            raise ValueError("Selected quality provenance differs from receipt")
        artifact.update({
            "source_directory": str(source_directory.relative_to(ROOT)),
            "source_parquet_sha256": receipt["parquet_sha256"],
            "source_receipt_sha256": file_sha(receipt_path),
            "source_row_count": receipt["row_count"], "source_asset_count": len(all_ids),
            "selected_asset_ids": asset_ids, "selected_raw_rows": len(selected),
            "selected_source_rows_sha256": _json_sha(selected.to_dict("records")),
            "selected_quality_run_ids": sorted(selected.quality_run_id.unique().tolist()),
            "selected_min_available_date": str(selected.available_date.min()),
            "selected_max_available_date": str(selected.available_date.max()),
        })
        print(json.dumps({"stage": "FIXED_INPUT_SELECTED", "asset_ids": asset_ids,
                          "raw_rows": len(selected), "as_of_dates": AS_OF_DATES}), flush=True)
        stage = "RAW_AMBIGUITY_CHECK"
        ambiguity = selected.assign(cfs_priority=selected.fs_type.eq("CFS"))
        keys = ["asset_id", "period_end", "fiscal_period", "metric", "cfs_priority",
                "available_date", "revision_key"]
        duplicated = ambiguity.loc[ambiguity.duplicated(keys, keep=False)]
        artifact["raw_priority_duplicate_rows"] = len(duplicated)
        artifact["raw_priority_duplicate_groups"] = int(duplicated.groupby(keys, dropna=False).ngroups)
        if len(duplicated):
            artifact["raw_priority_duplicate_sample"] = [
                {key: str(value) for key, value in row.items()}
                for row in duplicated[[*keys, "value", "quality_run_id"]].head(12).to_dict("records")
            ]
            raise ValueError("Ambiguous duplicate priorities are not silently deduplicated")
        numeric = pd.to_numeric(selected.value, errors="coerce")
        unexpected_non_numeric = selected.value.notna() & numeric.isna()
        artifact["raw_non_numeric_values"] = int(unexpected_non_numeric.sum())
        if unexpected_non_numeric.any() or np.isinf(numeric.to_numpy(dtype=float)).any():
            raise ValueError("Unrecognized numeric representation is outside fixture contract")
        selected = selected.copy()
        selected["value"] = numeric
        raw_rows = [
            {"asset_id": int(row.asset_id), "period_end": row.period_end.isoformat(),
             "fiscal_period": str(row.fiscal_period), "fs_type": str(row.fs_type),
             "available_date": row.available_date.isoformat(), "metric": str(row.metric),
             "value": _number(row.value), "revision_key": str(row.revision_key)}
            for row in selected.itertuples(index=False)
        ]
        targets = [{"asset_id": asset_id, "as_of_date": as_of, "metric": metric}
                   for asset_id in asset_ids for as_of in AS_OF_DATES for metric in METRICS]
        params = fundamental_sql.flow_ttm_parameters(raw_rows, targets)
        artifact["raw_parameter_sha256"] = hashlib.sha256(params[0].encode()).hexdigest()
        artifact["target_parameter_sha256"] = hashlib.sha256(params[1].encode()).hexdigest()
        artifact["target_count"] = len(targets)
        artifact["target_input_support"] = [
            {**target, "available_raw_rows": int((
                selected.asset_id.eq(target["asset_id"])
                & selected.metric.eq(target["metric"])
                & selected.available_date.le(pd.Timestamp(target["as_of_date"]))
            ).sum())} for target in targets
        ]
        stage = "PYTHON_REPLAY"
        python_rows = pd.DataFrame(raw_rows)
        python_rows["period_end"] = pd.to_datetime(python_rows.period_end)
        python_rows["available_date"] = pd.to_datetime(python_rows.available_date)
        python_result = fundamentals.materialize_pit(python_rows, verbose=False)
        stage = "LIVE_READ_ONLY_SQL"
        with task_connection(profile) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW transaction_read_only")
                if cursor.fetchone()[0] != "on":
                    raise ValueError("PostgreSQL transaction is not read-only")
                cursor.execute("SHOW transaction_isolation")
                isolation = cursor.fetchone()[0]
                if isolation != "repeatable read":
                    raise ValueError("PostgreSQL transaction must be repeatable read")
                cursor.execute("SELECT set_config('statement_timeout', '60s', true)")
                cursor.fetchone()
            sql_result = fundamental_sql.query_flow_ttm(conn, raw_rows, targets)
        artifact["transaction_isolation"] = isolation
        stage = "OUTPUT_COMPARISON"
        if len(sql_result) != len(targets) or [row["target_id"] for row in sql_result] != list(range(len(targets))):
            raise ValueError("SQL target exact set mismatch")
        comparisons = []
        for target_id, (target, sql_row) in enumerate(zip(targets, sql_result, strict=True)):
            if (sql_row["asset_id"] != target["asset_id"] or sql_row["metric"] != target["metric"]
                    or pd.Timestamp(sql_row["as_of_date"]) != pd.Timestamp(target["as_of_date"])):
                raise ValueError("SQL target identity mismatch")
            known = python_result[
                python_result.asset_id.eq(target["asset_id"])
                & python_result.available_date.le(pd.Timestamp(target["as_of_date"]))
            ]
            snapshot = known.iloc[-1] if len(known) else None
            fields = {}
            for sql_field, python_field in (("ttm_value", f"{target['metric']}_ttm"),
                                             ("standalone_value", target["metric"])):
                left = _number(snapshot[python_field]) if snapshot is not None else None
                right = _number(sql_row[sql_field])
                fields[sql_field] = {"python": left, "sql": right, "matched": _equal(left, right),
                                     "absolute_delta": None if left is None or right is None else abs(left - right)}
            comparisons.append({"target_id": target_id, **target, "fields": fields,
                                "matched": all(row["matched"] for row in fields.values()),
                                "sql_contiguous_four_quarters": sql_row["contiguous_four_quarters"],
                                "sql_recent_quarters": sql_row["recent_quarters"]})
        artifact["comparisons"] = comparisons
        artifact["matched_targets"] = sum(row["matched"] for row in comparisons)
        artifact["mismatched_targets"] = len(comparisons) - artifact["matched_targets"]
        artifact["finite_ttm_targets"] = sum(row["fields"]["ttm_value"]["python"] is not None for row in comparisons)
        artifact["null_ttm_targets"] = len(comparisons) - artifact["finite_ttm_targets"]
        artifact["status"] = "PASS" if artifact["mismatched_targets"] == 0 else "FAIL"
        if fundamentals.source_sha256() != EXPECTED_PYTHON_SHA:
            raise ValueError("Frozen materializer changed during validation")
    except Exception as exc:
        artifact.update({"status": "ERROR", "error_stage": stage,
                         "error_type": type(exc).__name__, "sqlstate": getattr(exc, "sqlstate", None),
                         "error_message_omitted": "No exception text or credentials are persisted"})
    artifact["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_artifact(output, artifact)
    print(json.dumps({key: artifact.get(key) for key in
                      ("status", "selected_asset_ids", "selected_raw_rows", "target_count",
                       "matched_targets", "mismatched_targets", "error_stage", "error_type", "sqlstate")},
                     ensure_ascii=False, indent=2), flush=True)
    return artifact["status"] == "PASS"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--aws-cli-profile", default="teamalpha")
    args = parser.parse_args()
    raise SystemExit(0 if validate(args.source, args.output, profile=args.aws_cli_profile) else 1)


if __name__ == "__main__":
    main()
