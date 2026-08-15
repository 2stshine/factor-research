#!/usr/bin/env python3
"""누적 시행을 다음 루프가 읽을 컨텍스트로 뽑는다.

`research/history.jsonl` 과 epoch `reflection.json` 을 읽어 `research/memory/lessons.md` 를 만든다.
`research/context/latest.md` 는 읽지도 쓰지도 않는다.

내보내는 것은 두 가지뿐이다.
  ① 정체성   cycle_id · factor · family · ruleset_version · 축 라벨 · variant_of
  ② 공개된 지시   reflection.json 의 permitted_next_actions · forbidden_actions 원문

①은 평가 **이전**에 정해지는 정보라 항상 봉인 밖이다. ②는 평가 뒤 생성될 수 있으므로
reflection 이 공개됐고 연결된 시행도 봉인 밖일 때만 싣는다. 출처를 입증할 수 없는 지시는
결과 파생으로 간주해 닫는다.

내보내지 않는 것 — verdict, failed_checks, strongest_relationship, 성과 수치, 결과 집계,
그리고 **평가에서 파생된 라벨 일체**(outcome · novelty · duplicates). 뒤쪽 셋은 이름만
범주형일 뿐 게이트 결과의 함수다. `_failure_bucket` 은 `failed_tiers` 의 순함수이고
`novelty` 는 `strongest_relationship` 을 3분할한 값이다.

봉인 판정은 우리가 정하지 않는다. `engine.research.exposed_after_cutoff` 를 그대로 부른다 —
`latest.md` 가 `WITHHELD_POST_CUTOFF` 를 찍는 바로 그 규칙이다. 여기에 reflection 의
`oos_status` 를 함께 본다. 경계가 바뀌면 엔진 한 곳만 고치면 된다.

    python scripts/lessons.py                   # lessons.md 생성
    python scripts/lessons.py --view crosstab   # 분류 교차표 (13테마 항상 전부)
    python scripts/lessons.py --view before-after
    python scripts/lessons.py --view duplication  # 중복 재발: 예측→발생→해결
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import stat
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import epochs, research as engine_research

# 컨텍스트로 나갈 수 있는 필드. 이 목록 밖은 어떤 경로로도 출력하지 않는다.
WHITELIST = frozenset({
    "cycle_id", "factor", "family", "ruleset_version",
    "cat_economic", "cat_data", "jkp_theme",
})

# 결과·수치 계열. 출력에 새면 테스트가 깨진다.
FORBIDDEN = frozenset({
    "verdict", "failed_checks", "strongest_relationship", "metrics",
    "ic_full", "ic_investable", "net_ir", "turnover", "hac_t", "net", "gross",
})

# taxonomy.md 축 3. 관측치가 0이어도 행을 지우지 않는다 — 하드코딩이 그 보장이다.
JKP_THEMES = (
    "Accruals", "Debt Issuance", "Investment", "Low Leverage", "Low Risk",
    "Momentum", "Profit Growth", "Profitability", "Quality", "Seasonality",
    "Short-Term Reversal", "Size", "Value",
)
CAT_DATA = ("Accounting", "Price", "Trading", "Event", "Analyst", "Options", "13F", "Other")
UNMATCHED = "(미매칭)"

LABEL_FIELDS = (
    "cycle_id", "factor", "ruleset_version", "cat_economic", "cat_data",
    "cat_data_source", "jkp_theme", "jkp_evidence", "osap_acronym",
    "paper_authors", "paper_year", "paper_journal", "paper_cites",
    "paper_cites_suspect", "variant_of", "analysis", "confidence",
    "evidence",
)

# 봉인된 시행의 자리에 남기는 표시. `latest.md` 의 WITHHELD_POST_CUTOFF 와 같은 뜻이지만
# 그 문자열 자체가 판정 어휘라서 쓰지 않는다.
SEALED_NOTE = "결과는 봉인 경계 뒤라 싣지 않는다"

# reflection 의 oos_status 가 이 값일 때만 그 epoch 의 평가 파생 라벨이 봉인 밖이다.
RELEASED_OOS_STATUSES = frozenset({"REVEALED"})


def _engine_result_vocabulary() -> frozenset[str]:
    """평가 파생 라벨의 값 어휘를 엔진 소스에서 뽑는다.

    목록을 여기에 옮겨 적으면 엔진이 값을 늘릴 때 우리 가드만 낡는다. 뽑히지 않으면
    가드가 조용히 약해지므로 실패로 처리한다.
    """
    outcomes = set(re.findall(
        r'return\s+"([A-Z][A-Z_]+)"', inspect.getsource(epochs._failure_bucket)))
    novelties = set(re.findall(
        r'novelty\s*=\s*"([A-Z][A-Z_]+)"', inspect.getsource(epochs.mark_evaluated)))
    if len(outcomes) < 5 or len(novelties) < 3:
        raise SystemExit(
            "엔진에서 평가 파생 라벨의 어휘를 뽑지 못했다. "
            "engine/epochs.py 의 _failure_bucket · mark_evaluated 구조가 바뀌었는지 확인하라."
        )
    return frozenset(outcomes | novelties)


RESULT_VOCABULARY = _engine_result_vocabulary()


def seal_state(root: Path, context_cutoff: str | None) -> tuple[object, str | None]:
    """엔진과 같은 방식으로 현재 컨텍스트의 가시 cutoff 와 진행 campaign 을 정한다."""
    active = []
    for row in epochs.context_rows(root):
        campaign = epochs.load_campaign(root, row["campaign_id"])
        if engine_research.is_active_campaign(campaign):
            active.append(campaign)
    if len(active) > 1:
        raise SystemExit("동시에 진행 중인 current-protocol campaign이 둘 이상입니다")
    if active:
        return pd.Timestamp(active[0]["discovery"]["data_cutoff"]).normalize(), active[0]["campaign_id"]
    if context_cutoff:
        return pd.Timestamp(context_cutoff).normalize(), None
    # 진행 campaign 도 인자도 없으면 경계를 알 수 없다. 열지 않고 닫는다.
    return None, None


def sealed_cycles(history: list[dict], visible_cutoff, active_campaign_id: str | None) -> set[str]:
    """봉인에 걸리는 cycle_id. 판정식은 엔진 것을 그대로 부른다."""
    if visible_cutoff is None:
        return {h["cycle_id"] for h in history}      # 경계 미상 = 전량 봉인
    return {
        h["cycle_id"] for h in history
        if engine_research.exposed_after_cutoff(
            h, visible_cutoff=visible_cutoff, active_campaign_id=active_campaign_id)
    }


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _atomic_write_text(path: Path, text: str) -> None:
    """Replace one generated memory artifact only after durable full write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _placeholder_label(history_row: dict) -> dict:
    """Create an identity-only label without guessing an external taxonomy."""
    report = history_row.get("report")
    strategy = history_row.get("strategy_file")
    evidence = "; ".join(
        str(value) for value in (report, strategy) if isinstance(value, str) and value
    )
    return {
        "cycle_id": history_row["cycle_id"],
        "factor": history_row["factor"],
        "ruleset_version": history_row.get("ruleset_version"),
        "cat_economic": None,
        "cat_data": None,
        "cat_data_source": "unreviewed",
        "jkp_theme": None,
        "jkp_evidence": None,
        "osap_acronym": None,
        "paper_authors": None,
        "paper_year": None,
        "paper_journal": None,
        "paper_cites": None,
        "paper_cites_suspect": False,
        "variant_of": None,
        "analysis": None,
        "confidence": "low",
        "evidence": evidence,
    }


