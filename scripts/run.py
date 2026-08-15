#!/usr/bin/env python
"""팩터 리서치 CLI.

  python scripts/run.py build                 # 패널 캐시 생성 (한 번)
  python scripts/run.py null --campaign ID    # 같은 크기의 귀무 campaign 오류율 측정
  python scripts/research.py campaign-start --campaign ID
  python scripts/research.py evaluate --campaign ID --epoch EPOCH --factor FACTOR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import factors as F
from engine import (
    epochs,
    fundamentals,
    gate,
    implementation,
    null,
    panel as P,
    publish,
    research,
    research_policy,
    silver,
    trials,
)
from engine.boundaries import (
    HISTORICAL_HOLDOUT_MODE,
    PROSPECTIVE_HOLDOUT_MODE,
    CampaignWindow,
    validate_manifest,
)

CACHE = Path(os.environ.get("CACHE_DIR", ".cache"))
TRIAL_DB = CACHE / "trials.sqlite3"
PANEL_CACHE = CACHE / "panel.pkl"
PANEL_ARCHIVE = CACHE / "panels"
PARITY_CHECKPOINT_ROOT = CACHE / "implementation-parity-checkpoints"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PARITY_CHECKPOINT_SCHEMA = "implementation-parity-sql-checkpoint-v1"


def _log_timing(stage: str, started: float, **context: object) -> None:
    """Emit and append operational timings without research outcomes."""
    allowed_context = {
        "factor", "factor_count", "phase", "registry_count", "sql",
        "target_table", "query_start_month", "query_end_month",
        "query_chunk_count", "chunk_index", "chunk_count",
        "checkpoint_reused", "database_temp_files_global_delta",
        "database_temp_bytes_global_delta", "kind", "replicate",
        "candidate_count", "family_count",
    }
    unexpected = set(context) - allowed_context
    if unexpected:
        print(
            f"[timing] 허용되지 않은 필드는 기록하지 않음: {sorted(unexpected)}",
            file=sys.stderr,
            flush=True,
        )
    context = {key: value for key, value in context.items() if key in allowed_context}
    payload = {
        "event": "research_timing_v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "seconds": round(time.perf_counter() - started, 3),
        **context,
    }
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    print(encoded.decode("utf-8").rstrip("\n"), file=sys.stderr, flush=True)
    path = Path(os.environ.get(
        "RESEARCH_TIMING_LOG", str(CACHE / "research-timings.jsonl"),
    ))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600,
        )
        try:
            os.write(descriptor, encoded)
        finally:
            os.close(descriptor)
    except OSError as exc:
        print(
            f"[timing] 영구 로그 기록 실패(계산은 계속): {exc}",
            file=sys.stderr,
            flush=True,
        )


def _database_temp_usage(conn) -> tuple[int, int]:
    """Read database-wide temp counters for operational before/after deltas."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_stat_clear_snapshot()")
        cursor.execute(
            "SELECT temp_files, temp_bytes FROM pg_stat_database "
            "WHERE datname = current_database()"
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("현재 DB의 temp I/O 통계를 읽을 수 없습니다")
    return int(row[0]), int(row[1])


def _external_gold_trial_rows(
    gold_trials: pd.DataFrame | None,
) -> list[tuple[str, None, None]]:
    """Normalize optional legacy Gold trials for the attempt ledger."""
    if gold_trials is None:
        return []
    if "definition_hash" not in gold_trials.columns:
        raise ValueError("Gold trial history에 definition_hash가 없습니다")
    return [
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ]


def _parity_query_windows(
    start: str | pd.Period,
    end: str | pd.Period,
    chunk_months: int | None,
) -> list[tuple[pd.Period, pd.Period]]:
    """Return exact, non-overlapping inclusive result windows for parity SQL."""
    first = pd.Period(start, freq="M")
    last = pd.Period(end, freq="M")
    if first > last:
        raise ValueError("Gold parity 시작월이 종료월보다 늦습니다")
    if chunk_months is None:
        return [(first, last)]
    if isinstance(chunk_months, bool) or not isinstance(chunk_months, int):
        raise ValueError("Gold manifest query_chunk_months는 정수여야 합니다")
    if chunk_months < 1:
        raise ValueError("Gold manifest query_chunk_months는 1 이상이어야 합니다")
    windows = []
    cursor = first
    while cursor <= last:
        window_end = min(cursor + (chunk_months - 1), last)
        windows.append((cursor, window_end))
        cursor = window_end + 1
    return windows


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sql_result_digest(frame: pd.DataFrame) -> str:
    """Digest exact SQL parity rows independent of Parquet representation."""
    required = {"asset_id", "as_of_date", "value", "rank"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"SQL checkpoint 필수 컬럼이 없습니다: {sorted(missing)}")
    has_factor = "factor" in frame.columns
    records: list[tuple[str, ...]] = []
    for row in frame.itertuples(index=False):
        values = row._asdict()
        try:
            asset_id = int(values["asset_id"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("SQL checkpoint asset_id가 정수가 아닙니다") from exc
        as_of_date = pd.Timestamp(values["as_of_date"])
        if pd.isna(as_of_date):
            raise ValueError("SQL checkpoint as_of_date가 비어 있습니다")
        value = float(values["value"])
        rank = float(values["rank"])
        if not np.isfinite(value) or not np.isfinite(rank):
            raise ValueError("SQL checkpoint value/rank는 유한해야 합니다")
        record = (
            str(values["factor"]) if has_factor else "",
            str(asset_id),
            str(as_of_date.normalize().date()),
            value.hex(),
            rank.hex(),
        )
        records.append(record)
    digest = hashlib.sha256()
    for record in sorted(records):
        digest.update("\x1f".join(record).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _parity_checkpoint_binding(
    campaign: dict,
    group: list[tuple],
    sql_path: Path,
    window_start: pd.Period,
    window_end: pd.Period,
) -> dict:
    return {
        "schema_version": _PARITY_CHECKPOINT_SCHEMA,
        "campaign_id": campaign["campaign_id"],
        "discovery_snapshot_digest": campaign["snapshot"][
            "discovery_input_digest"
        ],
        "sql_path": str(sql_path.relative_to(Path(__file__).resolve().parents[1])),
        "sql_sha256": _file_sha256(sql_path),
        "factor_names": sorted(item[0].name for item in group),
        "manifest_entry_digests": sorted(item[3]["manifest_entry_digest"] for item in group),
        "query_start_month": str(window_start),
        "query_end_month": str(window_end),
    }


def _parity_checkpoint_paths(binding: dict) -> tuple[Path, Path]:
    key = hashlib.sha256(_canonical_json_bytes(binding)).hexdigest()
    directory = PARITY_CHECKPOINT_ROOT / binding["campaign_id"] / key
    return directory / "result.parquet", directory / "manifest.json"


def _load_parity_checkpoint(binding: dict) -> pd.DataFrame | None:
    data_path, manifest_path = _parity_checkpoint_paths(binding)
    if not data_path.exists() and not manifest_path.exists():
        return None
    if not data_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("SQL parity checkpoint가 부분적으로만 존재합니다")
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    if metadata.get("binding") != binding:
        raise RuntimeError("SQL parity checkpoint binding이 현재 실행과 다릅니다")
    if metadata.get("parquet_sha256") != _file_sha256(data_path):
        raise RuntimeError("SQL parity checkpoint 파일 SHA-256이 다릅니다")
    frame = pd.read_parquet(data_path)
    if int(metadata.get("row_count", -1)) != len(frame):
        raise RuntimeError("SQL parity checkpoint row_count가 다릅니다")
    if metadata.get("columns") != list(frame.columns):
        raise RuntimeError("SQL parity checkpoint column 계약이 다릅니다")
    if metadata.get("result_digest") != _sql_result_digest(frame):
        raise RuntimeError("SQL parity checkpoint 행 digest가 다릅니다")
    return frame


def _write_parity_checkpoint(binding: dict, frame: pd.DataFrame) -> tuple[Path, Path]:
    data_path, manifest_path = _parity_checkpoint_paths(binding)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    result_digest = _sql_result_digest(frame)
    temporary_data: Path | None = None
    temporary_manifest: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".result-", suffix=".parquet", dir=data_path.parent, delete=False,
        ) as fh:
            temporary_data = Path(fh.name)
        frame.to_parquet(temporary_data, index=False)
        with temporary_data.open("rb") as fh:
            os.fsync(fh.fileno())
        metadata = {
            "binding": binding,
            "columns": list(frame.columns),
            "row_count": len(frame),
            "result_digest": result_digest,
            "parquet_sha256": _file_sha256(temporary_data),
        }
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".manifest-", suffix=".json",
            dir=data_path.parent, delete=False,
        ) as fh:
            fh.write(_canonical_json_bytes(metadata))
            fh.flush()
            os.fsync(fh.fileno())
            temporary_manifest = Path(fh.name)
        temporary_data.replace(data_path)
        temporary_data = None
        temporary_manifest.replace(manifest_path)
        temporary_manifest = None
    finally:
        if temporary_data is not None:
            temporary_data.unlink(missing_ok=True)
        if temporary_manifest is not None:
            temporary_manifest.unlink(missing_ok=True)
    return data_path, manifest_path


def _archive_panel(path: Path, *, key: str | None = None) -> Path:
    """Keep an immutable copy before an active panel cache is replaced."""
    file_digest = _file_sha256(path)
    destination = (
        PANEL_ARCHIVE / key / file_digest / "panel.pkl"
        if key is not None
        else PANEL_ARCHIVE / f"legacy-file-{file_digest}" / "panel.pkl"
    )
    if destination.exists():
        if _file_sha256(destination) != file_digest:
            raise RuntimeError(f"패널 archive key 충돌: {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".pkl.tmp")
    shutil.copyfile(path, temporary)
    temporary.replace(destination)
    return destination


def _activate_panel_cache(panel: P.Panel) -> tuple[Path, Path | None]:
    """Validate, archive, and atomically activate one fully-built panel."""
    CACHE.mkdir(parents=True, exist_ok=True)
    P.verify_return_roles(panel)
    evidence = P.verify_asset_identity(panel)
    temporary_path: Path | None = None
    previous_archive: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".panel-", suffix=".pkl", dir=CACHE,
            delete=False,
        ) as fh:
            pickle.dump(panel, fh)
            fh.flush()
            os.fsync(fh.fileno())
            temporary_path = Path(fh.name)
        with temporary_path.open("rb") as fh:
            persisted = pickle.load(fh)
        P.verify_return_roles(persisted)
        P.verify_asset_identity(persisted)
        # Persist the content-addressed version before changing the active file.
        _archive_panel(
            temporary_path, key=evidence["asset_identity_digest"],
        )
        if PANEL_CACHE.exists():
            previous_archive = _archive_panel(PANEL_CACHE)
        temporary_path.replace(PANEL_CACHE)
        temporary_path = None
        return PANEL_CACHE, previous_archive
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _implementation_contract(
    factor: F.Factor,
) -> tuple[publish.ImplementationRef, dict, Path, dict]:
    """Authenticate one repository-owned query and its research binding."""
    from factors.candidate_loader import RESEARCH_SPECS

    research_spec = RESEARCH_SPECS.get(factor.name)
    strategy_sha256 = (
        research_spec.get("strategy_sha256")
        if isinstance(research_spec, dict) else None
    )
    if not _SHA256.fullmatch(str(strategy_sha256)):
        raise ValueError(f"동결할 후보 전략 파일 SHA-256이 없습니다: {factor.name}")
    research_repo = Path(__file__).resolve().parents[1]
    manifest_path = research_repo / "implementations/gold/manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Gold 구현 manifest가 없습니다: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = manifest.get(factor.name)
    if spec is None:
        raise ValueError(f"Gold 구현이 없는 팩터입니다: {factor.name}")
    if int(spec.get("predicted_sign", 0)) != factor.predicted_sign:
        raise ValueError(f"Gold manifest predicted_sign 불일치: {factor.name}")
    if spec.get("research_definition_hash") != factor.definition_hash:
        raise ValueError(f"Gold manifest research_definition_hash 불일치: {factor.name}")
    if spec.get("value_contract") != publish.VALUE_CONTRACT_ID:
        raise ValueError(f"Gold value/rank 계약 불일치: {factor.name}")
    relative = Path(spec["sql"])
    sql_path = (research_repo / relative).resolve()
    if research_repo.resolve() not in sql_path.parents or not sql_path.is_file():
        raise ValueError(f"허용된 Gold SQL 파일을 찾을 수 없습니다: {relative}")
    sql_text = sql_path.read_text(encoding="utf-8")
    implementation.validate_feature_sql(sql_text)
    reference = publish.ImplementationRef(
        uri=f"repo://factor-research/{relative.as_posix()}",
        sha256=hashlib.sha256(sql_path.read_bytes()).hexdigest(),
        research_definition_hash=factor.definition_hash,
    )
    binding = {
        "factor": factor.name,
        "definition_hash": factor.definition_hash,
        "strategy_sha256": strategy_sha256,
        "predicted_sign": factor.predicted_sign,
        "value_contract": publish.VALUE_CONTRACT_ID,
        "implementation_uri": reference.uri,
        "implementation_sha256": reference.sha256,
        "manifest_entry_digest": implementation.manifest_entry_digest(spec),
    }
    return reference, spec, sql_path, binding


def _implementation_ref(factor: F.Factor) -> publish.ImplementationRef:
    """Bind a research factor to one allowlisted TeamAlpha Gold SQL file."""
    reference, _spec, _sql_path, _binding = _implementation_contract(factor)
    return reference


def _implementation_bindings(factors: list[F.Factor]) -> list[dict]:
    return [_implementation_contract(factor)[3] for factor in factors]


def load_registry():
    """Load stable builtins plus agent-authored candidates, idempotently."""
    import factors.builtin  # noqa: F401
    from factors.candidate_loader import load_candidates

    load_candidates(F.REGISTRY)
    return F.REGISTRY


def cmd_build(args):
    CACHE.mkdir(exist_ok=True)
    load_registry()
    with silver.connect(read_only=True) as conn:
        pan = P.build(conn)
        fund = fundamentals.build(conn)
    # Materializing the Silver revision ledger is the expensive part of a build.
    # Cache every PIT feature produced from that same immutable ledger so a newly
    # pre-registered factor does not force another full RDS transfer merely
    # because it asks for a previously unused accounting column.
    available_features = sorted(set(fund.columns) - {"asset_id", "available_date"})
    df = fundamentals.attach(pan.monthly, fund, available_features)
    df = df.sort_values(["Code", "ym"]).reset_index(drop=True)
    pan.monthly = df
    for tag, term in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        df[f"fwd_{tag}"] = P.forward_returns(pan, terminal=term)   # 인덱스 정렬 (위치대입 금지)
    pan.monthly = df
    active, previous_archive = _activate_panel_cache(pan)
    if previous_archive is not None:
        print(f"\n기존 캐시 보존: {previous_archive}")
    print(f"원시 연구 입력 캐시 저장: {active}  ({len(df):,}행, 팩터 선계산 없음)")
    print(f"asset identity: {pan.meta['asset_identity_digest']}")


def _load():
    with PANEL_CACHE.open("rb") as fh:
        panel = pickle.load(fh)
    required = {
        "asset_id", "adj_close", "total_return_close", "quality_run_id",
        "total_return_quality_run_id",
        "amihud_illiquidity_1m", "amihud_observations_1m",
        "daily_volatility_252d", "daily_return_observations_252d",
        "max_daily_return_1m", "max_daily_return_observations_1m",
        "price_high_252d", "price_high_observations_252d",
    }
    try:
        P.verify_return_roles(panel)
        return_evidence = silver.verify_total_return_validation_evidence(
            panel.meta.get("return_contract_validation_evidence"),
        )
    except RuntimeError:
        valid_return_contract = False
    else:
        valid_return_contract = (
            panel.meta.get("label_return_field") == "total_return_close"
            and panel.meta.get("label_return_methodology")
            == silver.TOTAL_RETURN_METHOD
            and panel.meta.get("label_return_contract_status") == "CERTIFIED"
            and panel.meta.get("label_return_usage")
            == silver.LABEL_RETURN_USAGE
            and panel.meta.get("label_candidate_access") is False
            and panel.meta.get("feature_price_field") == "adj_close"
            and panel.meta.get("feature_return_methodology")
            == silver.FEATURE_RETURN_METHOD
            and panel.meta.get("return_contract_validation_status") == "VERIFIED"
            and panel.meta.get("return_contract_run_id")
            == return_evidence["quality_run_id"]
            and panel.meta.get("return_contract_evidence_sha256")
            == return_evidence["evidence_sha256"]
        )
    try:
        P.verify_asset_identity(panel)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise SystemExit(
            "캐시의 asset identity 계약이 없거나 현재 내용과 일치하지 않습니다. "
            "`uv run python scripts/run.py build`로 현재 RDS에서 다시 만드세요."
        ) from exc
    if (
        panel.meta.get("source") != "RDS public Silver"
        or not required.issubset(panel.monthly.columns)
        or not valid_return_contract
    ):
        raise SystemExit(
            "캐시가 구형이거나 feature/label 수익률 계약이 없습니다. "
            "Silver 총수익 rebuild 후 `uv run python scripts/run.py build`로 "
            "인증 캐시를 다시 만드세요."
        )
    return panel


def _ensure_factor_columns(pan, targets):
    """인증된 연구 view에서 요청한 후보만 즉석 계산한다.

    build 캐시는 Silver/PIT 입력만 보관한다. 후보 값은 사전등록된 평가가
    요청될 때마다 격리된 2015+ 입력 view에서 계산하며 Gold에 쓰지 않는다.
    """
    df = pan.monthly
    research_policy.assert_research_input_frame(df)
    for factor in targets:
        research_policy.assert_allowed_lookback(
            name=factor.name, source=factor.source, params=factor.params,
        )
    missing = [f for f in targets if f"f_{f.name}" not in df.columns]
    if not missing:
        return df
    lacking = {c for f in missing for c in f.needs if c not in df.columns}
    if lacking:
        raise SystemExit(
            f"패널에 없는 컬럼이 필요합니다: {sorted(lacking)}\n"
            f"  → uv run python scripts/run.py build  (재빌드 필요)")
    print(f"[gate] 신규 팩터 {len(missing)}개 즉석 계산: "
          f"{', '.join(f.name for f in missing)}")
    compute_context = research_policy.build_factor_compute_context(df)
    for f in missing:
        started = time.perf_counter()
        try:
            column = f"f_{f.name}"
            df[column] = (
                research_policy.compute_factor(
                    f, df, context=compute_context,
                ) * f.predicted_sign
            )
            research_policy.bind_authoritative_factor_column(f, df, column)
        except Exception as exc:
            df[f"f_{f.name}"] = float("nan")
            print(f"  ⚠️  {f.name} 계산 실패: {type(exc).__name__}: {exc}")
        finally:
            _log_timing("discovery.factor_compute", started, factor=f.name)
    pan.monthly = df
    return df


def _candidate_preflight_frame(
    campaign: dict,
    panel: P.Panel,
    factors: list[F.Factor],
) -> tuple[P.Panel, P.Panel, pd.DataFrame, pd.Series, str, pd.Period]:
    """Build one label-free candidate frame shared by registration gates.

    Forward returns are never read. Investability is used only as T5's fixed
    comparison universe, exactly as in the final Gold signal gate.
    """
    discovery = _scope_discovery_panel(
        panel,
        data_cutoff=campaign["discovery"]["data_cutoff"],
        oos_start=campaign["oos"]["start"],
    )
    snapshot_digest = P.snapshot_digest(discovery)
    expected_digest = campaign["snapshot"]["discovery_input_digest"]
    if snapshot_digest != expected_digest:
        raise ValueError(
            "campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다"
        )
    research_panel = _research_input_panel(discovery)
    frame = _ensure_factor_columns(research_panel, factors)
    signal_end = pd.Period(campaign["discovery"]["signal_end"], freq="M")
    scope = (
        research_panel.universe.reindex(frame.index).fillna(False)
        & frame["ym"].ge(gate.RESEARCH_START)
        & frame["ym"].le(signal_end)
    )
    return discovery, research_panel, frame, scope, snapshot_digest, signal_end


def _candidate_input_feasibility(
    factors: list[F.Factor],
    *,
    frame: pd.DataFrame,
    scope: pd.Series,
    snapshot_digest: str,
    signal_end: pd.Period,
) -> dict:
    metrics: dict[str, dict] = {}
    for factor in factors:
        values = pd.to_numeric(frame[f"f_{factor.name}"], errors="coerce")
        scoped = pd.DataFrame({
            "ym": frame.loc[scope, "ym"],
            "available": values.loc[scope].notna(),
        })
        monthly = scoped.groupby("ym")["available"].mean()
        metrics[factor.name] = {
            "coverage": float(scoped["available"].mean()) if len(scoped) else 0.0,
            "monthly_coverage_p10": (
                float(monthly.quantile(.10)) if len(monthly) else 0.0
            ),
        }
    return research_policy.input_feasibility_artifact(
        factors,
        snapshot_digest=snapshot_digest,
        signal_start=str(gate.RESEARCH_START),
        signal_end=str(signal_end),
        metrics=metrics,
        minimum_coverage=gate.TH["coverage"],
        minimum_monthly_p10=gate.TH["monthly_coverage_p10"],
    )


def preflight_candidate_inputs(
    campaign: dict,
    panel: P.Panel,
    factors: list[F.Factor],
) -> dict:
    """Run T1.1's label-free coverage contract before registration."""
    _discovery, _research_panel, frame, scope, snapshot_digest, signal_end = (
        _candidate_preflight_frame(campaign, panel, factors)
    )
    return _candidate_input_feasibility(
        factors,
        frame=frame,
        scope=scope,
        snapshot_digest=snapshot_digest,
        signal_end=signal_end,
    )


def preflight_candidate_registration(
    campaign: dict,
    panel: P.Panel,
    factors: list[F.Factor],
) -> tuple[dict, dict]:
    """Run coverage and result-blind Gold correlation on one computed frame."""
    discovery, research_panel, frame, scope, snapshot_digest, signal_end = (
        _candidate_preflight_frame(campaign, panel, factors)
    )
    feasibility = _candidate_input_feasibility(
        factors,
        frame=frame,
        scope=scope,
        snapshot_digest=snapshot_digest,
        signal_end=signal_end,
    )
    with silver.connect(read_only=True) as conn:
        if campaign.get("input_generation") is not None:
            silver.verify_live_research_generation(
                conn, campaign["input_generation"],
            )
        else:
            silver.verify_live_total_return_contract(
                conn, research_panel.meta.get(
                    "return_contract_validation_evidence"
                ),
            )
            P.verify_live_asset_identity(
                conn,
                discovery,
                cutoff=str(pd.Timestamp(discovery.monthly["trade_date"].max()).date()),
            )
        approved = _approved_signals(conn, frame)
    eligible = (
        scope
        & research_panel.investable.reindex(frame.index).fillna(False)
    )
    relationships = gate.gold_signal_preflight(
        frame,
        {
            factor.name: frame[f"f_{factor.name}"]
            for factor in factors
        },
        approved,
        eligible=eligible,
    )
    gold_preflight = research_policy.gold_signal_preflight_artifact(
        factors,
        snapshot_digest=snapshot_digest,
        gold_family_digest=_signal_family_digest(approved),
        approved_factors=sorted(approved),
        relationships=relationships,
        threshold=gate.TH["max_gold_corr"],
        minimum_comparison_months=gate.TH["min_gold_corr_months"],
    )
    return feasibility, gold_preflight


def _reuse_factor_columns(
    source: pd.DataFrame,
    target_panel: P.Panel,
    targets: list[F.Factor],
) -> pd.DataFrame:
    """Copy causal factor outputs to an exact row-subset without recomputation."""
    keys = ["asset_id", "trade_date"]
    source_index = pd.MultiIndex.from_frame(source[keys])
    target = target_panel.monthly
    target_index = pd.MultiIndex.from_frame(target[keys])
    if source_index.has_duplicates or target_index.has_duplicates:
        raise ValueError("factor 재사용 row identity는 고유해야 합니다")
    positions = source_index.get_indexer(target_index)
    if (positions < 0).any():
        raise ValueError("discovery row가 confirmation snapshot의 exact subset이 아닙니다")
    for factor in targets:
        column = f"f_{factor.name}"
        if column not in source:
            raise ValueError(f"재사용할 factor column이 없습니다: {column}")
        if research_policy.authoritative_factor_values(
            factor, source, column,
        ) is None:
            raise ValueError(
                f"재사용할 factor column의 authoritative binding이 없습니다: {column}"
            )
        target[column] = source[column].to_numpy()[positions]
        research_policy.bind_authoritative_factor_column(factor, target, column)
    target_panel.monthly = target
    return target


def _approved_signals(conn, df: pd.DataFrame) -> dict[str, pd.Series]:
    approved_keys = silver.load_approved_factor_keys(conn)
    values = silver.load_approved_values(conn)
    target = pd.MultiIndex.from_arrays([df["asset_id"], df["ym"]])
    output = {
        name: pd.Series(float("nan"), index=df.index, dtype=float)
        for name in approved_keys
    }
    if values.empty:
        return output
    values["ym"] = pd.to_datetime(values["as_of_date"]).dt.to_period("M")
    for name, group in values.groupby("factor_key"):
        keyed = (group.sort_values("as_of_date")
                 .drop_duplicates(["asset_id", "ym"], keep="last")
                 .set_index(["asset_id", "ym"])["value"])
        output[str(name)] = pd.Series(keyed.reindex(target).to_numpy(dtype=float), index=df.index)
    return output


def _signal_family_digest(signals: dict[str, pd.Series]) -> str:
    digest = hashlib.sha256()
    for name in sorted(signals):
        digest.update(name.encode("utf-8"))
        digest.update(pd.util.hash_pandas_object(signals[name], index=True).values.tobytes())
    return digest.hexdigest()


def _research_policy_metadata() -> dict:
    return {
        "research_input_start": str(research_policy.RESEARCH_INPUT_START),
        "common_evaluation_start": str(research_policy.COMMON_EVALUATION_START),
        "max_factor_lookback_months": (
            research_policy.MAX_FACTOR_LOOKBACK_MONTHS
        ),
    }


def _research_input_panel(pan: P.Panel) -> P.Panel:
    """Derive the only frame that factor code is allowed to inspect.

    The parent panel keeps the complete pre-2015 history so its cache/live RDS
    identity digest remains verifiable.  This child view is created only after
    the parent identity has been checked and strips every cached factor column
    before exposing rows to candidate code.
    """
    parent_identity = pan.meta.get("asset_identity_digest")
    scoped = research_policy.research_input_frame(pan.monthly)
    scoped = scoped.drop(
        columns=[column for column in scoped if str(column).startswith("f_")],
        errors="ignore",
    ).copy()
    asset_ids = set(scoped["asset_id"].unique())
    dead = pan.dead[pan.dead.index.isin(asset_ids)].copy()
    meta = dict(pan.meta)
    meta.update(_research_policy_metadata())
    meta["parent_asset_identity_digest"] = parent_identity
    meta["parent_panel_start"] = str(pan.monthly["ym"].min())
    meta["parent_panel_end"] = str(pan.monthly["ym"].max())
    meta["asset_identity_scope"] = "research_input_derived_from_verified_parent"
    output = P.Panel(monthly=scoped, dead=dead, meta=meta)
    P.bind_asset_identity(output)
    research_policy.assert_research_input_frame(output.monthly)
    return output


def _rebuild_scoped_panel(
    pan: P.Panel,
    scoped: pd.DataFrame,
    **meta_updates,
) -> P.Panel:
    """Recompute dead membership and forward labels at the scoped boundary."""
    scoped = scoped.drop(
        columns=[column for column in scoped if str(column).startswith("f_")],
        errors="ignore",
    ).copy()
    last_day = pd.Timestamp(scoped["trade_date"].max())
    last_seen = scoped.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < last_day - pd.Timedelta(days=P.INACTIVE_DAYS)]
    # Later closure observations are expected to be appended before reveal.
    # Bind scoped evidence to stable source contracts, not mutable full-cache
    # metadata such as last_day/n_dead that lies beyond the frozen cutoff.
    meta = {
        key: pan.meta.get(key)
        for key in (
            "source",
            *P.RETURN_ROLE_META_KEYS,
            "label_return_contract_status",
            "return_contract_run_id",
            "return_contract_validation_status",
            "return_contract_evidence_sha256",
            "return_contract_scope_start",
            "return_contract_coverage_start",
            "return_contract_coverage_end",
            "return_contract_action_snapshot_run_id",
            "return_contract_asset_identity_digest",
            "return_contract_validation_evidence",
        )
        if key in pan.meta
    }
    meta.update(_research_policy_metadata())
    meta.update(meta_updates)
    output = P.Panel(monthly=scoped, dead=dead, meta=meta)
    P.bind_asset_identity(output)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = P.forward_returns(output, terminal=terminal)
    return output


def _closure_observation_identity(
    pan: P.Panel, *, closure_month: pd.Period | str,
) -> dict:
    """Bind every observation used to decide terminal membership at OOS."""
    month = pd.Period(closure_month, freq="M")
    observed = pan.monthly[pan.monthly["ym"].le(month)].copy()
    if observed.empty or observed["ym"].max() != month:
        raise ValueError(f"OOS closure month {month} 관측이 패널에 없습니다")
    return P.asset_identity_evidence(observed)


def _bind_closure_asset_identity(meta: dict, evidence: dict) -> None:
    for key in silver.ASSET_IDENTITY_META_KEYS:
        meta[f"closure_{key}"] = evidence[key]


def _closure_asset_identity(panel: P.Panel) -> dict:
    evidence = {}
    for key in silver.ASSET_IDENTITY_META_KEYS:
        meta_key = f"closure_{key}"
        if meta_key not in panel.meta:
            raise RuntimeError(
                f"confirmation closure identity 메타데이터가 없습니다: {meta_key}"
            )
        evidence[key] = panel.meta[meta_key]
    return evidence


def _verify_confirmation_live_identity(conn, panel: P.Panel) -> None:
    """Verify both return rows and closure rows in one DB snapshot."""
    P.verify_live_asset_identity(conn, panel)
    closure = _closure_asset_identity(panel)
    silver.verify_live_asset_identity(
        conn, closure, cutoff=closure["asset_identity_cutoff"],
    )


def _assert_confirmation_asset_identity(
    panel: P.Panel,
    *,
    mode: str,
    historical_snapshot_identity_digest: str | None,
) -> dict:
    """Authenticate confirmation rows under the campaign's boundary mode."""
    actual = P.verify_asset_identity(panel)
    if mode == HISTORICAL_HOLDOUT_MODE:
        if actual["asset_identity_digest"] != historical_snapshot_identity_digest:
            raise ValueError(
                "campaign 생성 당시 confirmation asset identity를 재현하지 못했습니다"
            )
    elif mode != PROSPECTIVE_HOLDOUT_MODE:
        raise ValueError(f"지원하지 않는 confirmation mode입니다: {mode!r}")
    # Prospective confirmation rows did not exist at campaign start. The
    # original snapshot is verified separately; future rows are cache↔live
    # checked in one repeatable-read transaction at reveal.
    return actual


def _scope_snapshot_panel(pan: P.Panel, *, snapshot_cutoff: str) -> P.Panel:
    """Rebuild the exact completed Silver input frozen at campaign creation."""
    cutoff = pd.Timestamp(snapshot_cutoff).normalize()
    frame = pan.monthly
    scoped = frame[
        pd.to_datetime(frame["trade_date"]).dt.normalize().le(cutoff)
    ].copy()
    if scoped.empty or pd.Timestamp(scoped["trade_date"].max()).normalize() != cutoff:
        raise ValueError(
            "현재 캐시로 campaign snapshot을 정확히 재현할 수 없습니다: "
            f"cutoff={cutoff.date()}"
        )
    return _rebuild_scoped_panel(
        pan, scoped, campaign_snapshot_cutoff=str(cutoff.date()),
    )


def _scope_discovery_panel(
    pan: P.Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period | str,
) -> P.Panel:
    """Expose only the campaign snapshot to candidate code and discovery gates."""
    cutoff = pd.Timestamp(data_cutoff).normalize()
    start = pd.Period(oos_start, freq="M")
    CampaignWindow.create(
        discovery_data_cutoff=str(cutoff.date()),
        oos_start=start,
        oos_months=gate.TH["min_oos_months"],
    )
    frame = pan.monthly
    scoped = frame[
        pd.to_datetime(frame["trade_date"]).dt.normalize().le(cutoff)
        & frame["ym"].lt(start)
    ].copy()
    if scoped.empty or pd.Timestamp(scoped["trade_date"].max()).normalize() != cutoff:
        raise ValueError(
            "현재 캐시로 campaign cutoff를 정확히 재현할 수 없습니다: "
            f"cutoff={cutoff.date()}. campaign 생성 당시 Silver snapshot을 복구하세요."
        )
    return _rebuild_scoped_panel(
        pan, scoped,
        campaign_data_cutoff=str(cutoff.date()),
        campaign_oos_start=str(start),
    )


def _scope_confirmation_panel(
    pan: P.Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period | str,
    oos_end: pd.Period | str,
) -> P.Panel:
    """Build the fixed OOS snapshot without leaking later observations.

    Signal/return rows stop at ``required_month``.  The immediately following
    month is visible only to prove that the return month is closed and to decide
    whether a name that vanished at the OOS boundary is inactive.  Otherwise a
    disappearing stock's terminal return can be selectively lost.
    """
    window = CampaignWindow.create(
        discovery_data_cutoff=data_cutoff,
        oos_start=oos_start,
        oos_months=gate.TH["min_oos_months"],
    )
    window.validate_oos_end(oos_end)
    signal_end = window.oos_signal_end
    required_month = window.oos_return_end
    closure_month = window.closure_month
    if pan.monthly["ym"].max() < closure_month:
        raise ValueError(
            f"OOS 수익률 월 {required_month}의 월말 확정에는 "
            f"다음 달({closure_month}) 관측이 필요합니다"
        )
    observed = pan.monthly[pan.monthly["ym"] <= closure_month].copy()
    if observed.empty or observed["ym"].max() != closure_month:
        raise ValueError(f"OOS 확정 월 {closure_month} 관측이 snapshot에 없습니다")
    closure_as_of = pd.Timestamp(observed["trade_date"].max()).normalize()
    closure_identity = P.asset_identity_evidence(
        observed, cutoff=closure_as_of,
    )
    inactive_ready_after = (
        signal_end.to_timestamp(how="end").normalize()
        + pd.Timedelta(days=P.INACTIVE_DAYS)
    )
    if closure_as_of <= inactive_ready_after:
        raise ValueError(
            "OOS 경계 비활성 종목을 판정하기에는 확정 월 관측일이 너무 이릅니다: "
            f"현재 {closure_as_of.date()}, 최소 {inactive_ready_after.date()} 이후"
        )
    scoped = observed[observed["ym"] <= required_month].copy()
    if scoped.empty or scoped["ym"].max() != required_month:
        raise ValueError(
            f"고정 OOS 마지막 수익률 월 {required_month}이 snapshot에 없습니다"
        )
    scoped = scoped.drop(
        columns=[column for column in scoped if str(column).startswith("f_")],
        errors="ignore",
    ).copy()
    last_seen = observed.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < closure_as_of - pd.Timedelta(days=P.INACTIVE_DAYS)]
    meta = {
        key: pan.meta.get(key)
        for key in (
            "source",
            *P.RETURN_ROLE_META_KEYS,
            "label_return_contract_status",
            "return_contract_run_id",
            "return_contract_validation_status",
            "return_contract_evidence_sha256",
            "return_contract_scope_start",
            "return_contract_coverage_start",
            "return_contract_coverage_end",
            "return_contract_action_snapshot_run_id",
            "return_contract_asset_identity_digest",
            "return_contract_validation_evidence",
        )
        if key in pan.meta
    }
    meta.update(_research_policy_metadata())
    meta.update({
        "confirmation_signal_end": str(signal_end),
        "confirmation_required_month": str(required_month),
        "confirmation_closure_month": str(closure_month),
        "confirmation_closure_as_of": str(closure_as_of.date()),
    })
    _bind_closure_asset_identity(meta, closure_identity)
    output = P.Panel(monthly=scoped, dead=dead, meta=meta)
    P.bind_asset_identity(output)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = P.forward_returns(output, terminal=terminal)
    return output


