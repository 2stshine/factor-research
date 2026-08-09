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
    python scripts/lessons.py --view duplication  # 중복 재발: 예측→발생→해결
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


def render_duplication(rows: list[dict], reflections: list[dict], labels: dict[str, dict]) -> str:
    """중복 재발을 예측·발생·해결 세 단으로 보인다.

    novelty 는 엔진이 reflection 채널에 범주형으로 남긴 값이다. 판정 수치가 아니라
    구조적 교훈이므로 봉인 반출 범위 안에 있다 — 이 뷰가 성립하는 근거다.
    """
    seen: dict[str, str] = {}          # factor -> novelty
    order: list[str] = []
    for ref in reflections:
        for lesson in ref.get("lessons", []):
            name = lesson.get("factor")
            if name and name not in seen:
                seen[name] = lesson.get("novelty") or "UNMEASURED"
                order.append(name)
    counts = Counter(seen.values())
    repeats = [f for f in order if seen[f] in {"DUPLICATE", "RELATED"}]
    parents = {r["factor"]: r.get("variant_of") for r in labels.values()}

    out = [
        "# 중복 연구가 실제로 일어나고 있다", "",
        "## ① 예측 — 기억층이 없으면 중복이 난다", "",
        "루프는 회차마다 독립이다. 앞 회차가 무엇을 시도했는지 다음 회차가 모르면",
        "같은 자리를 다시 판다. 이 계획의 전제이자, 검증 가능한 예측이다.", "",
        "## ② 발생 — 엔진이 스스로 중복이라고 찍었다", "",
        f"성찰이 남은 {len(seen)}건의 신규성 판정:", "",
    ]
    for key in ("DUPLICATE", "RELATED", "INDEPENDENT", "UNMEASURED"):
        if counts.get(key):
            out.append(f"- `{key}` {counts[key]}건")
    out += ["",
            f"**{len(repeats)}건이 신규가 아니다.** 우리가 붙인 라벨과 무관하게",
            "엔진이 판정한 값이다.", "",
            "| factor | 신규성 | 라벨이 지목한 부모 |",
            "|---|---|---|"]
    for name in repeats:
        out.append(f"| `{name}` | {seen[name]} | {parents.get(name) or '—'} |")

    agree = [f for f in repeats if parents.get(f)]
    out += ["",
            "## ③ 해결 — 기억층이 이 정보를 다음 회차로 넘긴다", "",
            "`lessons.md` 는 시행 전량의 정체성과 이 신규성 판정을 함께 싣는다.",
            "다음 회차는 무엇이 이미 시도됐고 무엇이 무엇의 변형인지 보고 시작한다.", "",
            f"라벨의 `variant_of` 와 엔진의 신규성 판정이 겹치는 건 {len(agree)}건이다 — ",
            "서로 다른 두 경로가 같은 중복을 지목한다.", "",
            "---", "",
            "> **봉인 관련 주석** — `novelty` 는 `reflection.json` 채널의 **범주형 라벨**이다.",
            "> 성과 수치도 판정 결과도 아니고, 엔진이 다음 epoch 에 넘기려고 만든 구조적 교훈이다.",
            "> 따라서 이 뷰가 쓰는 값은 전부 봉인 반출 허용 범위 안에 있다.",
            "> 반출 금지 대상 — 판정 결과, 실패한 검사의 이름, 성과 수치, 결과 집계 — 은 이 뷰에 없다.", ""]
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
    ap.add_argument("--view", choices=["lessons", "crosstab", "before-after", "duplication"], default="lessons")
    ap.add_argument("--out", help="지정하면 파일로 쓴다 (기본: lessons 만 저장)")
    args = ap.parse_args()

    root = Path(args.research_dir)
    history, labels, reflections = load(root)
    rows = identity_rows(history, labels)

    if args.view == "crosstab":
        text = render_crosstab(rows)
    elif args.view == "duplication":
        text = render_duplication(rows, reflections, {r["cycle_id"]: r for r in read_jsonl(root / "memory" / "labels.jsonl")})
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
