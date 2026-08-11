"""Load agent-authored research candidates without changing the builtin catalog."""
from __future__ import annotations

import ast
import hashlib
import linecache
import sys
import types
from collections.abc import Mapping
from pathlib import Path

from engine.factors import Factor, REGISTRY, Registry
from engine.research_policy import (
    MAX_FACTOR_LOOKBACK_MONTHS,
    factor_lookback_months,
)


CANDIDATE_DIR = Path(__file__).with_name("candidates")
RESEARCH_SPECS: dict[str, dict] = {}
DISABLED_RESEARCH_SPECS: dict[str, dict] = {}
_UNCERTIFIED_PIT_FEATURES = frozenset({
    "dividend_cash_ttm", "dividend_event_count_ttm",
})
REQUIRED_SPEC_FIELDS = {
    "thesis", "mechanism", "falsification", "expected_relationship", "data_notes",
}
_ALLOWED_CALL_NAMES = frozenset({"Factor", "range"})
_ALLOWED_ATTRIBUTES = frozenset({
    # Exact surface currently required by the checked-in single-factor
    # strategies.  This is intentionally an allowlist rather than a blacklist:
    # adding a new pandas operation requires an explicit code-review decision.
    "Series", "apply", "astype", "clip", "concat", "copy", "count", "cov",
    "eq", "fillna", "groupby", "gt", "index", "kurt", "loc", "log", "max",
    "mean", "min", "notna", "pct_change", "period_range", "pow", "prod",
    "rank", "reindex", "reset_index", "rolling", "set_index", "shift", "skew",
    "sort_values", "sqrt", "std", "to_numpy", "transform", "var", "where",
})
_BANNED_LOADED_NAMES = frozenset({
    "Path", "__builtins__", "__import__", "breakpoint", "compile", "eval",
    "exec", "getattr", "globals", "input", "locals", "open", "print",
    "setattr", "vars",
})
_GROUPBY_HISTORY_TERMINALS = frozenset({
    "apply", "count", "cov", "kurt", "max", "mean", "min", "prod",
    "rank", "skew", "std", "transform", "var",
})
_ROLLING_REDUCERS = frozenset({
    "apply", "count", "cov", "kurt", "max", "mean", "min", "prod",
    "skew", "std", "var",
})


def _simple_aliases(function: ast.FunctionDef) -> dict[str, ast.AST]:
    aliases: dict[str, ast.AST] = {}
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            aliases[node.targets[0].id] = node.value
    return aliases


def _resolved_nodes(
    node: ast.AST,
    aliases: Mapping[str, ast.AST],
    seen: frozenset[str] = frozenset(),
):
    """Walk an expression while expanding simple local aliases."""
    yield node
    if isinstance(node, ast.Name) and node.id in aliases and node.id not in seen:
        yield from _resolved_nodes(
            aliases[node.id], aliases, seen | {node.id},
        )
        return
    for child in ast.iter_child_nodes(node):
        yield from _resolved_nodes(child, aliases, seen)


def _subscript_label(node: ast.Subscript) -> str | None:
    value = node.slice
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value.lower()
    return None


def _group_axis(call: ast.Call, aliases: Mapping[str, ast.AST]) -> str:
    if not call.args:
        return "unknown"
    group_key = call.args[0]
    has_month = _is_preserved_group_key(group_key, "ym", aliases)
    has_asset = _is_preserved_group_key(group_key, "asset_id", aliases)
    if has_month:
        return "cross_sectional"
    if has_asset:
        return "asset_history"
    return "unknown"


def _is_preserved_group_key(
    node: ast.AST,
    label: str,
    aliases: Mapping[str, ast.AST],
    seen: frozenset[str] = frozenset(),
) -> bool:
    """Recognize exact month/asset keys, not arbitrary expressions using them."""
    if isinstance(node, ast.Name) and node.id in aliases and node.id not in seen:
        return _is_preserved_group_key(
            aliases[node.id], label, aliases, seen | {node.id},
        )
    if isinstance(node, ast.Subscript):
        return _subscript_label(node) == label
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(
            _is_preserved_group_key(item, label, aliases, seen)
            for item in node.elts
        )
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        # A positive lag of the exact month key still denotes one historical
        # cross-section. GroupBy itself preserves the receiver's key values.
        if node.func.attr in {"groupby", "shift"}:
            return _is_preserved_group_key(
                node.func.value, label, aliases, seen,
            )
    return False


