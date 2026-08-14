"""Static sampling and lookback limits for factor research.

The cached Silver panel may retain older history for source auditing.  Factor
code, however, only receives rows on or after ``RESEARCH_INPUT_START``.  The
common IC evaluation begins later, after the longest permitted warm-up.
"""
from __future__ import annotations

import ast
import hashlib
import math
import re

import numpy as np
import pandas as pd


RESEARCH_INPUT_START = pd.Period("2015-01", freq="M")
COMMON_EVALUATION_START = pd.Period("2018-03", freq="M")
MAX_FACTOR_LOOKBACK_MONTHS = 36
RESEARCH_MARKETS = frozenset({"KOSPI", "KOSDAQ"})
TRADING_DAYS_PER_MONTH = 21

_HISTORY_METHODS = frozenset({"diff", "pct_change", "rolling", "shift"})
_DIRECTIONAL_HISTORY_METHODS = frozenset({"diff", "pct_change", "shift"})
_MONTH_PARAMETER_NAMES = frozenset({"lookback"})
_FORBIDDEN_FACTOR_PREFIXES = ("f_", "fwd_")
CANDIDATE_LABEL_COLUMNS = frozenset({
    # ``total_return_close`` is reconstructed with the latest dividend
    # revision and is therefore an ex-post realized label, never a historical
    # factor feature. ``return_close`` is the ambiguous legacy alias that used
    # to expose it and is forbidden permanently.
    "total_return_close",
    "return_close",
})
UNCERTIFIED_PIT_FEATURE_COLUMNS = frozenset({
    # These aggregates are reconstructed from the latest-corrected dividend
    # ledger.  Until Silver publishes a historical-vintage/known-at contract,
    # they cannot be exposed to candidate code, even when omitted from needs.
    "dividend_cash_ttm",
    "dividend_event_count_ttm",
})
_FORBIDDEN_CANDIDATE_INPUTS = (
    CANDIDATE_LABEL_COLUMNS | UNCERTIFIED_PIT_FEATURE_COLUMNS
)
_FORBIDDEN_FACTOR_COLUMNS = _FORBIDDEN_CANDIDATE_INPUTS | frozenset({
    # Raw close is not split-adjusted.  Exposing it would let a candidate
    # silently mix stock splits and rights events into a historical return
    # feature even though ``adj_close`` is the only approved price feature.
    "close",
    # Universe-construction metadata may encode pre-2015 listing history or a
    # source-side eligibility decision.  The universe gate may inspect these,
    # but candidate strategy code must not be able to reverse-engineer it.
    "Name",
    "Market",
    "age_days",
    "amount",
    "available_date",
    "dataset_start",
    "first_seen",
    "in_universe",
    "instrument_type",
    "is_distress",
    "is_reit",
    "is_spac",
    "listed_from",
    "listed_to",
    "me_date",
    "ok_age",
    "ok_common",
    "ok_market",
    "ok_price",
    "quality_run_id",
    "seasoned",
    "ticker_match_count",
    "total_return_quality_run_id",
})


def _positive_int(value, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}는 양의 정수여야 합니다: {value!r}")
    integer = int(value)
    if value != integer or integer < 1:
        raise ValueError(f"{label}는 양의 정수여야 합니다: {value!r}")
    return integer


def _parameter_horizons(params: dict) -> list[int]:
    horizons: list[int] = []
    for key, value in params.items():
        if (
            key in _MONTH_PARAMETER_NAMES
            or key.endswith("_months")
            or key.endswith("_lag")
        ):
            horizons.append(_positive_int(value, label=key))

    if "window_days" in params:
        window_days = _positive_int(params["window_days"], label="window_days")
        horizons.append(math.ceil(window_days / TRADING_DAYS_PER_MONTH))

    if "history_years" in params:
        years = _positive_int(params["history_years"], label="history_years")
        months_per_year = _positive_int(
            params.get("months_per_year"), label="months_per_year",
        )
        horizons.append(years * months_per_year)
    return horizons


