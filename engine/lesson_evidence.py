"""Evidence schema for a reviewer, separate from candidate-generation memory.

No model calls, causal claims, data fetching, gate changes or new OOS evaluation.
Only the release-authenticated candidate-lessons exporter calls this builder.

New v2 evidence identifies results relative to the research root, so checkout
locations do not change packet/review hashes. V1 remains readable: the exporter
may preserve an existing v1 packet and accepted review only when its logical
identity and entire freshly rebuilt evidence still match the original hash.
This is not a migration of archived bytes or permission to reuse changed data.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import PurePosixPath


LEGACY_VERSION = "lesson-evidence-v1"
VERSION = "lesson-evidence-v2"
SUPPORTED_VERSIONS = frozenset({LEGACY_VERSION, VERSION})
RESULT_IDENTITY_CONTRACT = "research-root-relative-v1"
MISSING_SECTIONS = {
    "input_quality": "원시 입력·공개시점·결측·이상치 분포",
    "selection_profile": "분위별 업종·규모·부채·수익성·유동성 및 기존 신호 노출",
    "economic_outcomes": "가설에 맞는 이후 실적 변화·성숙 여부·비교군",
    "monthly_performance": "월별 IC·분위별 수익률·상하위 그룹 성과·비용과 표본 수",
    "regime_comparison": "월초에 알려진 레짐별 성과·표본 수·독립 발생 구간 수",
    "controlled_comparison": "업종·규모 통제 전후의 동일 표본 비교와 불확실성",
    "charts": "위 진단 수치표에서 생성한 이미지와 대응 evidence_id",
    "execution_costs": "실제 보유 규칙·회전율·거래비용 전후의 동일 표본 비교",
}


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode()).hexdigest()


def portable_provenance(evidence: dict) -> dict:
    """Bind the logical result, never the checkout used to locate its bytes.

    Legacy locations are compared lexically, not opened. Their campaign,
    epoch, cycle and definition bindings must still match independently.
    """
    provenance = dict(evidence)
    if "result" not in provenance:
        return provenance
    cycle = provenance.get("cycle")
    if not isinstance(cycle, str) or not cycle or cycle in {".", ".."} or "/" in cycle or "\\" in cycle:
        raise ValueError("Invalid lesson result cycle identity")
    result = provenance["result"]
    if not isinstance(result, str):
        raise ValueError("Invalid lesson result identity")
    parts = PurePosixPath(result.replace("\\", "/")).parts
    if ".." in parts or parts[-3:] != ("runs", cycle, "result.json"):
        raise ValueError("Lesson result location does not match its cycle")
    contract = provenance.get("result_identity_contract")
    if contract not in (None, RESULT_IDENTITY_CONTRACT):
        raise ValueError("Unsupported lesson result identity contract")
    provenance["result"] = f"runs/{cycle}/result.json"
    provenance["result_identity_contract"] = RESULT_IDENTITY_CONTRACT
    return provenance


def build_packet(
    record: dict, payload: dict, confirmation: dict | None, *, schema_version: str = VERSION,
) -> dict:
    if record["visibility"] != "RELEASED_QUALITATIVE":
        raise ValueError("Reviewer evidence is only available after release")
    if schema_version not in SUPPORTED_VERSIONS:
        raise ValueError("Unsupported lesson evidence schema")
    evidence = [{
        "id": "hypothesis", "kind": "PREREGISTERED_CLAIM_NOT_FACT",
        "data": {**record["hypothesis_and_calculation"],
                 "research_spec": payload.get("research_spec", {})},
    }]
    for phase, evaluation in [
        ("discovery", payload.get("evaluation", {})),
        ("confirmation", (confirmation or {}).get("evaluation", {})),
    ]:
        if phase == "confirmation" and confirmation is None:
            continue
        evidence.append({"id": f"{phase}.metrics", "kind": "AGGREGATE_METRICS",
                         "phase": phase, "data": evaluation.get("metrics", {})})
        for index, check in enumerate(evaluation.get("checks", [])):
            evidence.append({"id": f"{phase}.check.{index}", "kind": "GATE_OBSERVATION",
                             "phase": phase, "data": check})
    packet = {
        "schema_version": schema_version, "record_id": record["record_id"],
        "audience": "TERMINAL_RESULT_REVIEWER_ONLY",
        "provenance": (portable_provenance(record["evidence"])
                       if schema_version == VERSION else dict(record["evidence"])),
        "source_sha256": digest({"result": payload, "confirmation": confirmation}),
        "evidence": evidence,
        "diagnostics": {key: {"status": "NOT_COLLECTED", "needed": description}
                        for key, description in MISSING_SECTIONS.items()},
        "review_contract": {
            "facts_require_evidence_ids": True,
            "hypothesis_is_not_verified_mechanism": True,
            "missing_is_not_failed": True,
            "associations_do_not_prove_causation": True,
            "same_window_is_not_independent_replication": True,
            "forward_outcomes_are_diagnostic_only": True,
            "raw_evidence_not_for_candidate_generation": True,
        },
    }
    study = payload.get("mechanism_study")
    if study is not None:
        from engine.scientist_review import SOURCES, VERSION as SCIENTIST_VERSION
        packet["scientist"] = {"version": SCIENTIST_VERSION, "methods": SOURCES,
                               "study_status": study.get("status"),
                               "limitations": study.get("limitations", []),
                               "protocol": "observational diagnostics; analyst then critic; no gate changes"}
        packet["scientist"]["mechanism_plan_status"] = (
            "FROZEN_WITH_CANDIDATE" if payload.get("research_spec", {}).get("mechanism_plan")
            else "ABSENT_LEGACY_HYPOTHESIS_ONLY"
        )
        # The plots use the already signed signal, not the raw formula. Keep
        # this explicit for negative-direction factors and never infer a sign
        # from an old hypothesis sentence when metadata is absent.
        sign = payload.get("factor", {}).get("predicted_sign")
        orientation = study.get("signal_orientation")
        signed = orientation == "already_signed_by_predicted_sign"
        packet["scientist"]["study_context"] = {
            "phase": study.get("phase"),
            "data_cutoff": study.get("data_cutoff"),
            "sample": study.get("sample"),
            "signal_orientation": orientation,
            "predicted_sign": sign,
            "top_group_raw_direction": (
                "LOWER_RAW_VALUE" if signed and sign == -1
                else "HIGHER_RAW_VALUE" if signed and sign == 1
                else "UNKNOWN"
            ),
            "candidate_rebalance_months": payload.get("factor", {}).get("rebalance_months"),
            "diagnostic_groups": "MONTHLY_REFORMED_NOT_IMPLEMENTED_HOLDINGS",
            "return_contract": study.get("return_contract"),
            "economic_outcome_notes": study.get("economic_outcome_notes", []),
        }
        # Additive for new captures only: old content-addressed packets must
        # rebuild byte-for-byte without a newly invented timing attestation.
        if "execution_timing_contract" in study:
            packet["scientist"]["study_context"]["execution_timing_contract"] = study["execution_timing_contract"]
        if study.get("status") == "COLLECTED":
            if study.get("definition_hash") != payload.get("factor", {}).get("definition_hash") or study.get("phase") != "discovery":
                raise ValueError("Mechanism study binding mismatch")
            for section, diagnostic in study.get("sections", {}).items():
                if section not in MISSING_SECTIONS or diagnostic.get("status") not in {"AVAILABLE", "PARTIAL", "NOT_COLLECTED"}:
                    raise ValueError("Invalid diagnostic section")
                packet["diagnostics"][section] = diagnostic
                if diagnostic["status"] in {"AVAILABLE", "PARTIAL"}:
                    evidence.append({"id": f"diagnostic.discovery.{section}",
                                     "kind": "OBSERVATIONAL_DIAGNOSTIC", "phase": "discovery",
                                     "section": section, "data": diagnostic})
            # A rank association and a raw mean spread describe different
            # properties. Opposite directions warrant review, not a changed
            # gate, clipped data, or an automatic claim of corruption.
            warnings = []
            regime_basis = packet["diagnostics"]["regime_comparison"].get("data", {}).get("input_status", {})
            if regime_basis.get("pit_status") == "PIT_ASSUMED":
                packet["scientist"]["study_context"]["regime_input_basis"] = regime_basis
                warnings.append({
                    "code": "REGIME_PIT_ASSUMPTIONS_ACCEPTED",
                    "evidence_ids": ["diagnostic.discovery.regime_comparison"]
                        if packet["diagnostics"]["regime_comparison"]["status"] in {"AVAILABLE", "PARTIAL"} else [],
                    "meaning": "User-accepted historical availability/value assumptions are frozen with this regime diagnostic. Preserve the assumption label; do not claim first-vintage verification, infer proven contamination, or change a promotion gate.",
                })
            for outcome in packet["diagnostics"]["economic_outcomes"].get("data", {}).get("outcomes", []):
                rank = outcome.get("rank_ic", {}).get("mean")
                spread = outcome.get("top_minus_bottom", {}).get("mean")
                if all(isinstance(x, (int, float)) and math.isfinite(x) for x in (rank, spread)) and rank * spread < 0:
                    warnings.append({
                        "code": "ECONOMIC_RANK_MEAN_DISAGREEMENT",
                        "outcome": outcome.get("name"),
                        "evidence_ids": ["diagnostic.discovery.economic_outcomes"],
                        "meaning": "Rank association and raw group-mean spread have opposite signs. Check distributions, denominators and missingness before a mechanism claim; this does not establish an outlier or data error.",
                    })
            packet["scientist"]["interpretation_warnings"] = warnings
            from engine.mechanism_charts import diagnostic_charts
            charts = diagnostic_charts(study.get("sections", {}))
            if charts:
                packet["diagnostics"]["charts"] = {
                    "status": "AVAILABLE", "data": charts,
                    "limitations": ["Inline SVG bytes derived from the cited numeric tables; viewing is a separate reviewer action."],
                }
                evidence.append({"id": "diagnostic.discovery.charts", "kind": "DERIVED_VISUALIZATION",
                                 "section": "charts", "data": charts})
        else:
            packet["scientist"]["unavailable_reason"] = study.get("reason", "unknown")
    return packet


def review_template(record: dict, packet: dict) -> dict:
    version = packet.get("schema_version")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError("Unsupported lesson evidence schema")
    template = {
        "schema_version": version, "record_id": record["record_id"],
        "status": "DRAFT", "basis": record["review_basis"],
        "packet_sha256": digest(packet),
        "observations": [{"text": "", "evidence_ids": []}],
        "mechanism_assessment": [{
            "link": "측정 → 경제적 변화 → 가격 반영 → 비용 후 성과",
            "assessment": "UNTESTED", "evidence_ids": [],
        }],
        "economic_interpretation": "", "alternative_explanations": [""],
        "unresolved": [""],
        "general_lesson": "", "scope": "",
        "lesson_key": "", "stance": "UNCERTAIN",
        "analysis_origin": "RETROSPECTIVE_EXPLORATORY",
        "missing_evidence": [key for key, value in packet["diagnostics"].items() if value["status"] != "AVAILABLE"],
    }
    if "scientist" in packet:
        from engine.scientist_review import augment_template
        template = augment_template(template)
    return template


def validate_review(review: dict, record: dict, packet: dict, *, require_critic: bool = True) -> None:
    """Structural/evidence validation, not an automated truth/causality judge."""
    if record["visibility"] != "RELEASED_QUALITATIVE":
        raise ValueError("Candidate is not released")
    version = packet.get("schema_version")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError("Unsupported lesson evidence schema")
    expected = {"schema_version": version, "record_id": record["record_id"],
                "basis": record["review_basis"], "packet_sha256": digest(packet),
                "status": "REVIEWED"}
    if any(review.get(k) != v for k, v in expected.items()):
        raise ValueError("Review is stale, draft or bound to different evidence")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,79}", review.get("lesson_key", "")):
        raise ValueError("lesson_key must be a stable lowercase principle identifier")
    if review.get("stance") not in {"SUPPORTS", "CONTRADICTS", "UNCERTAIN"}:
        raise ValueError("Invalid lesson stance")
    if review.get("analysis_origin") != "RETROSPECTIVE_EXPLORATORY":
        raise ValueError("This review is retrospective, not a preregistered causal test")
    for field in ("economic_interpretation", "general_lesson", "scope"):
        text = review.get(field)
        if not isinstance(text, str) or not 0 < len(text.strip()) <= 600:
            raise ValueError(f"Missing/oversized qualitative text: {field}")
        if re.search(r"\d|%|IC|p값|수익률.*[=<>]", text):
            raise ValueError(f"Numeric performance is not exported to memory: {field}")
    for field in ("alternative_explanations", "unresolved"):
        items = review.get(field)
        if not isinstance(items, list) or not items or not all(
            isinstance(item, str) and item.strip() and len(item) <= 1200 for item in items
        ):
            raise ValueError(f"Explain alternatives and limitations: {field}")
    required_missing = {k for k, v in packet["diagnostics"].items()
                        if v["status"] != "AVAILABLE"}
    missing = review.get("missing_evidence")
    if not isinstance(missing, list) or set(missing) != required_missing:
        raise ValueError("Do not hide missing diagnostics")
    ids = {item["id"]: item["kind"] for item in packet["evidence"]}
    for field, text_field in (("observations", "text"), ("mechanism_assessment", "link")):
        items = review.get(field)
        if not isinstance(items, list) or not items:
            raise ValueError(f"Missing {field}")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get(text_field), str) or not item[text_field].strip():
                raise ValueError(f"Missing text in {field}")
            refs = item.get("evidence_ids")
            if not isinstance(refs, list) or any(ref not in ids for ref in refs):
                raise ValueError("Unknown evidence reference")
            if field == "mechanism_assessment":
                if item.get("assessment") not in {"SUPPORTED", "NOT_SUPPORTED", "MIXED", "UNTESTED"}:
                    raise ValueError("Invalid mechanism assessment")
                if item["assessment"] == "UNTESTED":
                    continue
            if not refs or all(ids[ref] == "PREREGISTERED_CLAIM_NOT_FACT" for ref in refs):
                raise ValueError("An observed finding needs observed evidence, not just the hypothesis")
    if "scientist" in packet or "scientist_version" in review:
        from engine.scientist_review import validate_analysis, validate_critic
        validate_analysis(review, packet)
        if require_critic:
            validate_critic(review, packet)
