from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from engine import phenomenon_references as references
from engine import reference_gold as gold
from engine.reference_library import load_catalog, definition_hash, CATALOG_PATH
from engine.research_generation import canonical, digest, make_generation


def source_values():
    catalog = load_catalog()
    selected = {definition["id"]: definition for definition in catalog[:2]}
    a, b = list(selected)
    rows = []
    # Different source coverage must produce an outer union of all three keys.
    for ref, assets in [(a, [1, 2]), (b, [2, 3])]:
        for asset in assets:
            rows.append({"reference_id": ref, "definition_hash": definition_hash(selected[ref]), "asset_id": asset,
                         "stock_code": {1: "005930", 2: "0037T0", 3: "000660"}[asset],
                         "date": "2025-01-31", "known_at": "2025-01-31T15:30:00+09:00", "value": float(asset)})
    metadata = {"dataset_id": "d" * 64, "generation_id": gold.GENERATION, "role": gold.ROLE,
                "profitability_approved": False, "legacy_gold_used": False, "definitions": selected,
                "source_version": "test-only-source"}
    return pd.DataFrame(rows), metadata


def repository(tmp_path, *, generation_id=gold.GENERATION):
    root = tmp_path / "repo"
    manifest = make_generation(generation_id=generation_id)
    manifest_path = Path("research/generations") / generation_id / (manifest["generation_sha256"] + ".json")
    (root / manifest_path).parent.mkdir(parents=True)
    (root / manifest_path).write_bytes(canonical(manifest) + b"\n")
    pointer = {"schema_version": "active-research-generation-v1", "generation_id": generation_id,
               "generation_sha256": manifest["generation_sha256"], "manifest_path": manifest_path.as_posix(),
               "legacy_gold_policy": "EXCLUDED_NO_FALLBACK"}
    pointer["pointer_sha256"] = digest(pointer)
    (root / "research/active-generation.json").write_bytes(canonical(pointer) + b"\n")
    catalog = root / references.CATALOG_PATH
    catalog.parent.mkdir(parents=True)
    catalog.write_bytes(CATALOG_PATH.read_bytes())
    body = {"schema_version": references.PROGRAM_SCHEMA, "generation_id": generation_id,
            "catalog_sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
            "reference_dataset_id": "d" * 64, "legacy_gold_policy": "EXCLUDED_NO_FALLBACK"}
    program = {**body, "program_sha256": digest(body)}
    (root / references.PROGRAM_PATH).write_bytes(canonical(program) + b"\n")
    return root, program


def fake_loader(monkeypatch, *, change=None):
    calls = []
    frame, metadata = source_values()
    if change:
        frame, metadata = change(frame, deepcopy(metadata))

    def load(conn, *, dataset_id, generation_id):
        calls.append((conn, dataset_id, generation_id))
        return frame, metadata

    monkeypatch.setattr(gold, "load_library", load)
    return calls


def test_exact_active_generation_catalog_and_dataset(monkeypatch, tmp_path):
    root, _ = repository(tmp_path)
    calls = fake_loader(monkeypatch)
    connection = object()
    frame, metadata = references.load_active_references(connection, root)
    assert len(frame) == 4 and metadata["dataset_id"] == "d" * 64
    assert calls == [(connection, "d" * 64, gold.GENERATION)]


def test_old_generation_never_queries_legacy_or_reference_gold(monkeypatch, tmp_path):
    root, _ = repository(tmp_path, generation_id="reference-factor-v3")
    calls = fake_loader(monkeypatch)
    with pytest.raises(ValueError, match="legacy fallback forbidden"):
        references.load_active_references(None, root)
    assert calls == []


@pytest.mark.parametrize("change", ["missing", "extra", "hash", "policy", "dataset", "catalog"])
def test_program_failures_precede_database_access(monkeypatch, tmp_path, change):
    root, program = repository(tmp_path)
    path = root / references.PROGRAM_PATH
    if change == "missing":
        path.unlink()
    elif change == "catalog":
        with (root / references.CATALOG_PATH).open("ab") as stream:
            stream.write(b"\n")
    else:
        if change == "extra":
            program["fallback"] = "latest"
        elif change == "hash":
            program["program_sha256"] = "e" * 64
        elif change == "policy":
            program["legacy_gold_policy"] = "ALLOW"
        else:
            program["reference_dataset_id"] = "latest"
        path.write_text(json.dumps(program))
    calls = fake_loader(monkeypatch)
    with pytest.raises(ValueError):
        references.load_active_references(None, root)
    assert calls == []


def test_symlinked_program_rejected(monkeypatch, tmp_path):
    root, _ = repository(tmp_path)
    path = root / references.PROGRAM_PATH
    alternate = tmp_path / "copy.json"
    alternate.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(alternate)
    calls = fake_loader(monkeypatch)
    with pytest.raises(ValueError, match="symlinked"):
        references.load_active_references(None, root)
    assert not calls