def _attribute_calls(
    node: ast.AST, attr: str, aliases: Mapping[str, ast.AST],
) -> list[ast.Call]:
    return [
        part for part in _resolved_nodes(node, aliases)
        if isinstance(part, ast.Call)
        and isinstance(part.func, ast.Attribute)
        and part.func.attr == attr
    ]


def _receiver_groupbys(
    node: ast.AST,
    aliases: Mapping[str, ast.AST],
    seen: frozenset[str] = frozenset(),
) -> list[ast.Call]:
    """Follow only a method receiver chain, not the expression's data lineage."""
    if isinstance(node, ast.Name) and node.id in aliases and node.id not in seen:
        return _receiver_groupbys(
            aliases[node.id], aliases, seen | {node.id},
        )
    if isinstance(node, ast.Subscript):
        return _receiver_groupbys(node.value, aliases, seen)
    if isinstance(node, ast.Attribute):
        return _receiver_groupbys(node.value, aliases, seen)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "groupby":
            return [node]
        # Calls such as concat/log create a new object and are not a GroupBy
        # receiver merely because one of their arguments originated there.
        if node.func.attr in _ALLOWED_ATTRIBUTES - {"concat", "log", "sqrt"}:
            return _receiver_groupbys(node.func.value, aliases, seen)
    return []


def _receiver_has_method(
    node: ast.AST,
    method: str,
    aliases: Mapping[str, ast.AST],
    seen: frozenset[str] = frozenset(),
) -> bool:
    if isinstance(node, ast.Name) and node.id in aliases and node.id not in seen:
        return _receiver_has_method(
            aliases[node.id], method, aliases, seen | {node.id},
        )
    if isinstance(node, ast.Subscript):
        return _receiver_has_method(node.value, method, aliases, seen)
    if isinstance(node, ast.Attribute):
        return _receiver_has_method(node.value, method, aliases, seen)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr == method or _receiver_has_method(
            node.func.value, method, aliases, seen,
        )
    return False


def _bounded_rolling_lambda(node: ast.AST) -> bool:
    """Accept only ``lambda values: values.rolling(...).reducer()`` shapes."""
    if not isinstance(node, ast.Lambda) or len(node.args.args) != 1:
        return False
    parameter = node.args.args[0].arg
    if not (
        isinstance(node.body, ast.Call)
        and isinstance(node.body.func, ast.Attribute)
        and node.body.func.attr in _ROLLING_REDUCERS
        and _attribute_calls(node.body.func.value, "rolling", {})
    ):
        return False
    saw_parameter = False
    unsafe_parameter = False

    def visit(part: ast.AST, *, under_rolling: bool = False) -> None:
        nonlocal saw_parameter, unsafe_parameter
        if (
            isinstance(part, ast.Call)
            and isinstance(part.func, ast.Attribute)
            and part.func.attr == "rolling"
        ):
            visit(part.func.value, under_rolling=True)
            for argument in part.args:
                visit(argument, under_rolling=False)
            for keyword in part.keywords:
                visit(keyword.value, under_rolling=False)
            return
        if (
            isinstance(part, ast.Name)
            and isinstance(part.ctx, ast.Load)
            and part.id == parameter
        ):
            saw_parameter = True
            if not under_rolling:
                unsafe_parameter = True
        for child in ast.iter_child_nodes(part):
            visit(child, under_rolling=under_rolling)

    visit(node.body)
    return saw_parameter and not unsafe_parameter


