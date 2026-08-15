"""`lessons.md` 가 봉인을 깨거나 조용히 항목을 잃지 않는지 잠근다.

이 파일이 지키는 것은 두 가지다.
  ① 반출 범위 — 판정 결과·검사 이름·성과 수치가 컨텍스트로 나가지 않는다.
  ② 무손실 — 시행 전량이 반영되고, 관측 0 인 분류 축도 행이 남는다.

②는 이 작업이 고치려던 결함 그 자체다. `latest.md` 가 `history[-30:]` 로 세 건을
말없이 버린 것과 같은 실패를 우리 산출물에서 반복하지 않기 위한 것이다.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "research"
sys.path.insert(0, str(REPO))

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


def _lessons_module():
    """생성기를 모듈로 들여온다. 봉인 판정을 테스트가 다시 구현하지 않기 위해서다."""
    spec = importlib.util.spec_from_file_location("lessons_mod", REPO / "scripts" / "lessons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sealed_cycles_carry_no_evaluation_labels(lessons):
    """봉인에 걸린 시행 줄에는 평가에서 파생된 라벨이 없어야 한다.

    이 작업이 고친 결함 그 자체다. `outcome` 은 `failed_tiers` 의 순함수라
    이름만 바뀐 판정이고, `novelty` 는 `strongest_relationship` 의 3분할이다.
    필드명 가드는 값이 바뀌어 있어서 못 잡는다.
    """
    module = _lessons_module()
    root = RESEARCH
    history, _, reflections = module.load(root)
    visible_cutoff, active = module.seal_state(root, None)
    sealed = module.sealed_lessons(
        history, reflections, module.sealed_cycles(history, visible_cutoff, active))
    assert sealed, "봉인 대상이 하나도 없다. 판정이 무력화됐는지 확인하라"

    for _, _, name in sealed:
        for line in lessons.splitlines():
            if f"`{name}`" not in line:
                continue
            for word in module.RESULT_VOCABULARY:
                assert not re.search(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])", line), \
                    f"봉인된 {name} 의 평가 파생 라벨이 컨텍스트로 나갔다: {word}"


def test_seal_rule_is_the_engine_function_not_a_copy():
    """판정식을 우리가 들고 있으면 엔진이 경계를 바꿀 때 우리 것만 낡는다."""
    module = _lessons_module()
    from engine import research as engine_research

    assert module.engine_research.exposed_after_cutoff is engine_research.exposed_after_cutoff
    source = (REPO / "scripts" / "lessons.py").read_text(encoding="utf-8")
    assert "engine_research.exposed_after_cutoff(" in source, "엔진 판정을 부르지 않는다"
    assert 'pd.Timestamp(row["data_cutoff"])' not in source, "봉인 비교식을 자체 구현했다"


def test_result_vocabulary_is_read_from_the_engine():
    """어휘 목록을 손으로 적어두면 엔진이 값을 늘릴 때 가드만 낡는다."""
    module = _lessons_module()
    from engine import epochs

    for word in re.findall(r'return\s+"([A-Z][A-Z_]+)"', inspect.getsource(epochs._failure_bucket)):
        assert word in module.RESULT_VOCABULARY, f"엔진 outcome 어휘가 가드에 빠졌다: {word}"
    for word in re.findall(r'novelty\s*=\s*"([A-Z][A-Z_]+)"', inspect.getsource(epochs.mark_evaluated)):
        assert word in module.RESULT_VOCABULARY, f"엔진 novelty 어휘가 가드에 빠졌다: {word}"


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


def test_current_sealed_directives_are_not_transcribed(lessons, history):
    """현재 최신 reflection은 봉인됐으므로 결과 파생 지시도 컨텍스트에 없어야 한다."""
    module = _lessons_module()
    reflections = sorted((RESEARCH / "campaigns").glob("*/epochs/*/reflection.json"))
    if not reflections:
        pytest.skip("성찰 기록이 없다")
    latest = json.loads(reflections[-1].read_text(encoding="utf-8"))
    directives = (latest.get("permitted_next_actions") or []) + (latest.get("forbidden_actions") or [])
    if not directives:
        pytest.skip("지시가 비어 있다")
    visible_cutoff, active = module.seal_state(RESEARCH, None)
    sealed_ids = module.sealed_cycles(history, visible_cutoff, active)
    assert not module.directives_released(latest, history, sealed_ids)
    for line in directives:
        assert line not in lessons, f"봉인된 엔진 지시가 컨텍스트로 나갔다: {line[:40]}"


def test_sealed_reflection_hides_results_and_result_derived_directives():
    """성공·실패·IC·신규성 및 그 결과에서 만든 지시가 봉인 밖으로 새지 않는다."""
    module = _lessons_module()
    history = [{
        "cycle_id": "cycle-canary", "campaign_id": "campaign-canary",
        "epoch_id": "epoch-canary", "factor": "factor-canary",
    }]
    reflection = {
        "campaign_id": "campaign-canary", "epoch_id": "epoch-canary",
        "oos_status": "SEALED",
        "lessons": [{
            "factor": "factor-canary", "family": "family-canary",
            "outcome": "CANARY_SUCCESS", "novelty": "CANARY_NOVELTY",
            "failed_checks": ["CANARY_FAILURE"], "metrics": {"ic_full": "CANARY_IC"},
        }],
        "duplicates": ["CANARY_DUPLICATE"],
        "permitted_next_actions": ["CANARY_PERMITTED_FROM_RESULT"],
        "forbidden_actions": ["CANARY_FORBIDDEN_FROM_RESULT"],
    }
    sealed_ids = {"cycle-canary"}
    sealed = module.sealed_lessons(history, [reflection], sealed_ids)
    release = module.directives_released(reflection, history, sealed_ids)
    text = module.render_lessons(
        [], [reflection], omitted=0, sealed=sealed, released_epochs=set()
    )
    changed_payload = {
        **reflection,
        "permitted_next_actions": ["A_DIFFERENT_RESULT_DERIVED_ACTION"],
        "forbidden_actions": [],
    }
    changed_text = module.render_lessons(
        [], [changed_payload], omitted=0, sealed=sealed, released_epochs=set()
    )

    assert not release
    assert text == changed_text, "봉인된 지시의 내용이나 개수가 출력에 영향을 줬다"
    for canary in (
        "CANARY_SUCCESS", "CANARY_NOVELTY", "CANARY_FAILURE", "CANARY_IC",
        "CANARY_DUPLICATE", "CANARY_PERMITTED_FROM_RESULT",
        "CANARY_FORBIDDEN_FROM_RESULT",
    ):
        assert canary not in text


def test_revealed_complete_reflection_transcribes_directives():
    """정확히 연결되고 공개된 epoch의 지시만 원문으로 연다."""
    module = _lessons_module()
    history = [{
        "cycle_id": "cycle-public", "campaign_id": "campaign-public",
        "epoch_id": "epoch-public", "factor": "factor-public",
    }]
    reflection = {
        "campaign_id": "campaign-public", "epoch_id": "epoch-public",
        "oos_status": "REVEALED",
        "lessons": [{
            "factor": "factor-public", "family": "family-public",
            "outcome": "INDEPENDENT", "novelty": "INDEPENDENT",
        }],
        "permitted_next_actions": ["PUBLIC_PERMITTED"],
        "forbidden_actions": ["PUBLIC_FORBIDDEN"],
    }
    sealed_ids: set[str] = set()
    sealed = module.sealed_lessons(history, [reflection], sealed_ids)
    release = module.directives_released(reflection, history, sealed_ids)
    text = module.render_lessons(
        [], [reflection], omitted=0, sealed=sealed,
        released_epochs={("campaign-public", "epoch-public")} if release else set(),
    )

    assert release
    assert "PUBLIC_PERMITTED" in text
    assert "PUBLIC_FORBIDDEN" in text


def test_directives_stay_sealed_without_exact_epoch_lineage():
    module = _lessons_module()
    history = [
        {"cycle_id": "cycle-a", "campaign_id": "campaign-x", "epoch_id": "epoch-x", "factor": "a"},
        {"cycle_id": "cycle-b", "campaign_id": "campaign-x", "epoch_id": "epoch-x", "factor": "b"},
    ]
    base = {"campaign_id": "campaign-x", "epoch_id": "epoch-x", "oos_status": "REVEALED"}
    assert not module.directives_released({**base, "lessons": []}, history, set())
    assert not module.directives_released(
        {**base, "lessons": [{"factor": "a"}]}, history, set()
    )
    partial = {
        **base,
        "lessons": [{"factor": "a", "family": "family-a"}],
        "duplicates": ["PARTIAL_EPOCH_DUPLICATE_CANARY"],
        "permitted_next_actions": ["PARTIAL_EPOCH_DIRECTIVE_CANARY"],
    }
    text = module.render_lessons(
        [], [partial], omitted=0,
        sealed=module.sealed_lessons(history, [partial], set()),
        released_epochs=set(),
    )
    assert "PARTIAL_EPOCH_DUPLICATE_CANARY" not in text
    assert "PARTIAL_EPOCH_DIRECTIVE_CANARY" not in text


def test_unknown_cutoff_seals_every_trial(history):
    """경계를 모르는 기본 경로는 한 건도 추측해서 열지 않는다."""
    module = _lessons_module()
    assert module.sealed_cycles(history, None, None) == {h["cycle_id"] for h in history}


def test_labels_cover_every_trial(history):
    """원장의 시행이 라벨에서 누락·중복·다른 팩터로 바뀌면 실패한다."""
    path = RESEARCH / "memory" / "labels.jsonl"
    labels = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    label_keys = [(r["cycle_id"], r["factor"]) for r in labels]
    history_keys = [(h["cycle_id"], h["factor"]) for h in history]
    assert len(label_keys) == len(set(label_keys)), "중복 라벨이 있다"
    assert label_keys == history_keys


def test_identity_label_sync_appends_unreviewed_rows_without_guessing(tmp_path):
    module = _lessons_module()
    root = tmp_path / "research"
    (root / "memory").mkdir(parents=True)
    history = [
        {
            "cycle_id": "cycle-reviewed", "factor": "reviewed_factor",
            "ruleset_version": "fr-test", "report": "runs/reviewed/report.md",
            "strategy_file": "factors/candidates/reviewed_factor.py",
        },
        {
            "cycle_id": "cycle-new", "factor": "new_factor",
            "ruleset_version": "fr-test", "report": "runs/new/report.md",
            "strategy_file": "factors/candidates/new_factor.py",
        },
    ]
    (root / "history.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in history), encoding="utf-8",
    )
    reviewed = module._placeholder_label(history[0])
    reviewed.update({
        "jkp_theme": "Quality", "jkp_evidence": "op_at",
        "confidence": "high",
    })
    (root / "memory" / "labels.jsonl").write_text(
        json.dumps(reviewed) + "\n", encoding="utf-8",
    )

    module.sync_identity_labels(root)
    labels = module.read_jsonl(root / "memory" / "labels.jsonl")

    assert [row["cycle_id"] for row in labels] == [
        "cycle-reviewed", "cycle-new",
    ]
    assert labels[0] == reviewed
    assert labels[1]["factor"] == "new_factor"
    assert labels[1]["jkp_theme"] is None
    assert labels[1]["cat_economic"] is None
    assert labels[1]["confidence"] == "low"
    assert labels[1]["cat_data_source"] == "unreviewed"


def test_refresh_lessons_includes_every_unreviewed_history_identity(tmp_path):
    module = _lessons_module()
    root = tmp_path / "research"
    (root / "memory").mkdir(parents=True)
    history = [
        {
            "cycle_id": "cycle-a", "factor": "factor_a", "family": "family_a",
            "ruleset_version": "fr-test", "report": "runs/a/report.md",
            "strategy_file": "factors/candidates/factor_a.py",
        },
        {
            "cycle_id": "cycle-b", "factor": "factor_b", "family": "family_b",
            "ruleset_version": "fr-test", "report": "runs/b/report.md",
            "strategy_file": "factors/candidates/factor_b.py",
        },
    ]
    (root / "history.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in history), encoding="utf-8",
    )

    path = module.refresh_lessons(root)
    text = path.read_text(encoding="utf-8")

    assert "시행 2건 · 생략 없음" in text
    assert "`cycle-a`" in text and "`factor_a`" in text
    assert "`cycle-b`" in text and "`factor_b`" in text
    assert len(module.read_jsonl(root / "memory" / "labels.jsonl")) == 2


def test_atomic_refresh_preserves_existing_artifact_permissions(tmp_path):
    module = _lessons_module()
    path = tmp_path / "lessons.md"
    path.write_text("before", encoding="utf-8")
    path.chmod(0o644)

    module._atomic_write_text(path, "after")

    assert path.read_text(encoding="utf-8") == "after"
    assert path.stat().st_mode & 0o777 == 0o644


def test_campaign_lifecycle_refreshes_lessons_automatically():
    from scripts import research as research_cli

    for function in (
        research_cli.cmd_context,
        research_cli.cmd_campaign_start,
        research_cli.cmd_epoch_close,
        research_cli.cmd_campaign_finalize,
        research_cli.cmd_campaign_reveal,
    ):
        assert "_refresh_research_memory" in inspect.getsource(function)


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
