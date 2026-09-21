"""Compact candidate-facing knowledge; operational history stays in its ledger."""
from pathlib import Path
import re


def _sections(text: str) -> dict[str, str]:
    """Read top-level sections without carrying adjacent reports into the prompt."""
    sections = {}
    title = None
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:]
            if title in sections:
                raise ValueError(f"Duplicate knowledge section: {title}")
            sections[title] = []
        elif title is not None:
            sections[title].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _registry_rows(sections: dict[str, str]) -> list[dict] | None:
    rows = []
    found = False
    for title, body in sections.items():
        if not title.startswith("Registered factors"):
            continue
        found = True
        for line in body.splitlines():
            if not line.startswith("| `"):
                continue
            cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
            if len(cells) != 5 or not re.fullmatch(r"[a-z][a-z0-9_]*", cells[0]):
                raise ValueError("Invalid registered definition identity")
            rows.append(dict(zip(("name", "category", "family", "definition_hash", "needs"), cells)))
    return rows if found else None


def _input_context(sections: dict[str, str]) -> str:
    if "Frozen research state" not in sections:
        raise ValueError("Filtered input context missing; run scripts/research.py context first")
    # Keep the existing input boundary and data-contract information. Campaign
    # status tables, outcome summaries, and duplicated identity counts are not
    # part of candidate knowledge. Execution still checks original manifests.
    lines = [line for line in sections["Frozen research state"].splitlines()
             if not line.startswith(("- Active sealed campaign:", "- Recorded autonomous cycles:"))]
    text = "## Frozen research state\n\n" + "\n".join(lines).strip() + "\n"
    if "Available strategy inputs" in sections:
        text += "\n## Available strategy inputs\n\n" + sections["Available strategy inputs"] + "\n"
    return text


def refresh_knowledge(
    root: Path | str = "research", *, context_text: str | None = None,
    context_cutoff: str | None = None,
) -> Path:
    from scripts.lessons import _atomic_write_text
    from scripts.literature import render_literature
    from scripts.factor_memory import build_factor_index, render_attempt_summary, write_factor_index

    root = Path(root)
    # Validate the external catalog before any memory regeneration side effects.
    literature_text = render_literature(root)
    if context_text is None:
        target = root / "KNOWLEDGE.md"
        if not target.exists():
            raise ValueError("KNOWLEDGE missing; run scripts/research.py context first")
        context_text = target.read_text(encoding="utf-8")
    sections = _sections(context_text)
    input_text = _input_context(sections)
    index = build_factor_index(root, registry_rows=_registry_rows(sections))
    from scripts.candidate_lessons import refresh_candidate_lessons, render_grouped_lessons
    candidate_records = refresh_candidate_lessons(root)
    text = (
        "# 연구 지식\n\n"
        "> 자동 생성. 지침은 INSTRUCTIONS.md에만 둔다. 외부 문헌과 내부 실증 교훈은 구분한다.\n"
        "> 사용할 데이터 · 기존 가설/계산의 요약 · 검토된 교훈과 문헌만 담는다.\n"
        "> 이 파일 생성은 DB 재인증이 아니다. 입력 경계는 아래, 실행 상태는 해당 campaign 원본에서 확인한다.\n\n"
        "보유 데이터·적재 범위·운영 상태는 [DATA_INVENTORY.md](DATA_INVENTORY.md)를 참조한다. "
        "아래 입력 목록은 현재 연구 패널에 연결된 데이터만 나타낸다.\n\n"
        + input_text + "\n" + render_attempt_summary(index)
        + "\n" + render_grouped_lessons(candidate_records)
        + ("\n" + literature_text if literature_text else "")
    )
    write_factor_index(root, index)
    target = root / "KNOWLEDGE.md"
    _atomic_write_text(target, text)
    return target


if __name__ == "__main__":
    print(refresh_knowledge())
