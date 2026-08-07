"""게이트 판정 → TeamAlpha-data 의 `gold.factor` 적재.

이 모듈이 리서치와 프로덕션의 **유일한 접점**이다.
factor-research 는 판정만 하고, 승인된 팩터를 실제로 계산·적재하는 건
TeamAlpha-data 의 `pipeline/gold/` 가 한다. 계약은 `gold.factor` 테이블이다.

팀 스키마가 강제하는 것(sql/gold_schema.sql):
  status='APPROVED'  → evaluation @> '{"passed": true}'
  status='REJECTED'  → evaluation @> '{"passed": false}'
  status='CANDIDATE' → 제약 없음
  UNIQUE (factor_key) WHERE status='APPROVED'   ← 계열당 승인 버전 하나
  UNIQUE (factor_key, version)
  factor_key ~ '^[a-z][a-z0-9_]*$'
그리고 factor_value 에는 APPROVED 인 팩터만 트리거가 허용한다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from engine.factors import Factor
from engine.gate import RULESET_VERSION, TH, Result, Verdict
from engine.panel import INVESTABLE_ADV
from engine import silver

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VALUE_CONTRACT_ID = "raw_value_direction_adjusted_rank_v1"


@dataclass(frozen=True)
class ImplementationRef:
    """Concrete production implementation bound to a research definition."""

    uri: str
    sha256: str
    research_definition_hash: str

    def __post_init__(self):
        if not self.uri.strip():
            raise ValueError("implementation uri는 비어 있을 수 없습니다")
        if not SHA256_RE.fullmatch(self.sha256):
            raise ValueError("implementation sha256은 64자리 소문자 hex여야 합니다")
        if not self.research_definition_hash.strip():
            raise ValueError("research_definition_hash는 비어 있을 수 없습니다")

# 우리 판정 → 팀 status.
# PROVISIONAL 은 팀 어휘에 없다. CANDIDATE 로 두고 근거를 evaluation 에 남긴다
# (CANDIDATE 만 evaluation 제약이 없어서 "통과도 탈락도 아님"을 표현할 수 있다).
STATUS = {
    Verdict.PROMOTE: "APPROVED",
    Verdict.PROVISIONAL: "CANDIDATE",
    Verdict.REJECT: "REJECTED",
}


def _py(v):
    """numpy 스칼라·NaN 을 JSON 직렬화 가능한 파이썬 기본형으로. jsonb 는 NaN 을 못 받는다."""
    import math
    if v is None:
        return None
    if hasattr(v, "item"):        # np.float64 / np.bool_ / np.int64
        v = v.item()
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    if isinstance(v, (bool, int, str)):
        return v
    return str(v)


def build_row(factor: Factor, result: Result, *, implementation: ImplementationRef,
              n_trials: int | None = None,
              null_family_error_rate: float | None = None, data_cutoff: str | None = None,
              approved_by: str | None = None) -> dict:
    """gold.factor 한 행. 판정 근거를 재검토 가능한 형태로 전부 담는다."""
    if not KEY_RE.match(factor.name):
        raise ValueError(f"factor_key 규칙 위반(^[a-z][a-z0-9_]*$): {factor.name}")
    if result.definition_hash != factor.definition_hash:
        raise ValueError("result.definition_hash가 현재 factor 정의와 일치하지 않습니다")
    if implementation.research_definition_hash != factor.definition_hash:
        raise ValueError("구현이 참조하는 research_definition_hash가 factor 정의와 다릅니다")

    status = STATUS[result.verdict]
    evaluation = {
        # 팀 스키마 CHECK 가 요구하는 필드
        "passed": result.verdict == Verdict.PROMOTE,
        # 우리 판정의 원래 등급 (PROVISIONAL 이 CANDIDATE 로 접히므로 여기 보존)
        "verdict": result.verdict.value,
        "ruleset_version": RULESET_VERSION,
        "criteria_defined": True,
        "research_certified": result.verdict == Verdict.PROMOTE,
        "approved_by": approved_by,
        "metrics": {k: _py(v) for k, v in result.metrics.items()},
        "checks": [
            {"tier": c.tier, "name": c.name, "passed": _py(c.passed),
             "value": _py(c.value), "threshold": c.threshold, "note": c.note}
            for c in result.checks
        ],
        "failed_checks": [c.name for c in result.failed],
        "labels": result.labels,
        "thresholds": TH,
        "n_trials": n_trials,
        "null_family_error_rate": null_family_error_rate,
        "data_cutoff": data_cutoff,
    }
    config = {
        "hypothesis": factor.hypothesis,
        "category": factor.category,
        "predicted_sign": factor.predicted_sign,
        "params": factor.params,
        "rebalance_months": factor.rebalance_months,
        "needs": list(factor.needs),
        "universe": {
            "source": "KRX", "markets": ["KOSPI", "KOSDAQ"], "asset_type": "stock",
            "common_stock_only": True, "exclude": ["SPAC", "REIT"],
            "min_listing_days": 250,
            "investable_rule": "adv20 > investable_adv_krw",
            "investable_adv_krw": INVESTABLE_ADV,
        },
        "pit": {"fundamental": "available_date", "market": "price_daily.market(날짜별)"},
        "research_definition_hash": implementation.research_definition_hash,
        "value_contract": {
            "id": VALUE_CONTRACT_ID,
            "value": "raw",
            "predicted_sign": factor.predicted_sign,
            "score": "value*predicted_sign",
            "rank": "score_descending",
            "raw_value_order": (
                "descending" if factor.predicted_sign == 1 else "ascending"
            ),
            "as_of_date": "asset_last_valid_trading_day_in_signal_month",
            "rank_partition": "signal_month_full_implementation_universe",
        },
    }
    return {
        "factor_key": factor.name,
        "description": (factor.hypothesis.strip().split(".")[0] + ".")[:200],
        "implementation_uri": implementation.uri,
        "implementation_hash": implementation.sha256,
        "config": config,
        "evaluation": evaluation,
        "status": status,
    }


UPSERT = """
INSERT INTO gold.factor
    (factor_key, version, description, implementation_uri,
     implementation_hash, config, evaluation, status)