def _validate_bounded_groupby_history(
    path: Path, function: ast.FunctionDef,
) -> None:
    """Reject raw full-history GroupBy reductions in candidate code."""
    aliases = _simple_aliases(function)
    for node in ast.walk(function):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _GROUPBY_HISTORY_TERMINALS
        ):
            continue
        receiver = node.func.value
        groupbys = _receiver_groupbys(receiver, aliases)
        if not groupbys:
            continue
        # A reducer on an explicit rolling object is time bounded; its window
        # is independently resolved and checked by ``factor_lookback_months``.
        if _receiver_has_method(receiver, "rolling", aliases):
            continue
        axes = {_group_axis(call, aliases) for call in groupbys}
        if axes == {"cross_sectional"}:
            continue
        if (
            node.func.attr == "transform"
            and node.args
            and _bounded_rolling_lambda(node.args[0])
        ):
            continue
        raise ValueError(
            f"{path}: 자산별 전체-history GroupBy.{node.func.attr}는 "
            "금지됩니다. 명시적 36개월 이하 rolling 또는 동월 횡단면 "
            "연산만 허용됩니다"
        )


def _validate_candidate_source(path: Path) -> str:
    """Reject import-time I/O and common filesystem/network escape hatches.

    Candidate modules are declarative strategy files, not general plugins.  A
    narrow import allowlist and no import-time calls prevent them from opening
    the full cache before the research boundary has been authenticated.
    """
    try:
        source = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: 후보 전략 파일은 UTF-8이어야 합니다") from exc
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"{path}: 후보 전략 Python 문법 오류: {exc}") from exc
    compute_functions = []
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            valid = all(
                (item.name, item.asname) in {("numpy", "np"), ("pandas", "pd")}
                for item in statement.names
            )
            if not valid:
                raise ValueError(
                    f"{path}: 허용되지 않은 import; numpy as np, pandas as pd만 가능합니다"
                )
            continue
        if isinstance(statement, ast.ImportFrom):
            if statement.level != 0:
                raise ValueError(f"{path}: 상대 import는 허용되지 않습니다")
            imported = [(item.name, item.asname) for item in statement.names]
            valid = (
                statement.module == "__future__"
                and imported == [("annotations", None)]
            ) or (
                statement.module == "engine.factors"
                and imported == [("Factor", None)]
            )
            if not valid:
                raise ValueError(
                    f"{path}: 허용되지 않은 import; from import는 "
                    "annotations와 Factor만 가능합니다"
                )
            continue
        if isinstance(statement, ast.FunctionDef):
            if statement.name != "compute" or statement.decorator_list:
                raise ValueError(f"{path}: decorator 없는 compute 함수 하나만 허용됩니다")
            compute_functions.append(statement)
            continue
        if isinstance(statement, ast.Assign):
            if (
                len(statement.targets) != 1
                or not isinstance(statement.targets[0], ast.Name)
                or not isinstance(statement.value, (ast.BinOp, ast.Call, ast.Constant, ast.Dict))
            ):
                raise ValueError(f"{path}: import 시 단순 상수·계약 선언만 허용됩니다")
            calls = [node for node in ast.walk(statement) if isinstance(node, ast.Call)]
            if any(
                not (isinstance(node.func, ast.Name) and node.func.id == "Factor")
                for node in calls
            ):
                raise ValueError(f"{path}: import 시 Factor 선언 외 함수 호출은 금지됩니다")
            continue
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            continue
        raise ValueError(
            f"{path}: 후보 모듈 최상위에는 import·상수·compute·계약만 허용됩니다"
        )
    if len(compute_functions) != 1:
        raise ValueError(f"{path}: compute 함수가 정확히 하나 필요합니다")

    top_level_imports = {
        id(statement)
        for statement in tree.body
        if isinstance(statement, (ast.Import, ast.ImportFrom))
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Import, ast.ImportFrom))
            and id(node) not in top_level_imports
        ):
            raise ValueError(f"{path}: 함수 내부 import는 허용되지 않습니다")
        if isinstance(node, ast.AsyncFunctionDef):
            raise ValueError(f"{path}: async 함수는 허용되지 않습니다")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in _BANNED_LOADED_NAMES:
                raise ValueError(f"{path}: 후보 전략에서 {node.id} 참조는 금지됩니다")
        if isinstance(node, ast.Attribute) and node.attr not in _ALLOWED_ATTRIBUTES:
            raise ValueError(f"{path}: 후보 전략에서 .{node.attr} 접근은 허용되지 않습니다")
        if isinstance(node, ast.Call):
            allowed = (
                isinstance(node.func, ast.Name)
                and node.func.id in _ALLOWED_CALL_NAMES
            ) or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in _ALLOWED_ATTRIBUTES
            )
            if not allowed:
                raise ValueError(f"{path}: 간접 또는 허용되지 않은 함수 호출입니다")
    return source


