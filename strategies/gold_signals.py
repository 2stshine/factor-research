"""APPROVED 팩터 값 로더 — `gold.factor`에 승인된 팩터만 전략 입력으로 넣는다.

엔진 빌드 캐시(`.cache/panel.pkl`)는 Silver/PIT 입력만 보관하고 팩터 값을 담지 않는다.
승인 팩터의 월말 값은 엔진이 `.cache/gold-signals/<generation_digest>/`에 wide 형태로
캐시해 두므로 전략은 그것을 읽는다. RDS 접속이 필요 없다.

**부호 — 곱하지 않는다.** `gold.factor_value.value`는 이미 방향 조정이 끝나 있다.
엔진 패널의 `f_` 컬럼과 같은 규약이라 값이 클수록 예측 고수익이고, `predicted_sign`을
다시 곱하면 `-1` 팩터가 전부 뒤집힌다.

`engine/publish.py`의 `value_contract`는 `value: "raw"` / `score: "value*predicted_sign"`
이라 적고 있지만 **적재된 값은 계약 문구와 다르다**. 확인 근거:

- `max_daily_return_mean_6m` 발행값 = −(패널 `max_daily_return_1m`의 6개월 평균),
  219,144행 전부 정확히 일치.
- 정의상 음수가 불가능한 양(변동성·가격범위·양수 비율)을 쓰는 `predicted_sign = -1`
  팩터 7종의 발행값이 97~100% 음수. `+1` 팩터는 0.3%만 음수.

`predicted_signs()`는 참조용으로 남겨 두지만 값 변환에는 쓰지 않는다.

    uv run python -m strategies.gold_signals    # 로드 가능 여부·커버리지 점검
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from strategies.gold import approved_factors

CACHE_ROOT = REPO_ROOT / ".cache" / "gold-signals"
IMPLEMENTATION_MANIFEST = REPO_ROOT / "implementations" / "gold" / "manifest.json"
SCHEMA_VERSION = "gold-signal-wide-cache-v1"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _locate(keys: tuple[str, ...]) -> tuple[Path, dict]:
    """승인 exact set과 일치하는 generation 캐시를 찾는다.

    캐시 디렉터리는 generation digest로 나뉘어 있고 승인 팩터가 늘 때마다 새로 생긴다.
    파일 시각이 아니라 **승인 집합 일치**로 고르므로, 캐시가 오래됐으면 조용히 옛
    팩터 집합을 쓰는 대신 실패한다.
    """
    if not CACHE_ROOT.is_dir():
        raise SystemExit(
            f"gold signal 캐시가 없습니다: {CACHE_ROOT}\n"
            "엔진 빌드/연구 루프가 한 번은 돌아야 생성됩니다."
        )
    wanted = sorted(keys)
    seen: list[int] = []
    for manifest_path in sorted(CACHE_ROOT.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        generation = manifest.get("generation", {})
        cached = list(generation.get("approved_factor_keys", []))
        seen.append(len(cached))
        if sorted(cached) == wanted:
            return manifest_path.parent, manifest
    raise SystemExit(
        f"승인 팩터 {len(wanted)}개와 일치하는 gold signal 캐시가 없습니다.\n"
        f"  캐시에 있는 generation 크기: {sorted(set(seen))}\n"
        "승인 목록을 갱신했다면 엔진을 한 번 돌려 캐시를 만드세요:\n"
        "  uv run python scripts/run.py build"
    )


def _verify(directory: Path, manifest: dict, keys: tuple[str, ...]) -> pd.DataFrame:
    """엔진이 쓴 무결성 필드를 그대로 재검증한다."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"gold signal 캐시 schema가 다릅니다: {directory}")
    data_path = directory / "signals.parquet"
    if not data_path.is_file():
        raise SystemExit(f"gold signal 캐시 parquet이 없습니다: {data_path}")
    if manifest.get("parquet_sha256") != _file_sha256(data_path):
        raise SystemExit(f"gold signal 캐시 SHA-256이 다릅니다: {data_path}")
    frame = pd.read_parquet(data_path)
    expected = ["asset_id", "ym", *manifest["generation"]["approved_factor_keys"]]
    if list(frame.columns) != expected:
        raise SystemExit("gold signal 캐시 컬럼이 승인 exact set과 다릅니다")
    if int(manifest.get("row_count", -1)) != len(frame):
        raise SystemExit("gold signal 캐시 row_count가 다릅니다")
    missing = sorted(set(keys) - set(frame.columns))
    if missing:
        raise SystemExit(f"캐시에 없는 승인 팩터: {missing}")
    return frame


def predicted_signs(keys: tuple[str, ...]) -> dict[str, int]:
    """구현 매니페스트에서 팩터별 `predicted_sign`을 읽는다."""
    manifest = json.loads(IMPLEMENTATION_MANIFEST.read_text(encoding="utf-8"))
    missing = [k for k in keys if k not in manifest]
    if missing:
        raise SystemExit(
            f"구현 매니페스트에 없는 승인 팩터: {missing}\n"
            f"  {IMPLEMENTATION_MANIFEST}"
        )
    return {k: int(manifest[k]["predicted_sign"]) for k in keys}


def load_signed(factors: tuple[str, ...] | None = None,
                verbose: bool = False) -> pd.DataFrame:
    """승인 팩터의 월말 값을 `f_<name>` 컬럼으로 반환한다.

    값은 그대로 옮긴다 — 발행 시점에 이미 방향이 적용돼 있다(모듈 docstring 참조).
    반환 컬럼: `asset_id`, `ym`(period[M]), `f_<factor>`...
    """
    keys = tuple(factors) if factors else approved_factors()
    if not keys:
        raise SystemExit(
            "승인 팩터 목록이 비어 있습니다. 먼저 목록을 갱신하세요:\n"
            "  uv run python -m strategies.gold"
        )
    directory, manifest = _locate(keys)
    frame = _verify(directory, manifest, keys)

    out = pd.DataFrame({
        "asset_id": frame["asset_id"].to_numpy(),
        "ym": pd.PeriodIndex(frame["ym"], freq="M"),
    })
    for key in keys:
        out[f"f_{key}"] = frame[key].astype(float)
    if verbose:
        print(f"  [gold_signals] generation {directory.name[:12]} · "
              f"{len(keys)}팩터 · {len(out):,}행 · {out['ym'].min()}~{out['ym'].max()}")
    return out


def main() -> None:
    keys = approved_factors()
    signed = load_signed(keys, verbose=True)
    fcols = [f"f_{k}" for k in keys]
    print(f"\nAPPROVED {len(keys)}개 · 종목 {signed['asset_id'].nunique():,} · "
          f"월 {signed['ym'].nunique()}")
    print("\n팩터별 결측 아닌 비율 / predicted_sign / 발행값 음수비율:")
    signs = predicted_signs(keys)
    for key in keys:
        column = signed[f"f_{key}"]
        print(f"  {key:44s} {column.notna().mean():6.1%}  "
              f"sign={signs[key]:+d}  neg={(column.dropna() < 0).mean():5.1%}")
    print(f"\n합계 결측 아닌 셀: {signed[fcols].notna().to_numpy().mean():.1%}")


if __name__ == "__main__":
    main()