def sync_identity_labels(root: Path) -> Path:
    """Keep labels lossless while leaving unreviewed taxonomy fields empty.

    Curated OSAP/JKP rows are preserved byte-for-value. New trials receive an
    identity-only placeholder in history order; no result or inferred theme is
    copied into the label. A later reviewed ``build_labels.py`` run may enrich
    those rows.
    """
    history = read_jsonl(root / "history.jsonl")
    labels_path = root / "memory" / "labels.jsonl"
    labels = read_jsonl(labels_path)
    history_cycles = [row.get("cycle_id") for row in history]
    if any(not isinstance(cycle_id, str) for cycle_id in history_cycles):
        raise ValueError("시행 원장 cycle_id가 비어 있습니다")
    if len(history_cycles) != len(set(history_cycles)):
        raise ValueError("시행 원장 cycle_id가 중복됐습니다")
    label_by_cycle: dict[str, dict] = {}
    for row in labels:
        cycle_id = row.get("cycle_id")
        if not isinstance(cycle_id, str) or cycle_id in label_by_cycle:
            raise ValueError("라벨 cycle_id가 비어 있거나 중복됐습니다")
        if set(row) != set(LABEL_FIELDS):
            raise ValueError(f"라벨 schema가 다릅니다: {cycle_id}")
        label_by_cycle[cycle_id] = row
    history_by_cycle = {row["cycle_id"]: row for row in history}
    extras = sorted(set(label_by_cycle) - set(history_by_cycle))
    if extras:
        raise ValueError(f"원장에 없는 라벨이 있습니다: {extras}")

    synchronized = []
    for history_row in history:
        current = label_by_cycle.get(history_row["cycle_id"])
        if current is None:
            current = _placeholder_label(history_row)
        elif (
            current.get("factor") != history_row.get("factor")
            or current.get("ruleset_version") != history_row.get("ruleset_version")
        ):
            raise ValueError(
                f"라벨 identity가 원장과 다릅니다: {history_row['cycle_id']}"
            )
        synchronized.append(current)
    encoded = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in synchronized
    )
    if not labels_path.exists() or labels_path.read_text(encoding="utf-8") != encoded:
        _atomic_write_text(labels_path, encoded)
    return labels_path


