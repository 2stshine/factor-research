"""Read-only diagnostics on an explicitly released, frozen Discovery frame.

No I/O, factor execution, source acquisition, gate evaluation or OOS access.
The caller must scope and project the frame BEFORE constructing this adapter.
Hash binding and date checks are logical safeguards, not process isolation or
proof that a provider's historical values were truly first-release vintages.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

import numpy as np
import pandas as pd


VERSION = "real-discovery-diagnostics-v1"
CATALOG = {
    "input_audit": {"cost": 1, "description": "Audit keys, coverage and the declared formation-availability evidence."},
    "association": {"cost": 2, "description": "Monthly rank IC and descriptive reformed quintile spreads."},
    "controls": {"cost": 3, "description": "Identical-sample raw and controlled associations; no fabricated industry."},
    "execution_cost": {"cost": 3, "description": "Read an explicitly contracted, same-window holdings/cost measurement."},
    "regime_interaction": {"cost": 3, "description": "Predeclared regime contrast in controlled monthly slopes, with support counts."},
    "economic_link": {"cost": 3, "description": "Two observed economic-outcome associations with horizon and maturity checks."},
}
_LIMITS = [
    "Discovery-only observational diagnostics; not independent OOS, factor admission or causal identification.",
    "Intervals are descriptive calendar-month HAC; adaptive inspection has no sequential error-control guarantee.",
    "Contract/hash checks bind supplied evidence, not source truth or historical first-release validity.",
    "Logical-only isolation: the trusted host must restrict source access independently.",
]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def frame_hash(frame: pd.DataFrame) -> str:
    """Order- and dtype-sensitive fingerprint; excludes incidental pandas index."""
    header = _canonical({"columns": list(frame.columns), "dtypes": [str(x) for x in frame.dtypes]})
    values = pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype="uint64").tobytes()
    return hashlib.sha256(header.encode() + values).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _month(value):
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}", value) is None:
        raise ValueError("Monthly bounds require YYYY-MM")
    return pd.Period(value, freq="M")


def _dates(values):
    # Integer nanoseconds must not become accidental 1970 availability dates.
    values = values.map(lambda v: None if isinstance(v, (int, float, np.number)) else v)
    parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    if not pd.api.types.is_datetime64_dtype(parsed.dtype):
        raise ValueError("Availability dates must be timezone-naive local calendar timestamps")
    return parsed


def _numeric(values):
    return pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)


def make_real_contract(frame, *, capability_id, dataset_id, snapshot_sha256,
                       factor_definition_hash, signal_start, signal_end,
                       maturity_cutoff, sealed_start, columns, controls=(),
                       feature_availability=None, economic=None, regime=None,
                       execution=None, question_kind="PREDICTIVE", question=None,
                       return_horizon_months=1, min_cross_section=30,
                       min_months=12):
    """Freeze a supplied projected frame; does not certify or release its data.

    columns has exactly month, asset_id, signal, signal_known_at (nullable),
    forward_return, return_known_at. A control is {name,column,kind,known_at};
    kind is numeric or categorical. Null feature known_at requires an explicit
    feature_availability {policy_id,status,evidence_sha256} with status
    POLICY_BOUND or ASSUMED. It does not fabricate per-cell timestamps.

    economic: {column,known_at,horizon_months,dataset_id}, optional
    measurement_kind=LEVEL|CHANGE (default CHANGE), optionally all of
    {return_column,return_known_at,return_horizon_months} for an aligned return.
    regime: {column,known_at,labels,contrast:[reference,target],definition_sha256,
    pit_status}. UNKNOWN is implicit. execution: {gross,net,cost,turnover,
    known_at,holdings_sha256,return_contract_sha256,cost_model_sha256,
    timing_contract,horizon_months}; these are supplied monthly portfolio
    measurements, NOT reconstructed from cross-sectional average returns.
    """
    result = {
        "version": VERSION, "phase": "DISCOVERY", "scope": "FROZEN_DISCOVERY_ONLY",
        "isolation_level": "LOGICAL_ONLY", "capability_id": capability_id,
        "dataset_id": dataset_id, "snapshot_sha256": snapshot_sha256,
        "factor_definition_hash": factor_definition_hash, "frame_sha256": frame_hash(frame),
        "allowed_columns": list(frame.columns), "signal_start": signal_start,
        "signal_end": signal_end, "maturity_cutoff": maturity_cutoff, "sealed_start": sealed_start,
        "columns": dict(columns), "controls": list(controls),
        "feature_availability": feature_availability, "economic": economic,
        "regime": regime, "execution": execution, "question_kind": question_kind,
        "question": question or "What does the fixed Discovery evidence establish, and what remains untested?",
        "return_horizon_months": return_horizon_months,
        "min_cross_section": min_cross_section, "min_months": min_months,
        "factor_approval_allowed": False, "gold_write_allowed": False,
        "causal_claim_allowed": False, "formal_sequential_error_control": False,
    }
    # Roundtrip forbids callable/opaque/nonfinite contract payloads.
    result = json.loads(_canonical(result))
    _validate(frame, result)
    return result


def _validate(frame, contract):
    if (contract.get("version") != VERSION or contract.get("phase") != "DISCOVERY"
            or contract.get("scope") != "FROZEN_DISCOVERY_ONLY"
            or contract.get("isolation_level") != "LOGICAL_ONLY"):
        raise ValueError("Only explicit frozen Discovery capabilities are supported")
    for field in ("factor_approval_allowed", "gold_write_allowed", "causal_claim_allowed", "formal_sequential_error_control"):
        if contract.get(field) is not False:
            raise ValueError("Diagnostic capabilities cannot authorize approval, writes or causal claims")
    if (not isinstance(frame, pd.DataFrame) or frame.empty or not frame.columns.is_unique
            or not all(isinstance(x, str) for x in frame.columns)
            or list(frame.columns) != contract["allowed_columns"]):
        raise ValueError("A nonempty exact projected frame is required; extra columns are forbidden")
    for field in ("capability_id", "dataset_id", "question"):
        if not isinstance(contract.get(field), str) or not contract[field].strip():
            raise ValueError(f"Missing {field}")
    for field in ("snapshot_sha256", "factor_definition_hash", "frame_sha256"):
        if not _hash(contract.get(field)):
            raise ValueError(f"Invalid {field}")
    if frame_hash(frame) != contract["frame_sha256"]:
        raise ValueError("Frozen frame hash mismatch")
    if contract["question_kind"] not in {"PREDICTIVE", "ECONOMIC", "EXPLANATORY"}:
        raise ValueError("Unknown question kind")
    for field, floor in (("return_horizon_months", 1), ("min_cross_section", 30), ("min_months", 12)):
        if type(contract[field]) is not int or contract[field] < floor:
            raise ValueError(f"Invalid {field}")
    start, end, sealed = (_month(contract[k]) for k in ("signal_start", "signal_end", "sealed_start"))
    if (not isinstance(contract["maturity_cutoff"], str)
            or re.fullmatch(r"\d{4}-\d{2}-\d{2}", contract["maturity_cutoff"]) is None):
        raise ValueError("Maturity cutoff must be a date-only YYYY-MM-DD inclusive local day")
    cutoff = pd.Timestamp(contract["maturity_cutoff"])
    if cutoff.tz is not None or pd.isna(cutoff) or not start <= end < sealed:
        raise ValueError("Invalid Discovery bounds")
    # Date-only cutoff includes that local calendar day, never a sealed month.
    cutoff = cutoff.normalize() + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    if cutoff >= sealed.start_time or cutoff < end.start_time:
        raise ValueError("Maturity cutoff must precede sealed scope and cover signal bounds")
    mapping = contract["columns"]
    roles = {"month", "asset_id", "signal", "signal_known_at", "forward_return", "return_known_at"}
    if set(mapping) != roles or any(mapping[k] not in frame for k in roles - {"signal_known_at"}):
        raise ValueError("Missing required mapped columns")
    if mapping["signal"] == mapping["forward_return"]:
        raise ValueError("Signal and outcome must be distinct columns")
    months = pd.PeriodIndex(frame[mapping["month"]], freq="M")
    if months.isna().any() or not ((months >= start) & (months <= end)).all():
        raise ValueError("Rows outside frozen Discovery scope; scope BEFORE handing data to adapter")
    if frame[mapping["asset_id"]].isna().any():
        raise ValueError("Asset identity must not be missing")
    requested = {v for v in mapping.values() if v is not None}
    feature_columns = {mapping["signal"]}
    label_columns = {mapping["forward_return"]}
    knowns = [mapping["signal_known_at"]]
    names = []
    for item in contract["controls"]:
        if (set(item) != {"name", "column", "kind", "known_at"}
                or item["kind"] not in {"numeric", "categorical"}
                or not isinstance(item["name"], str) or not item["name"]):
            raise ValueError("Invalid control specification")
        names.append(item["name"])
        requested.add(item["column"])
        feature_columns.add(item["column"])
        knowns.append(item["known_at"])
    if len(set(names)) != len(names):
        raise ValueError("Duplicate control names")
    policy = contract["feature_availability"]
    if any(x is None for x in knowns):
        if (not isinstance(policy, dict) or set(policy) != {"policy_id", "status", "evidence_sha256"}
                or policy["status"] not in {"POLICY_BOUND", "ASSUMED"}
                or not isinstance(policy["policy_id"], str) or not policy["policy_id"]
                or not _hash(policy["evidence_sha256"])):
            raise ValueError("Unavailable feature timestamps require an explicit bound availability policy")
    requested.update(x for x in knowns if x is not None)
    economic = contract["economic"]
    if economic is not None:
        required = {"column", "known_at", "horizon_months", "dataset_id"}
        aligned = {"return_column", "return_known_at", "return_horizon_months"}
        if (set(economic) - {"measurement_kind"} not in (required, required | aligned)
                or economic.get("measurement_kind", "CHANGE") not in {"LEVEL", "CHANGE"}):
            raise ValueError("Invalid economic outcome specification")
        for field in ("horizon_months",) + (("return_horizon_months",) if aligned <= set(economic) else ()):
            if type(economic[field]) is not int or economic[field] < 1:
                raise ValueError("Economic horizons must be positive integers")
        if not isinstance(economic["dataset_id"], str) or not economic["dataset_id"]:
            raise ValueError("Economic dataset identity required")
        requested.update(economic[k] for k in ("column", "known_at"))
        label_columns.add(economic["column"])
        if aligned <= set(economic):
            requested.update(economic[k] for k in ("return_column", "return_known_at"))
            label_columns.add(economic["return_column"])
    regime = contract["regime"]
    if regime is not None:
        required = {"column", "known_at", "labels", "contrast", "definition_sha256", "pit_status"}
        if set(regime) != required or not _hash(regime["definition_sha256"]):
            raise ValueError("Invalid frozen regime specification")
        if (regime["pit_status"] not in {"VERIFIED", "PIT_ASSUMED", "POLICY_BOUND"}
                or not isinstance(regime["labels"], list) or len(set(regime["labels"])) != len(regime["labels"])
                or not all(isinstance(x, str) and x and x != "UNKNOWN" for x in regime["labels"])
                or len(regime["contrast"]) != 2 or len(set(regime["contrast"])) != 2
                or not set(regime["contrast"]) <= set(regime["labels"])):
            raise ValueError("Regime labels and contrast must be fixed explicitly")
        requested.update(regime[k] for k in ("column", "known_at"))
        feature_columns.add(regime["column"])
    execution = contract["execution"]
    if execution is not None:
        required = {"gross", "net", "cost", "turnover", "known_at", "holdings_sha256",
                    "return_contract_sha256", "cost_model_sha256", "timing_contract", "horizon_months"}
        if (set(execution) != required or not all(_hash(execution[k]) for k in
                ("holdings_sha256", "return_contract_sha256", "cost_model_sha256"))
                or not isinstance(execution["timing_contract"], str) or not execution["timing_contract"]
                or type(execution["horizon_months"]) is not int or execution["horizon_months"] < 1):
            raise ValueError("Explicit holdings, cost and timing identities are required")
        requested.update(execution[k] for k in ("gross", "net", "cost", "turnover", "known_at"))
        label_columns.update(execution[k] for k in ("gross", "net", "cost", "turnover"))
    if feature_columns & label_columns:
        raise ValueError("Feature/control/regime and outcome roles must not overlap")
    if not requested <= set(frame.columns):
        raise ValueError("Declared capability columns are absent")
    # An allowlist must describe the actual semantic roles, not blindly bless
    # arbitrary extra/sealed/source columns in a broad dataframe.
    if requested != set(frame.columns):
        raise ValueError("Unassigned extra columns are forbidden in a projected diagnostic frame")


def _ic(first, second):
    if first.nunique() < 2 or second.nunique() < 2:
        return None
    value = first.rank(method="average").corr(second.rank(method="average"))
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def _estimate(months, values, *, lags=3, minimum=12, design=None, coefficient=0):
    """Calendar-spaced HAC OLS; missing months are zero score, not zero return."""
    index = pd.PeriodIndex(months, freq="M")
    y = np.asarray([np.nan if x is None else x for x in values], dtype=float)
    x = np.ones((len(y), 1)) if design is None else np.asarray(design, dtype=float)
    valid = np.isfinite(y) & np.isfinite(x).all(axis=1)
    n, k = int(valid.sum()), x.shape[1]
    result = {"mean": None, "standard_error": None, "ci95": None, "n_months": n,
              "minimum_months": minimum, "hac_lags": lags,
              "method": "calendar_month_hac_bartlett_descriptive",
              "status": "INSUFFICIENT_SUPPORT"}
    if n < k or np.linalg.matrix_rank(x[valid]) < k:
        return result
    beta = np.linalg.lstsq(x[valid], y[valid], rcond=None)[0]
    result["mean"] = float(beta[coefficient])
    if n <= k or n < minimum:
        return result
    scores = {month.ordinal: vector for month, vector in zip(index[valid],
              x[valid] * (y[valid] - x[valid] @ beta)[:, None])}
    meat = sum(np.outer(v, v) for v in scores.values())
    for lag in range(1, lags + 1):
        covariance = sum((np.outer(v, scores.get(t - lag, np.zeros(k))) for t, v in scores.items()), np.zeros((k, k)))
        meat += (1 - lag / (lags + 1)) * (covariance + covariance.T)
    bread = np.linalg.pinv(x[valid].T @ x[valid])
    variance = bread @ meat @ bread * n / (n - k)
    se = float(np.sqrt(max(0, variance[coefficient, coefficient])))
    result.update({"standard_error": se, "ci95": [float(beta[coefficient] - 1.96 * se),
                                                  float(beta[coefficient] + 1.96 * se)], "status": "DESCRIPTIVE"})
    return result


class RealDiagnosticLab:
    """Trusted host adapter. Researchers receive reports, never this object."""

    def __init__(self, frame: pd.DataFrame, contract: dict):
        _validate(frame, contract)
        self._contract = json.loads(_canonical(contract))
        self._frame = frame.copy(deep=True).reset_index(drop=True)
        self._columns = self._contract["columns"]
        self._months = pd.Series(pd.PeriodIndex(self._frame[self._columns["month"]], freq="M"))
        self._formation = self._months.dt.end_time
        self._cutoff = pd.Timestamp(contract["maturity_cutoff"]).normalize() + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
        self._cache = {}

    def public_case(self):
        c = self._contract
        return {"schema_version": VERSION, "question_kind": c["question_kind"], "question": c["question"],
                "data_kind": "REAL_FROZEN_DISCOVERY", "scope": c["scope"],
                "isolation_level": "LOGICAL_ONLY", "capability_id": c["capability_id"],
                "contract_sha256": hashlib.sha256(_canonical(c).encode()).hexdigest(),
                "signal_start": c["signal_start"], "signal_end": c["signal_end"],
                "maturity_cutoff": c["maturity_cutoff"], "month_count": int(self._months.nunique()),
                "asset_count": int(self._frame[self._columns["asset_id"]].nunique()),
                "formation_frequency": "monthly", "target_horizon_months": c["return_horizon_months"],
                "controls_requested": [x["name"] for x in c["controls"]],
                "feature_availability": deepcopy(c["feature_availability"]),
                "diagnostics": deepcopy(CATALOG), "factor_approval_allowed": False,
                "causal_identification_allowed": False, "limitations": list(_LIMITS)}

    def _feature(self, column, known_at, *, numeric=True):
        value = _numeric(self._frame[column]) if numeric else self._frame[column]
        if known_at is None:
            return value, {"status": self._contract["feature_availability"]["status"],
                           "missing_known_at": None, "late_count": None}
        known = _dates(self._frame[known_at])
        valid = known.notna() & known.le(self._formation)
        return value.where(valid), {"status": "TIMESTAMP_CHECKED_NOT_SOURCE_VERIFIED",
                                   "missing_known_at": int(known.isna().sum()),
                                   "late_count": int(known.gt(self._formation).sum())}

    def _outcome(self, column, known_at, horizon):
        value = _numeric(self._frame[column])
        known = _dates(self._frame[known_at])
        mature = (self._months + horizon).dt.end_time.le(self._cutoff)
        valid = known.notna() & known.le(self._cutoff) & known.gt(self._formation) & mature
        return value.where(valid), {"n_finite": int(value.notna().sum()),
            "n_usable": int((value.notna() & valid).sum()), "n_immature": int((~mature).sum()),
            "n_late_known_at": int(known.gt(self._cutoff).sum()),
            "n_invalid_known_at": int((known.isna() | known.le(self._formation)).sum()),
            "horizon_months": horizon}

    def _core(self):
        m, c = self._columns, self._contract
        signal, info = self._feature(m["signal"], m["signal_known_at"])
        returns, outcome = self._outcome(m["forward_return"], m["return_known_at"], c["return_horizon_months"])
        return signal, returns, info, outcome

    def _report(self, diagnostic):
        return {"diagnostic_id": diagnostic, "report_contract_version": VERSION,
                "status": "COMPUTED", "scope": "FROZEN_DISCOVERY_ONLY", "metrics": {},
                "evidence_scope": {"capability_id": self._contract["capability_id"],
                    "frame_sha256": self._contract["frame_sha256"],
                    "snapshot_sha256": self._contract["snapshot_sha256"],
                    "factor_definition_hash": self._contract["factor_definition_hash"],
                    "contract_sha256": hashlib.sha256(_canonical(self._contract).encode()).hexdigest()},
                "causal_identification": False, "limitations": list(_LIMITS)}

    def _unavailable(self, report, reason, datasets=()):
        report.update({"status": "NOT_COMPUTED", "reason": reason})
        if datasets:
            report["missing_datasets"] = list(datasets)
        return report

    def _audit(self, report):
        signal, returns, availability, maturity = self._core()
        n = len(self._frame)
        controls = {}
        for spec in self._contract["controls"]:
            values, info = self._feature(spec["column"], spec["known_at"], numeric=spec["kind"] == "numeric")
            controls[spec["name"]] = {**info, "missing_fraction": float(values.isna().mean())}
        counts = [x["late_count"] for x in controls.values()]
        # Fraction of rows with ANY late control, not sum of per-control counts.
        late_controls = pd.Series(False, index=self._frame.index)
        for spec in self._contract["controls"]:
            if spec["known_at"] is not None:
                late_controls |= _dates(self._frame[spec["known_at"]]).gt(self._formation)
        report["metrics"] = {
            "n_rows": n, "duplicate_key_count": int(self._frame.duplicated([self._columns["month"], self._columns["asset_id"]]).sum()),
            "late_signal_fraction": availability["late_count"] / n if availability["late_count"] is not None else None,
            "late_control_fraction": float(late_controls.mean()) if counts and all(x is not None for x in counts) else None,
            "missing_signal_fraction": float(signal.isna().mean()), "missing_return_fraction": float(returns.isna().mean()),
            "signal_availability": availability, "control_availability": controls,
            "availability_policy": deepcopy(self._contract["feature_availability"]), "return_maturity": maturity,
            "availability_rule": "features known by formation; outcome known and horizon matured by frozen cutoff",
            "historical_first_release_verified": False,
        }
        return report

    def _association(self, report):
        signal, returns, _, info = self._core()
        rows = []
        for month, indices in self._months.groupby(self._months).groups.items():
            s, r = signal.loc[indices], returns.loc[indices]
            valid = s.notna() & r.notna()
            row = {"month": str(month), "n_pairs": int(valid.sum()), "raw_ic": None, "gross_spread": None}
            if valid.sum() >= self._contract["min_cross_section"]:
                row["raw_ic"] = _ic(s[valid], r[valid])
                # Formation groups use all available signal rows, never select
                # the portfolio based on whether its future returns are known.
                s_ok = s.dropna()
                bins = np.floor((s_ok.rank(method="average") - .5) / len(s_ok) * 5).clip(0, 4)
                top, bottom = r.reindex(bins.index)[bins.eq(4)], r.reindex(bins.index)[bins.eq(0)]
                row.update({"top_count": len(top), "bottom_count": len(bottom),
                            "top_return_missing": int(top.isna().sum()), "bottom_return_missing": int(bottom.isna().sum())})
                if len(top) and len(bottom) and top.notna().all() and bottom.notna().all():
                    row["gross_spread"] = float(top.mean() - bottom.mean())
            rows.append(row)
        report["metrics"] = {name: self._summary(rows, name) for name in ("raw_ic", "gross_spread")}
        report["metrics"].update({"monthly": rows, "return_maturity": info,
            "portfolio": "monthly reformed equal-weight quintile difference; ties not split; not executable holdings"})
        if not any(row["raw_ic"] is not None for row in rows):
            return self._unavailable(report, "INSUFFICIENT_VALID_PAIRS")
        return report

    def _summary(self, rows, name, *, horizon=None):
        horizon = horizon or self._contract["return_horizon_months"]
        return _estimate([r["month"] for r in rows], [r.get(name) for r in rows],
                         lags=max(3, horizon - 1), minimum=max(self._contract["min_months"], horizon * 2))

    def _controlled_rows(self):
        signal, returns, _, _ = self._core()
        specs = self._contract["controls"]
        controls = {s["name"]: self._feature(s["column"], s["known_at"], numeric=s["kind"] == "numeric")[0]
                    for s in specs}
        rows = []
        for month, indices in self._months.groupby(self._months).groups.items():
            valid = signal.loc[indices].notna() & returns.loc[indices].notna()
            for values in controls.values():
                valid &= values.loc[indices].notna()
            common = valid[valid].index
            row = {"month": str(month), "n_common": len(common), "raw_ic": None,
                   "fully_adjusted_ic": None, "controlled_slope": None, "status": "INSUFFICIENT_SAMPLE"}
            matrices = {}
            for spec in specs:
                values = controls[spec["name"]].loc[common]
                if spec["kind"] == "numeric":
                    spread = values.std(ddof=0)
                    matrices[spec["name"]] = ((values - values.mean()) / spread).to_numpy()[:, None] if spread > 0 else np.empty((len(common), 0))
                else:
                    if values.nunique() > 20:
                        row["status"] = "TOO_MANY_CATEGORIES"
                        break
                    matrices[spec["name"]] = pd.get_dummies(values.astype(str), drop_first=True, dtype=float).to_numpy()
            else:
                covariates = np.column_stack(list(matrices.values())) if matrices else np.empty((len(common), 0))
                if len(common) >= max(self._contract["min_cross_section"], covariates.shape[1] + 5):
                    pair = np.column_stack((signal.loc[common], returns.loc[common])).astype(float)
                    row["raw_ic"] = _ic(pd.Series(pair[:, 0]), pd.Series(pair[:, 1]))
                    subsets = {"fully_adjusted_ic": list(matrices)}
                    if {"size", "liquidity"} <= matrices.keys():
                        subsets["size_liquidity_adjusted_ic"] = ["size", "liquidity"]
                    if "industry" in matrices:
                        subsets["sector_adjusted_ic"] = ["industry"]
                    for name, keys in subsets.items():
                        design = np.column_stack([np.ones(len(common)), *(matrices[k] for k in keys)])
                        residuals = pair - design @ np.linalg.lstsq(design, pair, rcond=None)[0]
                        variation = residuals.std(axis=0) > 1e-10 * np.maximum(pair.std(axis=0), 1e-12)
                        row[name] = _ic(pd.Series(residuals[:, 0]), pd.Series(residuals[:, 1])) if variation.all() else None
                    signal_std = pair[:, 0].std()
                    if signal_std > 0:
                        design = np.column_stack((np.ones(len(common)), covariates, (pair[:, 0] - pair[:, 0].mean()) / signal_std))
                        if np.linalg.matrix_rank(design) == design.shape[1]:
                            row["controlled_slope"] = float(np.linalg.lstsq(design, pair[:, 1], rcond=None)[0][-1])
                    for label, adjusted in (("size_liquidity_attenuation", "size_liquidity_adjusted_ic"),
                                            ("sector_attenuation", "sector_adjusted_ic"),
                                            ("full_attenuation", "fully_adjusted_ic")):
                        if row.get(adjusted) is not None and row["raw_ic"] is not None:
                            row[label] = row["raw_ic"] - row[adjusted]
                    row["status"] = "COMPUTED" if row["fully_adjusted_ic"] is not None else "NO_RESIDUAL_VARIATION"
            rows.append(row)
        return rows

    def _controls(self, report):
        if not self._contract["controls"]:
            return self._unavailable(report, "NO_CONTROL_CONTRACT", ["formation_time_controls"])
        rows = self._controlled_rows()
        fields = sorted({key for row in rows for key in row if key.endswith("_ic") or key.endswith("_attenuation")})
        # Raw vs fully-adjusted aggregate also uses the same months, not just
        # the same asset rows within each month. Pair-specific attenuation is
        # already null whenever either side is not estimable.
        report["metrics"] = {name: self._summary(rows, name) for name in fields}
        comparable = [row for row in rows if row["raw_ic"] is not None and row["fully_adjusted_ic"] is not None]
        report["metrics"]["raw_ic"] = self._summary(comparable, "raw_ic")
        report["metrics"]["fully_adjusted_ic"] = self._summary(comparable, "fully_adjusted_ic")
        report["metrics"].update({"monthly": rows, "sample_policy": "identical complete-case rows within every month",
            "raw_fully_adjusted_matched_months": len(comparable),
            "controls_applied": [x["name"] for x in self._contract["controls"]],
            "industry_control_available": any(x["name"] == "industry" for x in self._contract["controls"])})
        report["limitations"].append("Linear controls residualize both raw signal and return, then rank residuals; this is not the admission gate's one-sided rank neutralization.")
        if not report["metrics"]["industry_control_available"]:
            report["limitations"].append("Historical industry classification was not supplied; no sector-adjusted estimate is fabricated.")
        if not any(row["fully_adjusted_ic"] is not None for row in rows):
            return self._unavailable(report, "NO_ESTIMABLE_CONTROLLED_ASSOCIATION")
        return report

    def _economic(self, report):
        spec = self._contract["economic"]
        if spec is None:
            return self._unavailable(report, "NO_ECONOMIC_OUTCOME_CONTRACT", ["hypothesis_aligned_economic_outcome"])
        signal, returns, _, _ = self._core()
        economic, info = self._outcome(spec["column"], spec["known_at"], spec["horizon_months"])
        return_horizon = spec.get("return_horizon_months", self._contract["return_horizon_months"])
        if "return_column" in spec:
            returns, _ = self._outcome(spec["return_column"], spec["return_known_at"], return_horizon)
        measure = spec.get("measurement_kind", "CHANGE")
        signal_metric = "signal_to_economic_level_ic" if measure == "LEVEL" else "signal_to_economic_change_ic"
        return_metric = "economic_level_to_return_ic" if measure == "LEVEL" else "economic_change_to_return_ic"
        rows = []
        for month, indices in self._months.groupby(self._months).groups.items():
            s, e, r = signal.loc[indices], economic.loc[indices], returns.loc[indices]
            valid = s.notna() & e.notna() & r.notna()
            row = {"month": str(month), "n_common": int(valid.sum()),
                   signal_metric: None, return_metric: None}
            if valid.sum() >= self._contract["min_cross_section"]:
                row[signal_metric] = _ic(s[valid], e[valid])
                row[return_metric] = _ic(e[valid], r[valid])
            rows.append(row)
        horizon = max(spec["horizon_months"], return_horizon)
        comparable = [row for row in rows if row[signal_metric] is not None
                      and row[return_metric] is not None]
        report["metrics"] = {name: self._summary(comparable, name, horizon=horizon) for name in
                             (signal_metric, return_metric)}
        report["metrics"].update({"monthly": rows, "outcome_maturity": info,
            "economic_measurement_kind": measure, "economic_variable_column": spec["column"],
            "economic_dataset_id": spec["dataset_id"],
            "economic_horizon_months": spec["horizon_months"], "return_horizon_months": return_horizon,
            "same_horizon": spec["horizon_months"] == return_horizon,
            "joint_estimable_months": len(comparable),
            "sample_policy": "same signal/economic/return complete-case rows for both associations",
            "causal_identification": False, "temporal_mediation_identified": False})
        report["limitations"].append("Economic outcomes are future labels, not formation features. Selection/missing exits can bias observed associations. Two correlations do not identify mediation.")
        if spec["horizon_months"] != return_horizon:
            report["limitations"].append("Economic and return horizons differ; the longer-horizon economic outcome cannot explain the earlier return as a temporally established pathway.")
        if not comparable:
            return self._unavailable(report, "NO_MATURE_COMMON_ECONOMIC_SAMPLE")
        return report

    def _regime(self, report):
        spec = self._contract["regime"]
        if spec is None:
            return self._unavailable(report, "NO_REGIME_CONTRACT", ["formation_time_regime_context"])
        if not self._contract["controls"]:
            return self._unavailable(report, "NO_CONTROL_CONTRACT", ["formation_time_controls"])
        values, _ = self._feature(spec["column"], spec["known_at"], numeric=False)
        if not set(values.dropna().astype(str)) <= set(spec["labels"]) | {"UNKNOWN"}:
            return self._unavailable(report, "UNDECLARED_REGIME_LABEL")
        states = {}
        for month, indices in self._months.groupby(self._months).groups.items():
            observed = values.loc[indices].dropna().astype(str).unique()
            if len(observed) > 1:
                return self._unavailable(report, "INCONSISTENT_MARKET_STATE_WITHIN_MONTH")
            states[str(month)] = observed[0] if len(observed) else "UNKNOWN"
        rows = self._controlled_rows()
        # Missing months/states cannot invent a new episode of the same state.
        episodes, last, count = {}, None, 0
        for month in sorted(states):
            state = states[month]
            if state != "UNKNOWN":
                count += state != last
                last = state
                episodes[month] = count
        summaries = {}
        for state in spec["labels"]:
            subset = [row for row in rows if states[row["month"]] == state]
            support = len({episodes[r["month"]] for r in subset if r["controlled_slope"] is not None})
            estimate = self._summary(subset, "controlled_slope")
            estimate["n_episodes"] = support
            if support < 3:
                estimate.update({"standard_error": None, "ci95": None, "status": "INSUFFICIENT_REGIME_EPISODES"})
            summaries[state] = estimate
        reference, target = spec["contrast"]
        chosen = [row for row in rows if states[row["month"]] in {reference, target}]
        design = [[1, int(states[row["month"]] == target)] for row in chosen]
        interaction = _estimate([r["month"] for r in chosen], [r["controlled_slope"] for r in chosen],
                                design=np.asarray(design).reshape((-1, 2)), coefficient=1,
                                minimum=2 * self._contract["min_months"],
                                lags=max(3, self._contract["return_horizon_months"] - 1))
        if any(summaries[state]["ci95"] is None for state in (reference, target)):
            interaction.update({"standard_error": None, "ci95": None, "status": "INSUFFICIENT_REGIME_SUPPORT"})
        report["metrics"] = {"regimes": summaries, "interaction": interaction,
            "contrast": {"reference": reference, "target": target},
            "estimand": "target minus reference in controlled monthly return-on-standardized-signal slopes",
            "unknown_months": sum(x == "UNKNOWN" for x in states.values()),
            "definition_sha256": spec["definition_sha256"], "pit_status": spec["pit_status"]}
        report["limitations"].append("The contrast was declared before results; neither differing subgroup significance nor episode counts establish a causal or independent replication claim.")
        if interaction["mean"] is None:
            return self._unavailable(report, "NO_ESTIMABLE_PREREGISTERED_CONTRAST")
        return report

    def _execution(self, report):
        spec = self._contract["execution"]
        if spec is None:
            return self._unavailable(report, "NO_AUTHENTICATED_HOLDINGS_RETURN_COST_CONTRACT",
                                     ["same_window_holdings_and_cost_measurement"])
        columns = [spec[k] for k in ("gross", "net", "cost", "turnover", "known_at")]
        series = {key: self._outcome(spec[key], spec["known_at"], spec["horizon_months"])[0]
                  for key in ("gross", "net", "cost", "turnover")}
        records = []
        for month, indices in self._months.groupby(self._months).groups.items():
            block = self._frame.loc[indices, columns]
            # Monthly aggregate may repeat on asset rows, but must be identical.
            if any(block[column].nunique(dropna=False) != 1 for column in columns):
                return self._unavailable(report, "INCONSISTENT_MONTHLY_PORTFOLIO_MEASUREMENT")
            record = {"month": str(month)}
            for metric, key in (("gross_spread", "gross"), ("net_spread", "net"),
                                ("estimated_cost", "cost"), ("turnover", "turnover")):
                value = series[key].loc[indices[0]]
                record[metric] = float(value) if pd.notna(value) else None
            metric_names = ("gross_spread", "net_spread", "estimated_cost", "turnover")
            if all(record[k] is not None for k in metric_names):
                if (record["estimated_cost"] < 0 or record["turnover"] < 0 or not np.isclose(
                        record["gross_spread"] - record["estimated_cost"], record["net_spread"], atol=1e-10, rtol=1e-8)):
                    return self._unavailable(report, "PORTFOLIO_COST_IDENTITY_FAILED")
            else:
                record["unavailable_fields"] = [k for k in metric_names if record[k] is None]
                for metric in metric_names:
                    record[metric] = None
            records.append(record)
        report["metrics"] = {name: self._summary(records, name, horizon=spec["horizon_months"]) for name in
                             ("gross_spread", "net_spread", "estimated_cost", "turnover")}
        report["metrics"].update({"monthly": records, "holdings_sha256": spec["holdings_sha256"],
            "return_contract_sha256": spec["return_contract_sha256"], "cost_model_sha256": spec["cost_model_sha256"],
            "timing_contract": spec["timing_contract"], "measurement_source": "supplied_frozen_portfolio_artifact",
            "holdings_recomputed_here": False,
            "sample_policy": "identical complete calendar months for gross, net, cost and turnover"})
        report["limitations"].append("This adapter authenticates supplied measurement identity and arithmetic; it does not simulate fills or independently reverify underlying holdings.")
        if not any(row["net_spread"] is not None for row in records):
            return self._unavailable(report, "NO_MATURE_PORTFOLIO_MEASUREMENT")
        return report

    def run(self, diagnostic_id):
        if diagnostic_id not in CATALOG:
            raise ValueError("Unregistered diagnostic")
        if diagnostic_id in self._cache:
            return deepcopy(self._cache[diagnostic_id])
        report = self._report(diagnostic_id)
        if diagnostic_id != "input_audit" and self._frame.duplicated([self._columns["month"], self._columns["asset_id"]]).any():
            report = self._unavailable(report, "DUPLICATE_INPUT_KEYS")
        else:
            method = {"input_audit": self._audit, "association": self._association, "controls": self._controls,
                      "execution_cost": self._execution, "regime_interaction": self._regime, "economic_link": self._economic}[diagnostic_id]
            report = method(report)
        # No NaN/infinity may enter evidence ledgers or planner prompts.
        report = json.loads(_canonical(report))
        self._cache[diagnostic_id] = report
        return deepcopy(report)