def verify_implementations(campaign: dict, factors: list[F.Factor]) -> list[dict]:
    """Run read-only, discovery-only Python/Gold SQL parity for all qualifiers."""
    total_started = time.perf_counter()
    window = validate_manifest(
        campaign, expected_oos_months=gate.TH["min_oos_months"],
    )
    started = time.perf_counter()
    base_panel = _load()
    _log_timing("parity.panel_load", started)
    started = time.perf_counter()
    discovery_panel = _scope_discovery_panel(
        base_panel,
        data_cutoff=window.discovery_data_cutoff,
        oos_start=window.oos_signal_start,
    )
    snapshot_digest = P.snapshot_digest(discovery_panel)
    expected_digest = campaign["snapshot"]["discovery_input_digest"]
    if snapshot_digest != expected_digest:
        raise ValueError("campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다")
    identity = P.verify_asset_identity(discovery_panel)
    expected_identity = campaign["snapshot"].get(
        "discovery_asset_identity_digest"
    )
    if identity["asset_identity_digest"] != expected_identity:
        raise ValueError(
            "campaign 생성 당시 discovery asset identity를 재현하지 못했습니다"
        )
    _log_timing("parity.snapshot_scope", started)

    start = gate.RESEARCH_START
    end = window.discovery_signal_end
    evidence_by_name: dict[str, dict] = {}
    prepared: list[tuple[F.Factor, dict, Path, dict, pd.DataFrame]] = []

    # Python reference values depend only on the frozen local discovery
    # snapshot.  Compute them before opening the live RDS transaction so a
    # long local factor cannot consume the bounded SSM tunnel lifetime.  The
    # live identity check and every SQL parity query still share one
    # read-only REPEATABLE READ transaction below.
    research_panel = _research_input_panel(discovery_panel)
    frame = research_panel.monthly
    in_scope = (
        research_panel.universe
        & frame["ym"].ge(start)
        & frame["ym"].le(end)
    )
    for factor in factors:
        binding: dict | None = None
        from factors.candidate_loader import RESEARCH_SPECS
        strategy_sha256 = RESEARCH_SPECS[factor.name]["strategy_sha256"]
        try:
            _reference, spec, sql_path, binding = _implementation_contract(factor)
        except Exception as exc:
            evidence_by_name[factor.name] = implementation.failure_evidence(
                factor,
                discovery_signal_start=start,
                discovery_signal_end=end,
                discovery_snapshot_digest=snapshot_digest,
                strategy_sha256=strategy_sha256,
                stage="contract",
                error=exc,
                binding=binding,
            )
            continue
        started = time.perf_counter()
        try:
            research_policy.assert_allowed_lookback(
                name=factor.name,
                source=factor.source,
                params=factor.params,
            )
            raw = research_policy.compute_factor(factor, frame)
            if not isinstance(raw, pd.Series) or not raw.index.equals(frame.index):
                raise ValueError(
                    "Python factor가 입력 index의 Series를 반환하지 않습니다: "
                    f"{factor.name}"
                )
            raw = pd.to_numeric(raw, errors="coerce")
            finite = pd.Series(
                pd.notna(raw) & (raw.abs() != float("inf")), index=raw.index,
            )
            valid = in_scope & finite
            python_frame = frame.loc[
                valid, ["asset_id", "trade_date"]
            ].rename(columns={"trade_date": "as_of_date"})
            python_frame["value"] = raw.loc[valid].astype(float).to_numpy()
        except Exception as exc:
            evidence_by_name[factor.name] = implementation.failure_evidence(
                factor,
                discovery_signal_start=start,
                discovery_signal_end=end,
                discovery_snapshot_digest=snapshot_digest,
                strategy_sha256=strategy_sha256,
                stage="python_compute",
                error=exc,
                binding=binding,
            )
            continue
        finally:
            _log_timing(
                "parity.python_factor", started, factor=factor.name,
            )
        prepared.append((factor, spec, sql_path, binding, python_frame))

    try:
        with silver.connect(read_only=True) as conn:
            started = time.perf_counter()
            # This check and every parity query share one read-only transaction.
            # A re-keyed RDS therefore fails before candidate or Gold SQL runs.
            if campaign.get("input_generation") is not None:
                silver.verify_live_research_generation(
                    conn, campaign["input_generation"],
                )
            else:
                silver.verify_live_total_return_contract(
                    conn,
                    discovery_panel.meta.get(
                        "return_contract_validation_evidence"
                    ),
                )
                P.verify_live_asset_identity(
                    conn, discovery_panel,
                    cutoff=window.discovery_data_cutoff,
                )
            _log_timing("parity.live_identity", started)
            if prepared:
                query_groups: dict[Path, list[tuple]] = {}
                for item in prepared:
                    query_groups.setdefault(item[2], []).append(item)
                for sql_path in sorted(query_groups, key=str):
                    group = query_groups[sql_path]
                    sql_started = time.perf_counter()
                    try:
                        chunk_values = {
                            spec.get("query_chunk_months")
                            for _factor, spec, _path, _binding, _python in group
                        }
                        if len(chunk_values) != 1:
                            raise ValueError(
                                "공유 Gold SQL의 query_chunk_months가 서로 다릅니다"
                            )
                        windows = _parity_query_windows(
                            start, end, chunk_values.pop(),
                        )
                        planner_values = {
                            spec.get("planner_enable_nestloop", True)
                            for _factor, spec, _path, _binding, _python in group
                        }
                        if len(planner_values) != 1:
                            raise ValueError(
                                "공유 Gold SQL의 planner 계약이 서로 다릅니다"
                            )
                        planner_enable_nestloop = planner_values.pop()
                        sql_text = sql_path.read_text(encoding="utf-8")
                        query_frames = []
                        for chunk_index, (window_start, window_end) in enumerate(
                            windows, start=1,
                        ):
                            chunk_started = time.perf_counter()
                            checkpoint_binding = _parity_checkpoint_binding(
                                campaign, group, sql_path, window_start, window_end,
                            )
                            chunk_frame = _load_parity_checkpoint(
                                checkpoint_binding,
                            )
                            checkpoint_reused = chunk_frame is not None
                            temp_files_delta = 0
                            temp_bytes_delta = 0
                            if chunk_frame is None:
                                temp_files_before, temp_bytes_before = (
                                    _database_temp_usage(conn)
                                )
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        "SET LOCAL enable_nestloop = "
                                        + ("on" if planner_enable_nestloop else "off")
                                    )
                                    cursor.execute(sql_text, {
                                        "start_month": f"{window_start}-01",
                                        "end_month": f"{window_end}-01",
                                    })
                                    rows = cursor.fetchall()
                                    columns = [
                                        column.name for column in cursor.description
                                    ]
                                chunk_frame = pd.DataFrame(rows, columns=columns)
                                _write_parity_checkpoint(
                                    checkpoint_binding, chunk_frame,
                                )
                                temp_files_after, temp_bytes_after = (
                                    _database_temp_usage(conn)
                                )
                                temp_files_delta = (
                                    temp_files_after - temp_files_before
                                )
                                temp_bytes_delta = (
                                    temp_bytes_after - temp_bytes_before
                                )
                            query_frames.append(chunk_frame)
                            _log_timing(
                                "parity.sql_query_chunk",
                                chunk_started,
                                sql=sql_path.name,
                                factor_count=len(group),
                                chunk_index=chunk_index,
                                chunk_count=len(windows),
                                query_start_month=str(window_start),
                                query_end_month=str(window_end),
                                checkpoint_reused=checkpoint_reused,
                                database_temp_files_global_delta=temp_files_delta,
                                database_temp_bytes_global_delta=temp_bytes_delta,
                            )
                        query_frame = pd.concat(query_frames, ignore_index=True)
                        _log_timing(
                            "parity.sql_query",
                            sql_started,
                            sql=sql_path.name,
                            factor_count=len(group),
                            query_chunk_count=len(windows),
                        )
                        discriminated = any(
                            spec.get("result_factor") is not None
                            for _factor, spec, _path, _binding, _python in group
                        )
                        if discriminated and "factor" not in query_frame.columns:
                            raise ValueError(
                                "공유 Gold SQL에 factor discriminator가 없습니다"
                            )
                        for factor, spec, _path, binding, python_frame in group:
                            parity_started = time.perf_counter()
                            result_factor = spec.get("result_factor")
                            if discriminated:
                                if result_factor != factor.name:
                                    raise ValueError(
                                        "Gold manifest result_factor가 후보와 다릅니다: "
                                        f"{factor.name}"
                                    )
                                sql_frame = query_frame.loc[
                                    query_frame["factor"].eq(result_factor)
                                ].drop(columns="factor")
                            else:
                                sql_frame = query_frame
                            evidence_by_name[factor.name] = implementation.compare_parity(
                                factor,
                                python_frame,
                                sql_frame,
                                implementation_uri=binding["implementation_uri"],
                                implementation_sha256=binding["implementation_sha256"],
                                manifest_spec=spec,
                                discovery_signal_start=start,
                                discovery_signal_end=end,
                                discovery_snapshot_digest=snapshot_digest,
                                strategy_sha256=binding["strategy_sha256"],
                                atol=float(spec.get(
                                    "parity_atol", implementation.DEFAULT_ATOL,
                                )),
                                rtol=float(spec.get(
                                    "parity_rtol", implementation.DEFAULT_RTOL,
                                )),
                                allow_tolerance_equivalent_ranks=bool(spec.get(
                                    "allow_tolerance_equivalent_ranks", False,
                                )),
                            )
                            _log_timing(
                                "parity.compare",
                                parity_started,
                                factor=factor.name,
                            )
                    except Exception as exc:
                        _log_timing(
                            "parity.sql_query_or_compare_failed",
                            sql_started,
                            sql=sql_path.name,
                            factor_count=len(group),
                        )
                        for factor, _spec, _path, binding, _python_frame in group:
                            evidence_by_name[factor.name] = implementation.failure_evidence(
                                factor,
                                discovery_signal_start=start,
                                discovery_signal_end=end,
                                discovery_snapshot_digest=snapshot_digest,
                                strategy_sha256=binding["strategy_sha256"],
                                stage="sql_execute_or_parity",
                                error=exc,
                                binding=binding,
                            )
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        for factor, _spec, _sql_path, binding, _python_frame in prepared:
            if factor.name not in evidence_by_name:
                evidence_by_name[factor.name] = implementation.failure_evidence(
                    factor,
                    discovery_signal_start=start,
                    discovery_signal_end=end,
                    discovery_snapshot_digest=snapshot_digest,
                    strategy_sha256=binding["strategy_sha256"],
                    stage="database_connect",
                    error=exc,
                    binding=binding,
                )
        if not prepared:
            raise
    _log_timing("parity.total", total_started, factor_count=len(factors))
    return [evidence_by_name[factor.name] for factor in factors]


