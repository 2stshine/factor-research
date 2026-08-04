"""Load agent-authored research candidates without changing the builtin catalog."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path

from engine.factors import Factor, REGISTRY, Registry


CANDIDATE_DIR = Path(__file__).with_name("candidates")
RESEARCH_SPECS: dict[str, dict] = {}
REQUIRED_SPEC_FIELDS = {
    "thesis", "mechanism", "falsification", "expected_relationship", "data_notes",
}


def _load_module(path: Path):
    digest = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:12]
    module_name = f"factor_research_candidate_{path.stem}_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"후보 전략을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _validate_spec(path: Path, factor: Factor, value) -> dict:
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
        module = _load_module(path)
        factor = getattr(module, "FACTOR", None)
        if not isinstance(factor, Factor):
            raise ValueError(f"{path}: engine.factors.Factor 타입의 FACTOR가 필요합니다")
        research_spec = _validate_spec(path, factor, getattr(module, "RESEARCH_SPEC", None))
        if factor.name in registry:
            existing = registry[factor.name]
            if existing.definition_hash != factor.definition_hash:
                raise ValueError(f"{path}: 기존 팩터와 이름 충돌: {factor.name}")
        else:
            registry.add(factor)
        RESEARCH_SPECS[factor.name] = research_spec
        loaded.append(factor)
    return loaded
