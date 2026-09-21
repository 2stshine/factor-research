"""Compact, outcome-free definition inventory; never import candidate modules."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

VERSION = "factor-definition-index-v1"
INDEX_FILE = "memory/factor_index.json"
IDENTITY_FIELDS = ("cycle_id", "factor", "family", "definition_hash", "strategy_file", "ruleset_version")
METADATA_FIELDS = ("name", "category", "family", "exploration_domain", "needs", "params", "predicted_sign", "rebalance_months")
GROUPS = (
    ("composite", "과거 복합 점수", r"^(?:.*small_value|defensive_value|solvent_value|quality_stability)$"),
    ("dividend", "배당 수준·빈도", r"dividend"),
    ("seasonality", "수익률 계절성", r"seasonality"),
    ("size", "기업 규모", r"^size$"),
    ("valuation", "시가 대비 재무가치", r"yield|to_market|book_to_market|^value_"),
    ("surprise", "이익 서프라이즈", r"^sue$|earnings_change"),
    ("accruals", "운전자본 발생액", r"accrual"),
    ("investment", "자산·운전자본 성장", r"(?:asset|assets|working_capital)_growth|assets_growth"),
    ("earnings_growth", "이익·매출 성장", r"(?:income|sales|revenue)_growth"),
    ("financing", "자본·부채 변화와 발행", r"issuance|(?:capital_stock|equity|liabilit(?:y|ies))_growth"),
    ("asset_efficiency", "자산 대비 매출·회전율", r"asset_turnover|^revenue_to_|^current_asset_turnover"),
    ("profitability", "이익률·자산/자본 수익성", r"margin|roa|^qual_ro[ae]$|^qual_opm$|income_to_|return_on_capital|income_conversion|nonoperating_burden"),
    ("capital_structure", "재무구조·부채 상환 여력", r"leverage|^qual_lev$|liabilit|current_ratio|coverage|encumbrance"),
    ("balance_mix", "자산·자본 구성비", r"retained_earnings|capital_stock|paid_in_capital|noncurrent_asset|current_assets|working_capital|equity_to_"),
    ("reversal", "가격 반전", r"reversal|^rev_"),
    ("momentum", "가격·시장대비 모멘텀", r"momentum|^mom_"),
    ("trend_shape", "추세 지속·회복·고점 거리", r"persistence|positive_return|gain_loss|trend_efficiency|proximity|recovery|price_range"),
    ("illiquidity", "가격충격·Amihud 유동성", r"amihud"),
    ("trading", "거래대금·회전율", r"adv|trading|turnover"),
    ("extremes", "극단 수익·분포 비대칭", r"max_.*return|skewness|kurtosis"),
    ("market_exposure", "시장 민감도·동조성", r"market_beta|market_return_correlation"),
    ("volatility", "수익률 변동성·안정성", r"volatility|_vol_"),
    ("unknown", "계산 유형 미분류", r".*"),
)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _source_paths(root: Path) -> list[Path]:
    repo = root.parent
    return [repo / "factors/builtin.py", *sorted((repo / "factors/candidates").glob("*.py")), root / "history.jsonl"]


def _sources(root: Path) -> dict:
    return {str(p.relative_to(root.parent)): _digest(p.read_bytes()) if p.exists() else None for p in _source_paths(root)}


def _literal(node, constants):
    """Resolve only literal containers and simple numeric declaration arithmetic."""
    if isinstance(node, ast.Name):
        if node.id not in constants:
            raise ValueError("unresolved declaration")
        return constants[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_literal(n, constants) for n in node.elts]
    if isinstance(node, ast.Dict):
        return {_literal(k, constants): _literal(v, constants) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.BinOp):
        left, right = _literal(node.left, constants), _literal(node.right, constants)
        if type(left) not in (int, float) or type(right) not in (int, float):
            raise ValueError("non-numeric declaration")
        operations = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                      ast.Mult: lambda: left * right, ast.Div: lambda: left / right}
        if type(node.op) not in operations:
            raise ValueError("unsupported declaration arithmetic")
        return operations[type(node.op)]()
    return ast.literal_eval(node)


def _group(name: str) -> str:
    return next(key for key, _label, pattern in GROUPS if re.search(pattern, name))


def _definitions(path: Path, repo: Path) -> list[dict]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    constants, functions, calls = {}, {}, []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "FACTOR" and isinstance(node.value, ast.Call):
                calls.append(node.value)
            else:
                try:
                    constants[name] = _literal(node.value, constants)
                except (ValueError, TypeError, KeyError, ZeroDivisionError):
                    pass
        elif (path.name == "builtin.py" and isinstance(node, ast.Expr)
              and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
              and node.value.func.id == "_add"):
            calls.append(node.value)
    rows = []
    for call in calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords}
        row, unresolved = {}, []
        for field in METADATA_FIELDS:
            if field not in kwargs:
                continue
            try:
                row[field] = _literal(kwargs[field], constants)
            except (ValueError, TypeError, KeyError, ZeroDivisionError):
                unresolved.append(field)
        if not isinstance(row.get("name"), str) or not re.fullmatch(r"[a-z][a-z0-9_]*", row["name"]):
            raise ValueError(f"Static factor name unavailable: {path}")
        compute = kwargs.get("compute")
        if isinstance(compute, ast.Name):
            compute = functions.get(compute.id)
        # AST unparse strips comments; remove docstrings as well. Hypotheses,
        # RESEARCH_SPEC and module prose may contain old outcomes: never export.
        if isinstance(compute, ast.FunctionDef) and compute.body and isinstance(compute.body[0], ast.Expr) and isinstance(compute.body[0].value, ast.Constant) and isinstance(compute.body[0].value.value, str):
            compute.body = compute.body[1:] or [ast.Pass()]
        formula = ast.unparse(compute) if isinstance(compute, (ast.FunctionDef, ast.Lambda)) else None
        fields = {n.slice.value for n in ast.walk(compute) if isinstance(n, ast.Subscript)
                  and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)} if compute else set()
        row.update({"family": row.get("family") or row["name"], "needs": row.get("needs", []),
                    "params": row.get("params", {}), "source_path": str(path.relative_to(repo)),
                    "source_line": call.lineno, "source_sha256": _digest(source.encode()),
                    "calculation": formula, "referenced_fields": sorted(fields - {"asset_id", "ym"}),
                    "calculation_sha256": _digest(formula.encode()) if formula else None,
                    "hypothesis_status": "NOT_EXPORTED_UNREVIEWED_NARRATIVE",
                    "unresolved_fields": unresolved, "group": _group(row["name"]),
                    "definition_status": "SOURCE_PRESENT_NOT_EXECUTED"})
        rows.append(row)
    return rows


def _registry_rows(rows) -> list[dict]:
    result = []
    for row in rows:
        name = row.get("name", row.get("factor"))
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError("Invalid registry identity")
        result.append({"name": name, **{k: row.get(k) for k in ("category", "family", "definition_hash", "needs")}})
    return sorted(result, key=lambda row: (row["name"], str(row["definition_hash"])))


def build_factor_index(root: Path, registry_rows: list[dict] | None = None) -> dict:
    root = Path(root)
    previous = root / INDEX_FILE
    # The compact KNOWLEDGE no longer carries all registry rows. Retain that
    # legacy identity inventory, explicitly not a claim of current registration.
    if registry_rows is None and previous.exists():
        prior = json.loads(previous.read_text(encoding="utf-8"))
        if prior.get("schema_version") != VERSION:
            raise ValueError("Unsupported previous factor index")
        registry_rows = prior.get("observed_registry_rows", [])
    registry = _registry_rows(registry_rows or [])
    sources = _sources(root)
    definitions = []
    for path in _source_paths(root):
        if path.suffix == ".py" and path.exists():
            definitions.extend(_definitions(path, root.parent))
    names = [row["name"] for row in definitions]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate static factor names")
    known = set(names)
    for row in registry:
        if row["name"] not in known:
            definitions.append({**row, "group": "unknown", "definition_status": "SOURCE_UNAVAILABLE",
                                "hypothesis_status": "NOT_EXPORTED_UNREVIEWED_NARRATIVE"})
            known.add(row["name"])
    history_path = root / "history.jsonl"
    history = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()] if history_path.exists() else []
    trials, cycles = [], set()
    for record in history:
        identity = {key: record.get(key) for key in IDENTITY_FIELDS}
        cycle, name = identity["cycle_id"], identity["factor"]
        if (not isinstance(cycle, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", cycle)
                or cycle in cycles or not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name)):
            raise ValueError("Missing or duplicate trial identity")
        cycles.add(cycle)
        if name not in known:
            definitions.append({"name": name, "family": identity["family"], "group": "unknown",
                                "definition_status": "HISTORICAL_IDENTITY_ONLY",
                                "hypothesis_status": "NOT_EXPORTED_UNREVIEWED_NARRATIVE"})
            known.add(name)
        # Same name is a search link only, never proof that historical code is
        # unchanged. Preserve every historical hash/version and every trial.
        identity["current_definition_binding"] = "NOT_VERIFIED"
        trials.append(identity)
    if sources != _sources(root):
        raise ValueError("Source changed while building factor index")
    return {"schema_version": VERSION, "source_hashes": sources,
            "observed_registry_rows": registry,
            "definitions": sorted(definitions, key=lambda row: row["name"]),
            "trials": trials}


def write_factor_index(root: Path, index: dict) -> Path:
    from scripts.lessons import _atomic_write_text
    root = Path(root)
    if index.get("schema_version") != VERSION or index.get("source_hashes") != _sources(root):
        raise ValueError("Stale factor index; regenerate KNOWLEDGE")
    target = root / INDEX_FILE
    _atomic_write_text(target, _json(index))
    return target


def render_attempt_summary(index: dict) -> str:
    rows, trials = index["definitions"], index["trials"]
    byname = {row["name"]: row for row in rows}
    counts = Counter(byname[row["factor"]]["group"] for row in trials)
    source_count = sum(row["definition_status"] == "SOURCE_PRESENT_NOT_EXECUTED" for row in rows)
    lines = ["## 무엇을 이미 정의·시도했나", "",
             f"소스 정의 {source_count}개 · 원장 시행 {len(trials)}건. 코드 존재는 평가·사용 승인·Gold 승격이 아니다.",
             "아래는 이름·입력·계산 선언 중심의 탐색 요약이다. 가설 해석을 자동 추출한 것이 아니며 같은 그룹이 같은 신호라는 판정이나 경제적 교훈도 아니다.",
             "가설 원문의 과거 성과 혼입을 막기 위해 검토되지 않은 자연어는 색인에 복사하지 않는다.", "",
             "| 계산 유형 | 정의/시행 | 포함한 변형 | 예시 |", "|---|---:|---|---|"]
    for group, label, _pattern in GROUPS:
        members = [row for row in rows if row["group"] == group]
        if not members:
            continue
        names = [row["name"] for row in members]
        variants = []
        for term, text in (("acceleration", "성장 가속"), ("growth", "성장률"), ("change", "시차 변화"),
                           ("volatility", "변동성"), ("instability", "불안정성"), ("mean", "기간 평균")):
            if any(term in name for name in names):
                variants.append(text)
        periods = sorted({value for row in members for key, value in (row.get("params") or {}).items()
                          if key in {"lookback", "lookback_months", "window_months"} and type(value) in (int, float)})
        for row in members:
            params = row.get("params") or {}
            if type(params.get("history_years")) is int and type(params.get("months_per_year")) is int:
                periods.append(params["history_years"] * params["months_per_year"])
        periods = sorted(set(periods))
        if periods:
            variants.append("기간 " + "/".join(str(p) for p in periods) + "개월")
        examples = ", ".join(f"`{name}`" for name in names[:2])
        lines.append(f"| {label} (`{group}`) | {len(members)}/{counts[group]} | {'·'.join(variants) or '수준·비율 정의'} | {examples} |")
    lines += ["", f"전체 이름·계산 코드·입력·params·정의 파일·모든 시행 식별자는 `{INDEX_FILE}`에 보존한다.",
              "조회: `python -m scripts.factor_memory --query total_assets` 또는 `--group investment`, `--factor NAME`.",
              "후보를 만들기 전 해당 그룹과 입력을 검색해 수식·기간까지 비교한다. 이름만 바꾼 정의와 실패한 시행도 제외하지 않는다.",
              "검색은 결과 없는 색인만 읽는다. 원본이 바뀌면 갱신 전 사용을 거부한다. 역사 hash와 현재 파일의 동일성은 미확인으로 보존하며, 엔진 구조·상관 검사는 그대로 필요하다."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("research"))
    match = parser.add_mutually_exclusive_group(required=True)
    match.add_argument("--query")
    match.add_argument("--group", choices=[key for key, _label, _pattern in GROUPS])
    match.add_argument("--factor")
    args = parser.parse_args()
    path = args.root / INDEX_FILE
    index = json.loads(path.read_text(encoding="utf-8"))
    if index.get("schema_version") != VERSION or index.get("source_hashes") != _sources(args.root):
        parser.error("STALE: 원본 정의/시행이 변경됨. KNOWLEDGE를 갱신한 뒤 다시 조회하세요.")
    labels = {key: label for key, label, _pattern in GROUPS}
    selected = [row for row in index["definitions"] if
                (args.group and row["group"] == args.group) or
                (args.factor and row["name"] == args.factor) or
                (args.query and args.query.casefold() in (_json(row) + labels[row["group"]]).casefold())]
    names = {row["name"] for row in selected}
    print(_json({"definitions": selected, "trials": [row for row in index["trials"] if row["factor"] in names]}))


if __name__ == "__main__":
    main()
