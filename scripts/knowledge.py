"""Build the two-layer knowledge entry from already boundary-filtered artifacts."""
from pathlib import Path


def refresh_knowledge(
    root: Path | str = "research", *, context_text: str | None = None,
    context_cutoff: str | None = None,
) -> Path:
    from scripts.lessons import _atomic_write_text, render_memory

    root = Path(root)
    if context_text is None:
        target = root / "KNOWLEDGE.md"
        if not target.exists():
            raise ValueError("KNOWLEDGE missing; run scripts/research.py context first")
        context_text = target.read_text(encoding="utf-8").split("## 공개 가능한 최근 성찰")[0]
    memory_text = render_memory(root, context_cutoff=context_cutoff)
    from scripts.candidate_lessons import refresh_candidate_lessons, render_grouped_lessons
    candidate_records = refresh_candidate_lessons(root)
    # Recent-cycle table duplicates the complete identity index and carries outcomes.
    context_text = context_text.split("## Prior autonomous cycles")[0]
    context_text = context_text[context_text.index("## Frozen research state"):]
    # Fixed candidate rules belong only in INSTRUCTIONS. Retain filtered observations.
    before, rest = memory_text.split("## 2. 후보 하나가 갖춰야 할 것", 1)
    _, after = rest.split("## 3. 어느 쪽이 이미 채워졌나", 1)
    before = before[before.index("## 1. 이번 회차의 제약"):]
    # Per-epoch sealed identity bullets repeat the complete trial index.
    overview, identities = after.split("## 4. 시행 전량", 1)
    distribution, lessons = overview.split("### 구조적 교훈", 1)
    blocks = lessons.split("**campaign-")
    safe_blocks = ["**campaign-" + b for b in blocks[1:] if "봉인 경계 뒤" not in b]
    text = (
        "# 연구 지식\n\n"
        "> 자동 생성. 지침은 INSTRUCTIONS.md에만 둔다. 논문 지식은 미포함.\n"
        "> 데이터 컨텍스트와 연구 원장에서 생성하며 기존 봉인 필터를 적용한다.\n"
        "> 이 파일 생성은 DB 재인증이 아니다. 아래 cutoff와 campaign 상태를 확인한다.\n\n"
        + context_text + "\n## 공개 가능한 최근 성찰\n\n"
        + before.replace("## 1. 이번 회차의 제약", "### 관측된 제약")
        + "\n## 탐색 영역 분포\n" + distribution
        + "\n## 공개 가능한 구조적 교훈\n\n"
        + ("".join(safe_blocks) or "공개 가능한 교훈 없음. 봉인 시행은 아래 정체성만 제공한다.\n")
        + "\n## 전체 시행 정체성\n" + identities
        + "\n" + render_grouped_lessons(candidate_records)
    )
    target = root / "KNOWLEDGE.md"
    _atomic_write_text(target, text)
    return target


if __name__ == "__main__":
    print(refresh_knowledge())