def _confirmation_gate_result(row: dict) -> gate.Result:
    evaluation = row.get("evaluation") or {}
    if evaluation.get("factor") != row.get("factor"):
        raise ValueError("confirmation factor identity가 evaluation과 다릅니다")
    if evaluation.get("definition_hash") != row.get("definition_hash"):
        raise ValueError("confirmation definition hash가 evaluation과 다릅니다")
    if evaluation.get("verdict") != row.get("verdict"):
        raise ValueError("confirmation verdict가 evaluation과 다릅니다")
    try:
        verdict = gate.Verdict(row["verdict"])
    except (KeyError, ValueError) as exc:
        raise ValueError("confirmation verdict가 유효하지 않습니다") from exc
    checks = [
        gate.Check(
            str(check.get("tier")),
            str(check.get("name")),
            check.get("passed"),
            check.get("value"),
            str(check.get("threshold") or ""),
            str(check.get("note") or ""),
        )
        for check in evaluation.get("checks") or []
    ]
    return gate.Result(
        factor=row["factor"],
        definition_hash=row["definition_hash"],
        verdict=verdict,
        checks=checks,
        metrics=dict(evaluation.get("metrics") or {}),
        labels=list(evaluation.get("labels") or []),
    )


def _assert_promote_confirmation(result: gate.Result) -> None:
    if result.verdict != gate.Verdict.PROMOTE:
        raise ValueError(f"Gold 게시 대상이 PROMOTE가 아닙니다: {result.factor}")
    if any(check.passed is not True for check in result.checks):
        raise ValueError(f"Gold PROMOTE에 미통과 gate가 남아 있습니다: {result.factor}")
    for tier in ("T4.1", "T4.2", "T4.4"):
        matching = [check for check in result.checks if check.tier == tier]
        if len(matching) != 1 or matching[0].passed is not True:
            raise ValueError(
                f"Gold 자동 게시 {tier} exact PASS가 없습니다: {result.factor}"
            )
    metrics = result.metrics
    if (
        not metrics.get("null_count")
        or metrics.get("null_family_error_rate") is None
        or metrics.get("oos_fdr_status") != "PASS"
    ):
        raise ValueError(f"null/OOS family 보정 증거가 불완전합니다: {result.factor}")