def load(root: Path) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """시행 이력 · cycle_id 로 색인한 라벨 · epoch 성찰."""
    history = read_jsonl(root / "history.jsonl")
    labels = {r["cycle_id"]: r for r in read_jsonl(root / "memory" / "labels.jsonl")}
    reflections = []
    for path in sorted((root / "campaigns").glob("*/epochs/*/reflection.json")):
        reflections.append(json.loads(path.read_text(encoding="utf-8")))
    return history, labels, reflections


def identity_rows(history: list[dict], labels: dict[str, dict]) -> list[dict]:
    """레코드당 화이트리스트 필드만. 자르지 않는다."""
    rows = []
    for h in history:
        label = labels.get(h["cycle_id"], {})
        row = {
            "cycle_id": h["cycle_id"],
            "factor": h["factor"],
            "family": h.get("family") or h["factor"],
            "ruleset_version": h.get("ruleset_version") or "-",
            "jkp_theme": label.get("jkp_theme"),
            "cat_data": label.get("cat_data"),
            "cat_economic": label.get("cat_economic"),
        }
        rows.append({k: v for k, v in row.items() if k in WHITELIST})
    return rows


def sealed_lessons(
    history: list[dict], reflections: list[dict], sealed_ids: set[str]
) -> set[tuple]:
    """평가 파생 라벨을 가려야 할 (campaign, epoch, factor). 매핑이 안 되면 가린다."""
    index: dict[tuple, list[str]] = {}
    for h in history:
        key = (h.get("campaign_id"), h.get("epoch_id"), h["factor"])
        index.setdefault(key, []).append(h["cycle_id"])
    out = set()
    for ref in reflections:
        epoch_sealed = ref.get("oos_status") not in RELEASED_OOS_STATUSES
        for lesson in ref.get("lessons", []) or []:
            key = (ref.get("campaign_id"), ref.get("epoch_id"), lesson.get("factor"))
            cycles = index.get(key, [])
            if epoch_sealed or len(cycles) != 1 or cycles[0] in sealed_ids:
                out.add(key)
    return out


def directives_released(
    reflection: dict, history: list[dict], sealed_ids: set[str]
) -> bool:
    """지시가 속한 epoch의 시행 전부를 유일하게 식별하고 공개할 수 있을 때만 연다."""
    if reflection.get("oos_status") not in RELEASED_OOS_STATUSES:
        return False
    campaign_id = reflection.get("campaign_id")
    epoch_id = reflection.get("epoch_id")
    expected = [
        h for h in history
        if h.get("campaign_id") == campaign_id and h.get("epoch_id") == epoch_id
    ]
    lessons = reflection.get("lessons")
    if not expected or not isinstance(lessons, list) or not lessons:
        return False
    expected_factors = [h.get("factor") for h in expected]
    lesson_factors = [lesson.get("factor") for lesson in lessons if isinstance(lesson, dict)]
    if (
        len(lesson_factors) != len(lessons)
        or any(not isinstance(factor, str) or not factor for factor in lesson_factors)
        or len(set(expected_factors)) != len(expected_factors)
        or len(set(lesson_factors)) != len(lesson_factors)
        or set(lesson_factors) != set(expected_factors)
    ):
        return False
    return not any(h["cycle_id"] in sealed_ids for h in expected)