def _history_argument(call: ast.Call) -> ast.AST | None:
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg in {"periods", "window"}:
            return keyword.value
    return None


def _safe_integer_expression(node: ast.AST, params: dict) -> int:
    """Resolve a time-series horizon from literals and declared parameters."""
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return int(node.value)
    if isinstance(node, ast.Name):
        key = node.id.lower()
        if key not in params:
            raise ValueError(
                f"시계열 horizon {node.id}를 params에서 찾을 수 없습니다"
            )
        return _positive_int(params[key], label=key)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_integer_expression(node.operand, params)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv),
    ):
        left = _safe_integer_expression(node.left, params)
        right = _safe_integer_expression(node.right, params)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ValueError("시계열 horizon의 0 나눗셈은 허용하지 않습니다")
        return left // right
    raise ValueError("시계열 horizon 표현식을 params로 해석할 수 없습니다")


def _contains_explicit_negative(node: ast.AST) -> bool:
    """Return whether an expression contains an explicit unary minus."""
    return any(
        isinstance(part, ast.UnaryOp) and isinstance(part.op, ast.USub)
        for part in ast.walk(node)
    )


def factor_lookback_months(*, source: str, params: dict) -> int:
    """Infer the declared maximum history used by one factor definition.

    Month-valued parameters and literal pandas time-series calls are included.
    Daily Silver features are converted using 21 trading days per month.  A
    time-series definition whose horizon cannot be resolved is rejected rather
    than being treated as a zero-lookback signal.
    """
    horizons = _parameter_horizons(params)
    declared_horizon = max(horizons, default=0)
    if not source.strip():
        raise ValueError("팩터 소스를 읽을 수 없어 lookback을 검증할 수 없습니다")

    history_calls = 0
    if source:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # ``inspect.getsource`` can return only the trailing fragment that
            # contains an inline lambda.  The module itself is valid, so scan
            # that fragment conservatively instead of treating it as bad code.
            for method in _HISTORY_METHODS:
                history_calls += source.count(f".{method}(")
            for match in re.finditer(
                r"\.(diff|pct_change|rolling|shift)\(\s*(-?\d+)", source,
            ):
                method, raw_horizon = match.groups()
                horizon = int(raw_horizon)
                if method in _DIRECTIONAL_HISTORY_METHODS and horizon < 0:
                    raise ValueError(
                        f"{method}의 음수 horizon은 미래 행을 참조하므로 금지됩니다"
                    )
                if horizon < 1:
                    raise ValueError(f"{method} horizon은 양수여야 합니다: {horizon}")
                horizons.append(horizon)
            if ".pct_change()" in source:
                horizons.append(1)
            resolved_calls = len(re.findall(
                r"\.(?:diff|pct_change|rolling|shift)\(\s*-?\d+", source,
            )) + source.count(".pct_change()")
            if history_calls > resolved_calls and declared_horizon <= MAX_FACTOR_LOOKBACK_MONTHS:
                raise ValueError(
                    "시계열 연산의 모든 horizon을 params로 해석할 수 있어야 합니다"
                )
        else:
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in _HISTORY_METHODS
                ):
                    continue
                history_calls += 1
                argument = _history_argument(node)
                if node.func.attr == "pct_change" and argument is None:
                    horizons.append(1)
                    continue
                if argument is None:
                    if declared_horizon <= MAX_FACTOR_LOOKBACK_MONTHS:
                        raise ValueError(
                            f"{node.func.attr} horizon을 params로 해석할 수 없습니다"
                        )
                    continue
                if (
                    node.func.attr in _DIRECTIONAL_HISTORY_METHODS
                    and _contains_explicit_negative(argument)
                ):
                    raise ValueError(
                        f"{node.func.attr}의 음수 horizon은 미래 행을 "
                        "참조하므로 금지됩니다"
                    )
                try:
                    horizon = _safe_integer_expression(argument, params)
                except ValueError:
                    # A legacy over-limit definition such as the preserved
                    # five-year seasonality file is still classifiable as
                    # disabled from its explicit 60-month parameters.
                    if declared_horizon <= MAX_FACTOR_LOOKBACK_MONTHS:
                        raise
                    continue
                if (
                    node.func.attr in _DIRECTIONAL_HISTORY_METHODS
                    and horizon < 0
                ):
                    raise ValueError(
                        f"{node.func.attr}의 음수 horizon은 미래 행을 "
                        "참조하므로 금지됩니다"
                    )
                if horizon < 1:
                    raise ValueError(
                        f"{node.func.attr} horizon은 양수여야 합니다: {horizon}"
                    )
                horizons.append(horizon)

    if history_calls and not horizons:
        raise ValueError(
            "시계열 연산의 최대 lookback_months를 params로 선언해야 합니다"
        )
    return max(horizons, default=0)