SELECT %(factor_key)s,
       coalesce((SELECT max(version) FROM gold.factor
                  WHERE factor_key = %(factor_key)s), 0) + 1,
       %(description)s, %(implementation_uri)s, %(implementation_hash)s,
       %(config)s::jsonb, %(evaluation)s::jsonb, %(status)s
RETURNING factor_id, factor_key, version, status
"""

RETIRE_PREVIOUS = """
UPDATE gold.factor SET status = 'RETIRED'
 WHERE factor_key = %(factor_key)s AND status = 'APPROVED'
"""


def publish(conn, rows: list[dict], *, apply: bool = False) -> list[dict]:
    """gold.factor 에 적재. apply=False 면 아무것도 쓰지 않는다.

    같은 factor_key 의 기존 APPROVED 는 RETIRED 로 내린다
    (팀 스키마가 계열당 APPROVED 하나만 허용하므로 필수).
    """
    out = []
    for r in rows:
        payload = dict(r, config=json.dumps(r["config"], ensure_ascii=False),
                       evaluation=json.dumps(r["evaluation"], ensure_ascii=False))
        if not apply:
            out.append({**{k: r[k] for k in ("factor_key", "status")},
                        "version": "(dry-run)", "factor_id": None})
            continue
        with conn.cursor() as cur:
            if r["status"] == "APPROVED":
                cur.execute(RETIRE_PREVIOUS, {"factor_key": r["factor_key"]})
            cur.execute(UPSERT, payload)
            fid, key, ver, st = cur.fetchone()
            out.append({"factor_id": fid, "factor_key": key, "version": ver, "status": st})
    if apply:
        conn.commit()
    return out


def connect():
    """Gold shares the Silver database; this is the only mutating connection."""
    return silver.connect(read_only=False)