def render_lessons(
    rows: list[dict], reflections: list[dict], omitted: int, sealed: set[tuple],
    *, released_epochs: set[tuple] | None = None,
) -> str:
    """지시 먼저, 데이터 나중. 읽는 쪽이 제약을 맨 앞에서 만나게 배치한다."""
    released_epochs = released_epochs or set()
    latest = reflections[-1] if reflections else {}
    latest_key = (latest.get("campaign_id"), latest.get("epoch_id"))
    out = [
        "# 다음 회차 지침과 누적 시행",
        "",
        "> 결정론 코드가 만든다. 새 후보를 세우기 전에 위에서부터 읽는다.",
        "> **판정 결과는 담기지 않는다** — 봉인 OOS 를 지키기 위해 정체성과 구조적 교훈만 남긴다.",
        "",
    ]

    # ── ① 제약 — 공개된 reflection 의 지시만 원문 그대로 옮긴다 ───────────
    out += ["## 1. 이번 회차의 제약", ""]
    if latest and latest_key in released_epochs:
        out.append(
            f"아래는 `{latest.get('campaign_id')}` / `{latest.get('epoch_id')}` 의 "
            "`reflection.json` 에 엔진이 기록한 지시다. **원문 그대로 옮겼다.**"
        )
        out.append("")
        out.append("**해도 되는 것**")
        out.append("")
        for item in latest.get("permitted_next_actions", []) or ["(없음)"]:
            out.append(f"- {item}")
        out.append("")
        out.append("**하면 안 되는 것**")
        out.append("")
        for item in latest.get("forbidden_actions", []) or ["(없음)"]:
            out.append(f"- {item}")
    elif latest:
        out.append("최신 성찰의 지시는 봉인 경계 안에 있어 공개하지 않는다.")
    else:
        out.append("아직 성찰 기록이 없어 제약이 비어 있다.")
    out.append("")

    # ── ② 출력 계약 ──────────────────────────────────────────────────────
    out += [
        "## 2. 후보 하나가 갖춰야 할 것", "",
        "`factors/candidates/*.py` 의 `RESEARCH_SPEC` 스키마와 같다. 빈칸이 있으면 등록되지 않는다.", "",
        "| 항목 | 내용 |",
        "|---|---|",
        "| 이름 | snake_case. 단일 경제 신호 하나 |",
        "| `thesis` | 무엇을 주장하는가 |",
        "| `mechanism` | 왜 초과수익이 나는가. 경제적 메커니즘이지 통계적 기대가 아니다 |",
        "| `falsification` | 무엇을 보면 기각하는가 |",
        "| **`expected_relationship`** | **아래 목록의 어느 팩터와 어떻게 다른가.** 같은 개념의 재구성이면 새 후보가 아니다 |",
        "| `data_notes` | 쓰는 입력과 그 한계 |",
        "",
        "> `expected_relationship` 을 빈칸으로 두지 않는다. 이름이 달라도 같은 개념이면 중복이다 —",
        "> 아래 목록에서 **가장 가까운 것을 스스로 지목하고 무엇이 다른지 적는다.**",
        "",
        "**요청자가 무엇을 물었든, 후보를 낼 때는 항상 다음 한 줄을 붙인다.**",
        "",
        "```",
        "가장 가까운 기존 팩터: <4절 목록에서 하나> — 차이: <한 줄>",
        "```",
        "",
        f"붙일 대상이 떠오르지 않으면 4절을 다시 읽는다. 목록이 {len(rows)}건이라 \"없다\"는 답은 거의 틀린다.",
        "같은 변수를 부호나 표현만 뒤집은 것(예: 고점 대비 근접도 ↔ 고점 대비 낙폭,",
        "변동성 ↔ 안정성)은 **새 후보가 아니라 같은 후보**다.",
        "",
    ]

    # ── ③ 어느 쪽이 이미 채워졌나 (개념 축) ──────────────────────────────
    out += ["## 3. 어느 쪽이 이미 채워졌나", ""]
    themes = Counter(r.get("jkp_theme") or UNMATCHED for r in rows)
    for theme in JKP_THEMES:
        out.append(f"- {theme}: {themes.get(theme, 0)}건 등록")
    if themes.get(UNMATCHED):
        out.append(f"- {UNMATCHED}: {themes[UNMATCHED]}건")
    out.append("")

    out += ["### 구조적 교훈", ""]
    if not reflections:
        out.append("아직 성찰 기록 없음.")
    for ref in reflections:
        ref_key = (ref.get("campaign_id"), ref.get("epoch_id"))
        out.append(f"**{ref.get('campaign_id')} / {ref.get('epoch_id')}**")
        out.append("")
        epoch_sealed = ref_key not in released_epochs
        for lesson in ref.get("lessons", []):
            key = (ref.get("campaign_id"), ref.get("epoch_id"), lesson.get("factor"))
            if epoch_sealed or key in sealed:
                epoch_sealed = True
                out.append(f"- `{lesson.get('factor')}` ({lesson.get('family')}) — 시행함")
                continue
            out.append(
                f"- `{lesson.get('factor')}` ({lesson.get('family')}) — "
                f"{lesson.get('outcome')} · 신규성 {lesson.get('novelty')}"
            )
        # duplicates 는 같은 상관 신호에서 나온 평가 파생값이라 봉인되면 함께 가린다.
        if epoch_sealed:
            out.append(f"- {SEALED_NOTE}. 무엇을 시도했는지만 남는다.")
        else:
            for dup in ref.get("duplicates", []):
                out.append(f"- 중복: {dup}")
        out.append("")

    # ── ④ 시행 전량 (스캔용, 가장 뒤) ────────────────────────────────────
    out += [
        "## 4. 시행 전량", "",
        f"시행 {len(rows)}건" + (f" · 생략 {omitted}건" if omitted else " · 생략 없음"),
        "", "| cycle | factor | family | ruleset | 테마 | 데이터 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| `{r['cycle_id']}` | `{r['factor']}` | `{r['family']}` | "
            f"`{r['ruleset_version']}` | {r.get('jkp_theme') or '-'} | {r.get('cat_data') or '-'} |"
        )
    return "\n".join(out) + "\n"