def _load_module(path: Path):
    source = _validate_candidate_source(path)
    source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    path_digest = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:12]
    module_name = f"factor_research_candidate_{path.stem}_{path_digest}_{source_digest[:12]}"
    virtual_filename = f"{path.resolve()}#sha256={source_digest}"
    module = types.ModuleType(module_name)
    module.__file__ = virtual_filename
    module.__package__ = ""
    linecache.cache[virtual_filename] = (
        len(source), None, source.splitlines(keepends=True), virtual_filename,
    )
    sys.modules[module_name] = module
    try:
        exec(compile(source, virtual_filename, "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module, source_digest, source


def _validate_active_history_semantics(path: Path, source: str) -> None:
    tree = ast.parse(source, filename=str(path))
    compute = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "compute"
    ]
    if len(compute) != 1:
        raise ValueError(f"{path}: compute 함수가 정확히 하나 필요합니다")
    _validate_bounded_groupby_history(path, compute[0])


def _validate_spec(path: Path, factor: Factor, value, *, source_digest: str) -> dict:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: RESEARCH_SPEC dict가 필요합니다")
    missing = REQUIRED_SPEC_FIELDS - set(value)
    if missing:
        raise ValueError(f"{path}: RESEARCH_SPEC 필드 누락 {sorted(missing)}")
    output = {str(key): item for key, item in value.items()}
    output["factor_name"] = factor.name
    try:
        strategy_file = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        strategy_file = path
    output["strategy_file"] = str(strategy_file)
    output["strategy_sha256"] = source_digest
    return output


def load_candidates(
    registry: Registry = REGISTRY,
    directory: str | Path = CANDIDATE_DIR,
) -> list[Factor]:
    """Register every ``FACTOR`` in candidates/*.py, idempotently."""
    root = Path(directory)
    if not root.exists():
        return []
    loaded: list[Factor] = []
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module, source_digest, source = _load_module(path)
        factor = getattr(module, "FACTOR", None)
        if not isinstance(factor, Factor):
            raise ValueError(f"{path}: engine.factors.Factor 타입의 FACTOR가 필요합니다")
        research_spec = _validate_spec(
            path, factor, getattr(module, "RESEARCH_SPEC", None),
            source_digest=source_digest,
        )
        lookback = factor_lookback_months(
            source=factor.source, params=factor.params,
        )
        research_spec["max_lookback_months"] = lookback
        if lookback > MAX_FACTOR_LOOKBACK_MONTHS:
            research_spec["disabled_reason"] = (
                f"lookback {lookback}개월이 현재 연구 상한 "
                f"{MAX_FACTOR_LOOKBACK_MONTHS}개월을 초과"
            )
            DISABLED_RESEARCH_SPECS[factor.name] = research_spec
            RESEARCH_SPECS.pop(factor.name, None)
            continue
        unavailable = sorted(set(factor.needs) & _UNCERTIFIED_PIT_FEATURES)
        if unavailable:
            research_spec["disabled_reason"] = (
                "Silver가 historical-vintage/known_at 배당 feature 계약을 "
                f"아직 인증하지 않음: {unavailable}"
            )
            DISABLED_RESEARCH_SPECS[factor.name] = research_spec
            RESEARCH_SPECS.pop(factor.name, None)
            continue
        _validate_active_history_semantics(path, source)
        if factor.name in registry:
            existing = registry[factor.name]
            if existing.definition_hash != factor.definition_hash:
                raise ValueError(f"{path}: 기존 팩터와 이름 충돌: {factor.name}")
        else:
            registry.add(factor)
        RESEARCH_SPECS[factor.name] = research_spec
        DISABLED_RESEARCH_SPECS.pop(factor.name, None)
        loaded.append(factor)
    return loaded
