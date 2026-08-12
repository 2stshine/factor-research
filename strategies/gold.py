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


def approved_factors(default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """캐시된 APPROVED 팩터 목록. 없으면 `default`를 쓴다."""
    if CACHE.exists():
        return tuple(json.loads(CACHE.read_text()))
    return default


if __name__ == "__main__":
    refresh()
