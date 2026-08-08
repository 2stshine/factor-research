#!/usr/bin/env python3
"""누적 시행을 다음 루프가 읽을 컨텍스트로 뽑는다.

`research/history.jsonl` 과 epoch `reflection.json` 을 읽어 `research/memory/lessons.md` 를 만든다.
`research/context/latest.md` 는 읽지도 쓰지도 않는다.

내보내는 것은 두 가지뿐이다.
  ① 정체성   cycle_id · factor · family · ruleset_version · 축 라벨
  ② 교훈     reflection.json 의 lessons[] (outcome · novelty) 와 duplicates

내보내지 않는 것 — verdict, failed_checks, strongest_relationship, 결과 집계와 빈도,
성과 수치, 파라미터 수정안, analysis. 봉인 OOS 를 지키기 위한 제약이며 WHITELIST 가 강제한다.

    python scripts/lessons.py                   # lessons.md 생성
    python scripts/lessons.py --view crosstab   # 분류 교차표 (13테마 항상 전부)
    python scripts/lessons.py --view before-after
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

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


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def render_lessons(rows: list[dict], reflections: list[dict], omitted: int) -> str:
    out = [
        "# 누적 시행 컨텍스트",
        "",
        "> 결정론 코드가 만든다. 다음 루프는 새 후보를 세우기 전에 이 파일을 읽는다.",
        "> **판정 결과는 담기지 않는다** — 봉인 OOS 를 지키기 위해 정체성과 구조적 교훈만 남긴다.",
        "",
        f"시행 {len(rows)}건" + (f" · 생략 {omitted}건" if omitted else " · 생략 없음"),
        "",
        "## 시도한 것",
        "",
        "| cycle | factor | family | ruleset | 테마 | 데이터 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| `{r['cycle_id']}` | `{r['factor']}` | `{r['family']}` | "
            f"`{r['ruleset_version']}` | {r.get('jkp_theme') or '-'} | {r.get('cat_data') or '-'} |"
        )

    out += ["", "## 등록 팩터 요약", ""]
    themes = Counter(r.get("jkp_theme") or UNMATCHED for r in rows)
    for theme in JKP_THEMES:
        out.append(f"- {theme}: {themes.get(theme, 0)}건 등록")
    if themes.get(UNMATCHED):
        out.append(f"- {UNMATCHED}: {themes[UNMATCHED]}건")

    out += ["", "## 구조적 교훈", ""]
    if not reflections:
        out.append("아직 성찰 기록 없음.")
    for ref in reflections:
        out.append(f"### {ref.get('campaign_id')} / {ref.get('epoch_id')}")
        out.append("")
        for lesson in ref.get("lessons", []):
            out.append(
                f"- `{lesson.get('factor')}` ({lesson.get('family')}) — "
                f"{lesson.get('outcome')} · 신규성 {lesson.get('novelty')}"
            )
        for dup in ref.get("duplicates", []):
            out.append(f"- 중복: {dup}")
        out.append("")
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


def main() -> None:
    ap = argparse.ArgumentParser(description="누적 시행 컨텍스트를 만든다")
    ap.add_argument("--research-dir", default="research", help="기본 research")
    ap.add_argument("--view", choices=["lessons", "crosstab", "before-after"], default="lessons")
    ap.add_argument("--out", help="지정하면 파일로 쓴다 (기본: lessons 만 저장)")
    args = ap.parse_args()

    root = Path(args.research_dir)
    history, labels, reflections = load(root)
    rows = identity_rows(history, labels)

    if args.view == "crosstab":
        text = render_crosstab(rows)
    elif args.view == "before-after":
        text = render_before_after(rows, root / "context" / "latest.md")
    else:
        text = render_lessons(rows, reflections, omitted=0)

    # 부분 문자열이 아니라 독립 식별자로만 잡는다. `net_roa` 의 net, `trading_turnover_20d` 의
    # turnover 는 팩터명의 일부이지 metrics 키가 아니다.
    leaked = sorted(
        w for w in FORBIDDEN
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(w)}(?![A-Za-z0-9_])", text)
    )
    if leaked:
        raise SystemExit(f"금지 필드가 출력에 들어갔다: {', '.join(leaked)}")

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    elif args.view == "lessons":
        path = root / "memory" / "lessons.md"
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