def _create_gold_value_temp(conn, table: str) -> None:
    if table not in {"campaign_gold_values", "campaign_gold_verify"}:
        raise ValueError("허용되지 않은 Gold temp table 이름입니다")
    with conn.cursor() as cursor:
        cursor.execute(f"""
            CREATE TEMP TABLE {table} (
                factor TEXT NOT NULL,
                asset_id BIGINT NOT NULL,
                as_of_date DATE NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                rank BIGINT NOT NULL CHECK (rank > 0),
                PRIMARY KEY (factor, asset_id, as_of_date)
            ) ON COMMIT DROP
        """)


def _populate_gold_value_temp(
    conn,
    table: str,
    campaign: dict,
    factors: list[F.Factor],
) -> None:
    if table not in {"campaign_gold_values", "campaign_gold_verify"}:
        raise ValueError("허용되지 않은 Gold temp table 이름입니다")
    prepared = [
        (factor, *_implementation_contract(factor)[1:])
        for factor in factors
    ]
    query_groups: dict[Path, list[tuple]] = {}
    for item in prepared:
        query_groups.setdefault(item[2], []).append(item)
    start = gate.RESEARCH_START
    end = pd.Period(campaign["oos"]["signal_end"], freq="M")
    for sql_path in sorted(query_groups, key=str):
        group = query_groups[sql_path]
        chunk_values = {
            spec.get("query_chunk_months")
            for _factor, spec, _path, _binding in group
        }
        if len(chunk_values) != 1:
            raise ValueError("Gold 게시 공유 SQL의 chunk 계약이 서로 다릅니다")
        windows = _parity_query_windows(start, end, chunk_values.pop())
        planner_values = {
            spec.get("planner_enable_nestloop", True)
            for _factor, spec, _path, _binding in group
        }
        if len(planner_values) != 1:
            raise ValueError("Gold 게시 공유 SQL의 planner 계약이 서로 다릅니다")
        planner_enable_nestloop = planner_values.pop()
        query = sql_path.read_text(encoding="utf-8").strip().removesuffix(";")
        discriminated = any(
            spec.get("result_factor") is not None
            for _factor, spec, _path, _binding in group
        )
        if discriminated:
            targets = sorted(factor.name for factor, *_rest in group)
            wrapped = f"""
                INSERT INTO {table} (factor, asset_id, as_of_date, value, rank)
                SELECT factor, asset_id, as_of_date, value, rank
                FROM (
                    {query}
                ) values_for_campaign
                WHERE factor = ANY(%(publish_factors)s)
            """
        else:
            if len(group) != 1:
                raise ValueError("factor discriminator 없는 SQL은 단일 팩터여야 합니다")
            targets = [group[0][0].name]
            wrapped = f"""
                INSERT INTO {table} (factor, asset_id, as_of_date, value, rank)
                SELECT %(publish_factor)s, asset_id, as_of_date, value, rank
                FROM (
                    {query}
                ) values_for_campaign
            """
        for window_start, window_end in windows:
            params = {
                "start_month": f"{window_start}-01",
                "end_month": f"{window_end}-01",
                "publish_factors": targets,
                "publish_factor": targets[0],
            }
            started = time.perf_counter()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL enable_nestloop = "
                    + ("on" if planner_enable_nestloop else "off")
                )
                cursor.execute(wrapped, params)
            _log_timing(
                "gold.sql_materialize",
                started,
                sql=sql_path.name,
                target_table=table,
                query_start_month=str(window_start),
                query_end_month=str(window_end),
            )
    expected = sorted(factor.name for factor in factors)
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT DISTINCT factor FROM {table} ORDER BY factor")
        observed = [str(row[0]) for row in cursor.fetchall()]
        cursor.execute(f"""
            SELECT count(*)
            FROM {table}
            WHERE value::text IN ('NaN', 'Infinity', '-Infinity')
               OR rank <= 0
               OR as_of_date < %s::date
               OR as_of_date >= (%s::date + INTERVAL '1 month')
        """, (f"{start}-01", f"{end}-01"))
        invalid_count = int(cursor.fetchone()[0])
        cursor.execute(f"""
            SELECT factor,
                   count(DISTINCT date_trunc('month', as_of_date))::integer,
                   min(date_trunc('month', as_of_date))::date,
                   max(date_trunc('month', as_of_date))::date
            FROM {table}
            GROUP BY factor
            ORDER BY factor
        """)
        coverage = cursor.fetchall()
    expected_months = len(pd.period_range(start, end, freq="M"))
    coverage_valid = all(
        int(months) == expected_months
        and pd.Period(min_month, freq="M") == start
        and pd.Period(max_month, freq="M") == end
        for _factor, months, min_month, max_month in coverage
    ) and len(coverage) == len(expected)
    if observed != expected or invalid_count or not coverage_valid:
        raise ValueError(
            "Gold SQL materialization exact set/scope가 다릅니다: "
            f"expected={expected}, observed={observed}, invalid={invalid_count}, "
            f"coverage={coverage}"
        )


