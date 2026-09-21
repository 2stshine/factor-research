# Single-factor smoke run: resume checkpoint

Recorded 2026-09-20 12:20 KST. This is an operational checkpoint, not a factor result.
Inspect current processes and campaign files before resuming; this note can become stale.

## Evaluation completed — 2026-09-20 21:56 KST

- Recovered session `53261`: exit 0. Exactly one candidate was evaluated and recorded as `cycle-0229-operating_asset_growth_12m`.
- Epoch is CLOSED; campaign is CLOSED_NO_QUALIFIED. Candidate REJECT at T1.2: the three terminal-return scenario directions did not all remain positive. FDR is NOT_TESTABLE, not an independently executed significant-failure finding.
- OOS is NOT_USED (never revealed). SQL implementation parity and null calibration were not reached. No Gold write, commit or push.
- Candidate source SHA remains `630fc23ad5e23482695fc25074c9a27ab7aa567c3d33c0b27b7c41d9fb171ca7`; persisted result SHA `b237826021239506a24511ca037920e3c652b5bb6132837cb2379b18558e8f4a` matches the epoch binding.
- Evaluation subtotal was 721.826 seconds, followed by 1,504.656 seconds for 274 frozen registry definitions. This is about 37 minutes for evaluation and comparison, excluding earlier registration/context preparation. All 273 other registry signals now have cache entries.
- Mechanism diagnostics were COLLECTED. Three actual graphs were rendered and viewed. Market regimes and execution costs remain unavailable; financial follow-ups are partial and show conflicting rank versus raw-mean direction with unusually large group means. These are unresolved diagnostic limitations, not proof of data corruption or a causal mechanism.
- Added explicit signal orientation/holding-period context and a diagnostic-only economic rank/mean disagreement warning to the analyst/critic packet. The original result and factor/gates were not changed. Latest focused tests: 52 passed; earlier combined core tests: 202 passed (overlapping suites, do not add counts).
- Analyst review is `research/diagnostics/20260920-operating-asset-growth-review-v2.json`. The independent critic accepted it with evidence/hash validation; `lesson_review save` completed. The candidate review is CURRENT and REVIEWED, and the general lesson is reflected once in KNOWLEDGE. No-change regeneration is byte-identical. The factor smoke task and interpretation are complete; do not rerun it.
- Minor reporting clarification: T1.3 total-return certification did PASS. Unexecuted later tests refer to subsequent performance/promotion checks, SQL parity, null and OOS, not every check appearing after T1.2 in the report.
- The dedicated SSM session had already terminated from inactivity after database work completed. No research process remains running.

## Running evaluation — 2026-09-20 21:35 KST

- Tool session `53261`, local PID `25406`, remains the only evaluation process. Database preparation completed: `evaluation.live_inputs=697.557s`, candidate compute `1.199s`, gate calculation `1.517s`, evaluation subtotal `721.826s` (logs at 21:29 KST).
- It is now computing the frozen registry comparison set locally, before result persistence. At 21:34 KST, 75 comparison signal cache pairs existed under the campaign Discovery digest. This is cache progress, not candidate verdict or approval.
- Recover the live process before any retry: a candidate gate result may already exist in its running process even though no final cycle artifact has been written yet. Do not launch another evaluation.
- The registry calculation has not changed candidate definition, gates, periods, or Gold. Result-based AI Scientist interpretation and the required independent critic still await persisted, released evidence.

## Authoritative progress — 2026-09-20 21:17 KST

- Registration session `6242` completed successfully. `epochs/epoch-001/manifest.json` now freezes only `operating_asset_growth_12m`, definition `623a85a993bff126`, strategy SHA `630fc23ad5e23482695fc25074c9a27ab7aa567c3d33c0b27b7c41d9fb171ca7`.
- Input and APPROVED Gold correlation preflights both PASS; all 49 approved factors were included. Candidate status REGISTERED, OOS SEALED.
- Started the one authorized `epoch-evaluate` in tool session `53261`, application `fr-c20260920-e001-evaluate`. Recover this session and inspect artifacts before any restart.
- Registration spent approximately twelve minutes in Gold input preparation. EXPLAIN showed 10,695,426 factor/asset/month index probes. A bounded alternative range-query experiment matched 723 rows exactly but was slower on that sample; it was **not adopted** and must not be treated as a verified optimization.
- No candidate performance result exists yet at this checkpoint. No OOS reveal, Gold write, commit or push.

