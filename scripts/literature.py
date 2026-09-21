"""Render curated external literature, never trial evidence or execution authority.

The JSON catalog is manually source-checked; rendering does not browse, execute
paper code, certify local data, or claim a local replication.
"""
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlparse


VERSION = "factor-literature-v1"
GROUPS = ("economic_mechanism", "validation", "research_process")
GROUP_LABELS = dict(zip(GROUPS, ("가설과 경제적 메커니즘", "검증과 재현성", "레짐·AI 연구 과정")))
READ_SCOPES = {
    "PRIMARY_ABSTRACT": "원저자/출판사 초록 확인",
    "PRIMARY_TEXT_SECTIONS": "원논문 해당 절 확인",
}
TEXT_FIELDS = {
    "id": 80, "topic": 30, "label": 100, "title": 240, "authors": 200,
    "source_url": 500, "source_locator": 200, "read_scope": 30,
    "finding": 400, "project_application": 400, "diagnostic_question": 300,
    "data_requirements": 400, "limitations": 400,
}


def load_literature(root: Path | str) -> dict | None:
    path = Path(root) / "memory/literature.json"
    if not path.exists():
        return None  # Other/test research roots need not have a catalog.
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "reviewed_on", "entries"}:
        raise ValueError("Invalid literature catalog fields")
    if payload["schema_version"] != VERSION:
        raise ValueError("Unsupported literature catalog version")
    reviewed = date.fromisoformat(payload["reviewed_on"])
    entries = payload["entries"]
    if not isinstance(entries, list):
        raise ValueError("Literature entries must be a list")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != set(TEXT_FIELDS) | {"year", "local_replication"}:
            raise ValueError("Invalid literature entry fields")
        for field, maximum in TEXT_FIELDS.items():
            value = entry[field]
            if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
                raise ValueError(f"Invalid literature text: {field}")
        identity = entry["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,79}", identity) or identity in seen:
            raise ValueError("Duplicate or invalid literature identity")
        seen.add(identity)
        url = urlparse(entry["source_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or any(c in entry["source_url"] for c in '<>" \\'):
            raise ValueError("Literature source must be an HTTPS citation")
        if entry["topic"] not in GROUPS or entry["read_scope"] not in READ_SCOPES:
            raise ValueError("Invalid literature category or reading scope")
        if type(entry["year"]) is not int or not 1900 <= entry["year"] <= reviewed.year:
            raise ValueError("Invalid literature publication year")
        if entry["local_replication"] != "NOT_ESTABLISHED":
            raise ValueError("External literature cannot certify local replication")
    return payload


def _plain(value: str) -> str:
    # Keep curated prose as text, not new Markdown sections or active links.
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", value)


def render_literature(root: Path | str) -> str:
    catalog = load_literature(root)
    if catalog is None or not catalog["entries"]:
        return ""
    entries = catalog["entries"]
    lines = [
        "## 외부 문헌 지식",
        "",
        f"원문 확인: {catalog['reviewed_on']} · 선별 문헌 {len(entries)}건 · 저장 원본: `research/memory/literature.json`.",
        "논문 관측과 우리 프로젝트 적용 제안을 구분한다. 국내 실증 교훈·독립 재현·사용 가능한 데이터 인증이 아니다.",
        "현재 시점의 연구 참고자료다. 과거 시점에도 이 문헌을 알았다는 뜻이 아니며, 재사용한 과거 OOS가 새 독립 검증이 되지 않는다.",
        "논문 수익률·최적 파라미터를 옮겨 합격 기준으로 쓰지 않는다. 원문 전체 대신 해당 주장과 한계만 요약했다.",
        "입력 연결 상태는 검토일의 KNOWLEDGE/DATA_INVENTORY 기준이며 새 후보마다 가용성과 중복을 다시 확인한다.",
        "",
    ]
    for topic in GROUPS:
        selected = sorted((e for e in entries if e["topic"] == topic), key=lambda e: e["id"])
        if not selected:
            continue
        lines += [f"### {GROUP_LABELS[topic]}", ""]
        for item in selected:
            lines += [
                f"#### {item['id']} — {_plain(item['label'])}",
                "",
                f"- 출처: [{_plain(item['title'])} ({item['year']})](<{item['source_url']}>) — {_plain(item['authors'])}.",
                f"- 확인 범위: {READ_SCOPES[item['read_scope']]} · {_plain(item['source_locator'])}.",
                f"- 논문 관측: {_plain(item['finding'])}",
                f"- 프로젝트 적용 **제안**: {_plain(item['project_application'])}",
                f"- 구별할 질문: {_plain(item['diagnostic_question'])}",
                f"- 필요한 입력/현재 제약: {_plain(item['data_requirements'])}",
                f"- 해석 한계: {_plain(item['limitations'])} 국내 동일 정의 재현은 미확인.",
                "",
            ]
    return "\n".join(lines)