def assert_allowed_lookback(*, name: str, source: str, params: dict) -> int:
    """Return the declared lookback or reject definitions beyond 36 months."""
    lookback = factor_lookback_months(source=source, params=params)
    if lookback > MAX_FACTOR_LOOKBACK_MONTHS:
        raise ValueError(
            f"{name}: 최대 lookback {lookback}개월은 연구 상한 "
            f"{MAX_FACTOR_LOOKBACK_MONTHS}개월을 초과합니다"
        )
    return lookback


def research_input_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only 2015+ KRX common-stock rows to factor code."""
    required = {"ym", "instrument_type", "market"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"연구 입력 패널 필수 컬럼 누락: {sorted(missing)}")
    months = pd.PeriodIndex(frame["ym"], freq="M")
    scoped = frame.loc[
        (months >= RESEARCH_INPUT_START)
        & frame["instrument_type"].eq("common_stock").to_numpy()
        & frame["market"].isin(RESEARCH_MARKETS).to_numpy(),
    ].copy()
    if scoped.empty:
        raise ValueError(
            f"연구 입력 하한 {RESEARCH_INPUT_START} 이후 KRX common_stock "
            "Silver 행이 없습니다"
        )
    if pd.PeriodIndex(scoped["ym"], freq="M").min() < RESEARCH_INPUT_START:
        raise RuntimeError("연구 입력 하한보다 이른 행이 factor view에 노출됐습니다")
    if not scoped["instrument_type"].eq("common_stock").all():
        raise RuntimeError("보통주가 아닌 행이 factor view에 노출됐습니다")
    if not scoped["market"].isin(RESEARCH_MARKETS).all():
        raise RuntimeError("KOSPI/KOSDAQ 외 시장 행이 factor view에 노출됐습니다")
    return scoped


def factor_compute_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the only columns a candidate factor is allowed to inspect.

    Forward-return labels belong to the evaluator, cached factor columns belong
    to relationship/parity checks, and universe/lineage metadata belongs to the
    authenticated panel gate.  Candidate code receives none of those fields;
    only certified contemporaneous PIT inputs (including ``market``) remain.
    """
    assert_research_input_frame(frame)
    forbidden = [
        column for column in frame.columns
        if (
            column in _FORBIDDEN_FACTOR_COLUMNS
            or str(column).startswith(_FORBIDDEN_FACTOR_PREFIXES)
        )
    ]
    output = frame.drop(columns=forbidden, errors="ignore").copy()
    # pandas propagates ``DataFrame.attrs`` through copies. Silver contract,
    # coverage, and lineage evidence belong to the authenticated evaluator,
    # not to candidate strategy code.
    output.attrs.clear()
    leaked_labels = (
        CANDIDATE_LABEL_COLUMNS
        | {column for column in output if str(column).startswith("fwd_")}
    ) & set(output.columns)
    if leaked_labels:
        raise RuntimeError(
            "후보 입력에 ex-post forward label이 노출됐습니다: "
            f"{sorted(leaked_labels)}"
        )
    return output


def forbidden_candidate_inputs(columns) -> list[str]:
    """Return label-only or uncertified PIT fields declared as features."""
    return sorted(set(columns) & _FORBIDDEN_CANDIDATE_INPUTS)