## Latest execution — 2026-09-20 21:07 KST

- User authorized a different single candidate after the old input failure. Selected the existing, unattempted `operating_asset_growth_12m`; definition `623a85a993bff126`, formula `((total_assets-current_liabilities)_t / (total_assets-current_liabilities)_(t-12))-1`, sign `-1`. No definition edits or outcome-based parameter selection.
- Local label-free input check and structural batch policy passed: coverage `0.9440326557613664`, monthly coverage p10 `0.9339966032902028`, same frozen Discovery digest. Economic scope differs from raw total-asset growth: current liabilities are removed; this is not a certified measure of pure operating assets.
- AWS authenticated; context/live return validation finished successfully at about 21:04 KST. SSM session `ISB-35-ae8ptp3k8kdheugl7y86g9vacy` uses localhost:5433, tool session `91944`.
- Registration is running in tool session `6242`, DB application `fr-c20260920-e001-register`, observed backend `22373`. It is reading exact monthly APPROVED Gold comparisons. Do not duplicate it. At this checkpoint the campaign still has no epoch manifest.
- Added `candidate-input-check` to make the local-only availability check callable before registration; PASS does not authorize registration or certify live RDS. Research context now labels registry as code definitions, not approval.
- Combined preflight/invariants/policy/mechanism/knowledge/lesson tests: `202 passed in 11.98s`. No Discovery result yet, no OOS reveal or Gold write, no commit/push.
- Once registration exits, inspect authoritative manifests. If successful, run `epoch-evaluate` once, close/finalize, and follow the released-result analyst/critic workflow. Do not retrofit the old candidate's definition or claim its economic hypothesis failed.

## Latest update — 2026-09-20 14:21 KST

This section supersedes the process/login status under the older checkpoint below.

- AWS profile `teamalpha` device login completed successfully. No credential or device code is recorded here.
- Recovered registration process `31594`: exit 1, candidate input coverage preflight failure. No epoch was registered; campaign remains OPEN with an empty epoch list and SEALED OOS.
- Reproduced the label-free input check against the unchanged campaign snapshot: overall coverage `0.664737190281453` (minimum `0.5`), monthly coverage p10 `0.0` (minimum `0.3`). Definition hash is still `990062b564c6ae51`.
- Inspected only Discovery input availability, not returns: a usable `revenue_ttm / positive total_assets` input first appears in the current panel in `2017-02`. The frozen candidate also requires exact 12- and 24-month lags. Candidate coverage is zero for `2018-03` through `2019-01`, becomes nonzero in `2019-02`, and exceeds 30% in `2019-04`. Existing historical price rows alone do not supply the missing financial history.
- This is input infeasibility for the fixed evaluation period, not evidence against the economic hypothesis. No performance evaluation, chart review, OOS reveal, or Gold write occurred.
- Fixed registration order in `scripts/run.py`: validate the local input artifact before opening a live connection or loading Gold signals. Passing candidates retain live generation and exact Gold comparison checks. Added regression tests in `tests/test_candidate_registration_preflight.py`.
- Verification: registration preflight, Gold generation, invariants, and research policy suites passed together (`155 passed in 5.52s`); `git diff --check` passed.
- No new SSM tunnel or heavy SQL was launched in this resume. Do not rerun this candidate's registration expecting login to fix the missing history, and do not alter its formula, period, or gates to force a pass.
- End-to-end AI Scientist verification remains incomplete. It requires a separately selected feasible candidate or a properly certified historical input extension; neither has been silently substituted here.

## Completed