def render_crosstab(rows: list[dict]) -> str:
    """JKP 13테마 × Cat.Data. 관측 0인 행도 반드시 남는다."""
    grid = Counter(
        (r.get("jkp_theme") or UNMATCHED, r.get("cat_data") or UNMATCHED) for r in rows
    )
    columns = list(CAT_DATA) + [UNMATCHED]
    width = max(len(t) for t in JKP_THEMES) + 2
    out = ["# 분류 교차표", "", "```",
           " " * width + "".join(f"{c[:10]:>11}" for c in columns)]
    # 하드코딩된 JKP_THEMES 를 순회한다. 데이터에 있는 값만 모으면 빈 행이 사라진다.
    for theme in JKP_THEMES:
        out.append(f"{theme:<{width}}" + "".join(f"{grid.get((theme, c), 0):>11}" for c in columns))
    out.append(f"{UNMATCHED:<{width}}" + "".join(f"{grid.get((UNMATCHED, c), 0):>11}" for c in columns))
    out += ["```", "",
            f"행 {len(JKP_THEMES)} + 미매칭 1 · 시행 {len(rows)}건",
            "",
            "0 은 관측이 없다는 뜻이다. `Analyst` · `Options` · `13F` 열은 Silver 에 해당 데이터가 없어",
            "구조적으로 빌 수밖에 없다 — 연구를 안 한 것과 못 하는 것을 구분해서 읽는다.",
            ""]
    return "\n".join(out)


