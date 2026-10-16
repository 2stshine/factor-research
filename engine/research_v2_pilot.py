"""Trusted preparation and broker for a frozen six-definition protocol reanalysis.

The adapter never receives the full panel. Scope is cut before factor execution;
candidate computation retains its existing causal/label-isolation policy. This
is not campaign registration, a new discovery, gate evaluation, OOS revelation,
or Gold publication. Filesystem access by the host is not an OS security sandbox.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd

from engine import adaptive_research as audit
from engine import panel as P
from engine.boundaries import CampaignWindow
from engine.research_real_diagnostics import CATALOG, RealDiagnosticLab, make_real_contract
from engine.research_real_runtime import RealDiagnosticSession, make_contract as session_contract
from engine.research_regime_adoption import market_rows, validate_adoption


VERSION = "research-v2-real-reanalysis-pilot-v1"
SELECTED = ("net_roa", "operating_roa", "asset_growth_12m", "current_assets_growth_12m",
            "price_momentum_6_1", "price_momentum_12_3")
SIGNAL_START = "2016-02"
FIXED_ORDER = ("input_audit", "association", "controls", "regime_interaction",
               "economic_link", "execution_cost")
FINANCIAL = frozenset(SELECTED[:4])
REGIME_LABELS = ["UP_LOW", "UP_HIGH", "DOWN_LOW", "DOWN_HIGH"]


def _sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path, value):
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as target:
        target.write(body)
    return hashlib.sha256(body).hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_bytes())


def _code_bindings():
    root = Path(__file__).parent
    paths = [root / name for name in (
        "research_v2_pilot.py", "research_real_diagnostics.py", "research_real_runtime.py",
        "adaptive_research.py", "research_regime_adoption.py", "research_policy.py", "panel.py",
        "boundaries.py", "factors.py")]
    paths.extend(root.parent / "scripts" / name for name in ("run.py", "research.py", "research_v2.py"))
    return {str(path.relative_to(root.parent)): _sha_file(path) for path in paths}


def exposure_bindings(paths):
    """Hash pre-existing exposure metadata without parsing or returning results."""
    files = []
    for path in sorted({Path(item).resolve() for item in paths}):
        if not path.is_file():
            raise ValueError("A declared prior-exposure metadata file is missing")
        files.append({"path": str(path), "sha256": _sha_file(path), "bytes": path.stat().st_size})
    if not files:
        raise ValueError("Prior exposure metadata must be preserved, not reset")
    return {"files": files, "payloads_parsed": False, "historical_reuse": True,
            "trial_counts_reset": False, "independent_oos_claim": False}


def definition_identity(factor):
    filename = inspect.getfile(factor.compute)
    # Candidate loader compiles under a content-addressed virtual filename.
    # Only its exact, terminal suffix is accepted, and the physical bytes must
    # still match the compiled version. Arbitrary fragments are never stripped.
    compiled = re.fullmatch(r"(.+\.py)#sha256=([0-9a-f]{64})", filename)
    if "#sha256=" in filename and compiled is None:
        raise ValueError("Malformed content-addressed factor source filename")
    path = Path(compiled.group(1) if compiled else filename).resolve()
    source_file_sha256 = _sha_file(path)
    if compiled and compiled.group(2) != source_file_sha256:
        raise ValueError("Compiled factor source hash no longer matches physical bytes")
    body = {"name": factor.name, "source": factor.source, "source_file": str(path),
            "source_file_sha256": source_file_sha256, "legacy_definition_hash": factor.definition_hash,
            "predicted_sign": factor.predicted_sign, "params": factor.params,
            "needs": list(factor.needs), "rebalance_months": factor.rebalance_months,
            "hypothesis": factor.hypothesis, "category": factor.category,
            "family": factor.family, "exploration_domain": factor.exploration_domain}
    return {**body, "definition_sha256": audit.digest(body)}


def _validate_plan(plan):
    if (plan.get("schema_version") != "research-v2-completion-plan-v1"
            or plan.get("pilot_kind") != "EXPLICIT_PROTOCOL_REANALYSIS_NOT_NEW_FACTOR_DISCOVERY"
            or plan.get("selected_definitions") != list(SELECTED)
            or plan.get("selection_locked_before_new_performance") is not True
            or plan.get("replacement_on_poor_performance") is not False):
        raise ValueError("A frozen, outcome-blind six-definition reanalysis plan is required")


def _audit_binding(receipt, *, identity, snapshot, panel_file_sha):
    if not isinstance(receipt, dict):
        raise ValueError("An explicit authenticated/operator audit receipt is required")
    if receipt.get("kind") == "OPERATOR_ATTESTATION":
        if (receipt.get("observed_status") != "MATCH"
                or receipt.get("asset_identity_digest") != identity
                or receipt.get("snapshot_sha256") != snapshot
                or receipt.get("source_panel_file_sha256") != panel_file_sha
                or not isinstance(receipt.get("provenance"), str) or not receipt["provenance"].strip()):
            raise ValueError("Operator attestation is not bound to this panel")
        return "OPERATOR_ATTESTATION_OF_OBSERVED_MATCH_NOT_SIGNED_LIVE_PROOF"
    if (receipt.get("status") != "MATCH" or receipt.get("gold_write") is not False
            or receipt.get("cache", {}).get("asset_identity_digest") != identity
            or receipt.get("rds", {}).get("asset_identity_digest") != identity
            or receipt.get("snapshot_sha256") != snapshot
            or receipt.get("source_panel_file_sha256") != panel_file_sha
            or not isinstance(receipt.get("total_return_contract"), dict)
            or not receipt["total_return_contract"]):
        raise ValueError("Live MATCH receipt is not bound to this asset identity")
    return "CALLER_SUPPLIED_LIVE_MATCH_RECEIPT_NOT_CRYPTOGRAPHIC_ATTESTATION"


def _project_case(frame, eligible, factor, *, window, regime_contract):
    """Only Discovery rows can enter economic joins and public projections."""
    cutoff = pd.Timestamp(window.discovery_data_cutoff)
    cutoff_end = cutoff + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    months = pd.PeriodIndex(frame["ym"], freq="M")
    if months.max() >= window.oos_signal_start or pd.to_datetime(frame.trade_date).max() > cutoff_end:
        raise ValueError("Scope before projection/economic joins")
    use = (months >= pd.Period(SIGNAL_START, freq="M")) & (months <= window.discovery_signal_end)
    use &= eligible.reindex(frame.index).fillna(False).to_numpy()
    base = frame.loc[use].copy()
    if base.empty:
        raise ValueError("No common investable Discovery rows")
    if base.duplicated(["asset_id", "ym"]).any():
        raise ValueError("Duplicate Discovery asset-month")
    signal_name = f"f_{factor.name}"
    out = pd.DataFrame({"month": base["ym"].astype(str), "asset_id": base["asset_id"],
                        "signal": pd.to_numeric(base[signal_name], errors="coerce"),
                        "forward_return": pd.to_numeric(base["fwd_mid"], errors="coerce"),
                        "return_known_at": cutoff_end,
                        "market": base["market"].astype(str),
                        "log_market_cap": np.log(pd.to_numeric(base["market_cap"], errors="coerce").where(base["market_cap"] > 0)),
                        "log_adv20": np.log(pd.to_numeric(base["adv20"], errors="coerce").where(base["adv20"] > 0))})
    out = out.reset_index(drop=True)
    context = {row["month"]: row for row in market_rows(regime_contract, "KOSPI")}
    if not set(out.month).issubset(context):
        raise ValueError("Frozen KOSPI diagnostic context does not cover the signal scope")
    out["market_regime"] = out.month.map(lambda month: context[month]["regime"])
    # This is the source's explicitly assumed month-end decision convention,
    # not the adoption date nor a claimed observed source publication timestamp.
    out["regime_known_at"] = out.month.map(
        lambda month: pd.Timestamp(context[month]["decision_at"]).tz_convert("Asia/Seoul").tz_localize(None))
    regime = {"column": "market_regime", "known_at": "regime_known_at", "labels": REGIME_LABELS,
              "contrast": ["UP_LOW", "DOWN_HIGH"], "definition_sha256": regime_contract["rules_sha256"],
              "pit_status": "PIT_ASSUMED"}
    economic = None
    economic_notes = ["Economic outcome is absent; no mechanism claim from return association alone."]
    required = {"asset_id", "ym", "net_income_ttm", "total_assets", "available_date"}
    if factor.name in FINANCIAL and required.issubset(frame):
        source = frame[list(required)].copy()
        source["ym"] = pd.PeriodIndex(source["ym"], freq="M")
        if source.duplicated(["asset_id", "ym"]).any():
            raise ValueError("Duplicate economic snapshot key")
        source["public_roa"] = pd.to_numeric(source.net_income_ttm, errors="coerce") / pd.to_numeric(
            source.total_assets, errors="coerce").where(source.total_assets > 0)
        future = source[["asset_id", "ym", "public_roa", "available_date"]].copy()
        future["ym"] -= 12
        future = future.rename(columns={"public_roa": "future_roa", "available_date": "future_available_date"})
        keys = base[["asset_id", "ym"]].copy()
        current = source[["asset_id", "ym", "public_roa", "available_date"]]
        joined = keys.merge(current, on=["asset_id", "ym"], how="left", validate="one_to_one")
        joined = joined.merge(future, on=["asset_id", "ym"], how="left", validate="one_to_one")
        formation = pd.PeriodIndex(joined.ym, freq="M").end_time
        horizon = (pd.PeriodIndex(joined.ym, freq="M") + 12).end_time
        future_known = pd.to_datetime(joined.future_available_date, errors="coerce")
        current_known = pd.to_datetime(joined.available_date, errors="coerce")
        valid = future_known.gt(formation) & future_known.le(horizon) & future_known.le(cutoff_end)
        valid &= horizon <= cutoff_end
        kind = "LEVEL" if factor.name in SELECTED[:2] else "CHANGE"
        value = joined.future_roa
        if kind == "CHANGE":
            valid &= current_known.notna() & current_known.le(formation)
            value = value - joined.public_roa
        out["economic_outcome"] = pd.to_numeric(value, errors="coerce").replace([np.inf, -np.inf], np.nan).where(valid).to_numpy()
        out["economic_known_at"] = future_known.where(valid).to_numpy()
        economic = {"column": "economic_outcome", "known_at": "economic_known_at", "horizon_months": 12,
                    "dataset_id": f"SILVER_PUBLIC_ROA_12M_{kind}", "measurement_kind": kind}
        economic_notes = [
            f"Public PIT snapshot ROA {kind.lower()} at exact calendar t+12, not future fiscal-year earnings or surprise.",
            "Fresh actual filing availability must follow formation and not exceed horizon or exact cutoff; missing exits are not imputed.",
            "Twelve-month accounting outcome versus one-month return is descriptive, not temporal mediation.",
        ]
    out = out.replace([np.inf, -np.inf], np.nan)
    return out, economic, regime, economic_notes


def prepare_pilot(panel, boundary: CampaignWindow, *, plan: dict, regime_contract: dict,
                  audit_receipt: dict, output: Path, source_panel_file_sha256: str,
                  source_label: str, exposure_metadata: dict, factors=None) -> dict:
    """Trusted host only. Accept an already-loaded authenticated Panel.

    Writes a plan before signal calculation, then immutable frames/contracts and
    final manifest. A crash leaves an incomplete directory; never overwrite or
    silently resume it. No diagnostic reports are produced during preparation.
    """
    from scripts import run
    _validate_plan(plan)
    if (exposure_metadata.get("historical_reuse") is not True
            or exposure_metadata.get("trial_counts_reset") is not False
            or not exposure_metadata.get("files")):
        raise ValueError("Existing exposure metadata binding required")
    validate_adoption(regime_contract)
    if not isinstance(boundary, CampaignWindow) or boundary.oos_months != 36:
        raise ValueError("Existing 36-month historical boundary required")
    if not re.fullmatch(r"[a-f0-9]{64}", source_panel_file_sha256):
        raise ValueError("Actual panel-file SHA required")
    P.verify_return_roles(panel)
    identity = P.verify_asset_identity(panel)["asset_identity_digest"]
    snapshot = P.snapshot_digest(panel)
    audit_kind = _audit_binding(audit_receipt, identity=identity, snapshot=snapshot,
                                panel_file_sha=source_panel_file_sha256)
    if factors is None:
        registry = run.load_registry()
        factors = [registry[name] for name in SELECTED]
    if [f.name for f in factors] != list(SELECTED):
        raise ValueError("Exact prespecified definition set required")
    definitions = [definition_identity(factor) for factor in factors]
    window = {key: str(value) for key, value in vars(boundary).items()}
    start, end = SIGNAL_START, str(boundary.discovery_signal_end)
    if pd.Period(start) > boundary.discovery_signal_end:
        raise ValueError("No primary signal interval")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    frozen = {
        "schema_version": VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
        "pilot_kind": plan["pilot_kind"], "plan": deepcopy(plan), "plan_sha256": audit.digest(plan),
        "source_label": source_label, "source_panel_file_sha256": source_panel_file_sha256,
        "source_snapshot_sha256": snapshot, "asset_identity_digest": identity,
        "audit_kind": audit_kind, "audit_receipt": deepcopy(audit_receipt),
        "audit_receipt_sha256": audit.digest(audit_receipt), "boundary": window,
        "prior_exposure_metadata": deepcopy(exposure_metadata),
        "signal_start": start, "signal_end": end, "maturity_cutoff": boundary.discovery_data_cutoff,
        "sealed_start": str(boundary.oos_signal_start), "definitions": definitions,
        "regime_contract_sha256": regime_contract["contract_sha256"], "code_sha256": _code_bindings(),
        "factor_returns_evaluated": False, "oos_evaluated": False, "gold_write": False,
        "full_source_loaded_by_trusted_preparer": True,
        "oos_observations_exposed_to_investigator": False,
        "independent_oos_claim": False, "legacy_records_changed": False,
        "comparison_population": "same monthly investable KRX common-stock universe, no outcome-complete-case preselection",
        "regime_market": "KOSPI_POOLED_CONTEXT_FIXED_NOT_SELECTED_BY_PERFORMANCE",
        "feature_availability": "POLICY_BOUND_NOT_FABRICATED_PER_CELL_KNOWN_AT",
        "mandatory_diagnostics": ["input_audit", "association", "controls", "regime_interaction"],
        "financial_additional_required": ["economic_link"],
        "max_cost_units": 18, "max_actions": 12, "fixed_order": list(FIXED_ORDER),
    }
    frozen_sha = _write_json(output / "frozen-plan.json", frozen)
    _write_json(output / "regime-contract.json", regime_contract)
    # Cropping/rebuilding happens before any candidate code can execute.
    scoped = run._scope_discovery_panel(panel, data_cutoff=boundary.discovery_data_cutoff,
                                        oos_start=boundary.oos_signal_start)
    scoped = run._research_input_panel(scoped)
    discovery_snapshot = P.snapshot_digest(scoped)
    eligible = scoped.investable.copy()
    missing = {factor.name: sorted(set(factor.needs) - set(scoped.monthly)) for factor in factors}
    available = [factor for factor in factors if not missing[factor.name]]
    frame = run._ensure_factor_columns(scoped, available)
    for factor in factors:
        if missing[factor.name]:
            frame[f"f_{factor.name}"] = np.nan
    cases = []
    for factor, definition in zip(factors, definitions):
        if definition_identity(factor) != definition:
            raise ValueError("Factor definition changed after freeze")
        projected, economic, regime, notes = _project_case(
            frame, eligible, factor, window=boundary, regime_contract=regime_contract)
        contract = make_real_contract(projected, capability_id=f"{plan['plan_id']}:{factor.name}",
            dataset_id=source_label, snapshot_sha256=discovery_snapshot,
            factor_definition_hash=definition["definition_sha256"], signal_start=start, signal_end=end,
            maturity_cutoff=boundary.discovery_data_cutoff, sealed_start=str(boundary.oos_signal_start),
            columns={"month": "month", "asset_id": "asset_id", "signal": "signal", "signal_known_at": None,
                     "forward_return": "forward_return", "return_known_at": "return_known_at"},
            controls=[{"name": "market", "column": "market", "kind": "categorical", "known_at": None},
                      {"name": "size", "column": "log_market_cap", "kind": "numeric", "known_at": None},
                      {"name": "liquidity", "column": "log_adv20", "kind": "numeric", "known_at": None}],
            feature_availability={"policy_id": "EXISTING_SILVER_FEATURE_LABEL_ROLE_CONTRACT",
                                  "status": "POLICY_BOUND", "evidence_sha256": frozen_sha},
            economic=economic, regime=regime, execution=None,
            question_kind="ECONOMIC" if factor.name in FINANCIAL else "EXPLANATORY",
            question=f"{factor.name}: 동결된 단일 팩터의 다음 달 수익 연관성에서 규모·유동성·국면 등 경쟁 설명을 구분하고, 확인되지 않은 경제적 경로와 자료 부족을 명시하라.")
        case_dir = output / "cases" / factor.name
        case_dir.mkdir(parents=True, exist_ok=False)
        projected.to_parquet(case_dir / "frame.parquet", index=False)
        # Validate round-trip fingerprints, not just the in-memory input.
        RealDiagnosticLab(pd.read_parquet(case_dir / "frame.parquet"), contract)
        contract_sha = _write_json(case_dir / "contract.json", contract)
        required = list(frozen["mandatory_diagnostics"])
        if factor.name in FINANCIAL:
            required.append("economic_link")
        cases.append({"case_id": factor.name, "frame_file": f"cases/{factor.name}/frame.parquet",
                      "frame_file_sha256": _sha_file(case_dir / "frame.parquet"),
                      "contract_file": f"cases/{factor.name}/contract.json", "contract_file_sha256": contract_sha,
                      "data_contract_sha256": audit.digest(contract), "definition_sha256": definition["definition_sha256"],
                      "required_diagnostics": required, "row_count": len(projected),
                      "signal_finite_rows": int(projected.signal.notna().sum()),
                      "status": "PREPARED" if projected.signal.notna().any() else "NOT_COMPUTED",
                      "missing_inputs": missing[factor.name], "economic_notes": notes,
                      "industry_control_status": "NOT_AVAILABLE", "execution_cost_status": "NOT_COMPUTED_NO_HOLDINGS_CONTRACT"})
    if _code_bindings() != frozen["code_sha256"]:
        raise ValueError("Preparation code changed after freeze")
    manifest = {"schema_version": VERSION, "status": "PREPARED_NO_DIAGNOSTICS_RUN",
                "frozen_plan_file": "frozen-plan.json", "frozen_plan_file_sha256": frozen_sha,
                "regime_contract_file_sha256": _sha_file(output / "regime-contract.json"),
                "discovery_snapshot_sha256": discovery_snapshot, "cases": cases,
                "factor_admission_trials": 0, "oos_reads": 0, "gold_writes": 0,
                "oos_reads_definition": "No sealed diagnostics/outputs queried or disclosed; trusted source load/hash precedes scoping."}
    manifest["manifest_sha256"] = audit.digest(manifest)
    _write_json(output / "manifest.json", manifest)
    return manifest


class _ReadOnlySession(RealDiagnosticSession):
    """Archived event reader. Never initialize a DB or revalidate against new code."""

    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        events = self.events()  # Original chained audit hashes remain mandatory.
        contract = events[0]["contract"]
        if (contract.get("version") != "real-explanatory-diagnostic-session-v1"
                or contract.get("mode") != "REAL_DISCOVERY_REANALYSIS"):
            raise ValueError("Unsupported archived diagnostic session schema")
        if self._state(events)["state"] != "STOPPED":
            raise ValueError("Read-only archive export requires an already STOPPED session")

    def _connect(self):
        return sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)

    def _deny(self, *args, **kwargs):
        raise ValueError("Read-only archive permits closed export only")

    packet = request = submit = run = _deny


class PilotBroker:
    """Host filesystem broker. Expose packet/act, not files, to an investigator."""

    def __init__(self, root, *, read_only=False):
        if type(read_only) is not bool:
            raise ValueError("read_only must be an explicit Boolean")
        self.read_only = read_only
        self.root = Path(root).resolve()
        self.manifest = _read_json(self.root / "manifest.json")
        body = deepcopy(self.manifest)
        if body.pop("manifest_sha256", None) != audit.digest(body) or body.get("schema_version") != VERSION:
            raise ValueError("Pilot manifest hash/schema mismatch")
        self.frozen = _read_json(self.root / "frozen-plan.json")
        if (_sha_file(self.root / "frozen-plan.json") != body["frozen_plan_file_sha256"]
                or _sha_file(self.root / "regime-contract.json") != body["regime_contract_file_sha256"]):
            raise ValueError("Frozen input contract changed")
        if not self.read_only and self.frozen["code_sha256"] != _code_bindings():
            raise ValueError("Frozen diagnostic code changed; create a separately identified reanalysis")
        self.cases = {case["case_id"]: case for case in self.manifest["cases"]}
        if list(self.cases) != list(SELECTED):
            raise ValueError("Pilot exact set mismatch")
        if self.read_only:
            for case_id in self.cases:
                self._verified_case_contract(case_id)

    def _writable(self):
        if self.read_only:
            raise ValueError("Read-only archive permits closed export only")

    def _case(self, case_id):
        if case_id not in self.cases:
            raise ValueError("Unknown frozen case")
        return self.cases[case_id]

    def _path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Path escapes frozen pilot")
        return path

    def _verified_case_contract(self, case_id):
        case = self._case(case_id)
        paths = {kind: self._path(case[f"{kind}_file"]) for kind in ("frame", "contract")}
        if any(_sha_file(path) != case[f"{kind}_file_sha256"] for kind, path in paths.items()):
            raise ValueError("Frozen case bytes changed")
        contract = _read_json(paths["contract"])
        if audit.digest(contract) != case["data_contract_sha256"]:
            raise ValueError("Data contract digest changed")
        return paths, contract

    def _lab(self, case_id):
        self._writable()
        paths, contract = self._verified_case_contract(case_id)
        return RealDiagnosticLab(pd.read_parquet(paths["frame"]), contract)

    def _session_path(self, case_id, arm):
        self._case(case_id)
        if arm not in {"FIXED_REFERENCE", "HOST_LLM"}:
            raise ValueError("Unknown comparison arm")
        return self._path(f"sessions/{arm}/{case_id}.sqlite")

    def init_session(self, case_id, arm):
        self._writable()
        case = self._case(case_id)
        lab = self._lab(case_id)
        contract = session_contract(lab.public_case(), CATALOG, planner_kind=arm,
            required_diagnostics=case["required_diagnostics"],
            data_contract_sha256=case["data_contract_sha256"], max_cost_units=18, max_actions=12)
        session = RealDiagnosticSession(self._session_path(case_id, arm), contract)
        return session.packet()

    def _session(self, case_id, arm):
        session_class = _ReadOnlySession if self.read_only else RealDiagnosticSession
        session = session_class(self._session_path(case_id, arm))
        contract = session.events()[0]["contract"]
        case = self._case(case_id)
        if (contract["data_contract_sha256"] != case["data_contract_sha256"]
                or contract["planner_kind"] != arm
                or contract["required_diagnostics"] != case["required_diagnostics"]
                or (not self.read_only and contract["catalog"] != CATALOG)
                or (self.read_only and contract["catalog"] != contract["public_case"]["diagnostics"])
                or (self.read_only and set(contract["catalog"]) != set(self.frozen["fixed_order"]))
                or contract["max_cost_units"] != 18 or contract["max_actions"] != 12):
            raise ValueError("Session does not belong to frozen case")
        return session

    def packet(self, case_id, arm):
        self._writable()
        return self._session(case_id, arm).request()

    def act(self, case_id, arm, action, *, request_id, expected_revision):
        self._writable()
        return self._session(case_id, arm).submit(action, request_id=request_id,
            expected_revision=expected_revision, execute=self._lab(case_id).run)

    def export(self, case_id, arm):
        if self.read_only:
            self._verified_case_contract(case_id)
        result = self._session(case_id, arm).export()
        result.update(case_id=case_id, arm=arm, pilot_manifest_sha256=self.manifest["manifest_sha256"],
                      live_model_interpretation_certified=False)
        return result

    def collect_fixed(self, case_id):
        """Collect every registered diagnostic in frozen order; NEVER author a lesson."""
        self._writable()
        path = self._session_path(case_id, "FIXED_REFERENCE")
        if not path.exists():
            self.init_session(case_id, "FIXED_REFERENCE")
        lab = self._lab(case_id)
        session = self._session(case_id, "FIXED_REFERENCE")
        for diagnostic in FIXED_ORDER:
            packet = session.packet()
            completed = {item["diagnostic_id"] for item in packet["state"]["evidence"]}
            if diagnostic in completed:
                continue
            if packet["state"]["state"] != "ACTIVE":
                raise ValueError("Fixed session needs explicit reconciliation")
            packet = session.request()
            action = {"kind": "TEST", "reason": "사전에 동결한 비교 기준선의 진단 순서입니다.",
                "evidence_ids": [item["evidence_id"] for item in packet["state"]["evidence"]],
                "payload": {"diagnostic_id": diagnostic,
                    "rivals": [{"explanation": "주장과 부합하는 관계가 관측될 수 있다.", "expected_if_true": "해당 진단의 필요한 관측이 자료와 함께 반환된다."},
                               {"explanation": "대안 설명 또는 자료 부족으로 결론을 제한해야 할 수 있다.", "expected_if_true": "약화된 관계, 불확실성 또는 미수집 상태가 반환된다."}],
                    "changes_mind_if": "반환된 실제 증거와 미확인 상태에 따라 이후 해석자가 판단하며, 여기서는 자동 결론을 만들지 않는다."}}
            receipt = session.submit(action, request_id=f"fixed-{diagnostic}",
                expected_revision=packet["state"]["revision"], execute=lab.run)
            if receipt.get("status") != "OBSERVED":
                raise ValueError(f"Fixed diagnostic did not complete: {receipt.get('status')}")
        result = session.packet()
        result["collection_status"] = "FIXED_COLLECTION_COMPLETE_AWAITING_INDEPENDENT_LLM_INTERPRETATION"
        return result
