"""팩터 정의 레지스트리.

T0.5 구조적 방어: 팩터는 **가설을 먼저 등록해야** 만들어진다(`hypothesis` 필수).
그리고 게이트가 소스에서 숫자 리터럴을 스캔해 **선언 안 된 상수를 찾아낸다** —
에이전트가 "정의상 상수"라며 진짜 튜닝한 파라미터를 숨기는 경로를 막는다.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import textwrap
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

# 리터럴로 나와도 파라미터가 아닌 것들(인덱스·항등원·부호)
_BENIGN = {0, 1, -1, 2, 0.0, 1.0, -1.0, 100, 12, 4}
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_CATEGORIES = {"value", "quality", "momentum", "size", "earnings", "other"}


@dataclass(frozen=True)
class Factor:
    name: str
    category: str                      # value | quality | momentum | size | earnings | other
    hypothesis: str                    # T0.5 — 왜 이게 초과수익을 낼 것인가. 빈 문자열 금지.
    predicted_sign: int                # +1: 값이 클수록 미래수익 높음
    compute: Callable[[pd.DataFrame], pd.Series]
    params: dict = field(default_factory=dict)   # 선언된 파라미터(그리드 축이 된다)
    rebalance_months: int = 1
    needs: tuple[str, ...] = ()        # 필요한 재무 컬럼
    family: str | None = None          # 변형 팩터의 trial lineage

    def __post_init__(self):
        if not _NAME.fullmatch(self.name):
            raise ValueError(f"{self.name}: name 은 ^[a-z][a-z0-9_]*$ 형식이어야 한다")
        if self.category not in _CATEGORIES:
            raise ValueError(f"{self.name}: 지원하지 않는 category={self.category!r}")
        if not self.hypothesis.strip():
            raise ValueError(f"{self.name}: hypothesis 없이는 등록할 수 없다 (T0.5)")
        if self.predicted_sign not in (1, -1):
            raise ValueError(f"{self.name}: predicted_sign 은 +1 또는 -1")
        if self.rebalance_months < 1:
            raise ValueError(f"{self.name}: rebalance_months 는 1 이상")

    @property
    def source(self) -> str:
        try:
            return textwrap.dedent(inspect.getsource(self.compute))
        except (OSError, TypeError):
            return ""

    @property
    def definition_hash(self) -> str:
        """Hash every declared input that can change the factor definition."""
        payload = {
            "name": self.name,
            "family": self.family or self.name,
            "category": self.category,
            "hypothesis": self.hypothesis.strip(),
            "predicted_sign": self.predicted_sign,
            "source": self.source,
            "params": self.params,
            "rebalance_months": self.rebalance_months,
            "needs": list(self.needs),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()[:16]

    def undeclared_constants(self) -> list[float]:
        """T0.5 — 소스의 숫자 리터럴 중 선언되지 않은 것. 있으면 게이트가 REJECT."""
        src = self.source
        if not src:
            return []
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return []
        declared = set(self.params.values())
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                v = node.value
                if v in _BENIGN or v in declared:
                    continue
                found.append(v)
        return sorted(set(found))

    def composite_evidence(self) -> list[str]:
        """Return structural evidence that this definition blends factor scores.

        A factor may use several raw fields to form one economically meaningful
        ratio (for example operating income / assets).  What is disallowed is
        blending multiple already-normalized cross-sectional signals or other
        registered factor columns into a weighted score.
        """
        src = self.source
        if not src:
            return []
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return []
        rank_calls = 0
        factor_columns: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "rank"
            ):
                rank_calls += 1
            if isinstance(node, ast.Subscript):
                value = node.slice
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    if value.value.startswith("f_"):
                        factor_columns.add(value.value)
        evidence = []
        if rank_calls > 1:
            evidence.append(f"횡단면 rank {rank_calls}개 결합")
        if factor_columns:
            evidence.append(f"등록 팩터 컬럼 참조 {sorted(factor_columns)}")
        return evidence


class Registry:
    def __init__(self):
        self._f: dict[str, Factor] = {}

    def add(self, f: Factor) -> Factor:
        if f.name in self._f:
            raise ValueError(f"중복 등록: {f.name}")
        self._f[f.name] = f
        return f

    def factor(self, **kw):
        """데코레이터 등록. @registry.factor(name=..., hypothesis=..., ...)"""
        def deco(fn):
            self.add(Factor(compute=fn, **kw))
            return fn
        return deco

    def __getitem__(self, k) -> Factor:
        return self._f[k]

    def __iter__(self):
        return iter(self._f.values())

    def __len__(self):
        return len(self._f)

    def __contains__(self, key: str) -> bool:
        return key in self._f

    @property
    def needs(self) -> list[str]:
        out = set()
        for f in self._f.values():
            out.update(f.needs)
        return sorted(out)


REGISTRY = Registry()


def compute_all(reg: Registry, df: pd.DataFrame) -> pd.DataFrame:
    """등록된 팩터를 전부 계산해 컬럼으로 붙인다. 실패한 팩터는 NaN 컬럼."""
    out = df.copy()
    for f in reg:
        try:
            out[f"f_{f.name}"] = f.compute(out) * f.predicted_sign
        except Exception as exc:   # 계산 실패도 정보다 — 게이트가 REJECT 처리
            out[f"f_{f.name}"] = float("nan")
            print(f"  [factors] {f.name} 계산 실패: {type(exc).__name__}: {exc}")
    return out
