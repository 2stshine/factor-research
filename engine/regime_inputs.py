"""Freeze reviewed or explicitly assumption-accepted diagnostic context.

The approval is an upstream PIT review attestation, not a certification created
by this module. User-accepted assumptions remain PIT_ASSUMED, never PIT proof.
Hash checks authenticate binding, not economic truth. Neither path grants factor
input approval or changes a promotion gate.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

import pandas as pd

from engine.regimes import RULES, classify_monthly_market

VERSION = "diagnostic-regime-input-v1"
FROZEN = "frozen-diagnostic-regime-v1"
PIT_FLAGS = ("pit_approved", "publication_time_verified", "revision_history_verified",
             "historical_backtest_allowed")
DAY_BOUND = "OFFICIAL_POLICY_PUBLICATION_DAY_END_KST"
ASSUMPTION_SCHEMA = "pit-regime-assumption-v1"
ASSUMED_AVAILABILITY = "ASSUMED_HISTORICAL_AVAILABILITY"


def _valid_assumption_policy(policy):
    return (isinstance(policy, dict)
            and policy.get("schema_version") == "regime-assumption-policy-v1"
            and isinstance(policy.get("policy_id"), str) and bool(policy["policy_id"].strip())
            and isinstance(policy.get("authorization_text"), str)
            and bool(policy["authorization_text"].strip())
            and all(policy.get(k) is True for k in (
                "user_authorized", "new_campaigns_only", "diagnostics_only", "promotion_gates_unchanged"))
            and all(policy.get(k) is False for k in (
                "factor_feature_allowed", "historical_pit_verified")))


def _valid_assumption_scope(scope):
    return (isinstance(scope, dict) and all(
        isinstance(scope.get(k), str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", scope[k])
        for k in ("start_month", "end_month")) and scope["start_month"] <= scope["end_month"])


def _accepted_assumption(source, approval):
    assumptions = source.get("assumptions")
    policy = approval.get("assumption_policy")
    return (approval.get("schema_version") == ASSUMPTION_SCHEMA
            and approval.get("status") == "ASSUMPTION_ACCEPTED"
            and approval.get("source_layer") == "DERIVED_RESEARCH_CONTEXT"
            and approval.get("purpose") == "DIAGNOSTIC_ONLY"
            and all(approval.get(k) is False for k in (
                "pit_approved", "publication_time_verified", "publication_date_verified",
                "historical_availability_verified", "revision_history_verified",
                "factor_feature_allowed", "intraday_allowed"))
            and approval.get("historical_backtest_allowed") is True
            and source.get("pit_status") == "PIT_ASSUMED"
            and source.get("known_at_semantics") == ASSUMED_AVAILABILITY
            and isinstance(assumptions, list) and bool(assumptions)
            and all(isinstance(a, str) and bool(a.strip()) for a in assumptions)
            and _valid_assumption_scope(source.get("scope"))
            and approval.get("scope") == source["scope"]
            and _valid_assumption_policy(policy)
            and approval.get("assumption_policy_sha256") == digest(policy))


def _approved_review(source, approval):
    """Verified v1/v2 OR a separately labeled user assumption acceptance.

    A verified publication day suffices for month-end diagnostics. It does not
    certify an intraday timestamp or make arbitrary lagged Bronze PIT-safe.
    """
    if approval.get("schema_version") == ASSUMPTION_SCHEMA:
        return _accepted_assumption(source, approval)
    # A verified attestation cannot silently relabel an explicitly assumed source.
    if source.get("pit_status") == "PIT_ASSUMED":
        return False
    common = (approval.get("status") == "APPROVED"
              and approval.get("source_layer") == "SILVER"
              and approval.get("purpose") == "DIAGNOSTIC_ONLY")
    if approval.get("schema_version") == "pit-regime-approval-v1":
        return common and all(approval.get(k) is True for k in PIT_FLAGS)
    if approval.get("schema_version") != "pit-regime-approval-v2":
        return False
    return (common
            and all(approval.get(k) is True for k in (
                "pit_approved", "historical_backtest_allowed", "publication_date_verified",
                "historical_availability_verified", "revision_history_verified"))
            and approval.get("publication_time_verified") is False
            and approval.get("intraday_allowed") is False
            and approval.get("factor_feature_allowed") is False
            and approval.get("availability_basis") == DAY_BOUND
            and approval.get("revision_basis") == "DATED_OFFICIAL_POLICY_DECISIONS"
            and source.get("kind") == "macro_state"
            and source.get("macro_type") == "policy_rate"
            and source.get("known_at_semantics") == DAY_BOUND
            and source.get("frequency") == "MONTH_END"
            and source.get("value_semantics") == "ANNOUNCED_POLICY_TARGET")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def make_assumption_acceptance(source, policy, evidence, *, accepted_at):
    """Bind an explicit user policy without asserting historical verification.

    This does not infer consent, fetch evidence, register inputs, or mutate a
    campaign. The caller must supply the authorized policy and retain this
    separate acceptance artifact with the existing byte-hash contract.
    """
    approval = {
        "schema_version": ASSUMPTION_SCHEMA, "status": "ASSUMPTION_ACCEPTED",
        "source_layer": "DERIVED_RESEARCH_CONTEXT", "purpose": "DIAGNOSTIC_ONLY",
        "source_id": source.get("source_id"), "source_sha256": digest(source),
        "reviewer": "USER_AUTHORIZED_ASSUMPTION", "reviewed_at": accepted_at,
        "evidence": deepcopy(evidence), "scope": deepcopy(source.get("scope")),
        "assumption_policy": deepcopy(policy), "assumption_policy_sha256": digest(policy),
        "historical_backtest_allowed": True,
        **{k: False for k in ("pit_approved", "publication_time_verified",
                              "publication_date_verified", "historical_availability_verified",
                              "revision_history_verified",
                              "factor_feature_allowed", "intraday_allowed")},
    }
    _validate_approval(source, approval)
    return approval


def _assumption_metadata(contexts):
    assumed = [s for s in contexts if s["approval"].get("schema_version") == ASSUMPTION_SCHEMA]
    if not assumed:
        return {}
    return {"pit_status": "PIT_ASSUMED",
            "assumed_context_ids": [s["context_id"] for s in assumed],
            "verified_context_ids": [s["context_id"] for s in contexts
                                     if s["approval"].get("schema_version") != ASSUMPTION_SCHEMA],
            "assumption_policy_sha256s": sorted({s["approval"]["assumption_policy_sha256"] for s in assumed})}


def _source_assumption_metadata(source):
    if source["approval"].get("schema_version") != ASSUMPTION_SCHEMA:
        return {}
    return {"pit_status": "PIT_ASSUMED", "assumptions": deepcopy(source["assumptions"]),
            "known_at_semantics": source["known_at_semantics"], "scope": deepcopy(source["scope"]),
            "assumption_policy_sha256": source["approval"]["assumption_policy_sha256"]}


def read_context(path):
    """Read inputs plus separate, already-issued review artifacts. No network."""
    path = Path(path).resolve()
    bundle = json.loads(path.read_bytes())
    _require(bundle.get("schema_version") == VERSION, "Unsupported regime input schema")
    contexts = bundle.get("contexts")
    _require(isinstance(contexts, list) and bool(contexts), "No regime contexts configured")
    prepared = []
    for item in contexts:
        source = item["source"]
        review_path = (path.parent / item["approval_file"]).resolve()
        review_body = review_path.read_bytes()
        _require(hashlib.sha256(review_body).hexdigest() == item["approval_sha256"],
                 "Regime approval file hash mismatch")
        approval = json.loads(review_body)
        _validate_approval(source, approval)
        prepared.append({"source": source, "approval": approval,
                         "approval_sha256": item["approval_sha256"]})
    return {"schema_version": VERSION, "contexts": prepared}


def load_campaign_context(*, explicit_path=None, registry_path=None, disabled=False):
    """Resolve reviewed defaults only at NEW campaign creation.

    An explicit context overrides the registry; a corrupt/missing registered
    artifact fails closed rather than silently dropping diagnostic inputs.
    """
    _require(not (disabled and explicit_path), "Cannot disable and explicitly provide regime context")
    if disabled:
        return None
    if explicit_path:
        return read_context(explicit_path)
    if registry_path is None or not Path(registry_path).exists():
        return None
    path = Path(registry_path).resolve()
    registry = json.loads(path.read_bytes())
    _require(registry.get("schema_version") == "diagnostic-regime-registry-v1",
             "Unsupported regime registry")
    prepared = []
    for entry in registry["contexts"]:
        if entry.get("enabled") is not True:
            continue
        context_path = (path.parent / entry["file"]).resolve()
        _require(hashlib.sha256(context_path.read_bytes()).hexdigest() == entry["sha256"],
                 "Registered regime context hash mismatch")
        prepared.extend(read_context(context_path)["contexts"])
    return {"schema_version": VERSION, "contexts": prepared} if prepared else None


def _validate_approval(source, approval):
    _require(_approved_review(source, approval),
             "Regime input requires an approved Silver historical PIT review or an explicit diagnostic assumption acceptance; Bronze alone is blocked")
    _require(isinstance(source.get("source_id"), str) and bool(source["source_id"].strip()),
             "Missing regime source identity")
    _require(approval.get("source_id") == source["source_id"]
             and approval.get("source_sha256") == digest(source), "Regime approval source binding mismatch")
    _require(isinstance(approval.get("reviewer"), str) and bool(approval["reviewer"].strip()),
             "Regime approval requires an identified reviewer")
    reviewed = pd.Timestamp(approval.get("reviewed_at"))
    _require(not pd.isna(reviewed) and reviewed.tzinfo is not None
             and reviewed <= pd.Timestamp.now(tz="UTC"), "Invalid PIT review time")
    evidence = approval.get("evidence")
    _require(isinstance(evidence, list) and bool(evidence) and all(
        isinstance(e, dict) and isinstance(e.get("uri"), str) and bool(e["uri"])
        and _sha(e.get("sha256")) for e in evidence), "Missing upstream PIT review evidence references")


def freeze_context(bundle, *, data_cutoff, oos_start):
    """Embed scoped observations; no external path can drift during evaluation."""
    _require(bundle.get("schema_version") == VERSION, "Unsupported regime input schema")
    cutoff = pd.Timestamp(data_cutoff)
    last_signal = min(cutoff.to_period("M") - 1, pd.Period(oos_start, freq="M") - 2)
    contexts, ids = [], set()
    market_count = 0
    for item in bundle["contexts"]:
        source, approval = item["source"], item["approval"]
        _validate_approval(source, approval)
        _require(_sha(item.get("approval_sha256")), "Missing approval artifact hash")
        context_id = source.get("context_id")
        _require(isinstance(context_id, str) and re.fullmatch(r"[A-Za-z0-9_^.-]+", context_id)
                 and context_id not in ids, "Duplicate or invalid regime context identity")
        ids.add(context_id)
        kind = source.get("kind")
        _require(kind in {"market_index", "macro_state"}, "Unsupported regime context kind")
        market_count += kind == "market_index"
        _require(market_count <= 1, "Only one primary official market index is supported")
        if kind == "market_index":
            _require(source.get("official_market_index") is True and bool(source.get("market_id")),
                     "Market context must identify an official index, not an ETF proxy")
        else:
            states, rules = source.get("states"), source.get("classification_rules")
            _require(isinstance(states, list) and len(states) >= 2 and len(set(states)) == len(states)
                     and all(isinstance(s, str) and s and s != "UNKNOWN" for s in states),
                     "Macro state dictionary must be explicit")
            _require(isinstance(rules, dict) and bool(rules.get("version")),
                     "Macro classification rules must be versioned and frozen")
        data = pd.DataFrame(source["rows"])
        needed = {"month", "known_at", "close" if kind == "market_index" else "state"}
        _require(needed.issubset(data.columns), "Incomplete regime input rows")
        months = pd.PeriodIndex(data["month"], freq="M")
        _require(not months.isna().any(), "Missing regime observation month")
        # Drop OOS/embargo observations before examining values or availability.
        data = data.loc[months <= last_signal, sorted(needed)].copy()
        data["month"] = pd.PeriodIndex(data["month"], freq="M").astype(str)
        if approval.get("schema_version") == ASSUMPTION_SCHEMA:
            _require(data["month"].between(source["scope"]["start_month"], source["scope"]["end_month"]).all(),
                     "Assumed regime observation is outside accepted scope")
        _require(not data["month"].duplicated().any(), "Regime revisions require explicit PIT resolution")
        known = pd.to_datetime(data["known_at"], errors="raise")
        _require(not known.isna().any() and known.dt.tz is None,
                 "known_at must be timezone-naive Korean decision-calendar dates")
        _require((known.dt.to_period("M") >= pd.PeriodIndex(data["month"], freq="M")).all(),
                 "known_at precedes observation month")
        if approval.get("schema_version") == "pit-regime-approval-v2":
            _require((known.to_numpy() == pd.PeriodIndex(data["month"], freq="M")
                      .end_time.floor("s").to_numpy()).all(),
                     "Policy day-bound input must use month-end decision bounds, not intraday times")
        if kind == "macro_state":
            _require(set(data["state"]).issubset(set(source["states"]) | {"UNKNOWN"}),
                     "Unrecognized macro state")
        else:
            _require(not data["close"].map(lambda x: isinstance(x, bool)).any(), "Boolean index level")
            data["close"] = pd.to_numeric(data["close"], errors="raise")
            _require(data["close"].map(lambda x: math.isfinite(x) and x > 0).all(),
                     "Index levels must be finite and positive")
        data["known_at"] = known.dt.strftime("%Y-%m-%dT%H:%M:%S")
        entry = {k: deepcopy(v) for k, v in source.items() if k != "rows"}
        entry.update(rows=data.sort_values("month").to_dict(orient="records"),
                     upstream_source_sha256=digest(source), approval=deepcopy(approval),
                     approval_sha256=item["approval_sha256"])
        contexts.append(entry)
    _require(bool(contexts), "Empty regime context bundle")
    result = {"schema_version": FROZEN, "data_cutoff": str(cutoff.date()),
              "last_signal_month": str(last_signal), "market_rules_version": RULES["version"],
              "contexts": contexts, "purpose": "DIAGNOSTIC_ONLY",
              **_assumption_metadata(contexts)}
    return {**result, "sha256": digest(result)}


def frozen_digest(campaign):
    frozen = campaign.get("diagnostic_regimes")
    if frozen is None:
        return None
    _require(frozen.get("schema_version") == FROZEN
             and frozen.get("sha256") == digest({k: v for k, v in frozen.items() if k != "sha256"}),
             "Frozen regime context hash mismatch")
    return frozen["sha256"]


def campaign_context(campaign):
    """Resolve immutable, campaign-bound data for the actual diagnostic call."""
    frozen = campaign.get("diagnostic_regimes")
    if frozen is None:
        return None, {}, {"status": "NOT_CONFIGURED", "reason": "NO_FROZEN_PIT_REGIME_INPUT"}
    frozen_digest(campaign)
    cutoff = pd.Timestamp(campaign["discovery"]["data_cutoff"])
    last = min(cutoff.to_period("M") - 1, pd.Period(campaign["oos"]["start"], freq="M") - 2)
    _require(frozen["data_cutoff"] == str(cutoff.date()) and frozen["last_signal_month"] == str(last),
             "Frozen regime context campaign boundary mismatch")
    market, macro = None, {}
    for source in frozen["contexts"]:
        approval = source["approval"]
        _require(_approved_review(source, approval)
                 and approval.get("source_sha256") == source["upstream_source_sha256"],
                 "Frozen PIT approval mismatch")
        data = pd.DataFrame(source["rows"])
        if data.empty:
            continue
        _require((pd.PeriodIndex(data["month"], freq="M") <= last).all(), "Regime input crosses embargo/OOS")
        if approval.get("schema_version") == ASSUMPTION_SCHEMA:
            _require(data["month"].between(source["scope"]["start_month"], source["scope"]["end_month"]).all(),
                     "Frozen assumed regime observation is outside accepted scope")
        if source["kind"] == "market_index":
            if (pd.to_datetime(data["known_at"]) <= last.end_time).any():
                market = classify_monthly_market(data, as_of=str(last.end_time.date()),
                    market_id=source["market_id"], source_id=source["source_id"],
                    rules_version=frozen["market_rules_version"])
                if approval.get("schema_version") == ASSUMPTION_SCHEMA:
                    market["pit_status"] = "PIT_ASSUMED"
                    market.attrs.update(_source_assumption_metadata(source))
        else:
            # A delayed state never becomes known retroactively for that month.
            late = pd.to_datetime(data["known_at"]) > pd.PeriodIndex(data["month"], freq="M").end_time
            data.loc[late, "state"] = "UNKNOWN"
            data["effective_month"] = (pd.PeriodIndex(data["month"], freq="M") + 1).astype(str)
            macro[source["context_id"]] = {"rows": data.to_dict(orient="records"),
                "states": source["states"], "source_id": source["source_id"],
                "classification_rules": source["classification_rules"],
                "rules_sha256": digest(source["classification_rules"]),
                "approval_sha256": source["approval_sha256"],
                **_source_assumption_metadata(source)}
    identity = [{k: source[k] for k in ("context_id", "source_id", "kind", "market_id",
                "states", "classification_rules") if k in source} for source in frozen["contexts"]]
    for entry, source in zip(identity, frozen["contexts"]):
        entry.update(_source_assumption_metadata(source))
    assumption_metadata = _assumption_metadata(frozen["contexts"])
    return market, macro, {"status": "FROZEN_ASSUMED_INPUT" if assumption_metadata else "FROZEN_PIT_INPUT",
                          "sha256": frozen["sha256"],
                          "input_contract_sha256": digest(identity),
                          "last_signal_month": str(last),
                          "context_ids": [x["context_id"] for x in frozen["contexts"]],
                          **assumption_metadata}


def attach_macro_context(section, contexts, performance):
    """Compare every frozen macro axis; no best-cell choice or factor gate."""
    from engine.mechanism_diagnostics import _regime_episode_ids, _regime_summary

    if not contexts:
        return
    original_status = section["status"]
    views = {}
    for name, context in contexts.items():
        rows = pd.DataFrame(context["rows"]).sort_values("month")
        lookup = rows.set_index("month")["state"].to_dict()
        monthly = [{**row, "state": lookup.get(row["month"], "UNKNOWN"),
                    "effective_month": str(pd.Period(row["month"], freq="M") + 1)}
                   for row in performance]
        usable = sum(r["state"] != "UNKNOWN" and r["n_pairs"] > 0 for r in monthly)
        status = "AVAILABLE" if monthly and usable == len(monthly) else "PARTIAL" if usable else "NOT_COLLECTED"
        views[name] = {"status": status, "source_id": context["source_id"],
                       "classification_rules": context["classification_rules"],
                       "rules_sha256": context["rules_sha256"],
                       "approval_sha256": context["approval_sha256"], "monthly": monthly,
                       "states": _regime_summary(monthly, "state", set(context["states"]) | {"UNKNOWN"},
                                                  _regime_episode_ids(rows, "state"))}
        for key in ("pit_status", "assumptions", "known_at_semantics", "scope", "assumption_policy_sha256"):
            if key in context:
                views[name][key] = deepcopy(context[key])
    section["data"]["macro_views"] = views
    section["data"]["market_status"] = original_status
    statuses = [original_status, *(v["status"] for v in views.values())]
    section["status"] = ("AVAILABLE" if all(x == "AVAILABLE" for x in statuses)
                         else "PARTIAL" if any(x != "NOT_COLLECTED" for x in statuses)
                         else "NOT_COLLECTED")
    section["limitations"].extend([
        "Macro states use separately reviewed, frozen classifications; this pipeline does not infer or certify them from Bronze.",
        "All configured axes and UNKNOWN states are retained. Multiple views are exploratory, not extra factor promotion gates.",
    ])
    if any(context.get("pit_status") == "PIT_ASSUMED" for context in contexts.values()):
        section["limitations"].append(
            "PIT_ASSUMED axes use user-accepted historical-availability/value assumptions; "
            "they are not verified first-release vintages and do not alter promotion gates "
            "or authorize factor-feature use.")
