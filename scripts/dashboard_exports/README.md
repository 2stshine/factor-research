# Research dashboard source exports

Run these scripts from the repository root using its existing virtual environment.
They generate sanitized JSON under `output/research-dashboard-source/`; they do
not update the Site checkout or publish a website. These scripts are the maintained
copies; the older scripts beside the generated output are working-session copies.

## Released research catalog

```sh
.venv/bin/python scripts/dashboard_exports/export_research_catalog.py
```

For a reproducible labeled snapshot, pass `--as-of 2026-09-23`. To keep an existing
artifact, also pass `--output output/research-dashboard-source/research-catalog-next.json`.
`as_of` is the export timestamp or requested label, not a new data certification.
The output includes the source ledger SHA-256 and each record's evidence hashes.

The exporter reads the existing candidate-lessons ledger, current campaign/epoch
states, and already released evidence. A record must already be
`RELEASED_QUALITATIVE` and belong to a terminal `CLOSED_NO_QUALIFIED` campaign or a
`REVEALED` campaign whose one-time confirmation passes the existing protocol,
exact-set, and digest checks. It checks source identity, frozen artifact hashes
where present, an exact evidence-packet rebuild, and current review bindings.
Pending records are counted before any raw result or evidence packet is opened.
Unreviewed candidates retain released definitions and numerical evidence but do
not acquire invented lessons. Rejected and provisional records are retained.

This export does not refresh research memory, certify Silver, run a candidate,
reveal OOS, write to a database, or alter Gold. If upstream knowledge is stale,
this command does not make it current. Regime diagnostics retain their Discovery
scope and `PIT_ASSUMED` labels. Confirmation-packet portfolio metrics retain their
Discovery period attribution and documented units.

## Gold catalog

Offline metadata snapshot, written separately so an existing snapshot is preserved:

```sh
.venv/bin/python scripts/dashboard_exports/export_gold_catalog.py --local --output output/research-dashboard-source/gold-local-catalog.json
```

Live read-only metadata refresh, only after the existing AWS login and SSM tunnel
are valid and the normal read-only database environment is configured:

```sh
.venv/bin/python scripts/dashboard_exports/export_gold_catalog.py --live
```

The live command's default output is `output/research-dashboard-source/gold-catalog.json`.
`--output` can write an alternate file. These scripts do not start tunnels, log
in, bootstrap schemas, change configuration, query factor-value rows, or write to
RDS. A failed live connection reports a redacted failure and does not replace the
existing artifact. Do not relabel local output as a verified current DB catalog.

`as_of` records when the export was made; `catalog_as_of` records the underlying
catalog evidence time. Always display `is_live`, `status`, and `source` with the
data. The September 23 source artifact has 49 entries and is explicitly
`NONLIVE_SNAPSHOT_CURRENT_DB_UNVERIFIED`, based on September 21 revealed
confirmation metadata; current approved membership was not rechecked against RDS.

## Verification and delivery boundary

At the September 23 post-review export, research counts were 203 ledger records,
177 released, 26 pending, 177 reviewed, and 0 unreviewed. The earlier same-day
snapshot had 2 reviewed and 175 unreviewed; the archive-only review completed
without rerunning research. Released verdicts were 29 PROMOTE,
142 REJECT, and 6 PROVISIONAL across 25 campaigns. These are reference counts, not
hardcoded acceptance criteria for future source changes.

Keep reviewer exports within the authorized dashboard audience (the owner has
explicitly authorized this existing dashboard's public access). Sanitized
paths and removed credentials do not make released performance suitable for the
candidate-generation context. Moving these files into a Site and deploying it is
a separate workflow; refresh does not silently deploy or change research state.