def _gold_value_difference_count(conn) -> tuple[int, int]:
    """Compare persisted Gold only with transaction-local SQL staging."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT count(*) FROM (
                (SELECT ids.factor_key AS factor, values.asset_id,
                        values.as_of_date, values.value, values.rank::bigint AS rank
                 FROM gold.factor_value values
                 JOIN campaign_gold_factor_ids ids USING (factor_id)
                 EXCEPT ALL
                 SELECT factor, asset_id, as_of_date, value, rank
                 FROM campaign_gold_values)
                UNION ALL
                (SELECT factor, asset_id, as_of_date, value, rank
                 FROM campaign_gold_values
                 EXCEPT ALL
                 SELECT ids.factor_key AS factor, values.asset_id,
                        values.as_of_date, values.value, values.rank::bigint AS rank
                 FROM gold.factor_value values
                 JOIN campaign_gold_factor_ids ids USING (factor_id))
            ) differences
        """)
        persisted_difference = int(cursor.fetchone()[0])
    return 0, persisted_difference


def _campaign_batch_orthogonality(
    campaign: dict,
    panel: P.Panel,
    factors: list[F.Factor],
) -> dict:
    """Recompute the discovery-scope mutual Gold correlation gate."""
    ordered = sorted(factors, key=lambda factor: factor.name)
    if len(ordered) < 2:
        names = [factor.name for factor in ordered]
        return {
            "schema_version": "gold-batch-orthogonality-v1",
            "policy": "lexical_first_independent_of_research_outcomes_v1",
            "threshold": gate.TH["max_gold_corr"],
            "minimum_comparison_months": gate.TH["min_gold_corr_months"],
            "candidate_factors": names,
            "pairs": [],
            "survivors": names,
            "suppressed": [],
        }
    discovery = _scope_discovery_panel(
        panel,
        data_cutoff=campaign["discovery"]["data_cutoff"],
        oos_start=campaign["oos"]["start"],
    )
    research_panel = _research_input_panel(discovery)
    frame = _ensure_factor_columns(research_panel, ordered)
    signal_end = pd.Period(campaign["discovery"]["signal_end"], freq="M")
    eligible = (
        research_panel.universe
        & research_panel.investable
        & frame["ym"].ge(gate.RESEARCH_START)
        & frame["ym"].le(signal_end)
    )
    signals = {
        factor.name: frame[f"f_{factor.name}"]
        for factor in ordered
    }
    return gate.batch_signal_orthogonality(
        frame, signals, eligible=eligible,
    )