def render_duplication(
    rows: list[dict], reflections: list[dict], labels: dict[str, dict], sealed: set[tuple]
) -> str:
    """중복 재발을 예측·발생·해결 세 단으로 보인다.

    **사람이 읽는 분석 뷰이지 에이전트 컨텍스트가 아니다.** `lessons.md` 만 파일로 쓰이고
    SKILL.md 가 등록한다. 그래서 여기서는 봉인된 판정을 수치로 세지 않고, 몇 건이 가려졌는지만
    밝힌 뒤 봉인 밖 신호인 라벨의 `variant_of` 로 같은 주장을 세운다.
    """
    measured: dict[str, str] = {}       # factor -> novelty (봉인 밖만)
    withheld: list[str] = []
    for ref in reflections:
        for lesson in ref.get("lessons", []):
            name = lesson.get("factor")
            if not name:
                continue
            key = (ref.get("campaign_id"), ref.get("epoch_id"), name)
            if key in sealed:
                if name not in withheld:
                    withheld.append(name)
                continue
            measured.setdefault(name, lesson.get("novelty") or "UNMEASURED")
    counts = Counter(measured.values())
    repeats = [f for f, v in measured.items() if v in {"DUPLICATE", "RELATED"}]
    parents = {r["factor"]: r.get("variant_of") for r in labels.values()}
    variants = [f for f, p in parents.items() if p]

    out = [
        "# 중복 연구가 실제로 일어나고 있다", "",
        "## ① 예측 — 기억층이 없으면 중복이 난다", "",
        "루프는 회차마다 독립이다. 앞 회차가 무엇을 시도했는지 다음 회차가 모르면",
        "같은 자리를 다시 판다. 이 계획의 전제이자, 검증 가능한 예측이다.", "",
        "## ② 발생", "",
    ]
    if withheld:
        out += [
            f"성찰이 남은 {len(withheld) + len(measured)}건 중 **{len(withheld)}건은 봉인 경계 뒤**라",
            "엔진의 신규성 판정을 여기에 세지 않는다. 판정을 반출하지 않고도 중복을 말할 수 있는",
            "경로가 아래 ③이다.", "",
        ]
    if measured:
        out += [f"봉인 밖 {len(measured)}건의 신규성 판정:", ""]
        for key in ("DUPLICATE", "RELATED", "INDEPENDENT", "UNMEASURED"):
            if counts.get(key):
                out.append(f"- `{key}` {counts[key]}건")
        out += ["", f"**{len(repeats)}건이 신규가 아니다.**", ""]

    out += [
        "## ③ 해결 — 봉인 밖 신호로 같은 것을 말한다", "",
        "라벨의 `variant_of` 는 공개 분류(OSAP·JKP)와 정의를 보고 붙인다. **평가 결과를 쓰지 않는다.**",
        f"시행 {len(rows)}건 중 **{len(variants)}건이 다른 시행의 변형**으로 지목돼 있다.", "",
        "| factor | 변형의 부모 | 테마 |",
        "|---|---|---|",
    ]
    themes = {r["factor"]: r.get("jkp_theme") for r in labels.values()}
    for name in variants:
        out.append(f"| `{name}` | `{parents[name]}` | {themes.get(name) or '—'} |")
    out += ["",
            "`lessons.md` 는 이 계보와 시행 전량의 정체성을 다음 회차로 넘긴다.",
            "판정이 아니라 **무엇을 이미 시도했는가**가 중복을 막는다.", "",
            "---", "",
            "> **봉인 관련 주석** — `outcome` 은 `failed_tiers` 의 순함수이고 `novelty` 는",
            "> `strongest_relationship` 을 3분할한 값이다. 둘 다 이름만 범주형일 뿐 게이트 결과의",
            "> 함수라, 봉인에 걸리는 시행에서는 반출하지 않는다. 위 ③의 `variant_of` 는 공개 분류에서",
            "> 유도한 값이라 경계와 무관하다.", ""]
    return "\n".join(out)