def compute_factor(factor, frame: pd.DataFrame) -> pd.Series:
    """Compute each signal month from only its declared trailing window.

    Static source checks are useful, but they cannot prove that every pandas
    expression is causal.  The authoritative calculation therefore never
    gives candidate code the full research history: for each output month it
    supplies the current cross-section plus at most the declared number of
    prior months, then keeps only that month's output.  This makes the 36-month
    ceiling an execution boundary for every month rather than a sampled
    after-the-fact check.
    """
    visible = factor_compute_frame(frame)
    lookback = assert_allowed_lookback(
        name=factor.name, source=factor.source, params=factor.params,
    )
    months = pd.PeriodIndex(visible["ym"], freq="M")
    output = np.full(len(visible), np.nan, dtype=float)
    for anchor in sorted(pd.unique(months)):
        local_mask = (months >= anchor - lookback) & (months <= anchor)
        local = visible.loc[local_mask].copy()
        observed = factor.compute(local)
        if not isinstance(observed, pd.Series) or not observed.index.equals(
            local.index
        ):
            raise ValueError(
                f"{factor.name}: 후보 출력은 입력과 같은 index의 Series여야 합니다"
            )
        local_months = pd.PeriodIndex(local["ym"], freq="M")
        anchor_values = pd.to_numeric(
            observed.loc[local_months == anchor], errors="raise",
        ).to_numpy(dtype=float)
        output[np.flatnonzero(months == anchor)] = anchor_values
    return pd.Series(output, index=frame.index)


_AUTHORITATIVE_FACTOR_BINDINGS_ATTR = (
    "factor_research_authoritative_factor_bindings_v1"
)


def _factor_column_digest(values: pd.Series) -> str:
    """Bind one computed factor column to its exact index, dtype, and values."""
    hashed = pd.util.hash_pandas_object(values, index=True).to_numpy(
        dtype="uint64", copy=False,
    )
    payload = b"\0".join((
        str(values.dtype).encode("utf-8"),
        str(len(values)).encode("ascii"),
        hashed.tobytes(),
    ))
    return hashlib.sha256(payload).hexdigest()


def bind_authoritative_factor_column(factor, frame: pd.DataFrame, column: str) -> None:
    """Record that ``column`` came from this engine's bounded computation.

    The binding is invocation-local DataFrame metadata, not a persistent factor
    cache.  It lets the integrity gate reuse the already-computed values as the
    first side of its determinism comparison while retaining an independent
    second computation and the causal anchor checks.
    """
    if column not in frame:
        raise ValueError(f"authoritative factor column이 없습니다: {column}")
    values = frame[column]
    bindings = dict(frame.attrs.get(_AUTHORITATIVE_FACTOR_BINDINGS_ATTR) or {})
    bindings[column] = {
        "definition_hash": factor.definition_hash,
        "predicted_sign": int(factor.predicted_sign),
        "row_count": len(frame),
        "value_digest": _factor_column_digest(values),
    }
    frame.attrs[_AUTHORITATIVE_FACTOR_BINDINGS_ATTR] = bindings


def authoritative_factor_values(
    factor, frame: pd.DataFrame, column: str,
) -> pd.Series | None:
    """Return bound raw values only when the exact invocation binding matches."""
    binding = (
        frame.attrs.get(_AUTHORITATIVE_FACTOR_BINDINGS_ATTR) or {}
    ).get(column)
    if not isinstance(binding, dict) or column not in frame:
        return None
    values = frame[column]
    expected = {
        "definition_hash": factor.definition_hash,
        "predicted_sign": int(factor.predicted_sign),
        "row_count": len(frame),
        "value_digest": _factor_column_digest(values),
    }
    if binding != expected:
        return None
    return pd.to_numeric(values, errors="raise") * factor.predicted_sign