def publish_revealed_campaign(
    campaign_id: str,
    panel: P.Panel,
) -> dict:
    """Atomically publish deterministic batch-orthogonal PROMOTE survivors."""
    load_registry()
    campaign = epochs.load_campaign("research", campaign_id)
    confirmation_panel = _scope_confirmation_panel(
        panel,
        data_cutoff=campaign["discovery"]["data_cutoff"],
        oos_start=campaign["oos"]["start"],
        oos_end=campaign["oos"]["signal_end"],
    )
    confirmations = epochs.load_confirmation("research", campaign_id)
    qualified = campaign.get("qualified_factors") or []
    qualified_names = sorted(row["name"] for row in qualified)
    factors = [F.REGISTRY[name] for name in qualified_names]
    current_bindings = _implementation_bindings(factors)
    verification = epochs.load_implementation_verification(
        "research", campaign_id, current_bindings=current_bindings,
        finalized_publication=True,
    )
    parity_rows = verification.get("implementations") or []
    if (
        sorted(row.get("factor") for row in parity_rows) != qualified_names
        or any(row.get("passed") is not True or row.get("status") != "PASS" for row in parity_rows)
    ):
        raise ValueError("qualified 전체의 Python/Gold SQL parity가 PASS가 아닙니다")
    confirmation_by_name = {
        row["factor"]: row for row in confirmations["confirmations"]
    }
    if sorted(confirmation_by_name) != qualified_names:
        raise ValueError("qualified/confirmation exact set이 다릅니다")
    results = {
        name: _confirmation_gate_result(confirmation_by_name[name])
        for name in qualified_names
    }
    promote_names = sorted(
        name for name, result in results.items()
        if result.verdict == gate.Verdict.PROMOTE
    )
    if set(promote_names) != {
        row["factor"] for row in confirmations["confirmations"]
        if row.get("verdict") == gate.Verdict.PROMOTE.value
    }:
        raise ValueError("PROMOTE/publish exact set을 재현하지 못했습니다")
    if not promote_names:
        return {
            "schema_version": "gold-auto-publication-v2",
            "campaign_id": campaign_id,
            "status": "NO_PROMOTE_NO_WRITE",
            "qualified_factors": qualified_names,
            "promote_factors": [],
            "published_factors": [],
            "database_mutated": False,
        }
    for name in promote_names:
        _assert_promote_confirmation(results[name])
    promote_factors = [F.REGISTRY[name] for name in promote_names]
    batch_orthogonality = _campaign_batch_orthogonality(
        campaign, confirmation_panel, promote_factors,
    )
    publish_names = list(batch_orthogonality["survivors"])
    publish_factors = [F.REGISTRY[name] for name in publish_names]
    binding_by_name = {row["factor"]: row for row in current_bindings}
    metadata_rows = []
    for factor in publish_factors:
        binding = binding_by_name[factor.name]
        implementation_ref = publish.ImplementationRef(
            uri=binding["implementation_uri"],
            sha256=binding["implementation_sha256"],
            research_definition_hash=binding["definition_hash"],
        )
        result = results[factor.name]
        metadata_rows.append(publish.build_row(
            factor,
            result,
            implementation=implementation_ref,
            n_trials=int(campaign["discovery_family_size"]),
            null_family_error_rate=result.metrics.get("null_family_error_rate"),
            data_cutoff=campaign["discovery"]["data_cutoff"],
            approved_by="automatic_exact_campaign_gate_v2",
            campaign_id=campaign_id,
            strategy_sha256=binding["strategy_sha256"],
            manifest_entry_digest=binding["manifest_entry_digest"],
        ))
    conn = silver.connect(read_only=False)
    try:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"factor-research:{campaign_id}",),
            )
        silver.verify_live_total_return_contract(
            conn,
            confirmation_panel.meta.get("return_contract_validation_evidence"),
        )
        _verify_confirmation_live_identity(conn, confirmation_panel)
        research_panel = _research_input_panel(confirmation_panel)
        approved_before = _approved_signals(conn, research_panel.monthly)
        gold_family_digest = _signal_family_digest(approved_before)
        expected_gold_digests = {
            result.metrics.get("null_gold_family_digest")
            for result in results.values()
        }
        if expected_gold_digests != {gold_family_digest}:
            raise ValueError(
                "null calibration 뒤 live Gold family가 변경됐습니다: "
                f"expected={expected_gold_digests}, observed={gold_family_digest}"
            )
        _create_gold_value_temp(conn, "campaign_gold_values")
        _populate_gold_value_temp(
            conn, "campaign_gold_values", campaign, publish_factors,
        )
        published = publish.upsert_approved_metadata_atomic(conn, metadata_rows)
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TEMP TABLE campaign_gold_factor_ids (
                    factor_id BIGINT PRIMARY KEY,
                    factor_key TEXT UNIQUE NOT NULL
                ) ON COMMIT DROP
            """)
            cursor.executemany(
                "INSERT INTO campaign_gold_factor_ids VALUES (%s, %s)",
                [(row["factor_id"], row["factor_key"]) for row in published],
            )
            cursor.execute("""
                DELETE FROM gold.factor_value values
                USING campaign_gold_factor_ids ids
                WHERE values.factor_id = ids.factor_id
            """)
            cursor.execute("""
                INSERT INTO gold.factor_value (
                    factor_id, asset_id, as_of_date, value, rank
                )
                SELECT ids.factor_id, source.asset_id, source.as_of_date,
                       source.value, source.rank::integer
                FROM campaign_gold_values source
                JOIN campaign_gold_factor_ids ids
                  ON ids.factor_key = source.factor
                ORDER BY source.factor, source.as_of_date, source.asset_id
            """)
        source_difference, persisted_difference = _gold_value_difference_count(conn)
        if source_difference or persisted_difference:
            raise ValueError(
                "Gold SQL staging/persisted exact parity 실패: "
                f"source={source_difference}, persisted={persisted_difference}"
            )
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ids.factor_key, f.status, count(values.factor_id)::bigint AS row_count,
                       min(values.as_of_date) AS min_date,
                       max(values.as_of_date) AS max_date,
                       count(values.factor_id)
                         - count(DISTINCT (values.asset_id, values.as_of_date))
                           AS duplicate_count
                FROM campaign_gold_factor_ids ids
                JOIN gold.factor f ON f.factor_id = ids.factor_id
                LEFT JOIN gold.factor_value values ON values.factor_id = ids.factor_id
                GROUP BY ids.factor_key, f.status
                ORDER BY ids.factor_key
            """)
            post_rows = [
                dict(zip([column.name for column in cursor.description], row, strict=True))
                for row in cursor.fetchall()
            ]
        if (
            [row["factor_key"] for row in post_rows] != publish_names
            or any(
                row["status"] != "APPROVED"
                or int(row["row_count"]) <= 0
                or int(row["duplicate_count"]) != 0
                for row in post_rows
            )
        ):
            raise ValueError("Gold APPROVED/row/date/duplicate 사후 검증에 실패했습니다")
        evidence = {
            "schema_version": "gold-auto-publication-v2",
            "campaign_id": campaign_id,
            "status": "APPROVED_ATOMIC",
            "qualified_factors": qualified_names,
            "promote_factors": promote_names,
            "published_factors": publish_names,
            "batch_orthogonality": batch_orthogonality,
            "database_mutated": True,
            "gold_staging_contract": (
                "single_repeatable_read_temp_sql_materialization_v1"
            ),
            "source_sql_materialization_count": 1,
            "implementation_verification_digest": campaign[
                "implementation_verification_digest"
            ],
            "confirmation_result_digest": campaign[
                "confirmation_result_digest"
            ],
            "gold_family_digest_before": gold_family_digest,
            "source_recompute_difference_count": source_difference,
            "persisted_recompute_difference_count": persisted_difference,
            "factors": [
                {
                    **published_row,
                    **{
                        "row_count": int(post_row["row_count"]),
                        "min_date": str(post_row["min_date"]),
                        "max_date": str(post_row["max_date"]),
                        "duplicate_count": int(post_row["duplicate_count"]),
                    },
                }
                for published_row, post_row in zip(published, post_rows, strict=True)
            ],
        }
        conn.commit()
        return evidence
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reconcile_gold_batch_orthogonality(
    campaign_id: str,
    panel: P.Panel,
) -> dict:
    """Atomically retire previously published factors suppressed by batch T5."""
    load_registry()
    campaign = epochs.load_campaign("research", campaign_id)
    confirmation_panel = _scope_confirmation_panel(
        panel,
        data_cutoff=campaign["discovery"]["data_cutoff"],
        oos_start=campaign["oos"]["start"],
        oos_end=campaign["oos"]["signal_end"],
    )
    confirmation = epochs.load_confirmation("research", campaign_id)
    promote_names = sorted(
        row["factor"] for row in confirmation["confirmations"]
        if row.get("verdict") == gate.Verdict.PROMOTE.value
    )
    promote_factors = [F.REGISTRY[name] for name in promote_names]
    batch = _campaign_batch_orthogonality(
        campaign, confirmation_panel, promote_factors,
    )
    survivors = list(batch["survivors"])
    retired = sorted(row["factor"] for row in batch["suppressed"])
    if not retired:
        raise ValueError("현재 campaign Gold 배치에는 0.70 초과 충돌이 없습니다")
    publication_path = campaign.get("gold_publication")
    if not publication_path:
        raise ValueError("기존 Gold publication evidence가 없습니다")
    publication = json.loads(Path(publication_path).read_text(encoding="utf-8"))
    if publication.get("published_factors") != promote_names:
        raise ValueError(
            "기존 Gold publication이 원래 PROMOTE exact set과 다릅니다"
        )

    conn = silver.connect(read_only=False)
    try:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"factor-research:{campaign_id}:batch-orthogonality",),
            )
        silver.verify_live_total_return_contract(
            conn,
            confirmation_panel.meta.get("return_contract_validation_evidence"),
        )
        _verify_confirmation_live_identity(conn, confirmation_panel)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT f.factor_id, f.factor_key,
                       f.evaluation->>'campaign_id' AS campaign_id,
                       count(v.factor_id)::bigint AS row_count
                FROM gold.factor f
                LEFT JOIN gold.factor_value v USING (factor_id)
                WHERE f.status = 'APPROVED'
                  AND f.factor_key = ANY(%s)
                GROUP BY f.factor_id, f.factor_key, f.evaluation
                ORDER BY f.factor_key
            """, (promote_names,))
            columns = [column.name for column in cursor.description]
            before = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        if (
            [row["factor_key"] for row in before] != promote_names
            or any(row["campaign_id"] != campaign_id for row in before)
            or any(int(row["row_count"]) <= 0 for row in before)
        ):
            raise ValueError(
                "Gold reconciliation 전 APPROVED/campaign/value exact set이 다릅니다"
            )
        factor_ids = {
            row["factor_key"]: int(row["factor_id"])
            for row in before
        }
        deleted_rows: dict[str, int] = {}
        retirement_payloads = {
            row["factor"]: {
                "policy": batch["policy"],
                "threshold": batch["threshold"],
                "kept_factor": row["kept_factor"],
                "campaign_id": campaign_id,
            }
            for row in batch["suppressed"]
        }
        with conn.cursor() as cursor:
            for name in retired:
                cursor.execute(
                    "DELETE FROM gold.factor_value WHERE factor_id = %s",
                    (factor_ids[name],),
                )
                deleted_rows[name] = int(cursor.rowcount)
                cursor.execute("""
                    UPDATE gold.factor
                    SET status = 'RETIRED',
                        evaluation = evaluation || jsonb_build_object(
                            'batch_orthogonality_retirement', %s::jsonb
                        )
                    WHERE factor_id = %s AND status = 'APPROVED'
                """, (
                    json.dumps(retirement_payloads[name], sort_keys=True),
                    factor_ids[name],
                ))
                if cursor.rowcount != 1:
                    raise ValueError(f"Gold factor RETIRED 전환 실패: {name}")
            cursor.execute("""
                SELECT f.factor_key, count(v.factor_id)::bigint AS row_count
                FROM gold.factor f
                LEFT JOIN gold.factor_value v USING (factor_id)
                WHERE f.status = 'APPROVED'
                  AND f.factor_key = ANY(%s)
                GROUP BY f.factor_key
                ORDER BY f.factor_key
            """, (promote_names,))
            after = [(str(name), int(count)) for name, count in cursor.fetchall()]
            cursor.execute("""
                SELECT count(*)::bigint
                FROM gold.factor_value
                WHERE factor_id = ANY(%s)
            """, ([factor_ids[name] for name in retired],))
            retired_value_count = int(cursor.fetchone()[0])
        if (
            [name for name, _count in after] != survivors
            or any(count <= 0 for _name, count in after)
            or retired_value_count != 0
            or any(deleted_rows[name] <= 0 for name in retired)
        ):
            raise ValueError("Gold batch reconciliation 사후 exact set 검증 실패")
        evidence = {
            "schema_version": "gold-batch-reconciliation-v1",
            "campaign_id": campaign_id,
            "status": "BATCH_ORTHOGONALITY_RECONCILED",
            "reconciled_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "database_mutated": True,
            "batch_orthogonality": batch,
            "approved_factors_before": promote_names,
            "approved_factors_after": survivors,
            "retired_factors": retired,
            "deleted_value_rows": deleted_rows,
            "retired_value_rows_after": retired_value_count,
            "survivor_row_counts": {
                name: count for name, count in after
            },
            "original_gold_publication_digest": campaign.get(
                "gold_publication_digest"
            ),
        }
        conn.commit()
        return evidence
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _merge_discovery_and_oos(
    discovery: gate.Result,
    confirmation: gate.Result,
) -> gate.Result:
    """Combine frozen-boundary development evidence with new OOS T4 only."""
    discovery.labels = [
        label for label in discovery.labels
        if label not in {"oos_sealed", "fdr_pending", "discovery_pass"}
    ]
    discovery.metrics["evaluation_phase"] = "full"
    discovery.metrics.update({
        key: value
        for key, value in confirmation.metrics.items()
        if key.startswith("oos_")
    })
    oos_check = next(
        (check for check in confirmation.checks if check.tier == "T4.1"),
        None,
    )
    if oos_check is None:
        failures = ", ".join(check.name for check in confirmation.failed) or "OOS 계산 불가"
        oos_check = gate.Check(
            "T4.1", "고정 OOS IC", False, None,
            gate.oos_effect_threshold_label(),
            failures,
        )
    discovery.checks.append(oos_check)
    if "oos_ic" in confirmation.series:
        discovery.series["oos_ic"] = confirmation.series["oos_ic"]
    return discovery


def _assert_confirmation_discovery_ics(results: list[gate.Result]) -> None:
    """Fail the whole batch before any sealed OOS value can be computed."""
    invalid = [
        result.factor
        for result in results
        if result.metrics.get("ic_investable") is None
        or not np.isfinite(result.metrics["ic_investable"])
        or result.metrics["ic_investable"] <= 0
    ]
    if invalid:
        raise ValueError(
            "인증된 Discovery 투자 가능 IC가 없거나 비양수입니다. "
            "부분 OOS 공개를 막기 위해 전체 confirmation을 중단합니다: "
            f"{invalid}"
        )


def _evaluate(
    args,
    *,
    phase: str = "discovery",
    oos_start: pd.Period | str | None = None,
    oos_end: pd.Period | str | None = None,
    data_cutoff: str | None = None,
    factor_names: list[str] | None = None,
    record_ledger: bool = True,
    defer_multiple_testing: bool = False,
    calibration_scope: dict | None = None,
    frozen_discovery: dict[str, dict] | None = None,
    discovery_snapshot_digest: str | None = None,
    discovery_asset_identity_digest: str | None = None,
    snapshot_asset_identity_digest: str | None = None,
    closure_asset_identity_digest: str | None = None,
    confirmation_mode: str | None = None,
    preloaded_panel: P.Panel | None = None,
    input_generation: dict | None = None,
):
    total_started = time.perf_counter()
    if phase == "discovery" and (
        data_cutoff is None
        or oos_start is None
        or discovery_snapshot_digest is None
        or discovery_asset_identity_digest is None
    ):
        raise ValueError(
            "epoch-1.8 discovery는 campaign의 동결 cutoff·OOS 시작월·discovery "
            "snapshot digest와 asset identity digest가 필수입니다. "
            "scripts/research.py campaign workflow를 "
            "사용하세요."
        )
    load_registry()
    started = time.perf_counter()
    base_pan = preloaded_panel if preloaded_panel is not None else _load()
    _log_timing("evaluation.panel_load", started, phase=phase)
    frozen_oos = pd.Period(oos_start, freq="M") if oos_start is not None else None
    frozen_oos_end = pd.Period(oos_end, freq="M") if oos_end is not None else None
    development_pan = None
    if phase == "discovery" and (data_cutoff is not None or oos_start is not None):
        if data_cutoff is None or oos_start is None:
            raise ValueError("campaign discovery에는 data_cutoff와 oos_start가 모두 필요합니다")
        pan = _scope_discovery_panel(
            base_pan, data_cutoff=data_cutoff, oos_start=oos_start,
        )
        if P.snapshot_digest(pan) != discovery_snapshot_digest:
            raise ValueError(
                "campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다"
            )
        if (
            P.verify_asset_identity(pan)["asset_identity_digest"]
            != discovery_asset_identity_digest
        ):
            raise ValueError(
                "campaign 생성 당시 discovery asset identity를 재현하지 못했습니다"
            )
    elif phase == "full" and oos_end is not None:
        if data_cutoff is None or frozen_oos is None:
            raise ValueError("봉인 confirmation에는 discovery cutoff와 OOS start가 필요합니다")
        pan = _scope_confirmation_panel(
            base_pan,
            data_cutoff=data_cutoff,
            oos_start=frozen_oos,
            oos_end=oos_end,
        )
        if frozen_discovery is not None:
            if data_cutoff is None or frozen_oos is None:
                raise ValueError("봉인 confirmation에는 discovery cutoff와 OOS start가 필요합니다")
            development_pan = _scope_discovery_panel(
                base_pan, data_cutoff=data_cutoff, oos_start=frozen_oos,
            )
            if (
                discovery_snapshot_digest is None
                or P.snapshot_digest(development_pan) != discovery_snapshot_digest
            ):
                raise ValueError(
                    "campaign 생성 당시 discovery Silver snapshot을 재현하지 못했습니다"
                )
            if (
                discovery_asset_identity_digest is None
                or P.verify_asset_identity(development_pan)["asset_identity_digest"]
                != discovery_asset_identity_digest
            ):
                raise ValueError(
                    "campaign 생성 당시 discovery asset identity를 재현하지 못했습니다"
                )
        if confirmation_mode is None:
            raise ValueError("봉인 confirmation에는 campaign mode가 필요합니다")
        _assert_confirmation_asset_identity(
            pan,
            mode=confirmation_mode,
            historical_snapshot_identity_digest=snapshot_asset_identity_digest,
        )
        if (
            closure_asset_identity_digest is not None
            and _closure_asset_identity(pan)["asset_identity_digest"]
            != closure_asset_identity_digest
        ):
            raise ValueError(
                "campaign 생성 당시 closure asset identity를 재현하지 못했습니다"
            )
    else:
        pan = base_pan
    if factor_names is not None:
        targets = [F.REGISTRY[name] for name in factor_names]
    else:
        targets = [F.REGISTRY[args.factor]] if args.factor else list(F.REGISTRY)
    frozen_artifacts_bound = bool(
        development_pan is not None
        and frozen_discovery is not None
        and all(
            frozen_discovery.get(f.definition_hash, {}).get(
                "discovery_result_artifact"
            )
            and frozen_discovery.get(f.definition_hash, {}).get(
                "discovery_result_artifact_sha256"
            )
            for f in targets
        )
    )
    authenticated_pan = pan
    authenticated_development_pan = development_pan
    authenticated_df = authenticated_pan.monthly
    confirmation_snapshot_digest = (
        P.snapshot_digest(authenticated_pan) if phase == "full" else None
    )
    ledger = trials.TrialLedger(TRIAL_DB)
    started = time.perf_counter()
    with silver.connect(read_only=True) as conn:
        if input_generation is not None:
            silver.verify_live_research_generation(conn, input_generation)
        else:
            silver.verify_live_total_return_contract(
                conn,
                authenticated_pan.meta.get(
                    "return_contract_validation_evidence"
                ),
            )
            if phase == "full" and oos_end is not None:
                _verify_confirmation_live_identity(conn, authenticated_pan)
            else:
                P.verify_live_asset_identity(
                    conn, authenticated_pan,
                    cutoff=str(pd.Timestamp(
                        authenticated_df["trade_date"].max(),
                    ).date()),
                )
        # Only after the complete cache/live identity has matched do we derive
        # the 2015+ frame that factor code and gates are allowed to inspect.
        pan = _research_input_panel(authenticated_pan)
        development_pan = (
            _research_input_panel(authenticated_development_pan)
            if authenticated_development_pan is not None else None
        )
        df = pan.monthly
        development_df = (
            development_pan.monthly if development_pan is not None else None
        )
        approved = _approved_signals(conn, df)
        development_approved = (
            _approved_signals(conn, development_df)
            if development_df is not None and not frozen_artifacts_bound
            else None
        )
        gold_trials = (
            None if frozen_artifacts_bound
            else silver.load_gold_trial_history(conn)
        )
    _log_timing("evaluation.live_inputs", started, phase=phase)
    gold_family_digest = _signal_family_digest(approved)
    cutoff = str(df["trade_date"].max().date())
    calibration = None
    if phase == "full":
        calibration_path = CACHE / "null_dist.parquet"
        calibration = pd.read_parquet(calibration_path) if calibration_path.exists() else None
        scope = calibration_scope or {}
        # This must run before factor columns are computed on the sealed OOS.
        # A missing/stale calibration is operationally recoverable and must not
        # consume the campaign's one-time confirmation reveal.
        gate.assert_null_calibration(
            calibration, data_cutoff=cutoff, oos_start=frozen_oos,
            discovery_family_size=scope.get("discovery_family_size"),
            oos_family_size=scope.get("oos_family_size"),
            discovery_family_digest=scope.get("discovery_family_digest"),
            oos_family_digest=scope.get("oos_family_digest"),
            gold_family_digest=gold_family_digest,
            confirmation_snapshot_digest=confirmation_snapshot_digest,
            research_data_cutoff=scope.get("research_data_cutoff"),
            oos_end=frozen_oos_end,
            qualification_policy=scope.get("qualification_policy"),
        )
    df = _ensure_factor_columns(pan, targets)
    development_df = (
        _reuse_factor_columns(df, development_pan, targets)
        if development_pan is not None else None
    )
    # Gold's legacy trial rows contain return Sharpe/p-values.  They still count
    # as attempted definitions, but must not enter v3's IC multiple testing.
    external = _external_gold_trial_rows(gold_trials)
    summary = ledger.summary(
        [factor.definition_hash for factor in targets], external=external,
        ruleset_version=gate.RULESET_VERSION,
    )
    results: list[gate.Result] = []
    if development_pan is not None and development_df is not None:
        development_context = gate.build_evaluation_context(
            development_pan,
            development_df,
            oos_start=frozen_oos,
            data_cutoff=data_cutoff,
            phase="discovery",
        )
        if frozen_discovery is None:
            raise ValueError("봉인 confirmation에는 discovery artifact가 필요합니다")
        if frozen_artifacts_bound:
            results = [
                research.load_authenticated_discovery_result(
                    frozen_discovery[f.definition_hash], f,
                )
                for f in targets
            ]
        else:
            # Backward-compatible fallback for campaigns created before result
            # artifacts were bound into the campaign-wide BY evidence.
            for f in targets:
                started = time.perf_counter()
                existing = {
                    name: values
                    for name, values in (development_approved or {}).items()
                    if name != f.name
                }
                results.append(gate.evaluate(
                    f, development_pan, development_df, existing=existing,
                    trial_count=summary.count, prior_sharpes=summary.sharpes,
                    oos_start=frozen_oos, data_cutoff=data_cutoff,
                    phase="discovery", context=development_context,
                    include_diagnostics=False,
                ))
                _log_timing(
                    "evaluation.gate", started,
                    factor=f.name, phase="discovery",
                )
        for result in results:
            frozen = frozen_discovery.get(result.definition_hash)
            if frozen is None:
                raise ValueError(
                    f"확정 discovery family에 없는 자동 통과 후보입니다: {result.factor}"
                )
            current_p = result.metrics.get("ic_p_investable")
            frozen_p = frozen.get("pvalue")
            if (
                current_p is None or frozen_p is None
                or not pd.notna(current_p)
                or abs(float(current_p) - float(frozen_p)) > 1e-12
            ):
                raise ValueError(
                    f"동결 discovery p값을 재현하지 못했습니다: {result.factor}. "
                    "campaign 생성 당시 Silver snapshot을 복구하세요."
                )
            current_digest = gate.discovery_evidence_digest(
                result,
                ruleset_version=frozen.get("evidence_ruleset_version"),
            )
            if current_digest != frozen.get("discovery_evidence_digest"):
                raise ValueError(
                    f"동결 discovery 증거를 재현하지 못했습니다: {result.factor}. "
                    "campaign 생성 당시 Silver snapshot을 복구하세요."
                )
        gate.apply_multiple_testing(
            results,
            [
                (definition_hash, float(row["by_input_pvalue"]))
                for definition_hash, row in frozen_discovery.items()
            ],
            total_trials=len(frozen_discovery),
        )
        for result in results:
            expected_q = frozen_discovery[result.definition_hash].get("qvalue")
            actual_q = result.metrics.get("fdr_qvalue")
            if expected_q is None or abs(float(actual_q) - float(expected_q)) > 1e-12:
                raise ValueError(f"동결 discovery q값 재현 실패: {result.factor}")

        authenticated_discovery = results
        _assert_confirmation_discovery_ics(authenticated_discovery)
        for factor, discovery_result in zip(
            targets, authenticated_discovery, strict=True,
        ):
            gate.attach_portfolio_diagnostics(
                discovery_result,
                factor,
                development_pan,
                development_df,
                context=development_context,
            )
        results = []
        for f, discovery_result in zip(targets, authenticated_discovery, strict=True):
            started = time.perf_counter()
            confirmation_signal_contract = gate.certify_confirmation_signal(
                f, df, discovery_result,
            )
            confirmation_result = gate.evaluate_oos(
                f, pan, df, oos_start=frozen_oos, oos_end=frozen_oos_end,
                data_cutoff=data_cutoff,
                discovery_ic=discovery_result.metrics.get("ic_investable"),
                confirmation_signal_contract=confirmation_signal_contract,
            )
            results.append(_merge_discovery_and_oos(
                discovery_result, confirmation_result,
            ))
            _log_timing(
                "evaluation.gate", started, factor=f.name, phase="full",
            )
    else:
        evaluation_context = gate.build_evaluation_context(
            pan,
            df,
            oos_start=frozen_oos,
            data_cutoff=data_cutoff,
            phase=phase,
        )
        for f in targets:
            started = time.perf_counter()
            # A new version of an already-approved factor is compared with other
            # Gold families, not with its own currently active version.
            existing = {name: values for name, values in approved.items() if name != f.name}
            results.append(gate.evaluate(
                f, pan, df, existing=existing, trial_count=summary.count,
                prior_sharpes=summary.sharpes, oos_start=frozen_oos,
                oos_end=frozen_oos_end, data_cutoff=data_cutoff, phase=phase,
                context=evaluation_context,
                include_diagnostics=(phase != "discovery"),
            ))
            _log_timing(
                "evaluation.gate", started, factor=f.name, phase=phase,
            )
        gate.apply_multiple_testing(
            results, summary.pvalues, defer=defer_multiple_testing,
            total_trials=summary.ic_count,
        )
    if phase == "full":
        gate.apply_oos_multiple_testing(results)
        gate.apply_null_calibration(
            results, calibration, data_cutoff=cutoff, oos_start=frozen_oos,
            discovery_family_size=(calibration_scope or {}).get("discovery_family_size"),
            oos_family_size=(calibration_scope or {}).get("oos_family_size"),
            discovery_family_digest=(calibration_scope or {}).get("discovery_family_digest"),
            oos_family_digest=(calibration_scope or {}).get("oos_family_digest"),
            gold_family_digest=gold_family_digest,
            confirmation_snapshot_digest=confirmation_snapshot_digest,
            research_data_cutoff=(calibration_scope or {}).get("research_data_cutoff"),
            oos_end=frozen_oos_end,
            qualification_policy=(calibration_scope or {}).get("qualification_policy"),
        )
    if record_ledger:
        for factor, result in zip(targets, results, strict=True):
            ledger.record(factor, result, data_cutoff=cutoff, ruleset_version=gate.RULESET_VERSION)
    _log_timing(
        "evaluation.total", total_started, phase=phase, factor_count=len(targets),
    )
    return pan, df, targets, results


def cmd_gate(args):
    del args
    raise SystemExit(
        "전체 패널 gate는 봉인 OOS를 노출하므로 epoch-1.8에서 비활성화했습니다. "
        "scripts/research.py의 campaign-start → epoch-start → evaluate를 사용하세요."
    )


def cmd_null(args):
    total_started = time.perf_counter()
    load_registry()
    pan = _load()
    print(f"합성 귀무 campaign 측정 (종류당 {args.n}개 family)...")
    campaign = epochs.load_campaign("research", args.campaign)
    if campaign.get("protocol_version") != epochs.PROTOCOL_VERSION:
        raise SystemExit("현재 protocol로 만든 campaign만 귀무 보정할 수 있습니다")
    if campaign.get("ruleset_version") != gate.RULESET_VERSION:
        raise SystemExit("현재 ruleset으로 만든 campaign만 귀무 보정할 수 있습니다")
    if campaign.get("status") != "READY_FOR_CONFIRMATION":
        raise SystemExit("자동 기준 통과가 확정된 campaign만 귀무 보정할 수 있습니다")
    factors = [F.REGISTRY[row["name"]] for row in campaign["qualified_factors"]]
    bindings = _implementation_bindings(factors)
    snapshot = _scope_snapshot_panel(
        pan, snapshot_cutoff=campaign["snapshot"]["data_cutoff"],
    )
    snapshot_identity = P.verify_asset_identity(snapshot)["asset_identity_digest"]
    if snapshot_identity != campaign["snapshot"].get("asset_identity_digest"):
        raise SystemExit("campaign 생성 당시 snapshot asset identity를 재현하지 못했습니다")
    epochs.assert_reveal_ready(
        "research", args.campaign, pan.monthly["trade_date"].max(),
        snapshot_digest=P.snapshot_digest(snapshot),
        current_bindings=bindings,
    )
    pan = _scope_confirmation_panel(
        pan,
        data_cutoff=campaign["discovery"]["data_cutoff"],
        oos_start=campaign["oos"]["start"],
        oos_end=campaign["oos"]["signal_end"],
    )
    expected_closure_identity = campaign["snapshot"].get(
        "closure_asset_identity_digest"
    )
    if (
        campaign["oos"].get("mode") == "trailing_historical_holdout"
        and _closure_asset_identity(pan)["asset_identity_digest"]
        != expected_closure_identity
    ):
        raise SystemExit("campaign 생성 당시 closure asset identity를 재현하지 못했습니다")
    ledger = trials.TrialLedger(TRIAL_DB)
    confirmation_snapshot_digest = P.snapshot_digest(pan)
    with silver.connect(read_only=True) as conn:
        if campaign.get("input_generation") is not None:
            silver.verify_live_research_generation(
                conn, campaign["input_generation"],
            )
        else:
            silver.verify_live_total_return_contract(
                conn, pan.meta.get("return_contract_validation_evidence"),
            )
            _verify_confirmation_live_identity(conn, pan)
        gold_trials = silver.load_gold_trial_history(conn)
        pan = _research_input_panel(pan)
        approved = _approved_signals(conn, pan.monthly)
    summary = ledger.summary(external=[
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ], ruleset_version=gate.RULESET_VERSION)
    oos_start = pd.Period(campaign["oos"]["start"], freq="M")
    out = null.measure(
        pan, n=args.n, trial_count=summary.count,
        prior_sharpes=summary.sharpes, oos_start=oos_start,
        oos_end=pd.Period(campaign["oos"]["signal_end"], freq="M"),
        research_data_cutoff=campaign["discovery"]["data_cutoff"],
        discovery_family_size=int(campaign["discovery_family_size"]),
        oos_family_size=len(campaign["qualified_factors"]),
        discovery_family_digest=campaign["discovery_family_digest"],
        oos_family_digest=campaign["oos_family_digest"],
        gold_family_digest=_signal_family_digest(approved),
        confirmation_snapshot_digest=confirmation_snapshot_digest,
        qualification_policy=campaign["qualification_policy"],
        existing=approved,
        # The null calculation is campaign-independent when every frozen
        # computational input matches. ``measure`` derives a content-addressed
        # JSONL filename and rebinds only the campaign family evidence digests.
        checkpoint_path=CACHE / "null-checkpoints" / "by-calculation",
        timing_callback=_log_timing,
        input_generation_digest=(
            (campaign.get("input_generation") or {}).get("generation_digest")
        ),
    )
    out.to_parquet(CACHE / "null_dist.parquet", index=False)
    _log_timing("null.total", total_started, family_count=len(out))


def cmd_publish(args):
    """Never recompute or write Gold outside the authenticated campaign flow."""
    del args
    raise SystemExit(
        "범용 publish는 비활성화했습니다. REVEALED campaign의 exact PROMOTE 집합은 "
        "scripts/research.py campaign-publish --campaign <id> 경로에서만 자동 적재됩니다."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    g = sub.add_parser("gate"); g.add_argument("--factor")
    n = sub.add_parser("null"); n.add_argument("--n", type=int, default=25)
    n.add_argument("--campaign", required=True, help="동결된 campaign manifest에 귀무 보정을 결박")
    p = sub.add_parser("publish")
    p.add_argument("--factor"); p.add_argument("--apply", action="store_true")
    p.add_argument("--approved-by", help="PROMOTE를 최종 확인한 사람")
    p.add_argument("--only-approved", action="store_true",
                   help="PROMOTE 만 적재 (기본은 판정 전체를 기록)")
    a = ap.parse_args()
    {"build": cmd_build, "gate": cmd_gate, "null": cmd_null,
     "publish": cmd_publish}[a.cmd](a)


if __name__ == "__main__":
    main()