def test_published_definition_must_match_current_catalog(monkeypatch, tmp_path):
    root, _ = repository(tmp_path)

    def changed(frame, metadata):
        ref = next(iter(metadata["definitions"]))
        definition = metadata["definitions"][ref]
        definition["formula"] = "different formula"
        definition["definition_hash"] = definition_hash(definition)
        return frame, metadata

    fake_loader(monkeypatch, change=changed)
    with pytest.raises(ValueError, match="differs from active catalog"):
        references.load_active_references(None, root)


def test_wrong_loaded_dataset_rejected(monkeypatch, tmp_path):
    root, _ = repository(tmp_path)
    fake_loader(monkeypatch, change=lambda frame, metadata: (frame, {**metadata, "dataset_id": "f" * 64}))
    with pytest.raises(ValueError, match="different dataset"):
        references.load_active_references(None, root)


def test_outer_union_missing_measurements_and_known_at_are_explicit():
    frame, metadata = source_values()
    ids = list(metadata["definitions"])
    result = references.reference_fields(frame, metadata, ids)
    assert result.asset_id.tolist() == [1, 2, 3]
    assert result.stock_code.tolist() == ["005930", "0037T0", "000660"]
    assert result[ids[0]].tolist()[:2] == [1.0, 2.0]
    assert result[ids[1]].tolist()[1:] == [2.0, 3.0]
    assert pd.isna(result.loc[0, ids[1]]) and pd.isna(result.loc[2, ids[0]])
    assert pd.isna(result.loc[0, ids[1] + "__known_at"])
    assert result.attrs["missing_counts"] == {ref: 1 for ref in ids}
    assert not result.attrs["imputed"] and not result.attrs["alpha_approved"]
    assert "eligible" not in result and "return" not in result and "market_cap" not in result


def test_raw_sign_not_applied_again_and_known_at_is_per_reference():
    frame, metadata = source_values()
    first, second = list(metadata["definitions"])
    frame.loc[frame.reference_id.eq(first), "known_at"] = "2025-01-29T16:00:00+09:00"
    result = references.reference_fields(frame, metadata, [first, second])
    assert result.loc[1, first] == 2.0  # size orientation=-1 is NOT reapplied.
    assert result.loc[1, first + "__known_at"] != result.loc[1, second + "__known_at"]


@pytest.mark.parametrize("bad", [[], ["legacy_factor"], ["kr_size_issue_v1", "kr_size_issue_v1"]])
def test_explicit_unique_dataset_subset_required(bad):
    frame, metadata = source_values()
    with pytest.raises(ValueError):
        references.reference_fields(frame, metadata, bad)


@pytest.mark.parametrize("change", ["hash", "future", "numeric_code", "duplicate", "extra_label", "conflicting_code", "inf"])
def test_pivot_refuses_corrupt_rows(change):
    frame, metadata = source_values()
    if change == "hash":
        frame.loc[0, "definition_hash"] = "f" * 64
    elif change == "future":
        frame.loc[0, "known_at"] = "2025-02-01T00:00:00+09:00"
    elif change == "numeric_code":
        frame["stock_code"] = frame.stock_code.astype(object)
        frame.loc[0, "stock_code"] = 5930
    elif change == "duplicate":
        frame = pd.concat([frame, frame.iloc[:1]])
    elif change == "extra_label":
        frame["fwd_return"] = .5
    elif change == "conflicting_code":
        frame.loc[2, "stock_code"] = "999999"
    else:
        frame.loc[0, "value"] = float("inf")
    with pytest.raises(ValueError):
        references.reference_fields(frame, metadata, list(metadata["definitions"]))


def test_metadata_cannot_relabel_as_alpha_or_legacy():
    frame, metadata = source_values()
    for override in [{"profitability_approved": True}, {"legacy_gold_used": True}, {"generation_id": "legacy"}]:
        with pytest.raises(ValueError):
            references.reference_fields(frame, {**metadata, **override}, list(metadata["definitions"]))


def test_active_loader_forwards_explicit_snapshot_without_changing_binding(monkeypatch, tmp_path):
    root, _ = repository(tmp_path)
    frame, metadata = source_values()
    snapshot = tmp_path / "exact.parquet"
    calls = []

    def loader(conn, **kwargs):
        calls.append(kwargs)
        return frame, metadata

    monkeypatch.setattr(gold, "load_library", loader)
    references.load_active_references(None, root, snapshot_path=snapshot)
    assert calls == [{"dataset_id": "d" * 64, "generation_id": gold.GENERATION, "snapshot_path": snapshot}]