def causal_lookback_check(
    factor,
    frame: pd.DataFrame,
    reference: pd.Series,
) -> tuple[bool, str]:
    """Empirically reject dependencies outside each anchor's prior 36 months.

    Recompute deterministic anchors spanning the full common evaluation era:
    the first usable month, 25/50/75% positions, and the latest three usable
    months.  This catches definitions that leak only in an older branch as well
    as unconditional expanding/full-history calculations, without the cost of
    recomputing every month.
    """
    assert_research_input_frame(frame)
    if not isinstance(reference, pd.Series) or not reference.index.equals(frame.index):
        return False, "기준 출력이 입력 index의 Series가 아닙니다"
    months = pd.PeriodIndex(frame["ym"], freq="M")
    valid_months = []
    for anchor in sorted(pd.unique(months)):
        if anchor < COMMON_EVALUATION_START:
            continue
        anchor_mask = months == anchor
        expected = pd.to_numeric(reference.loc[anchor_mask], errors="coerce")
        if np.isfinite(expected.to_numpy(dtype=float)).any():
            valid_months.append(anchor)
    if not valid_months:
        return False, "36개월 인과성 검사를 수행할 유효 출력월이 없습니다"

    last = len(valid_months) - 1
    positions = {
        0,
        round(last * .25),
        round(last * .50),
        round(last * .75),
        max(0, last - 2),
        max(0, last - 1),
        last,
    }
    selected = [valid_months[position] for position in sorted(positions)]
    for anchor in selected:
        anchor_mask = months == anchor
        expected = pd.to_numeric(reference.loc[anchor_mask], errors="coerce")
        start = anchor - MAX_FACTOR_LOOKBACK_MONTHS
        local_mask = (months >= start) & (months <= anchor)
        local = frame.loc[local_mask].copy()
        try:
            observed = compute_factor(factor, local)
        except Exception as exc:
            return False, (
                f"{anchor}의 36개월 제한 재계산 실패: "
                f"{type(exc).__name__}: {exc}"
            )
        if not isinstance(observed, pd.Series) or not observed.index.equals(local.index):
            return False, f"{anchor}의 제한 재계산 출력 index가 다릅니다"
        local_anchor = pd.PeriodIndex(local["ym"], freq="M") == anchor
        actual = pd.to_numeric(observed.loc[local_anchor], errors="coerce")
        expected_anchor = expected.reindex(actual.index)
        expected_values = expected_anchor.to_numpy(dtype=float)
        actual_values = actual.to_numpy(dtype=float)
        finite_expected = np.isfinite(expected_values)
        if not np.array_equal(finite_expected, np.isfinite(actual_values)):
            return False, f"{anchor} 출력 결측 패턴이 36개월 제한 재계산과 다릅니다"
        if finite_expected.any() and not np.allclose(
            expected_values[finite_expected], actual_values[finite_expected],
            rtol=1e-10, atol=1e-12, equal_nan=True,
        ):
            return False, f"{anchor} 출력이 36개월 이전 행에 의존합니다"
    return True, (
        f"평가기간 전반의 결정적 anchor {len(selected)}개에서 "
        "36개월 제한 재계산 일치"
    )


def assert_research_input_frame(frame: pd.DataFrame) -> None:
    """Fail if factor code can see pre-2015 or non-common-stock rows."""
    if (
        frame.empty
        or "ym" not in frame
        or "instrument_type" not in frame
        or "market" not in frame
    ):
        raise ValueError("팩터 계산용 연구 입력 패널이 비었습니다")
    earliest = pd.PeriodIndex(frame["ym"], freq="M").min()
    if earliest < RESEARCH_INPUT_START:
        raise ValueError(
            f"팩터 계산 입력은 {RESEARCH_INPUT_START}부터여야 합니다: "
            f"현재 시작 {earliest}"
        )
    if not frame["instrument_type"].eq("common_stock").all():
        raise ValueError("팩터 계산 입력에는 KRX common_stock만 허용됩니다")
    if not frame["market"].isin(RESEARCH_MARKETS).all():
        raise ValueError("팩터 계산 입력에는 KOSPI/KOSDAQ만 허용됩니다")