- Matched the latest producer rounding contract (TeamAlpha-data origin/main `43ad47bf82e89b32af1c8f4db0003526405da1ce`), including the stable scale drift limit and two-stage price quantization. The earlier upstream-corruption diagnosis is superseded.
- Built and activated the new certified `.cache/panel.pkl`: 736,672 monthly rows and 94,186 financial PIT snapshots across 3,076 financial-reporting assets. Previous cache preserved under `.cache/panels/legacy-file-e9c24f5af410beadfdb3371f691bdcbf3a605d3081c89d4179d2cb38e5326b82/panel.pkl`.
- Refreshed `research/KNOWLEDGE.md` and created `campaign-20260920-001`, one epoch, one candidate in program `single-factor-scientist-20260920`.
- Fixed partial Gold generation detection: SQL `COUNT(DISTINCT ...)` ignored unbound entries. The cached catalog had 37 approved factors, while the live catalog had 49, including untagged legacy entries. An incompletely bound catalog now uses a fresh, read-only query instead of trusting the partial cache. No Gold metadata, values or status changed.
- Replaced the uncacheable catalog's full-history sort with indexed, asset/month-targeted last-observation lookups. Missing comparisons remain missing; no factor is omitted. No permanent DB object was added.
- PostgreSQL fixture exact parity passed (five output rows, including sign, month boundary, missingness, exact decimal and retired exclusion). Bounded live old/new query comparison passed on five assets × three Discovery months: 723 identical rows. This is bounded query parity, not the candidate's Python/Gold SQL parity.
- Tests: total-return contract 201 passed; identity/invalidation 30 passed; latest combined Gold-reader/invariants/mechanism/knowledge suite 181 passed. `git diff --check` passed.

## In progress / blocked

- Candidate: `asset_turnover_acceleration_12m`, unchanged definition hash `990062b564c6ae51`.
- Campaign manifest is authoritative: `research/campaigns/campaign-20260920-001/manifest.json`.
- Discovery cutoff: 2023-06-30; signal evaluation ends 2023-05. OOS 2023-07–2026-06 remains SEALED, labeled HISTORICAL_REUSED_WINDOW.
- Epoch registration preflight is still running: unified terminal session `31594`, local Python PID `16107`, command `epoch-start --campaign campaign-20260920-001 --epoch epoch-001 --factors asset_turnover_acceleration_12m`. At this checkpoint there is no epoch manifest yet. It will be written only if preflight succeeds.
- The previous full-history Gold query was safely canceled (local PID 15725 / DB PID 29491); cancellation was verified. Do not restart it.
- Current SSM tunnel: terminal session `63019`, `ISB-35-ei3c2nopsh6ox6ye24edrgrt8u`, localhost:5433 to the configured RDS. The old localhost:5432 tunnel was closed.
- AWS SSO expired for new Secrets Manager requests. Device-flow login is open in the default Chrome browser, terminal session `2187`. No one-time code or credential is stored here. The browser requires user sign-in. The existing SQL/SSM connection remains active.
- The `.env` database URL has no password. Do not treat it as an alternative working credential. After login, obtain the configured secret through AWS CLI in memory; never print or save the credential.
- No Discovery outcome, ledger trial, mechanism study, OOS result or economic lesson has been produced for this candidate yet. No Gold write, commit or push was performed.

## Resume order

1. Recover the existing preflight process/result before starting any new command. Check whether `epochs/epoch-001/manifest.json` now exists. Do not duplicate a running job.
2. Confirm SSO login and the tunnel. Do not rebuild the already certified Silver cache unless live generation verification reports an actual change.
3. If registration succeeded, run `epoch-evaluate` once for the saved campaign/epoch, then close the epoch and finalize the campaign. If preflight failed, diagnose its actual error without altering the candidate or gates.
4. Only proceed to parity/null/one-time confirmation if qualification and the authorized workflow require it. This smoke task has not requested Gold writes.
5. After release, prepare the evidence packet, inspect actual charts, write evidence-grounded mechanism analysis, obtain the separate critic required by INSTRUCTIONS, and save the accepted lesson. Keep missing regime/industry/cost information explicit.
6. Use the observed result to finish the requested AI Scientist improvement. This part is still pending; infrastructure tests are not a completed factor evaluation.

Preserve existing dirty work, unrelated `.Rhistory`, FMP scripts, `output/` and `tmp/`. There has been no request to commit or push this turn.