def render_before_after(rows: list[dict], latest: Path) -> str:
    """현행 latest.md 와 신규 컨텍스트의 반영 범위를 나란히 놓는다. latest.md 는 읽기만 한다."""
    before = 0
    notice = "없음"
    if latest.exists():
        text = latest.read_text(encoding="utf-8")
        before = sum(1 for line in text.splitlines() if line.startswith("| `cycle-"))
        if "생략됐다" in text:
            notice = "있음"
    return "\n".join([
        "# before / after",
        "",
        "| | 현행 `latest.md` | 신규 `lessons.md` |",
        "|---|---:|---:|",
        f"| 반영된 시행 | {before} | {len(rows)} |",
        f"| 생략 고지 | {notice} | 있음 |",
        f"| 분류 축 | 없음 | JKP 13테마 · OSAP 2축 |",
        "",
        "반영 수는 실행 시점의 파일에서 읽는다. 두 수가 같아도 정상이다.",
        "",
    ])


def _validate_rendered_memory(text: str, sealed: set[tuple]) -> None:
    """Reject result fields and sealed result-derived vocabulary."""
    leaked = sorted(
        word for word in FORBIDDEN
        if re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])", text,
        )
    )
    if leaked:
        raise ValueError(f"금지 필드가 출력에 들어갔다: {', '.join(leaked)}")
    for name in sorted(factor for _, _, factor in sealed):
        for line in text.splitlines():
            if f"`{name}`" not in line:
                continue
            hit = sorted(
                word for word in RESULT_VOCABULARY
                if re.search(
                    rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])",
                    line,
                )
            )
            if hit:
                raise ValueError(
                    f"봉인된 시행 {name} 의 평가 파생 라벨이 출력에 들어갔다: "
                    f"{', '.join(hit)}"
                )


def refresh_lessons(
    root: Path | str = "research", *, context_cutoff: str | None = None,
) -> Path:
    """Synchronize lossless identity labels and atomically refresh lessons."""
    root = Path(root)
    sync_identity_labels(root)
    history, labels, reflections = load(root)
    rows = identity_rows(history, labels)
    visible_cutoff, active_campaign_id = seal_state(root, context_cutoff)
    sealed_ids = sealed_cycles(history, visible_cutoff, active_campaign_id)
    sealed = sealed_lessons(history, reflections, sealed_ids)
    released_epochs = {
        (reflection.get("campaign_id"), reflection.get("epoch_id"))
        for reflection in reflections
        if directives_released(reflection, history, sealed_ids)
    }
    text = render_lessons(
        rows, reflections, omitted=0, sealed=sealed,
        released_epochs=released_epochs,
    )
    _validate_rendered_memory(text, sealed)
    path = root / "memory" / "lessons.md"
    _atomic_write_text(path, text)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="누적 시행 컨텍스트를 만든다")
    ap.add_argument("--research-dir", default="research", help="기본 research")
    ap.add_argument("--view", choices=["lessons", "crosstab", "before-after", "duplication"], default="lessons")
    ap.add_argument("--out", help="지정하면 파일로 쓴다 (기본: lessons 만 저장)")
    ap.add_argument(
        "--context-cutoff",
        help="진행 중 campaign 이 없을 때의 가시 cutoff. 없으면 전량 봉인으로 본다",
    )
    args = ap.parse_args()

    root = Path(args.research_dir)
    sync_identity_labels(root)
    history, labels, reflections = load(root)
    rows = identity_rows(history, labels)

    visible_cutoff, active_campaign_id = seal_state(root, args.context_cutoff)
    sealed_ids = sealed_cycles(history, visible_cutoff, active_campaign_id)
    sealed = sealed_lessons(history, reflections, sealed_ids)
    released_epochs = {
        (reflection.get("campaign_id"), reflection.get("epoch_id"))
        for reflection in reflections
        if directives_released(reflection, history, sealed_ids)
    }

    if args.view == "crosstab":
        text = render_crosstab(rows)
    elif args.view == "duplication":
        text = render_duplication(
            rows, reflections,
            {r["cycle_id"]: r for r in read_jsonl(root / "memory" / "labels.jsonl")},
            sealed,
        )
    elif args.view == "before-after":
        text = render_before_after(rows, root / "context" / "latest.md")
    else:
        text = render_lessons(
            rows, reflections, omitted=0, sealed=sealed,
            released_epochs=released_epochs,
        )

    try:
        _validate_rendered_memory(text, sealed)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.out:
        _atomic_write_text(Path(args.out), text)
        print(f"wrote {args.out}")
    elif args.view == "lessons":
        path = root / "memory" / "lessons.md"
        _atomic_write_text(path, text)
        print(f"wrote {path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
