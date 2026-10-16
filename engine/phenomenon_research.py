"""Append-only phenomenon research graph and bounded deterministic experiments.

Public API: ``GraphStore(root, actors=...)`` initializes an immutable local actor
policy. ``append_node(kind, payload, actor=..., role=..., known_at=...)`` accepts
proposed question/hypothesis/prediction/argument, source/data_requirement, study
and test_plan nodes. ``append_edge`` records typed relations. ``register_study``,
``choose_next_test`` and ``execute_test`` implement a bounded adaptive workflow;
``review_claim`` requires an independent reviewer. ``snapshot(claim_ids,
as_of=...)``, ``validate_snapshot`` and ``create_strategy`` bind strategy design
to reviewed, scoped knowledge. ``invalidate``/``supersede`` retain history while
blocking dependent records. ``records``, ``get`` and ``validate`` verify hashes,
the append chain, roles, contracts and graph references on every read.
``packet(study_id)`` exposes a bounded decision context and ``stop_study`` records
an explicit terminal decision without turning a stopped study into a finding.
``search_claims(query, as_of=..., universe=None, limit=10,
include_synthetic=False)`` retrieves active reviewed knowledge with complete
counterevidence context; lexical matching never ranks by observed returns.

Minimum input contracts are demonstrated in tests/test_phenomenon_research.py.
Sources bind a canonical SHA256 of the complete supplied row list, explicit
columns, split, universe, period, provenance and PIT policy. Each row has an
observation_at, decision_at, feature_known_at and outcome_known_at (aware ISO
timestamps), plus the declared numeric/group fields. Input availability must
precede the decision; outcome availability must precede the research cutoff.
The feature and outcome timestamps are NEVER interchangeable. Source/PIT
attestations require an upstream certified adapter: this module validates their
consistency, not their truth, and performs no remote data or Gold access.

Only coverage, mean_difference and correlation are executable. Outputs are
descriptive observations, not p-values, causal conclusions or automatic market
confirmation. Adaptive test priorities are declared decision heuristics, not
estimated information gain. Synthetic evidence remains SOFTWARE_TEST_ONLY.
Confirmation requires an explicit separately bound exposure/protocol contract;
claim review cannot promote exploratory evidence into confirmation. Strategies
are research specifications, never publication/trade authorization.

The filesystem/actor registry is a trusted local application boundary, not an
authentication service. Content addressing detects accidental/tampered bytes
against retained records/snapshots, not a privileged attacker rewriting every
record and external checkpoint. Keep snapshot digests outside this directory
for truncation detection. POSIX flock serializes writers; successful runs consume
budget even if a crash prevents writing their companion evidence node.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Mapping, Sequence


SCHEMA = "phenomenon-research-v1"
ROLES = frozenset({"researcher", "executor", "reviewer", "strategist", "curator"})
PROPOSED = frozenset({"question", "hypothesis", "prediction", "argument", "data_requirement", "study", "test_plan"})
KINDS = PROPOSED | {"source", "test_run", "evidence", "claim", "strategy"}
OPERATORS = frozenset({"coverage", "mean_difference", "correlation"})
STAGES = frozenset({"EXPLORATORY", "CONFIRMATION"})
SHA = re.compile(r"[a-f0-9]{64}\Z")
TIME_FIELDS = {"observation_at", "decision_at", "feature_known_at", "outcome_known_at"}
MAX_SEARCH_CONTEXT_NODES = 2000


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value, label):
    _require(isinstance(value, str) and value.strip(), f"Nonempty {label} required")
    return value


def _time(value):
    _require(isinstance(value, str), "Aware ISO timestamp required")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Aware ISO timestamp required") from error
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "Aware ISO timestamp required")
    return parsed


def _sha(value, label="SHA256"):
    _require(isinstance(value, str) and SHA.fullmatch(value), f"Invalid {label}")
    return value


def _strings(values, label, *, minimum=1):
    _require(isinstance(values, list) and len(values) >= minimum and all(isinstance(x, str) and x.strip() for x in values), f"{label} must be a nonempty string list")
    _require(len(set(values)) == len(values), f"Duplicate {label}")
    return values


def _number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def _scope(value):
    _require(isinstance(value, dict), "Explicit scope required")
    _text(value.get("universe"), "scope universe")
    _require(_time(value["start"]) <= _time(value["end"]), "Reversed scope period")


def _immutable(path: Path, value):
    raw = canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class GraphStore:
    """An isolated, no-fallback graph. Existing actor policy cannot be replaced."""

    def __init__(self, root, *, actors: Mapping[str, Sequence[str]] | None = None):
        self.root = Path(root).absolute()
        _require(".." not in self.root.parts and not any(x.is_symlink() for x in (self.root, *self.root.parents)), "Symlink/traversal graph root rejected")
        self.root.mkdir(parents=True, exist_ok=True)
        self.log = self.root / "records"
        _require(not self.log.is_symlink(), "Symlink records rejected")
        self.log.mkdir(exist_ok=True)
        with self._locked():
            records = self._load()
            if not records:
                _require(bool(actors), "Explicit actors required for a new graph")
                policy = {name: sorted(set(roles)) for name, roles in actors.items()}
                _require(all(isinstance(name, str) and name.strip() and roles and set(roles) <= ROLES for name, roles in policy.items()), "Invalid actor role policy")
                body = {"schema": SCHEMA, "seq": 0, "previous": None, "type": "policy", "kind": "actors", "payload": policy,
                        "actor": None, "role": None, "known_at": None, "dependencies": []}
                self._write(body)
            elif actors is not None:
                _require(records[0]["payload"] == {name: sorted(set(roles)) for name, roles in actors.items()}, "Immutable actor policy differs")

    @contextmanager
    def _locked(self):
        path = self.root / ".writer.lock"
        _require(not path.is_symlink(), "Symlink writer lock rejected")
        with path.open("a+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def _write(self, body):
        record = {**body, "id": digest(body)}
        path = self.log / f"{body['seq']:08d}-{record['id']}.json"
        _immutable(path, record)
        return record

    def _load(self):
        records = []
        for path in sorted(self.log.iterdir()):
            _require(path.is_file() and not path.is_symlink() and re.fullmatch(r"\d{8}-[a-f0-9]{64}\.json", path.name), "Unexpected graph record path")
            try:
                record = json.loads(path.read_bytes())
                body = {k: v for k, v in record.items() if k != "id"}
                _require(record["id"] == digest(body) and path.name == f"{len(records):08d}-{record['id']}.json", "Graph hash/sequence tampering")
                _require(record["schema"] == SCHEMA and record["seq"] == len(records) and record["previous"] == (records[-1]["id"] if records else None), "Broken append chain")
                if not records:
                    _require(record["type"] == "policy" and record["kind"] == "actors" and record["payload"], "Missing actor policy")
                    _require(all(isinstance(k, str) and v and isinstance(v, list) and set(v) <= ROLES for k, v in record["payload"].items()), "Invalid actor policy")
                else:
                    self._validate_record(record, records)
                records.append(record)
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise ValueError(f"Malformed graph record: {path.name}") from error
        return records

    @staticmethod
    def _nodes(records):
        return {r["id"]: r for r in records if r["type"] == "node"}

    @staticmethod
    def _node(nodes, node_id, kinds=None):
        _require(node_id in nodes, "Missing node reference")
        record = nodes[node_id]
        _require(kinds is None or record["kind"] in kinds, "Wrong referenced node type")
        return record

    def records(self):
        with self._locked():
            return self._load()

    def get(self, node_id):
        return self._node(self._nodes(self.records()), node_id)

    def validate(self):
        records = self.records()
        return {"schema": SCHEMA, "record_count": len(records), "node_count": len(self._nodes(records)),
                "head": records[-1]["id"], "statuses": self._statuses(records), "publication_authorized": False}

    def _append(self, records, record_type, kind, payload, *, actor, role, known_at, dependencies=()):
        # JSON roundtrip prevents mutation of the caller's dictionaries after validation.
        body = json.loads(canonical({"schema": SCHEMA, "seq": len(records), "previous": records[-1]["id"],
                "type": record_type, "kind": kind, "payload": payload, "actor": actor, "role": role,
                "known_at": known_at, "dependencies": sorted(set(dependencies))}))
        try:
            self._validate_record(body, records)
        except (KeyError, TypeError) as error:
            raise ValueError(f"Malformed {kind} contract: {error}") from error
        record = self._write(body)
        records.append(record)
        return record

    def _refs(self, kind, p):
        refs = []
        for field in ("question_id", "hypothesis_id", "prediction_id", "study_id", "source_id", "plan_id", "run_id"):
            if field in p:
                refs.append(p[field])
        for field in ("hypothesis_ids", "premise_ids", "argument_ids", "requirement_ids", "source_ids", "claim_ids"):
            refs.extend(p.get(field, []))
        if kind == "claim":
            refs.extend(item["evidence_id"] for item in p.get("evidence_relations", []))
        if kind == "study":
            refs.extend(p.get("confirmation_contract", {}).get("allowed_source_ids", []))
        return refs

    def append_node(self, kind, payload, *, actor, role, known_at, dependencies=()):
        _require(kind in PROPOSED | {"source"}, "Observed/reviewed nodes require a checked helper")
        with self._locked():
            records = self._load()
            return self._append(records, "node", kind, payload, actor=actor, role=role, known_at=known_at,
                                dependencies=[*dependencies, *self._refs(kind, payload)])

    def _validate_record(self, record, previous):
        _require(record["role"] in previous[0]["payload"].get(record["actor"], []), "Actor is not authorized for role")
        when = _time(record["known_at"])
        if len(previous) > 1:
            _require(when >= _time(previous[-1]["known_at"]), "Research known_at cannot go backwards")
        nodes = self._nodes(previous)
        _require(isinstance(record["dependencies"], list) and len(set(record["dependencies"])) == len(record["dependencies"]), "Invalid dependencies")
        _require(all(ref in nodes for ref in record["dependencies"]), "Missing dependency or dependency cycle")
        kind, p, role = record["kind"], record["payload"], record["role"]
        _require(isinstance(p, dict), "Object payload required")
        if record["type"] == "node":
            _require(kind in KINDS, "Unknown node kind")
            expected = "researcher" if kind in PROPOSED else {"source": "curator", "test_run": "executor", "evidence": "executor", "claim": "reviewer", "strategy": "strategist"}[kind]
            _require(role == expected, "Invalid role for node")
            _require(set(self._refs(kind, p)) <= set(record["dependencies"]), "Missing semantic dependency")
            self._validate_node(kind, p, record, previous, nodes)
        elif record["type"] == "edge":
            self._validate_edge(kind, p, record, previous, nodes)
        elif record["type"] == "event":
            self._validate_event(kind, p, record, previous, nodes)
        else:
            raise ValueError("Unknown record type")

    def _validate_node(self, kind, p, record, previous, nodes):
        n = lambda ref, kinds=None: self._node(nodes, ref, kinds)
        if kind == "question":
            _text(p.get("title"), "question title")
            _text(p.get("question"), "question")
        elif kind == "hypothesis":
            n(p["question_id"], {"question"})
            _text(p.get("statement"), "hypothesis statement")
            _strings(p.get("alternatives"), "competing explanations")
        elif kind == "prediction":
            n(p["hypothesis_id"], {"hypothesis"})
            _text(p.get("statement"), "testable prediction")
            _text(p.get("observable"), "observable")
            _strings(p.get("assumptions"), "prediction assumptions")
        elif kind == "argument":
            _require(p.get("premise_mode") == "all", "Arguments must require ALL premises")
            _strings(p.get("premise_ids"), "premises")
            for ref in p["premise_ids"]:
                n(ref, {"hypothesis", "prediction", "evidence", "claim", "argument"})
            _require(p.get("inference_type") in {"DEDUCTION", "ABDUCTION", "INDUCTION"}, "Unknown inference type")
            _text(p.get("conclusion"), "proposed conclusion")
            _strings(p.get("assumptions"), "argument assumptions")
            _text(p.get("warrant"), "inference warrant")
            _require(p.get("epistemic_status") == "PROPOSED", "An argument is not empirical evidence")
        elif kind == "source":
            _text(p.get("source_ref"), "source reference")
            _text(p.get("data_version"), "source version")
            _sha(p.get("rows_sha256"), "source rows SHA256")
            _strings(p.get("data_root_ids"), "source dependency roots")
            _strings(p.get("columns"), "source columns")
            _require(TIME_FIELDS | {"row_id"} <= set(p["columns"]), "Missing PIT timestamp/identity columns")
            roles = p.get("field_roles", {})
            _require(isinstance(roles, dict) and set(roles) == set(p["columns"]) - TIME_FIELDS - {"row_id"} and set(roles.values()) <= {"FEATURE", "OUTCOME"}, "Explicit feature/outcome column roles required")
            _scope(p.get("scope"))
            _require(p.get("stage") in STAGES and p.get("origin") in {"SYNTHETIC", "OBSERVED"}, "Explicit source stage/origin required")
            _require(p.get("pit_policy") in {"VERIFIED", "PIT_ASSUMED"}, "Explicit source PIT policy required")
            _require(p.get("readiness") in {"READY", "PENDING"}, "Source readiness required")
        elif kind == "data_requirement":
            _text(p.get("question"), "missing-data question")
            _text(p.get("discriminates"), "explanations the data distinguishes")
            _require(p.get("status") in {"OPEN", "SATISFIED"}, "Data requirement status required")
            for ref in p.get("source_ids", []):
                n(ref, {"source"})
            if p["status"] == "SATISFIED":
                _require(p.get("source_ids") and all(n(x)["payload"]["readiness"] == "READY" for x in p["source_ids"]), "Satisfied requirement needs ready source")
        elif kind == "study":
            n(p["question_id"], {"question"})
            _strings(p.get("hypothesis_ids"), "study hypotheses", minimum=2)
            _require(all(n(ref, {"hypothesis"})["payload"]["question_id"] == p["question_id"] for ref in p["hypothesis_ids"]), "Study hypotheses must address the same question")
            _require(p.get("stage") in STAGES, "Explicit study stage required")
            _scope(p.get("scope"))
            _require(all(type(p.get(key)) is int and p[key] > 0 for key in ("max_runs", "max_rows")), "Positive study budgets required")
            _require(p.get("allowed_pit_policies") and set(p["allowed_pit_policies"]) <= {"VERIFIED", "PIT_ASSUMED"}, "PIT allowance required")
            if p["stage"] == "CONFIRMATION":
                contract = p.get("confirmation_contract", {})
                for key in ("protocol_sha256", "holdout_manifest_sha256", "exposure_ledger_sha256"):
                    _sha(contract.get(key), key)
                _require(_time(contract["registered_at"]) <= _time(record["known_at"]), "Confirmation registration is in the future")
                _require(contract.get("prior_exposure_disclosed") is True, "Confirmation requires prior-exposure disclosure")
                _strings(contract.get("allowed_source_ids"), "confirmation sources")
                roots = set()
                for ref in contract["allowed_source_ids"]:
                    source = n(ref, {"source"})["payload"]
                    _require(source["stage"] == "CONFIRMATION", "Confirmation source split mismatch")
                    roots.update(source["data_root_ids"])
                prior_evidence = [x for x in nodes.values() if x["kind"] == "evidence"]
                used_roots = {root for x in prior_evidence for root in x["payload"]["data_root_ids"]}
                used_digests = {nodes[nodes[x["payload"]["plan_id"]]["payload"]["source_id"]]["payload"]["rows_sha256"] for x in prior_evidence}
                source_digests = {nodes[ref]["payload"]["rows_sha256"] for ref in contract["allowed_source_ids"]}
                _require(not roots & used_roots and not source_digests & used_digests, "Confirmation data already exposed; root aliases do not reset exposure")
        elif kind == "test_plan":
            study = n(p["study_id"], {"study"})["payload"]
            _require(not self._stop_event(p["study_id"], previous), "Stopped study cannot register new test plans")
            prediction = n(p["prediction_id"], {"prediction"})["payload"]
            source = n(p["source_id"], {"source"})["payload"]
            _require(prediction["hypothesis_id"] in study["hypothesis_ids"], "Prediction does not belong to study")
            _require(p.get("operator") in OPERATORS, "Operator is not allowlisted")
            _require(p.get("stage") == study["stage"] == source["stage"], "Test stage/source split mismatch")
            _require(source["scope"] == study["scope"], "Source/study scope must be exactly bound")
            _require(source["pit_policy"] in study["allowed_pit_policies"], "PIT policy not allowed by study")
            _require(type(p.get("row_budget")) is int and 0 < p["row_budget"] <= study["max_rows"], "Plan row budget invalid")
            _require(_number(p.get("priority")) and 0 < p["priority"] <= 5, "Declared information priority must be in (0,5]")
            _strings(p.get("discriminates"), "test competing explanations", minimum=2)
            _require(set(p["discriminates"]) <= set(study["hypothesis_ids"]), "Unknown competing explanation")
            for key in ("selection_reason", "if_consistent", "if_inconsistent"):
                _text(p.get(key), key)
            params = p.get("parameters", {})
            _require(isinstance(params, dict), "Operator parameters required")
            fields = [params.get("value_field")] if p["operator"] != "correlation" else [params.get("x_field"), params.get("y_field")]
            if p["operator"] == "mean_difference":
                fields.append(params.get("group_field"))
                _require(isinstance(params.get("groups"), list) and len(params["groups"]) == 2 and len(set(params["groups"])) == 2, "Two comparison groups required")
            _require(all(f in source["field_roles"] for f in fields), "Operator fields not allowed by source")
            if p["operator"] == "correlation":
                _require(source["field_roles"][params["x_field"]] == "FEATURE" and source["field_roles"][params["y_field"]] == "OUTCOME", "Feature/outcome direction mismatch")
            if p["operator"] == "mean_difference":
                _require(source["field_roles"][params["group_field"]] == "FEATURE" and source["field_roles"][params["value_field"]] == "OUTCOME", "Group must be a feature and measured value an outcome")
            _require(_number(params.get("threshold")) and params.get("direction") in {"ABOVE", "BELOW"}, "Predeclared threshold and direction required")
            _require(type(params.get("min_rows")) is int and 2 <= params["min_rows"] <= p["row_budget"], "Minimum row count must fit plan budget")
            for ref in p.get("requirement_ids", []):
                n(ref, {"data_requirement"})
            if study["stage"] == "CONFIRMATION":
                _require(p["source_id"] in study["confirmation_contract"]["allowed_source_ids"], "Source not admitted to confirmation contract")
                _require(not any(x["kind"] == "test_run" and x["payload"]["study_id"] == p["study_id"] for x in nodes.values()), "Confirmation test plans cannot adapt after first run")
        elif kind == "test_run":
            plan = n(p["plan_id"], {"test_plan"})
            source = n(plan["payload"]["source_id"])["payload"]
            _require(p["study_id"] == plan["payload"]["study_id"] and p["source_id"] == plan["payload"]["source_id"], "Run context mismatch")
            _require(p.get("input_sha256") == source["rows_sha256"], "Run input does not match source")
            _sha(p.get("implementation_sha256"), "executor implementation SHA256")
            _require(p.get("result_sha256") == digest(p["result"]) and p.get("status") == "SUCCEEDED", "Unverified run result")
            _require(p["result"].get("interpretation") == "DESCRIPTIVE_NOT_CAUSAL", "Run may not assert causal confirmation")
            _require(type(p.get("row_count")) is int and p["row_count"] > 0, "Invalid run row count")
            self._check_executable(plan, previous, p["row_count"])
        elif kind == "evidence":
            run = n(p["run_id"], {"test_run"})
            plan = n(run["payload"]["plan_id"])["payload"]
            source = n(plan["source_id"])["payload"]
            _require(p.get("plan_id") == run["payload"]["plan_id"] and p.get("study_id") == plan["study_id"], "Evidence context mismatch")
            _require(p.get("result") == run["payload"]["result"] and p.get("result_sha256") == run["payload"]["result_sha256"], "Evidence/result hash mismatch")
            for key in ("stage", "origin", "data_root_ids", "scope", "pit_policy"):
                _require(p.get(key) == source[key], f"Evidence {key} mismatch")
            _require(p.get("epistemic_status") == "OBSERVED" and p.get("empirical_use") == ("SOFTWARE_TEST_ONLY" if source["origin"] == "SYNTHETIC" else "DESCRIPTIVE_RESEARCH"), "Evidence epistemic status mismatch")
            _require(record["actor"] == run["actor"], "Evidence must be emitted by run executor")
            _require(not any(x["kind"] == "evidence" and x["payload"]["run_id"] == p["run_id"] for x in nodes.values()), "Run evidence already emitted")
        elif kind == "claim":
            self._validate_claim(p, record, previous, nodes)
        elif kind == "strategy":
            self._validate_strategy(p, record, previous, nodes)

    def _validate_claim(self, p, record, previous, nodes):
        _text(p.get("statement"), "scoped claim")
        hypothesis = self._node(nodes, p["hypothesis_id"], {"hypothesis"})
        _require(p.get("conclusion_type") in {"ASSOCIATION", "MEASUREMENT", "PREDICTIVE"}, "Descriptive tests do not authorize causal claims")
        _scope(p.get("scope"))
        _strings(p.get("limitations"), "claim limitations")
        _require(p.get("judgment") in {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT"}, "Claim judgment invalid")
        _require(p.get("stage") in STAGES and p.get("epistemic_status") == "INDEPENDENT_REVIEWED", "Explicit reviewed stage required")
        relations = p.get("evidence_relations")
        _require(isinstance(relations, list) and relations, "Reviewed claim requires observed evidence, not arguments alone")
        _require(len({x["evidence_id"] for x in relations}) == len(relations), "Duplicate claim evidence")
        relevant = self._question_evidence(hypothesis["payload"]["question_id"], p["scope"], nodes)
        _require({x["id"] for x in relevant} <= {x["evidence_id"] for x in relations}, "Review must address all existing same-question/scope evidence, including counterevidence")
        supporting, origins = [], set()
        statuses = self._statuses(previous)
        for link in relations:
            evidence = self._node(nodes, link["evidence_id"], {"evidence"})
            _require(link.get("stance") in {"SUPPORTS", "CHALLENGES", "INCONCLUSIVE", "EXCLUDED_INVALID"}, "Evidence stance invalid")
            _text(link.get("reason"), "evidence interpretation")
            ep = evidence["payload"]
            plan = nodes[ep["plan_id"]]["payload"]
            _require(p["hypothesis_id"] in plan["discriminates"], "Evidence does not test this hypothesis or its declared competitors")
            _require(p["scope"] == ep["scope"], "Claim scope must match tested scope; wider generalization is a new hypothesis")
            if link["stance"] == "SUPPORTS":
                supporting.append(ep)
            if link["stance"] == "EXCLUDED_INVALID":
                _require(statuses[evidence["id"]] in {"INVALIDATED", "SUPERSEDED", "DEPENDENCY_BLOCKED"}, "Only invalidated evidence may be excluded; inconvenient results must remain")
            else:
                origins.add(ep["origin"])
        for ref in p.get("argument_ids", []):
            self._node(nodes, ref, {"argument"})
        if p["judgment"] == "SUPPORTED":
            _require(supporting, "Supported claim needs supporting evidence")
        if p["stage"] == "CONFIRMATION":
            _require(supporting and all(x["stage"] == "CONFIRMATION" for x in supporting), "Exploratory evidence cannot become confirmation")
        _require(p.get("empirical_use") == ("SOFTWARE_TEST_ONLY" if "SYNTHETIC" in origins else "DESCRIPTIVE_RESEARCH"), "Synthetic evidence cannot become an empirical market claim")
        ancestors = self._ancestors(record["dependencies"], nodes)
        authors = {nodes[x]["actor"] for x in ancestors if nodes[x]["kind"] in {"hypothesis", "prediction", "argument", "test_plan", "test_run", "evidence"}}
        _require(record["actor"] not in authors, "Claim reviewer must be independent of research and execution authors")
        material = self._material_ancestors(self._material_dependencies(record), nodes, previous)
        _require(all(statuses[x] == "ACTIVE" for x in material), "Claim prerequisites are not active")

    def _validate_strategy(self, p, record, previous, nodes):
        _text(p.get("name"), "strategy name")
        _require(p.get("purpose") in {"RESEARCH_ONLY", "SOFTWARE_TEST_ONLY"}, "No automatic strategy publication")
        _require(p.get("publication_authorized") is False, "No automatic publication")
        snap = p.get("knowledge_snapshot")
        self._validate_snapshot(snap, previous, require_current=True)
        _require(_time(snap["as_of"]) <= _time(record["known_at"]), "Snapshot cannot come from a future research time")
        _require(p.get("claim_ids") == snap["claim_ids"], "Strategy claims must exactly match snapshot")
        for ref in p["claim_ids"]:
            claim = self._node(nodes, ref, {"claim"})["payload"]
            _require(claim["judgment"] == "SUPPORTED", "Strategy may only use reviewed supported claims")
            _require(claim["empirical_use"] != "SOFTWARE_TEST_ONLY" or p["purpose"] == "SOFTWARE_TEST_ONLY", "Synthetic claim cannot become market strategy")
        execution = p.get("execution", {})
        _require(execution.get("rebalance") == "MONTHLY" and execution.get("signal_cutoff") == "MONTH_END_AFTER_CLOSE" and execution.get("fill") == "NEXT_MONTH_FIRST_TRADABLE_OPEN", "Monthly PIT execution contract required")
        for field in ("unavailable_price_rule", "corporate_action_policy"):
            _text(execution.get(field), field)
        costs = p.get("costs", {})
        _require(all(_number(costs.get(k)) and costs[k] >= 0 for k in ("commission_bps", "slippage_bps")), "Explicit nonnegative cost assumptions required")
        _text(costs.get("tax_model"), "tax model")
        _strings(p.get("benchmarks"), "benchmarks")
        _require({"MARKET_TR", "UNIVERSE_EQUAL_WEIGHT"} <= set(p["benchmarks"]), "Market TR and same-universe equal-weight benchmarks required")
        for key in ("entry_rule", "exit_rule", "sizing_rule", "risk_limits", "validation_plan"):
            _text(p.get(key), key)

    @staticmethod
    def _ancestors(refs, nodes):
        result, todo = set(), list(refs)
        while todo:
            current = todo.pop()
            if current not in result:
                result.add(current)
                todo.extend(nodes[current]["dependencies"])
        return result

    @staticmethod
    def _material_dependencies(node):
        excluded = {x["evidence_id"] for x in node["payload"].get("evidence_relations", []) if x["stance"] == "EXCLUDED_INVALID"} if node["kind"] == "claim" else set()
        return [ref for ref in node["dependencies"] if ref not in excluded]

    def _material_ancestors(self, refs, nodes, records):
        result, todo = set(), list(refs)
        edges = [r for r in records if r["type"] == "edge" and r["kind"] == "depends_on"]
        while todo:
            current = todo.pop()
            if current not in result:
                result.add(current)
                todo.extend(self._material_dependencies(nodes[current]))
                todo.extend(r["payload"]["target"] for r in edges if r["payload"]["source"] == current)
        return result

    @staticmethod
    def _question_evidence(question_id, scope, nodes):
        return [record for record in nodes.values() if record["kind"] == "evidence" and record["payload"]["scope"] == scope
                and nodes[record["payload"]["study_id"]]["payload"]["question_id"] == question_id]

    def _statuses(self, records):
        nodes = self._nodes(records)
        statuses = {key: "ACTIVE" for key in nodes}
        for record in records:
            p = record["payload"]
            if record["type"] == "event" and record["kind"] in {"invalidate", "supersede"}:
                statuses[p["target"]] = "INVALIDATED" if record["kind"] == "invalidate" else "SUPERSEDED"
            elif record["type"] == "edge" and record["kind"] in {"challenges", "contradicts"}:
                if nodes[p["target"]]["kind"] == "claim" and statuses[p["target"]] == "ACTIVE":
                    statuses[p["target"]] = "REVIEW_REQUIRED"
            elif record["type"] == "node" and record["kind"] == "data_requirement" and p["status"] == "OPEN":
                statuses[record["id"]] = "PREREQUISITE_MISSING"
            elif record["type"] == "node" and record["kind"] == "source" and p["readiness"] != "READY":
                statuses[record["id"]] = "PREREQUISITE_MISSING"
        for ref, node in nodes.items():
            if node["kind"] == "claim" and statuses[ref] == "ACTIVE":
                p = node["payload"]
                question = nodes[p["hypothesis_id"]]["payload"]["question_id"]
                cited = {x["evidence_id"] for x in p["evidence_relations"]}
                if any(evidence["seq"] > node["seq"] and evidence["id"] not in cited for evidence in self._question_evidence(question, p["scope"], nodes)):
                    statuses[ref] = "REVIEW_REQUIRED"
        changed = True
        while changed:
            changed = False
            for ref, node in nodes.items():
                extra = [r["payload"]["target"] for r in records if r["type"] == "edge" and r["kind"] == "depends_on" and r["payload"]["source"] == ref]
                if statuses[ref] == "ACTIVE" and any(statuses[d] != "ACTIVE" for d in [*self._material_dependencies(node), *extra]):
                    statuses[ref] = "DEPENDENCY_BLOCKED"
                    changed = True
        return statuses

    def _validate_edge(self, kind, p, record, previous, nodes):
        src, dst = self._node(nodes, p["source"]), self._node(nodes, p["target"])
        _require(p["source"] != p["target"], "Self edge/cycle rejected")
        _text(p.get("rationale"), "edge rationale")
        _require(set(record["dependencies"]) == {p["source"], p["target"]}, "Edge dependency mismatch")
        allowed = {"competes_with": ({"hypothesis"}, {"hypothesis"}),
                   "supports": ({"evidence"}, {"claim"}), "challenges": ({"evidence"}, {"claim", "hypothesis"}),
                   "contradicts": ({"claim"}, {"claim"}), "depends_on": (KINDS, KINDS)}
        _require(kind in allowed and src["kind"] in allowed[kind][0] and dst["kind"] in allowed[kind][1], "Unsupported inference or edge types")
        _require(record["role"] == ("reviewer" if kind in {"supports", "challenges", "contradicts"} else "researcher"), "Invalid edge role")
        if kind == "supports":
            _require(any(x["evidence_id"] == src["id"] and x["stance"] == "SUPPORTS" for x in dst["payload"]["evidence_relations"]), "New support requires a new reviewed claim")
        if kind == "depends_on":
            adjacency = {key: set(x["dependencies"]) for key, x in nodes.items()}
            for edge in previous:
                if edge["type"] == "edge" and edge["kind"] == "depends_on":
                    adjacency[edge["payload"]["source"]].add(edge["payload"]["target"])
            seen, todo = set(), [p["target"]]
            while todo:
                target = todo.pop()
                _require(target != p["source"], "Dependency cycle rejected")
                if target not in seen:
                    seen.add(target)
                    todo.extend(adjacency[target])

    def append_edge(self, kind, source, target, *, actor, role, known_at, rationale):
        with self._locked():
            records = self._load()
            return self._append(records, "edge", kind, {"source": source, "target": target, "rationale": rationale},
                                actor=actor, role=role, known_at=known_at, dependencies=[source, target])

    def _validate_event(self, kind, p, record, previous, nodes):
        if kind in {"invalidate", "supersede"}:
            _require(record["role"] == "curator", "Curator required for invalidation")
            target = self._node(nodes, p["target"])
            _text(p.get("reason"), "invalidation reason")
            _require(p["target"] in record["dependencies"], "Missing invalidation target")
            if kind == "supersede":
                replacement = self._node(nodes, p["replacement"])
                _require(replacement["kind"] == target["kind"] and p["target"] != p["replacement"], "Supersession must preserve node type")
                _require(p["target"] not in self._ancestors([p["replacement"]], nodes), "Replacement cannot depend on superseded record")
        elif kind == "test_selection":
            _require(record["role"] == "researcher", "Researcher required to choose experiment")
            self._node(nodes, p["study_id"], {"study"})
            candidates = self._eligible_plans(p["study_id"], previous)
            _require(p.get("candidate_plan_ids") == sorted(x["id"] for x in candidates), "Adaptive choice must include all eligible plans")
            _require(candidates and p["chosen_plan_id"] == sorted(candidates, key=lambda x: (-x["payload"]["priority"] / x["payload"]["row_budget"], x["id"]))[0]["id"], "Selection must follow declared decision heuristic")
            context = sorted(x["id"] for x in nodes.values() if x["kind"] == "evidence" and x["payload"]["study_id"] == p["study_id"])
            _require(p.get("prior_evidence_ids") == context, "Adaptive decision omitted prior evidence")
        elif kind == "study_stop":
            _require(record["role"] == "researcher", "Researcher required to stop study")
            self._node(nodes, p["study_id"], {"study"})
            _require(p.get("status") in {"SUFFICIENT_FOR_REVIEW", "UNRESOLVED", "DATA_BLOCKED", "BUDGET_STOP"}, "Explicit study stopping status required")
            _text(p.get("reason"), "study stopping reason")
            _require(not self._stop_event(p["study_id"], previous), "Study is already stopped")
            evidence = sorted(x["id"] for x in nodes.values() if x["kind"] == "evidence" and x["payload"]["study_id"] == p["study_id"])
            _require(p.get("evidence_ids") == evidence, "Stop decision must include complete observed evidence context")
            _require(set(record["dependencies"]) == {p["study_id"], *evidence}, "Stop decision dependencies mismatch")
        else:
            raise ValueError("Unknown event kind")

    def invalidate(self, node_id, *, actor, known_at, reason):
        with self._locked():
            records = self._load()
            return self._append(records, "event", "invalidate", {"target": node_id, "reason": reason},
                                actor=actor, role="curator", known_at=known_at, dependencies=[node_id])

    def supersede(self, old_id, new_id, *, actor, known_at, reason):
        with self._locked():
            records = self._load()
            return self._append(records, "event", "supersede", {"target": old_id, "replacement": new_id, "reason": reason},
                                actor=actor, role="curator", known_at=known_at, dependencies=[old_id, new_id])

    def register_study(self, payload, *, actor, known_at):
        return self.append_node("study", payload, actor=actor, role="researcher", known_at=known_at)

    @staticmethod
    def _stop_event(study_id, records):
        return next((r for r in records if r["type"] == "event" and r["kind"] == "study_stop" and r["payload"]["study_id"] == study_id), None)

    def stop_study(self, study_id, *, actor, known_at, reason, status="UNRESOLVED"):
        """Record a terminal research decision; no reopen or result promotion."""
        with self._locked():
            records = self._load()
            evidence = sorted(r["id"] for r in records if r["type"] == "node" and r["kind"] == "evidence" and r["payload"]["study_id"] == study_id)
            return self._append(records, "event", "study_stop", {"study_id": study_id, "status": status, "reason": reason, "evidence_ids": evidence},
                                actor=actor, role="researcher", known_at=known_at, dependencies=[study_id, *evidence])

    def packet(self, study_id, *, as_of=None):
        """Return proposed alternatives, ALL observations and actionable budgets.

        This local packet never queries old campaigns, Gold, external datasets
        or a hidden OOS store. An actor can reason over it without pretending a
        graph edge is truth. A stop is final for this study; a new study needs a
        separate contract and preserves the existing exposure history.
        """
        records = self.records()
        if as_of is not None:
            cutoff = _time(as_of)
            records = [r for r in records if r["known_at"] is None or _time(r["known_at"]) <= cutoff]
        nodes = self._nodes(records)
        study = self._node(nodes, study_id, {"study"})
        p = study["payload"]
        statuses = self._statuses(records)
        plans = [r for r in nodes.values() if r["kind"] == "test_plan" and r["payload"]["study_id"] == study_id]
        evidence = [r for r in nodes.values() if r["kind"] == "evidence" and r["payload"]["study_id"] == study_id]
        runs = [r for r in nodes.values() if r["kind"] == "test_run" and r["payload"]["study_id"] == study_id]
        requirements = sorted({ref for plan in plans for ref in plan["payload"].get("requirement_ids", [])})
        eligible = self._eligible_plans(study_id, records)
        eligible_ids = [r["id"] for r in eligible]
        used_runs, used_rows = self._budget(study_id, records)
        stop = self._stop_event(study_id, records)
        choices = [r for r in records if r["type"] == "event" and r["kind"] == "test_selection" and r["payload"]["study_id"] == study_id]
        selected = choices[-1]["payload"]["chosen_plan_id"] if choices else None
        actions = []
        if not stop and statuses[study_id] == "ACTIVE":
            actions.append("STOP_STUDY")
            if used_runs < p["max_runs"] and used_rows < p["max_rows"] and (p["stage"] == "EXPLORATORY" or used_runs == 0):
                actions.append("REGISTER_TEST_PLAN")
            if eligible:
                actions.append("CHOOSE_NEXT_TEST")
            if selected in eligible_ids:
                actions.append("EXECUTE_SELECTED_TEST")
        if evidence:
            actions.append("INDEPENDENT_REVIEW")
        claims = [r for r in nodes.values() if r["kind"] == "claim" and r["payload"]["hypothesis_id"] in p["hypothesis_ids"]]
        relevant = {study_id, p["question_id"], *p["hypothesis_ids"], *requirements, *(r["id"] for r in plans), *(r["id"] for r in runs),
                    *(r["id"] for r in evidence), *(r["id"] for r in claims)}
        return {"schema": SCHEMA + "-packet", "head": records[-1]["id"], "study": study,
                "question": nodes[p["question_id"]], "hypotheses": [nodes[ref] for ref in p["hypothesis_ids"]],
                "hypothesis_resolution": "NOT_AUTOMATICALLY_RESOLVED_BY_DESCRIPTIVE_TESTS",
                "predictions": [r for r in nodes.values() if r["kind"] == "prediction" and r["payload"]["hypothesis_id"] in p["hypothesis_ids"]],
                "plans": plans, "runs": runs, "all_evidence": evidence, "reviewed_scoped_claims": claims,
                "requirements": [nodes[ref] for ref in requirements], "unresolved_requirement_ids": [ref for ref in requirements if statuses[ref] != "ACTIVE"],
                "eligible_plan_ids": sorted(eligible_ids), "selected_plan_id": selected if selected in eligible_ids else None,
                "remaining_runs": max(0, p["max_runs"] - used_runs), "remaining_rows": max(0, p["max_rows"] - used_rows),
                "stop_decision": stop, "allowed_actions": actions, "statuses": {ref: statuses[ref] for ref in sorted(relevant)},
                "knowledge_warning": "Proposed hypotheses/arguments are not facts; claims are scoped reviews, not causal proof. All observations, including counterevidence, must be considered.",
                "publication_authorized": False}

    def _budget(self, study_id, records):
        runs = [r for r in records if r["type"] == "node" and r["kind"] == "test_run" and r["payload"]["study_id"] == study_id]
        return len(runs), sum(x["payload"]["row_count"] for x in runs)

    def _eligible_plans(self, study_id, records):
        nodes = self._nodes(records)
        study = self._node(nodes, study_id, {"study"})["payload"]
        if self._stop_event(study_id, records):
            return []
        used, rows = self._budget(study_id, records)
        if used >= study["max_runs"]:
            return []
        statuses = self._statuses(records)
        executed = {r["payload"]["plan_id"] for r in nodes.values() if r["kind"] == "test_run"}
        return [r for r in nodes.values() if r["kind"] == "test_plan" and r["payload"]["study_id"] == study_id and r["id"] not in executed and statuses[r["id"]] == "ACTIVE" and r["payload"]["row_budget"] <= study["max_rows"] - rows]

    def choose_next_test(self, study_id, candidate_plan_ids, *, actor, known_at):
        with self._locked():
            records = self._load()
            eligible = self._eligible_plans(study_id, records)
            _require(eligible, "Study budget exhausted or no executable unrun tests")
            _require(sorted(candidate_plan_ids) == sorted(x["id"] for x in eligible), "All eligible plans must be considered")
            selected = sorted(eligible, key=lambda x: (-x["payload"]["priority"] / x["payload"]["row_budget"], x["id"]))[0]
            context = sorted(r["id"] for r in records if r["type"] == "node" and r["kind"] == "evidence" and r["payload"]["study_id"] == study_id)
            payload = {"study_id": study_id, "candidate_plan_ids": sorted(candidate_plan_ids), "chosen_plan_id": selected["id"],
                       "prior_evidence_ids": context, "rule": "DECLARED_PRIORITY_PER_RESERVED_ROW_NOT_OPTIMAL_INFORMATION_GAIN"}
            return self._append(records, "event", "test_selection", payload, actor=actor, role="researcher", known_at=known_at,
                                dependencies=[study_id, *candidate_plan_ids, *context])

    def _check_executable(self, plan, records, row_count):
        p = plan["payload"]
        _require(plan["id"] in {x["id"] for x in self._eligible_plans(p["study_id"], records)}, "Plan already run, blocked, or budget exhausted")
        _require(row_count <= p["row_budget"], "Input exceeds plan row budget")
        selections = [r for r in records if r["type"] == "event" and r["kind"] == "test_selection" and r["payload"]["study_id"] == p["study_id"]]
        _require(selections and selections[-1]["payload"]["chosen_plan_id"] == plan["id"], "Plan must be selected before execution")

    def execute_test(self, plan_id, rows, *, actor, known_at):
        """Execute an allowlisted descriptive calculation; never import/eval code."""
        with self._locked():
            records = self._load()
            nodes = self._nodes(records)
            plan = self._node(nodes, plan_id, {"test_plan"})
            p = plan["payload"]
            source = nodes[p["source_id"]]["payload"]
            _require(isinstance(rows, list) and rows, "Nonempty input rows required")
            self._check_executable(plan, records, len(rows))
            _require(digest(rows) == source["rows_sha256"], "Input rows SHA256 differs from frozen source")
            ids = set()
            for row in rows:
                _require(isinstance(row, dict) and set(row) == set(source["columns"]), "Unexpected/missing input column")
                _require(row.get("row_id") not in ids and row.get("row_id") is not None, "Unique row_id required")
                ids.add(row["row_id"])
                _require(_time(source["scope"]["start"]) <= _time(row["observation_at"]) <= _time(source["scope"]["end"]), "Row outside approved data scope")
                _require(_time(row["feature_known_at"]) <= _time(row["decision_at"]), "Feature was not market-known at decision")
                _require(_time(row["observation_at"]) <= _time(row["decision_at"]) <= _time(row["outcome_known_at"]) <= _time(known_at), "Outcome/research known_at ordering invalid")
            result = _calculate(p["operator"], p["parameters"], rows)
            run_payload = {"plan_id": plan_id, "study_id": p["study_id"], "source_id": p["source_id"], "status": "SUCCEEDED",
                           "row_count": len(rows), "input_sha256": digest(rows), "result": result, "result_sha256": digest(result),
                           "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
            run = self._append(records, "node", "test_run", run_payload, actor=actor, role="executor", known_at=known_at,
                               dependencies=self._refs("test_run", run_payload))
            evidence_payload = {"run_id": run["id"], "plan_id": plan_id, "study_id": p["study_id"], "result": result,
                                "result_sha256": digest(result), "epistemic_status": "OBSERVED",
                                "empirical_use": "SOFTWARE_TEST_ONLY" if source["origin"] == "SYNTHETIC" else "DESCRIPTIVE_RESEARCH",
                                **{key: source[key] for key in ("stage", "origin", "scope", "pit_policy", "data_root_ids")}}
            evidence = self._append(records, "node", "evidence", evidence_payload, actor=actor, role="executor", known_at=known_at,
                                    dependencies=self._refs("evidence", evidence_payload))
            return {"run": run, "evidence": evidence, "remaining_runs": nodes[p["study_id"]]["payload"]["max_runs"] - self._budget(p["study_id"], records)[0]}

    def review_claim(self, payload, *, actor, known_at):
        with self._locked():
            records = self._load()
            return self._append(records, "node", "claim", payload, actor=actor, role="reviewer", known_at=known_at,
                                dependencies=self._refs("claim", payload))

    def _snapshot(self, claim_ids, records, as_of):
        cutoff = _time(as_of)
        visible = [r for r in records if r["known_at"] is None or _time(r["known_at"]) <= cutoff]
        nodes = self._nodes(visible)
        _require(claim_ids and len(set(claim_ids)) == len(claim_ids), "Explicit unique claims required")
        for ref in claim_ids:
            self._node(nodes, ref, {"claim"})
        selected = self._ancestors(claim_ids, nodes)
        edges = set()
        # Sibling observations for the same question/scope are included even
        # before somebody adds an explicit challenge edge: retrieval is not only
        # the claim author's favorable citations.
        for ref in claim_ids:
            p = nodes[ref]["payload"]
            question = nodes[p["hypothesis_id"]]["payload"]["question_id"]
            for evidence in self._question_evidence(question, p["scope"], nodes):
                selected.update(self._ancestors([evidence["id"]], nodes))
        changed = True
        while changed:
            before = len(selected)
            for edge in visible:
                if edge["type"] == "edge" and (edge["payload"]["target"] in selected or edge["payload"]["source"] in selected):
                    edges.add(edge["id"])
                    selected.update(self._ancestors([edge["payload"]["source"], edge["payload"]["target"]], nodes))
            changed = len(selected) > before
        statuses = self._statuses(visible)
        required = self._material_ancestors(claim_ids, nodes, visible)
        body = {"schema": SCHEMA + "-snapshot", "as_of": as_of, "head": visible[-1]["id"], "record_count": len(visible),
                "claim_ids": list(claim_ids), "node_ids": sorted(selected), "edge_ids": sorted(edges),
                "required_node_ids": sorted(required),
                "statuses": {key: statuses[key] for key in sorted(selected)}, "publication_authorized": False}
        return {**body, "snapshot_sha256": digest(body)}

    def snapshot(self, claim_ids, *, as_of):
        return self._snapshot(claim_ids, self.records(), as_of)

    def search_claims(self, query, *, as_of, universe=None, limit=10, include_synthetic=False):
        """Deterministic local retrieval, not an embedding or performance search.

        Search only statement/question/hypothesis text. Match count is lexical
        relevance, NEVER confidence, information gain or observed profitability.
        Equal matches use newest research known_at then stable record identity.
        Empty text lists recent active reviewed claims. Negative/inconclusive
        reviewed claims are retained; strategy_eligible is an additional flag,
        not a truth assertion. Default excludes SOFTWARE_TEST_ONLY records.

        Statuses are computed AS OF the requested research clock. A historical
        hit may be invalid now: create_strategy still requires a CURRENT checked
        snapshot. No archived graph, external data or legacy memory is searched.
        A 2,000-node response budget rejects oversized COMPLETE contexts rather
        than silently dropping contradictions; narrow the query/result limit.
        The application adapter must recheck upstream source permissions.
        """
        _require(isinstance(query, str) and len(query) <= 2048, "Search query must be text of at most 2048 characters")
        _require(type(limit) is int and 1 <= limit <= 50, "Search limit must be an integer from 1 to 50")
        _require(type(include_synthetic) is bool, "include_synthetic must be an explicit boolean")
        if universe is not None:
            _text(universe, "exact universe filter")
        cutoff = _time(as_of)
        tokens = sorted(set(re.findall(r"\w+", query.casefold(), flags=re.UNICODE)))
        _require(len(tokens) <= 32, "Search query exceeds 32-token budget")
        _require(not query.strip() or tokens, "Nonempty query must contain searchable text")
        records = [record for record in self.records() if record["known_at"] is None or _time(record["known_at"]) <= cutoff]
        nodes, statuses = self._nodes(records), self._statuses(records)
        matches = []
        for claim in nodes.values():
            if claim["kind"] != "claim" or statuses[claim["id"]] != "ACTIVE":
                continue
            p = claim["payload"]
            if p["epistemic_status"] != "INDEPENDENT_REVIEWED" or (not include_synthetic and p["empirical_use"] == "SOFTWARE_TEST_ONLY"):
                continue
            if universe is not None and p["scope"]["universe"] != universe:
                continue
            hypothesis = nodes[p["hypothesis_id"]]["payload"]
            question = nodes[hypothesis["question_id"]]["payload"]
            text = " ".join([p["statement"], hypothesis["statement"], question["title"], question["question"]]).casefold()
            matched = [token for token in tokens if token in text]
            if tokens and not matched:
                continue
            matches.append((claim, matched))
        matches.sort(key=lambda pair: (-len(pair[1]), -_time(pair[0]["known_at"]).timestamp(), pair[0]["id"]))
        results, context_count = [], 0
        for claim, matched in matches[:limit]:
            p = claim["payload"]
            snapshot = self._snapshot([claim["id"]], records, as_of)
            context_count += len(snapshot["node_ids"])
            _require(context_count <= MAX_SEARCH_CONTEXT_NODES, "Complete retrieval context exceeds 2000-node budget; reduce result limit or narrow query")
            sources = [nodes[ref] for ref in snapshot["required_node_ids"] if nodes[ref]["kind"] == "source"]
            policies = sorted({source["payload"]["pit_policy"] for source in sources})
            limitations = list(p["limitations"])
            if "PIT_ASSUMED" in policies:
                limitations.append("PIT_ASSUMED: at least one required source uses a disclosed availability/vintage assumption, not verified initial-release values.")
            limitations.append("Source/PIT authenticity depends on upstream review; hash consistency is not factual proof.")
            results.append({"claim": claim, "matched_tokens": matched, "lexical_match_count": len(matched),
                            "scope": p["scope"], "stage": p["stage"], "empirical_use": p["empirical_use"],
                            "judgment": p["judgment"], "strategy_eligible": p["judgment"] == "SUPPORTED" and p["empirical_use"] != "SOFTWARE_TEST_ONLY",
                            "software_strategy_eligible": p["judgment"] == "SUPPORTED" and p["empirical_use"] == "SOFTWARE_TEST_ONLY",
                            "pit_policies": policies, "limitations": limitations,
                            "source_prerequisites": [{"id": source["id"], **{key: source["payload"][key] for key in
                                ("source_ref", "data_version", "scope", "origin", "pit_policy", "readiness")}} for source in sources],
                            "snapshot": snapshot})
        return {"schema": SCHEMA + "-claim-search", "query": query, "as_of": as_of, "universe": universe,
                "include_synthetic": include_synthetic, "limit": limit, "total_matches": len(matches), "results": results,
                "ranking": "LEXICAL_MATCH_COUNT_THEN_RESEARCH_KNOWN_AT_DESC_THEN_ID; NEVER_OUTCOME_PERFORMANCE",
                "context_node_count": context_count, "publication_authorized": False,
                "knowledge_warning": "Reviewed claims remain scoped judgments, not causal truth or investment approval. Historical snapshots require current revalidation before strategy use."}

    def _validate_snapshot(self, snapshot, records, *, require_current):
        _require(isinstance(snapshot, dict), "Knowledge snapshot required")
        body = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
        _require(snapshot.get("snapshot_sha256") == digest(body), "Snapshot hash mismatch")
        count = snapshot.get("record_count")
        _require(type(count) is int and 0 < count <= len(records) and records[count - 1]["id"] == snapshot.get("head"), "Snapshot append-chain anchor missing")
        _require(snapshot == self._snapshot(snapshot["claim_ids"], records[:count], snapshot["as_of"]), "Snapshot context or dependency mismatch")
        if require_current:
            _require(snapshot["head"] == records[-1]["id"], "Stale knowledge snapshot; retrieve and review again")
            _require(all(snapshot["statuses"][ref] == "ACTIVE" for ref in snapshot["required_node_ids"]), "Snapshot has invalidated/missing/review-required prerequisites")
        return snapshot

    def validate_snapshot(self, snapshot, *, require_current=True):
        return self._validate_snapshot(snapshot, self.records(), require_current=require_current)

    def create_strategy(self, payload, snapshot, *, actor, known_at):
        with self._locked():
            records = self._load()
            p = {**payload, "knowledge_snapshot": snapshot, "claim_ids": snapshot["claim_ids"], "publication_authorized": False}
            # Invalid evidence remains in the snapshot context but an explicit
            # independent EXCLUDED_INVALID review can remove it as a premise.
            return self._append(records, "node", "strategy", p, actor=actor, role="strategist", known_at=known_at,
                                dependencies=snapshot["required_node_ids"])


def _calculate(operator, params, rows):
    """Descriptive-only deterministic result; thresholds were frozen in plan."""
    minimum = params["min_rows"]
    if operator == "coverage":
        values = [r[params["value_field"]] for r in rows]
        valid = [x for x in values if _number(x)]
        _require(len(values) >= minimum, "Insufficient rows")
        effect, used = len(valid) / len(values), len(values)
        detail = {"valid_count": len(valid), "null_or_nonfinite_count": len(values) - len(valid)}
    elif operator == "mean_difference":
        groups = params["groups"]
        usable = [r for r in rows if _number(r[params["value_field"]])]
        _require(all(r[params["group_field"]] in groups for r in usable), "Unexpected comparison group")
        samples = [[r[params["value_field"]] for r in usable if r[params["group_field"]] == group] for group in groups]
        _require(len(usable) >= minimum and all(len(x) >= 2 for x in samples), "Insufficient rows per comparison group")
        means = [sum(x) / len(x) for x in samples]
        effect, used = means[0] - means[1], len(usable)
        detail = {"groups": groups, "group_counts": [len(x) for x in samples], "group_means": means}
    else:
        _require(operator == "correlation", "Unknown executable operator")
        pairs = [(r[params["x_field"]], r[params["y_field"]]) for r in rows if _number(r[params["x_field"]]) and _number(r[params["y_field"]])]
        _require(len(pairs) >= minimum and len(pairs) >= 3, "Insufficient rows for correlation")
        xbar, ybar = (sum(x[i] for x in pairs) / len(pairs) for i in (0, 1))
        numerator = sum((x - xbar) * (y - ybar) for x, y in pairs)
        denom = math.sqrt(sum((x - xbar) ** 2 for x, y in pairs) * sum((y - ybar) ** 2 for x, y in pairs))
        _require(denom > 0, "Constant series correlation is undefined")
        effect, used, detail = numerator / denom, len(pairs), {}
    _require(_number(effect), "Nonfinite experiment result")
    consistent = effect > params["threshold"] if params["direction"] == "ABOVE" else effect < params["threshold"]
    return {"operator": operator, "effect": effect, "rows_used": used, "rows_supplied": len(rows), "detail": detail,
            "directionally_consistent": consistent, "interpretation": "DESCRIPTIVE_NOT_CAUSAL", "statistical_confirmation": False}
