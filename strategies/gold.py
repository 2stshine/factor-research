"""gold.factor 카탈로그 조회 — 전략이 쓸 팩터 목록을 하드코딩하지 않는다.

승격 팩터가 늘어나면 이 목록이 자동으로 따라간다. RDS 조회 결과는 캐시하므로 평소
실행에는 접속이 필요 없다.

    uv run python -m strategies.gold        # 목록 갱신 (RDS 필요)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine import silver

CACHE = REPO_ROOT / ".cache" / "gold_factors.json"
GENERATION_ROOT = REPO_ROOT / ".cache" / "gold-signals"

GOLD_SQL = """
SELECT factor_key, version, status,
       evaluation->>'verdict'         AS verdict,
       evaluation->>'ruleset_version' AS ruleset
FROM gold.factor
WHERE status = 'APPROVED'
ORDER BY factor_key, version
"""


def refresh(verbose: bool = True) -> list[str]:
    """RDS에서 APPROVED 팩터 목록을 받아 캐시한다."""
    with silver.connect(read_only=True) as conn:
        with conn.cursor() as cur:
            cur.execute(GOLD_SQL)
            rows = cur.fetchall()
    keys = sorted({r[0] for r in rows})
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(keys, ensure_ascii=False, indent=2))
    if verbose:
        print(f"gold.factor APPROVED {len(keys)}개")
        for r in rows:
            print(f"  {r[0]:<45} v{r[1]}  {r[3]}  {r[4]}")
        print(f"\n캐시 저장: {CACHE}")
    return keys


def _newest_generation() -> tuple[float, tuple[str, ...]] | None:
    """엔진이 남긴 gold signal 캐시 중 가장 최근 generation의 승인 목록.

    엔진(연구 루프)은 승격이 일어날 때마다 generation 캐시를 새로 쓰므로, 이
    manifest들이 로컬에서 가장 신선한 승인 집합 증거인 경우가 많다. RDS 조회
    스냅샷(`CACHE`)과 기록자가 달라 어느 쪽이 낡았는지는 mtime으로 가른다.
    """
    newest: tuple[float, tuple[str, ...]] | None = None
    if not GENERATION_ROOT.is_dir():
        return None
    for manifest_path in GENERATION_ROOT.glob("*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        keys = manifest.get("generation", {}).get("approved_factor_keys")
        if not keys:
            continue
        mtime = manifest_path.stat().st_mtime
        if newest is None or mtime > newest[0]:
            newest = (mtime, tuple(sorted(str(k) for k in keys)))
    return newest


def approved_factors(default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """가장 최근 로컬 증거 기준의 APPROVED 팩터 목록.

    RDS 조회 캐시(`refresh`)와 엔진 generation 캐시 중 **더 최근에 쓰인 쪽**을
    쓴다. 연구 루프가 승격을 이어가는 동안 RDS 캐시만 믿으면 전략이 옛
    부분집합으로 조용히 돌게 된다 — 실제로 승인 32개 시점에 22개 캐시로 돌던
    사고가 있었다. RDS 캐시는 `python -m strategies.gold`를 다시 돌리면 최신이
    되고, 그러면 다시 그쪽이 이긴다.
    """
    snapshot: tuple[float, tuple[str, ...]] | None = None
    if CACHE.exists():
        snapshot = (CACHE.stat().st_mtime, tuple(json.loads(CACHE.read_text())))
    generation = _newest_generation()
    if generation is not None and (snapshot is None or generation[0] > snapshot[0]):
        if snapshot is not None and set(generation[1]) != set(snapshot[1]):
            print(
                f"  [gold] RDS 조회 캐시({len(snapshot[1])}개)보다 최신인 엔진 "
                f"generation({len(generation[1])}개)을 사용합니다 — "
                "`uv run python -m strategies.gold`로 동기화를 권장합니다"
            )
        return generation[1]
    if snapshot is not None:
        return snapshot[1]
    return default


if __name__ == "__main__":
    refresh()