def published_snapshot():
    """Real publication validator fixture; no DB or synthetic-certification bypass."""
    definition = load_catalog()[0]
    frame = pd.DataFrame([{"reference_id": definition["id"], "definition_hash": definition_hash(definition),
                           "asset_id": 1, "stock_code": "0037T0", "date": "2020-01-31",
                           "known_at": "2020-01-31T23:59:59+09:00", "value": 1.0}])
    attestation = {"status": "CERTIFIED", "source_type": "RDS_CERTIFIED_KRX_PRICE_ONLY", "source_version": "test-only",
                   "input_sha256": "a" * 64, "evidence_sha256": "b" * 64}
    parity = {"passed": True, "values_sha256": digest(gold.canonical_values(frame)), "rows_compared": 1,
              "sql_sha256": "c" * 64, "rtol": 1e-10, "atol": 0,
              "kind": "INDEPENDENT_POSTGRES_FORMULAS_SAME_ATTESTED_PRICE_FEATURES"}
    validation = {"value_rows": 1, "source_version": "test-only", "input_sha256": "a" * 64,
                  "source_evidence_sha256": "b" * 64, "role": "MEASUREMENT_CONTROL", "alpha_approved": False,
                  "implementation_sha256": "d" * 64,
                  "references": [{"reference_id": definition["id"], "definition_hash": definition_hash(definition),
                                  "value_rows": 1, "status": "MEASUREMENT_VALIDATED"}]}
    publication, rows = gold.build_publication(frame, [definition], attestation=attestation, validation=validation, parity=parity)
    return frame, publication, rows


class SnapshotConnection:
    """Fake database returns independently supplied committed rows and metadata."""
    def __init__(self, metadata, rows):
        self.metadata = metadata
        self.rows = rows
        self.commands = []
        self.transaction_count = 0
        self.last_sql = ""

    def transaction(self):
        from contextlib import nullcontext
        self.transaction_count += 1
        return nullcontext()

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=None):
        self.commands.append((sql, params))
        self.last_sql = sql
        if sql == gold.READBACK_SQL:
            assert params == (gold.READBACK_CHUNK_SIZE, self.metadata["dataset_id"], gold.GENERATION)

    def fetchone(self):
        return (self.metadata,) if self.metadata is not None else None

    @property
    def description(self):
        from types import SimpleNamespace
        return [SimpleNamespace(name=key) for key in self.rows[0]]

    def fetchall(self):
        if self.last_sql == gold.READBACK_SQL:
            return [tuple(row.values()) for row in gold.binary_readback_chunks(self.rows)]
        assert "SELECT reference_id" in self.last_sql
        return [tuple(row.values()) for row in self.rows]


@pytest.mark.parametrize("full_schema", [False, True])
def test_snapshot_uses_database_metadata_and_all_row_hashes_not_raw_network_rows(tmp_path, full_schema):
    frame, metadata, rows = published_snapshot()
    if full_schema:
        frame = frame.assign(market="KOSPI", oriented_value=-1.0, source_version=metadata["source_version"],
                             input_sha256=metadata["input_sha256"])
    path = tmp_path / "values.parquet"
    frame.to_parquet(path, index=False)
    conn = SnapshotConnection(metadata, rows)
    output, loaded = gold.load_library(conn, dataset_id=metadata["dataset_id"], snapshot_path=path)
    assert set(output) == references.VALUE_COLUMNS and output.value.tolist() == [1.0]
    assert output.stock_code.tolist() == ["0037T0"] and loaded == metadata
    assert conn.transaction_count == 1
    assert sum(sql == gold.READBACK_SQL for sql, _ in conn.commands) == 1
    assert not any("SELECT reference_id" in sql for sql, _ in conn.commands)
    assert not any("INSERT" in sql or "UPDATE" in sql for sql, _ in conn.commands)


def test_default_loader_still_reads_every_database_row():
    _, metadata, rows = published_snapshot()
    conn = SnapshotConnection(metadata, rows)
    output, loaded = gold.load_library(conn, dataset_id=metadata["dataset_id"])
    assert gold.canonical_values(output) == rows and loaded == metadata
    assert any("SELECT reference_id" in sql for sql, _ in conn.commands)
    assert not any(sql == gold.READBACK_SQL for sql, _ in conn.commands)


def test_cache_tamper_rejected_against_database_publication(tmp_path):
    frame, metadata, rows = published_snapshot()
    frame.loc[0, "value"] = 999.0
    # Cached pandas metadata is not a trusted replacement for DB publication.
    frame.attrs = {"dataset_id": metadata["dataset_id"], "values_sha256": digest(gold.canonical_values(frame))}
    path = tmp_path / "values.parquet"
    frame.to_parquet(path, index=False)
    conn = SnapshotConnection(metadata, rows)
    with pytest.raises(ValueError, match="digest"):
        gold.load_library(conn, dataset_id=metadata["dataset_id"], snapshot_path=path)
    assert not any(sql == gold.READBACK_SQL for sql, _ in conn.commands)


