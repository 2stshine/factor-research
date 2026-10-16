"""Local fail-closed boundary for archived research (not database RBAC).

No environment flag silently re-enables legacy Gold. Explicit legacy CLI access
allows local reproduction, never publication, under an active new generation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_POLICY = ROOT / "research" / "active-generation.json"


def new_generation_active() -> bool:
    if not ACTIVE_POLICY.exists():
        # A missing pointer in an initialized workspace is an error, not a
        # fallback to whichever old Gold cache happens to be most recent.
        if (ACTIVE_POLICY.parent / "generations").exists():
            raise ValueError("Active research generation pointer is missing")
        return False
    policy = json.loads(ACTIVE_POLICY.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or not policy:
        raise ValueError("Invalid active research generation policy")
    # Once the explicit cutover file exists, no legacy Gold writes/fallbacks.
    # Exact pointer/hash/library validation belongs to research_generation.
    return True


def require_legacy_read(action: str) -> None:
    if new_generation_active():
        raise ValueError(
            f"{action}: legacy Gold is archived and excluded from the active generation. "
            "Use the new generation's exact library; an empty library is not an old-Gold fallback."
        )


def require_legacy_gold_write(action: str) -> None:
    if new_generation_active():
        raise ValueError(
            f"{action}: legacy Gold is preserved read-only by this repository. "
            "Use the isolated new-generation reference publisher; this legacy publisher remains disabled."
        )


def require_legacy_cli(command: str, *, explicit: bool = False, writes_gold: bool = False) -> None:
    if not new_generation_active():
        return
    if writes_gold:
        require_legacy_gold_write(command)
    if not explicit:
        raise ValueError(
            f"{command}: archived research entry point. Use scripts.research_generation active "
            "for the active generation; --legacy is required for explicit legacy reproduction."
        )
