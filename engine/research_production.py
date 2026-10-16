"""Same-run production Discovery handoff to bounded host-driven v2 diagnostics.

Admission, OOS and Gold are unchanged. A pending interpretation is never labeled
reviewed. Immutable handoffs permit diagnostics to resume without rerunning a
factor. The host supplies actual investigator and independent critic decisions.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile

import pandas as pd

from engine.adaptive_research import digest
from engine.research_real_diagnostics import CATALOG, RealDiagnosticLab
from engine.research_real_runtime import RealDiagnosticSession, make_contract

VERSION = "production-research-v2-v1"
ROOT = Path(__file__).resolve().parents[1]
TERMINAL_STATUSES = {"STOPPED", "DATA_REQUESTED_NOT_ACQUIRED", "NEW_TEST_PENDING_REVIEW"}


def _production_context(manifest):
    return {"campaign_id": manifest["campaign_id"], "factor": manifest["factor"],
            "readiness": deepcopy(manifest["readiness"]),
            "input_history": deepcopy(manifest["input_history"]),
            "input_profiles": deepcopy(manifest.get("input_profiles", {})),
            "note": "Same-run explanatory diagnostics; admission/OOS handled only by the separate production gate."}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if path.exists():
        if path.read_text() != body:
            raise ValueError(f"Immutable artifact differs: {path}")
    else:
        with path.open("x") as stream:
            stream.write(body)
    return sha(path)


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("Unsafe research identifier")
    return value


def code_bindings():
    names = ("research_production.py", "research_production_evidence.py",
             "research_regime_production.py", "research_real_diagnostics.py",
             "research_real_runtime.py", "adaptive_research.py", "gate.py",
             "research_memory_transfer.py", "research_memory_v2.py", "epochs.py")
    return {**{name: sha(ROOT / "engine" / name) for name in names},
            "scripts/run.py": sha(ROOT / "scripts/run.py"),
            "scripts/research.py": sha(ROOT / "scripts/research.py")}


def freeze_campaign(policy, *, window, macro_context=None, repo_root=ROOT):
    """Called before campaign creation, never attached to an existing campaign."""
    from engine.research_regime_production import freeze_regime_context
    if (policy.get("version") != VERSION or policy.get("enabled") is not True
            or policy.get("automatic_gold_publication") is not False
            or policy.get("legacy_campaign_migration") is not False
            or policy.get("graph_retrieval") is not False
            or policy.get("utility_ranking_weight") != 0):
        raise ValueError("Unsupported production diagnostic policy")
    if policy.get("max_cost_units") != 18 or policy.get("max_actions") != 12:
        raise ValueError("Unreviewed diagnostic budget")
    regime_path = Path(repo_root) / policy["regime_source"]
    now = datetime.now(timezone.utc).isoformat()
    from engine.gate import RESEARCH_START
    regime = freeze_regime_context(read(regime_path), signal_start=str(RESEARCH_START),
        data_cutoff=str(window.discovery_data_cutoff), oos_start=str(window.oos_signal_start),
        frozen_at=now, macro_context=macro_context)
    value = {"version": VERSION, "policy": deepcopy(policy), "frozen_at": now,
             "regime": regime, "source_regime_file_sha256": sha(regime_path),
             "code_sha256": code_bindings(), "gate_changed": False,
             "automatic_interpretation_claim": False, "legacy_memory_imported": False}
    value["sha256"] = digest(value)
    return value


def validate_campaign(config, *, require_live_code=False):
    if config is None:
        return None
    body = deepcopy(config)
    expected = body.pop("sha256", None)
    if body.get("version") != VERSION or expected != digest(body):
        raise ValueError("Production diagnostic configuration changed")
    from engine.research_regime_production import validate_frozen_context
    validate_frozen_context(body["regime"])
    if require_live_code and body["code_sha256"] != code_bindings():
        raise ValueError("Diagnostic code changed since campaign freeze; stop before candidate evaluation")
    return expected


def target_scope(campaign, strategy_sha256):
    config = campaign["research_v2"]
    validate_campaign(config)
    from engine.gate import RESEARCH_START
    return {"market": "KOSPI_KOSDAQ", "universe": "FROZEN_INVESTABLE_KRX_COMMON_STOCKS",
            "period": f"{RESEARCH_START}/{campaign['discovery']['signal_end']}",
            "horizon": "ONE_MONTH_RETURN", "data_snapshot": campaign["snapshot"]["discovery_input_digest"],
            "feature_definition": strategy_sha256,
            "pit_policy": "POLICY_BOUND_FEATURES_AND_PIT_ASSUMED_REGIME", "protocol_version": VERSION,
            "regime_definition": digest(config["regime"]),
            "cost_model": "EXISTING_GATE_SEPARATE_EXECUTION_DIAGNOSTICS",
            "information_lag": "CERTIFIED_FEATURE_KNOWN_AT", "task_class": "NEW_SINGLE_FACTOR_RESEARCH"}


def freeze_candidate_plans(campaign, factors, specs, *, memory_bindings, epoch_id, strategy_digests, repo_root=ROOT):
    from engine.research_production_evidence import validate_diagnostic_plan
    from engine.research_memory_transfer import require_campaign_memory_usage
    from engine.research_regime_production import macro_catalog
    validate_campaign(campaign["research_v2"], require_live_code=True)
    macro = macro_catalog(campaign["research_v2"]["regime"])
    plans = {}
    for factor in factors:
        spec = specs[factor.name]
        if spec["strategy_sha256"] != strategy_digests.get(factor.name):
            raise ValueError("Diagnostic spec differs from candidate source SHA")
        plan = validate_diagnostic_plan(deepcopy(spec.get("diagnostic_plan", {})))
        for axis in plan["macro_axes"]:
            if axis not in macro or not set(plan["macro_contrasts"][axis]).issubset(macro[axis]["states"]):
                raise ValueError("Preregistered macro axis/contrast is not in the frozen source")
        binding = memory_bindings.get(factor.name)
        if not binding:
            raise ValueError("Explicit v2 memory usage or audited empty retrieval required")
        context_path = Path(binding["context_path"])
        if sha(context_path) != binding["context_file_sha256"]:
            raise ValueError("Frozen memory context file changed")
        checked = require_campaign_memory_usage(Path(repo_root) / campaign["research_v2"]["policy"]["memory_pointer"],
            read(context_path), expected_scope=target_scope(campaign, spec["strategy_sha256"]),
            task_id=f"{campaign['campaign_id']}/{_id(epoch_id)}/{factor.name}", repo_root=repo_root)
        if any(binding.get(key) != value for key, value in checked.items()):
            raise ValueError("Memory binding does not match its audited usage")
        plans[factor.name] = {"diagnostic_plan": plan, "strategy_sha256": spec["strategy_sha256"],
                              "definition_hash": factor.definition_hash, "memory": binding}
    return plans


def prepare_memory_bindings(root, campaign, epoch_id, factors, specs, *, repo_root=ROOT):
    """An empty retrieval can be acknowledged mechanically; nonempty needs the host."""
    from engine.research_memory_transfer import prepare_campaign_context, record_campaign_usage, require_campaign_memory_usage
    pointer = Path(repo_root) / campaign["research_v2"]["policy"]["memory_pointer"]
    bindings = {}
    for factor in factors:
        task = f"{campaign['campaign_id']}/{_id(epoch_id)}/{factor.name}"
        path = Path(root) / "campaigns" / _id(campaign["campaign_id"]) / "v2" / "context" / f"{_id(epoch_id)}--{_id(factor.name)}.json"
        scope = target_scope(campaign, specs[factor.name]["strategy_sha256"])
        if path.exists():
            context = read(path)
        else:
            context = prepare_campaign_context(pointer, target_scope=scope, task_id=task,
                query=f"{factor.name} {factor.exploration_domain} 측정 통제 경제적 경로 미확인",
                research_as_of=datetime.now(timezone.utc).isoformat(), repo_root=repo_root)
            write(path, context)
        if not context["context"]:
            record_campaign_usage(pointer, context, used={}, rejected={}, actor=task,
                key=f"empty-context:{context['context_sha256']}", repo_root=repo_root)
        binding = require_campaign_memory_usage(pointer, context, expected_scope=scope, task_id=task, repo_root=repo_root)
        bindings[factor.name] = {**binding, "context_path": str(path), "context_file_sha256": sha(path)}
    return bindings


def handoff(root, campaign, epoch, panel, frame, factor, result):
    """Persist only the already-computed, bounded Discovery projection."""
    from engine.research_production_evidence import prepare_discovery_evidence
    from engine.research_regime_production import project_regime_context
    config = campaign.get("research_v2")
    if config is None:
        return {"status": "LEGACY_PATH_UNCHANGED"}
    config_sha = validate_campaign(config)
    if config["code_sha256"] != code_bindings():
        raise ValueError("Diagnostic code changed since campaign freeze")
    if epoch.get("research_v2_sha256") != config_sha:
        raise ValueError("Epoch is not bound to v2 campaign policy")
    candidate = epoch["research_v2_plans"][factor.name]
    if candidate["definition_hash"] != factor.definition_hash:
        raise ValueError("Frozen candidate definition changed")
    destination = Path(root) / "campaigns" / _id(campaign["campaign_id"]) / "v2" / _id(epoch["epoch_id"]) / _id(factor.name)
    if destination.exists():
        # Exact prior handoff may be reused only if all bindings still match.
        broker = ProductionBroker(destination)
        if (broker.manifest["candidate"] != candidate or broker.manifest["campaign_sha256"] != config_sha):
            raise ValueError("Existing handoff belongs to a different frozen candidate")
        return broker.initialize()
    prepared = prepare_discovery_evidence(panel, frame, factor, result, campaign,
        {"diagnostic_plan": candidate["diagnostic_plan"], "strategy_sha256": candidate["strategy_sha256"]},
        regime_projection=lambda view: project_regime_context(view, config["regime"],
            macro_axes=candidate["diagnostic_plan"].get("macro_axes", [])))
    if prepared["status"] != "PREPARED":
        return {key: value for key, value in prepared.items() if key not in {"frame", "contract"}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Incomplete attempts remain recoverable siblings, never masquerade as a
    # completed handoff. Only a fully verified bundle is renamed into place.
    staging = Path(tempfile.mkdtemp(prefix=f".{factor.name}-preparing-", dir=destination.parent))
    def save_lab(name, data):
        folder = staging / name
        folder.mkdir(parents=True)
        data["frame"].to_parquet(folder / "frame.parquet", index=False)
        RealDiagnosticLab(pd.read_parquet(folder / "frame.parquet"), data["contract"])
        return {"frame": f"{name}/frame.parquet", "frame_sha256": sha(folder / "frame.parquet"),
                "contract": f"{name}/contract.json", "contract_sha256": write(folder / "contract.json", data["contract"])}
    primary = save_lab("primary", prepared)
    children = {group: {key: save_lab(f"{group}/{_id(key)}", item) for key, item in prepared.get(group, {}).items()}
                for group in ("regime_labs", "macro_labs")}
    manifest = {"version": VERSION, "campaign_id": campaign["campaign_id"], "epoch_id": epoch["epoch_id"],
                "factor": factor.name, "candidate": candidate, "campaign_sha256": config_sha,
                "primary": primary, **children, "required_diagnostics": prepared["required_diagnostics"],
                "readiness": prepared["readiness"], "input_history": prepared["input_history"],
                "input_profiles": prepared.get("input_profiles", {}),
                "review_scope": target_scope(campaign, candidate["strategy_sha256"]),
                "code_sha256": code_bindings(), "data_contract_sha256": digest(prepared["contract"]),
                "new_factor_evaluations": 0, "oos_reads": 0, "gold_writes": 0}
    # The ENTIRE planner-visible context belongs to the original contract and
    # PROMPT hash; do not append unaudited fields after session.request().
    public_case = RealDiagnosticLab(prepared["frame"], prepared["contract"]).public_case()
    public_case["production_context"] = _production_context(manifest)
    manifest["session_contract"] = make_contract(public_case, CATALOG, planner_kind="HOST_LLM",
        required_diagnostics=manifest["required_diagnostics"],
        data_contract_sha256=manifest["data_contract_sha256"], max_cost_units=18, max_actions=12)
    manifest["session_contract_sha256"] = digest(manifest["session_contract"])
    manifest["sha256"] = digest(manifest)
    write(staging / "manifest.json", manifest)
    staging.rename(destination)
    broker = ProductionBroker(destination)
    broker.initialize()
    return broker.receipt()


class _ReadOnlyProductionSession(RealDiagnosticSession):
    """Read the original event chain without executing current diagnostic code.

    Active status/export is permitted for the host, not as a public lesson.
    The broker separately authenticates the original frozen session contract.
    No constructor initialization, writable SQLite connection, or action exists.
    """

    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        contract = self.events()[0]["contract"]
        if (contract.get("version") != "real-explanatory-diagnostic-session-v1"
                or contract.get("mode") != "REAL_DISCOVERY_REANALYSIS"):
            raise ValueError("Unsupported original diagnostic session schema")

    def _connect(self):
        return sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)

    def _deny(self, *args, **kwargs):
        raise ValueError("Read-only production archive cannot execute or change sessions")

    packet = request = submit = run = _deny

    def export(self):
        value = super().export()
        original = value["events"][0]["contract"]
        value.update(version=original["version"], mode=original["mode"])
        return value


class ProductionBroker:
    def __init__(self, path, *, read_only=False):
        if type(read_only) is not bool:
            raise ValueError("read_only must be an explicit Boolean")
        self.read_only = read_only
        self.root = Path(path).resolve()
        self.manifest = read(self.root / "manifest.json")
        body = deepcopy(self.manifest)
        supported_versions = {"production-research-v2-v1"} if self.read_only else {VERSION}
        if body.pop("sha256", None) != digest(body) or body.get("version") not in supported_versions:
            raise ValueError("Production handoff manifest changed")
        if not self.read_only and self.manifest["code_sha256"] != code_bindings():
            raise ValueError("Diagnostic code changed; existing results remain immutable")
        contract = self.manifest["session_contract"]
        if (digest(contract) != self.manifest["session_contract_sha256"]
                or contract["data_contract_sha256"] != self.manifest["data_contract_sha256"]
                or contract["public_case"]["contract_sha256"] != self.manifest["data_contract_sha256"]
                or contract["required_diagnostics"] != self.manifest["required_diagnostics"]
                or contract["public_case"].get("production_context") != _production_context(self.manifest)
                or contract["planner_kind"] != "HOST_LLM"
                or contract["catalog"] != contract["public_case"]["diagnostics"]
                or contract["max_cost_units"] != 18 or contract["max_actions"] != 12
                or any(contract.get(key) is not False for key in
                       ("factor_approval_allowed", "gold_write_allowed", "causal_claim_allowed"))):
            raise ValueError("Frozen session contract is not bound to production handoff")
        if self.read_only:
            self._verify_sources()

    def _writable(self):
        if self.read_only:
            raise ValueError("Read-only production archive cannot execute or change sessions")

    def _path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Frozen evidence path escaped handoff")
        return path

    def _verified_binding(self, binding):
        paths = {kind: self._path(binding[kind]) for kind in ("frame", "contract")}
        if any(sha(path) != binding[f"{kind}_sha256"] for kind, path in paths.items()):
            raise ValueError("Frozen evidence file changed")
        return paths, read(paths["contract"])

    def _verify_sources(self):
        # Byte authentication only: an archive never loads a DataFrame or lab.
        _, primary = self._verified_binding(self.manifest["primary"])
        if digest(primary) != self.manifest["data_contract_sha256"]:
            raise ValueError("Frozen primary contract changed")
        for group in ("regime_labs", "macro_labs"):
            for binding in self.manifest[group].values():
                self._verified_binding(binding)

    def _lab(self, binding):
        self._writable()
        paths, contract = self._verified_binding(binding)
        return RealDiagnosticLab(pd.read_parquet(paths["frame"]), contract)

    def initialize(self):
        self._writable()
        path = self._path("session.sqlite")
        if not path.exists():
            self._verify_sources()
            RealDiagnosticSession(path, self.manifest["session_contract"])
        return self.receipt()

    def session(self):
        session_class = _ReadOnlyProductionSession if self.read_only else RealDiagnosticSession
        session = session_class(self._path("session.sqlite"))
        events = session.events()
        contract = events[0]["contract"]
        if contract != self.manifest["session_contract"]:
            raise ValueError("Cross-candidate diagnostic session")
        for event in events:
            if event["type"] == "PROMPT":
                packet = event["packet"]
                if (digest(packet) != event["packet_sha256"]
                        or packet["contract_sha256"] != self.manifest["session_contract_sha256"]
                        or packet["public_case"] != contract["public_case"]):
                    raise ValueError("Original delivered packet audit mismatch")
            if "evidence" in event:
                evidence = event["evidence"]
                response = evidence["response"]
                if (evidence["response_sha256"] != digest(response)
                        or response.get("evidence_scope", {}).get("contract_sha256") != self.manifest["data_contract_sha256"]
                        or response.get("scope") != "FROZEN_DISCOVERY_ONLY"
                        or response.get("causal_identification") is not False):
                    raise ValueError("Original evidence is not bound to frozen Discovery")
        return session

    def run(self, diagnostic_id):
        self._writable()
        primary = self._lab(self.manifest["primary"])
        if diagnostic_id != "regime_interaction":
            return primary.run(diagnostic_id)
        result = primary.run(diagnostic_id)
        reports = {group: {key: self._lab(binding).run("regime_interaction") for key, binding in self.manifest[group].items()}
                   for group in ("regime_labs", "macro_labs")}
        flat = [report for items in reports.values() for report in items.values()]
        if flat:
            for report in flat:
                interaction = report.get("metrics", {}).get("interaction", {})
                if interaction.get("status", "").startswith("INSUFFICIENT"):
                    report["status"] = "INSUFFICIENT_SUPPORT"
            # Every requested stratum counts. Preserve partial estimates, but
            # never let one supported market conceal another unsupported one.
            result["status"] = "COMPUTED" if all(r["status"] == "COMPUTED" for r in flat) else "NOT_COMPUTED" if all(r["status"] == "NOT_COMPUTED" for r in flat) else "INSUFFICIENT_SUPPORT"
            result["metrics"] = {"stratified_markets": reports["regime_labs"], "prespecified_macro_axes": reports["macro_labs"],
                                  "pooled_market_regime_estimate": False,
                                  "status_by_stratum": {f"{group}:{name}": r["status"] for group, items in reports.items() for name, r in items.items()}}
            result["missing_datasets"] = sorted({d for r in flat for d in r.get("missing_datasets", [])})
            result["limitations"] = list(dict.fromkeys(result.get("limitations", []) + [
                "Separate market strata and predeclared macro axes, not independent experiments or a search for the best regime.",
                "Child statuses and support counts remain authoritative; aggregate COMPUTED does not mean every stratum is supported."]))
        return result

    def packet(self):
        self._writable()
        return self.session().request()

    def act(self, action, *, request_id, expected_revision):
        self._writable()
        return self.session().submit(action, request_id=request_id, expected_revision=expected_revision, execute=self.run)

    def export(self):
        self._verify_sources()
        return self.session().export()

    def status(self):
        self._verify_sources()
        session = self.session()
        state = session._state(session.events())
        return {**self.receipt(), "session_state": state["state"], "revision": state["revision"],
                "terminal_status": state["terminal"]["status"] if state["terminal"] else None,
                "evidence_count": len(state["evidence"]), "cost_units_used": state["cost_units_used"]}

    def receipt(self):
        return {"status": "READY_FOR_HOST_DIAGNOSTICS", "path": str(self.root),
                "manifest_sha256": self.manifest["sha256"], "new_factor_evaluations": 0,
                "oos_reads": 0, "gold_writes": 0, "reviewed_lesson": False}


def prepare_review(path, output, *, research_root="research"):
    """One closed campaign/candidate -> same independent critic release schema."""
    from engine import epochs
    from engine.research_v2_release import VERSION as RELEASE_VERSION, draft_template
    broker = ProductionBroker(path, read_only=True)
    manifest = broker.manifest
    campaign = epochs.load_campaign(research_root, manifest["campaign_id"])
    if campaign["status"] not in {"REVEALED", "CLOSED_NO_QUALIFIED"}:
        raise ValueError("Qualitative memory release waits for final campaign disposition")
    # Authenticate the original campaign copy without applying new code/rules.
    config = deepcopy(campaign["research_v2"])
    campaign_sha = config.pop("sha256", None)
    if campaign_sha != digest(config) or campaign_sha != manifest["campaign_sha256"]:
        raise ValueError("Review campaign does not match the original frozen handoff")
    export = broker.export()
    if export["state"]["state"] != "STOPPED":
        raise ValueError("Actual host interpretation must close the diagnostic session")
    cid = "--".join((manifest["campaign_id"], manifest["epoch_id"], manifest["factor"]))
    terminal = [index for index, event in enumerate(export["events"]) if event.get("status") in TERMINAL_STATUSES]
    if not terminal:
        raise ValueError("Explicit investigator terminal decision missing")
    if not export["state"]["evidence"]:
        raise ValueError("A proposal without observed evidence is not a reviewable lesson")
    decision = export["events"][terminal[-1]]
    complete = decision["status"] == "STOPPED" and export.get("explanation_complete", False)
    source = {"terminal_prefix_sha256": digest(export["events"][:terminal[-1] + 1]),
              "reports": export["state"]["evidence"], "terminal_event": decision,
              "terminal_status": decision["status"], "explanation_complete": complete,
              "unperformed_required_diagnostics": export.get("unperformed_required_diagnostics", []),
              "production_context": deepcopy(manifest["session_contract"]["public_case"]["production_context"]),
              "campaign_status": campaign["status"], "source_handoff_sha256": manifest["sha256"],
              "readiness": manifest["readiness"], "oos_results_included": False}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    relative = f"sources/{cid}/HOST_LLM.json"
    source_sha = write(output / relative, source)
    root_id = "production-root-" + manifest["data_contract_sha256"]
    evidence = {}
    for item in source["reports"]:
        if item["response_sha256"] != digest(item["response"]):
            raise ValueError("Evidence hash changed")
        eid = f"{cid}/{item['diagnostic_id']}/{item['response_sha256'][:20]}"
        evidence[eid] = {"evidence_id": eid, "case_id": cid, "root_id": root_id,
                         "report": item["response"], "source_arms": ["HOST_LLM"]}
    case = {"case_id": cid, "root_id": root_id, "scope": deepcopy(manifest["review_scope"]),
            "sources": [{"path": relative, "sha256": source_sha, "terminal_prefix_sha256": source["terminal_prefix_sha256"], "arm": "HOST_LLM"}],
            "source_statuses": {eid: row["report"]["status"] for eid, row in evidence.items()},
            "unperformed_diagnostics": {"HOST_LLM": export.get("unperformed_required_diagnostics", [])},
            "evidence_ids": sorted(evidence)}
    bundle = {"schema_version": RELEASE_VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
              "audience": "CLOSED_DISCOVERY_REVIEWER_ONLY", "cases": {cid: case}, "evidence": evidence,
              "source_kind": VERSION, "release_mode": "PRODUCTION_DISCOVERY", "research_time_distinct_from_market_time": True,
              "isolation_level": "LOGICAL_ONLY", "independent_oos_claim": False,
              "new_factor_approval": False, "same_case_arms_are_independent_evidence": False}
    bundle["bundle_sha256"] = digest(bundle)
    write(output / "review-bundle.json", bundle)
    write(output / "templates" / f"{cid}.json", draft_template(bundle, cid))
    return {"status": "AWAITING_ACTUAL_ANALYST_AND_INDEPENDENT_CRITIC", "release_root": str(output), "case_id": cid,
            "terminal_status": decision["status"], "explanation_complete": complete,
            "unperformed_required_diagnostics": export.get("unperformed_required_diagnostics", [])}
