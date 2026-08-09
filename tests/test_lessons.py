"""`lessons.md` 가 봉인을 깨거나 조용히 항목을 잃지 않는지 잠근다.

이 파일이 지키는 것은 두 가지다.
  ① 반출 범위 — 판정 결과·검사 이름·성과 수치가 컨텍스트로 나가지 않는다.
  ② 무손실 — 시행 전량이 반영되고, 관측 0 인 분류 축도 행이 남는다.

②는 이 작업이 고치려던 결함 그 자체다. `latest.md` 가 `history[-30:]` 로 세 건을
말없이 버린 것과 같은 실패를 우리 산출물에서 반복하지 않기 위한 것이다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research"

# 컨텍스트에 나오면 안 되는 판정 흔적. 팩터명 일부로 등장하는 경우를 배제하려고
# 독립 식별자로만 찾는다 (`net_roa` 의 net 은 metrics 키가 아니다).
FORBIDDEN_TOKENS = ("verdict", "failed_checks", "strongest_relationship", "metrics",
                    "ic_full", "ic_investable", "hac_t")
VERDICT_VALUES = ("REJECT", "PROVISIONAL", "PROMOTE", "WITHHELD_POST_CUTOFF")
JKP_THEMES = ("Accruals", "Debt Issuance", "Investment", "Low Leverage", "Low Risk",
              "Momentum", "Profit Growth", "Profitability", "Quality", "Seasonality",
              "Short-Term Reversal", "Size", "Value")


def run_view(view: str | None = None) -> str:
    cmd = [sys.executable, "scripts/lessons.py"]
    if view:
        cmd += ["--view", view]
    done = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture(scope="module")
def lessons() -> str:
    run_view()
    return (RESEARCH / "memory" / "lessons.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def history() -> list[dict]:
    path = RESEARCH / "history.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# ── ① 반출 범위 ──────────────────────────────────────────────────────────

def test_context_carries_no_verdict(lessons):
    for value in VERDICT_VALUES:
        assert value not in lessons, f"판정 결과가 컨텍스트로 나갔다: {value}"


def test_context_carries_no_metric_keys(lessons):
    for token in FORBIDDEN_TOKENS:
        assert not re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", lessons), \
            f"금지 필드가 컨텍스트로 나갔다: {token}"


def test_context_carries_no_decimal_numbers(lessons):
    """성과 수치는 소수로 나온다. ruleset 버전(fr-3.9.0)만 예외다."""
    stripped = re.sub(r"fr-\d+\.\d+\.\d+", "", lessons)
    assert not re.search(r"\d+\.\d+", stripped), "소수점 숫자가 컨텍스트에 있다"


# ── ② 무손실 ─────────────────────────────────────────────────────────────

def test_every_trial_is_listed(lessons, history):
    assert lessons.count("| `cycle-") == len(history), \
        "시행이 조용히 빠졌다. 이 층은 자르지 않는다"


def test_crosstab_keeps_every_theme_even_at_zero():
    """관측 0 인 축도 행이 남아야 빈칸이 빈칸으로 보인다."""
    crosstab = run_view("crosstab")
    for theme in JKP_THEMES:
        assert re.search(rf"^{re.escape(theme)}\s", crosstab, re.M), \
            f"관측 0 인 분류 축의 행이 사라졌다: {theme}"


def test_crosstab_cells_sum_to_trial_count(history):
    crosstab = run_view("crosstab")
    rows = [l for l in crosstab.splitlines()
            if re.match(r"^[A-Z(]", l) and not l.startswith("Accounting")]
    total = sum(int(n) for row in rows for n in re.findall(r"\b\d+\b", row))
    assert total == len(history), "교차표 셀 합이 시행 수와 다르다"


# ── 결정론 · 경계 ────────────────────────────────────────────────────────

def test_generation_is_deterministic():
    assert run_view("crosstab") == run_view("crosstab")


def test_generator_never_writes_latest_md():
    path = RESEARCH / "context" / "latest.md"
    before = path.read_bytes() if path.exists() else None
    run_view()
    run_view("crosstab")
    after = path.read_bytes() if path.exists() else None
    assert before == after, "이 층은 latest.md 를 건드리지 않는다"


def test_engine_directives_are_transcribed(lessons):
    """엔진이 reflection 에 쓴 지시를 원문으로 싣는다. 요약하지 않는다."""
    reflections = sorted((RESEARCH / "campaigns").glob("*/epochs/*/reflection.json"))
    if not reflections:
        pytest.skip("성찰 기록이 없다")
    latest = json.loads(reflections[-1].read_text(encoding="utf-8"))
    directives = (latest.get("permitted_next_actions") or []) + (latest.get("forbidden_actions") or [])
    if not directives:
        pytest.skip("지시가 비어 있다")
    for line in directives:
        assert line in lessons, f"엔진 지시가 원문 그대로 실리지 않았다: {line[:40]}"


def test_labels_cover_every_trial(history):
    """라벨이 시행보다 적으면 분류 축이 조용히 비어 보인다."""
    path = RESEARCH / "memory" / "labels.jsonl"
    labels = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert {r["cycle_id"] for r in labels} == {h["cycle_id"] for h in history}


def test_label_themes_are_within_the_closed_vocabulary():
    path = RESEARCH / "memory" / "labels.jsonl"
    labels = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    for record in labels:
        assert record["jkp_theme"] in JKP_THEMES or record["jkp_theme"] is None, \
            f"허용값 밖의 분류 축: {record['jkp_theme']}"


def test_variant_of_points_at_a_real_factor_without_cycles():
    path = RESEARCH / "memory" / "labels.jsonl"
    labels = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    parents = {r["factor"]: r["variant_of"] for r in labels}
    for child, parent in parents.items():
        if parent is None:
            continue
        assert parent in parents, f"{child} 의 부모가 등록 팩터가 아니다: {parent}"
        seen, node = {child}, parent
        while node is not None:
            assert node not in seen, f"variant_of 에 순환이 있다: {child}"
            seen.add(node)
            node = parents.get(node)