def test_valid_cache_cannot_hide_changed_database_values(tmp_path):
    frame, metadata, rows = published_snapshot()
    path = tmp_path / "values.parquet"
    frame.to_parquet(path, index=False)
    rows[0]["known_at"] = "2020-01-31T14:59:58+00:00"
    conn = SnapshotConnection(metadata, rows)
    with pytest.raises(ValueError, match="binary read-back differs"):
        gold.load_library(conn, dataset_id=metadata["dataset_id"], snapshot_path=path)


@pytest.mark.parametrize("bad", ["missing_dataset", "wrong_dataset", "wrong_generation"])
def test_snapshot_cannot_replace_exact_database_identity(tmp_path, bad):
    frame, metadata, rows = published_snapshot()
    path = tmp_path / "values.parquet"
    frame.to_parquet(path, index=False)
    expected_id = metadata["dataset_id"]
    if bad == "missing_dataset":
        metadata = None
    elif bad == "wrong_dataset":
        metadata = {**metadata, "dataset_id": "f" * 64}
    else:
        metadata = {**metadata, "generation_id": "legacy"}
    conn = SnapshotConnection(metadata, rows)
    with pytest.raises(ValueError, match="dataset"):
        gold.load_library(conn, dataset_id=expected_id, snapshot_path=path)


@pytest.mark.parametrize("bad", ["extra_label", "missing_column", "partial_library_schema", "wrong_provenance"])
def test_snapshot_requires_known_schema_and_matching_provenance(tmp_path, bad):
    frame, metadata, rows = published_snapshot()
    if bad == "extra_label":
        frame["forward_return"] = .1
    elif bad == "missing_column":
        frame = frame.drop(columns="known_at")
    elif bad == "partial_library_schema":
        frame["market"] = "KOSPI"
    else:
        frame = frame.assign(market="KOSPI", oriented_value=-1., source_version="unrelated",
                             input_sha256=metadata["input_sha256"])
    path = tmp_path / "values.parquet"
    frame.to_parquet(path, index=False)
    conn = SnapshotConnection(metadata, rows)
    with pytest.raises(ValueError, match="schema|provenance"):
        gold.load_library(conn, dataset_id=metadata["dataset_id"], snapshot_path=path)


@pytest.mark.parametrize("bad", ["symlink", "parent_symlink", "not_parquet", "directory", "missing"])
def test_snapshot_must_be_explicit_regular_non_symlink_parquet(tmp_path, bad):
    frame, metadata, rows = published_snapshot()
    path = tmp_path / "values.parquet"
    if bad == "directory":
        path.mkdir()
    elif bad != "missing":
        frame.to_parquet(path, index=False)
        if bad == "symlink":
            linked = tmp_path / "linked.parquet"
            linked.symlink_to(path)
            path = linked
        elif bad == "parent_symlink":
            linked = tmp_path / "linked"
            linked.symlink_to(tmp_path, target_is_directory=True)
            path = linked / path.name
        else:
            path = path.rename(tmp_path / "values.pickle")
    with pytest.raises(ValueError, match="regular non-symlink parquet"):
        gold.load_library(SnapshotConnection(metadata, rows), dataset_id=metadata["dataset_id"], snapshot_path=path)


@pytest.mark.parametrize("command", ["catalog", "build", "publish"])
def test_readback_snapshot_option_rejected_for_other_commands(monkeypatch, command):
    import sys
    from scripts import reference_library as cli

    def forbidden_connection(*args, **kwargs):
        pytest.fail("Invalid CLI options must not reach a database")

    monkeypatch.setattr(cli.silver, "connect", forbidden_connection)
    monkeypatch.setattr(sys, "argv", ["reference_library", command, "--snapshot-path", "values.parquet"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2


def test_readback_cli_forwards_snapshot_to_verified_loader(monkeypatch, tmp_path, capsys):
    from contextlib import nullcontext
    import sys
    from scripts import reference_library as cli

    frame, metadata, _ = published_snapshot()
    path = tmp_path / "values.parquet"
    conn = object()
    calls = []

    def loader(connection, **kwargs):
        calls.append((connection, kwargs))
        return frame, metadata

    monkeypatch.setattr(cli.silver, "connect", lambda: nullcontext(conn))
    monkeypatch.setattr(cli.gold, "load_library", loader)
    monkeypatch.setattr(sys, "argv", ["reference_library", "readback", "--dataset-id", metadata["dataset_id"],
                                     "--snapshot-path", str(path)])
    cli.main()
    assert calls == [(conn, {"dataset_id": metadata["dataset_id"], "snapshot_path": path})]
    assert json.loads(capsys.readouterr().out)["digest_verified"] is True
