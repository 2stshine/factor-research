"""Append-safe local research trial ledger.

Repeated execution of an identical definition is not a new trial.  Any change
to source, parameters, sign, inputs, or rebalance policy changes the definition
hash and therefore increases the multiplicity count.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class TrialSummary:
    count: int
    ic_count: int
    sharpes: tuple[float, ...]
    pvalues: tuple[tuple[str, float], ...]


def _summarize_rows(
    rows: list[tuple],
    current_hashes: list[str] | tuple[str, ...],
    external: (
        list[tuple[str, float | None, float | None]]
        | tuple[tuple[str, float | None, float | None], ...]
    ),
    ruleset_version: str | None,
) -> TrialSummary:
    merged = {
        str(row[0]): (
            row[1],
            row[2] if ruleset_version is None or row[3] == ruleset_version else None,
        )
        for row in rows
    }
    for definition_hash, net_ir, hac_pvalue in external:
        # Gold history contributes previously attempted hashes, but must not
        # erase a richer immutable local observation of the same definition.
        merged.setdefault(str(definition_hash), (net_ir, hac_pvalue))
    count = len(set(merged) | set(current_hashes))
    ic_definitions = set(current_hashes)
    ic_definitions.update(
        str(row[0])
        for row in rows
        if ruleset_version is None or row[3] == ruleset_version
    )
    ic_definitions.update(
        str(definition_hash)
        for definition_hash, _net_ir, hac_pvalue in external
        if hac_pvalue is not None
    )
    sharpes = tuple(
        float(values[0]) for values in merged.values() if values[0] is not None
    )
    pvalues = tuple(
        (definition_hash, float(values[1]))
        for definition_hash, values in merged.items()
        if values[1] is not None
    )
    return TrialSummary(max(count, 1), len(ic_definitions), sharpes, pvalues)


def read_trial_summary(
    path: str | Path,
    current_hashes: list[str] | tuple[str, ...] = (),
    external: (
        list[tuple[str, float | None, float | None]]
        | tuple[tuple[str, float | None, float | None], ...]
    ) = (),
    ruleset_version: str | None = None,
) -> TrialSummary:
    """Read an existing trial ledger without creating or mutating it.

    This is intentionally separate from :class:`TrialLedger`: constructing a
    ledger is the write-capable path that creates its parent and schema. Audit
    and retrospective code can use this helper without accidentally creating a
    new empty ledger that looks like valid research history.
    """
    resolved = Path(path).expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise FileNotFoundError(f"시행 원장이 파일이 아닙니다: {resolved}")
    uri = f"{resolved.as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=30) as conn:
        rows = conn.execute(
            "SELECT definition_hash, net_ir, hac_pvalue, ruleset_version FROM trial"
        ).fetchall()
    return _summarize_rows(rows, current_hashes, external, ruleset_version)


class TrialLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trial (
                    definition_hash TEXT PRIMARY KEY,
                    factor_name TEXT NOT NULL,
                    family TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    data_cutoff TEXT,
                    ruleset_version TEXT NOT NULL,
                    net_ir REAL,
                    hac_pvalue REAL,
                    verdict TEXT NOT NULL,
                    first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def definition_hashes(self) -> frozenset[str]:
        """Return every definition ever evaluated through the local engine."""
        with self._connect() as conn:
            rows = conn.execute("SELECT definition_hash FROM trial").fetchall()
        return frozenset(str(row[0]) for row in rows)

    def summary(
        self,
        current_hashes: list[str] | tuple[str, ...] = (),
        external: list[tuple[str, float | None, float | None]] | tuple[tuple[str, float | None, float | None], ...] = (),
        ruleset_version: str | None = None,
    ) -> TrialSummary:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT definition_hash, net_ir, hac_pvalue, ruleset_version FROM trial"
            ).fetchall()
        return _summarize_rows(rows, current_hashes, external, ruleset_version)

    def fixed_oos_start(
        self,
        months: list[pd.Period],
        *,
        requested: str | None = None,
        default_months: int = 36,
        min_in_sample: int = 60,
        min_oos_months: int = 36,
    ) -> pd.Period:
        """Legacy pre-epoch splitter; epoch-1.5 campaign code must not use it."""
        ordered = sorted(set(months))
        if len(ordered) < min_in_sample + min_oos_months:
            raise ValueError(
                "T4에는 개발/OOS를 합쳐 최소 "
                f"{min_in_sample + min_oos_months}개월이 필요합니다: 현재 {len(ordered)}개월"
            )
        if requested:
            chosen = pd.Period(requested, freq="M")
        else:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT value FROM metadata WHERE key='oos_start'"
                ).fetchone()
                if row:
                    chosen = pd.Period(row[0], freq="M")
                else:
                    index = max(min_in_sample, len(ordered) - default_months)
                    chosen = ordered[index]
                    conn.execute(
                        "INSERT INTO metadata(key,value) VALUES('oos_start',?)",
                        (str(chosen),),
                    )
        if chosen not in ordered:
            raise ValueError(f"OOS_START={chosen}가 패널 기간에 없습니다")
        if ordered.index(chosen) < min_in_sample:
            raise ValueError(f"OOS_START={chosen}: in-sample이 {min_in_sample}개월보다 짧습니다")
        return chosen

    def record(self, factor, result, *, data_cutoff: str, ruleset_version: str) -> None:
        metrics = result.metrics
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trial(
                    definition_hash, factor_name, family, params_json,
                    data_cutoff, ruleset_version, net_ir, hac_pvalue, verdict
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(definition_hash) DO UPDATE SET
                    last_seen=CURRENT_TIMESTAMP
                """,
                (
                    factor.definition_hash,
                    factor.name,
                    factor.family or factor.name,
                    json.dumps(factor.params, ensure_ascii=False, sort_keys=True),
                    data_cutoff,
                    ruleset_version,
                    metrics.get("net_ir"),
                    # Legacy column name retained for SQLite compatibility;
                    # ruleset v3 stores the investable-universe IC p-value.
                    metrics.get("ic_p_investable"),
                    result.verdict.value,
                ),
            )
