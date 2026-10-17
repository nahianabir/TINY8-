"""Tiny8 Studio — shared validation rules.

These mirror the limits enforced by the command-line asset converter
(tools/sprite_convert.py) so the GUI cannot accept an asset the engine
will reject.  Tests in tools/tiny8_studio/tests/ pin the constants to
those in tools/sprite_convert.py to keep them in sync.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple


# Engine limits (mirror tiny8_config.h and tools/sprite_convert.py).
MAX_SPRITE_W      = 32
MAX_SPRITE_H      = 32
MAX_PROGMEM_BYTES = 28 * 1024  # 28 KB user-Flash ceiling for the Uno
MAX_TILE_IDS      = 16         # tile palette size
MAX_MAP_W         = 64         # 64 tiles x 8 px = 512 px world
MAX_MAP_H         = 64


@dataclass
class Issue:
    """A single validation finding."""
    level: str   # "error" | "warn"
    msg:   str

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.msg}"


def validate_sprite(name: str, w: int, h: int, bits: List[int]) -> List[Issue]:
    issues: List[Issue] = []
    if not name or not name.replace("_", "").isalnum():
        issues.append(Issue("error", f"asset name {name!r} must be alphanumeric/underscore"))
    if w <= 0 or h <= 0:
        issues.append(Issue("error", f"dimensions must be positive (got {w}x{h})"))
    if w > MAX_SPRITE_W:
        issues.append(Issue("error", f"width {w} > max {MAX_SPRITE_W}"))
    if h > MAX_SPRITE_H:
        issues.append(Issue("error", f"height {h} > max {MAX_SPRITE_H}"))
    expected = ((w + 7) // 8) * h
    if len(bits) != expected and (w > 0 and h > 0):
        issues.append(Issue("error", f"byte count {len(bits)} != expected {expected}"))
    return issues


def validate_tilemap(name: str, w: int, h: int, tiles: List[int],
                     palette_size: int) -> List[Issue]:
    issues: List[Issue] = []
    if not name or not name.replace("_", "").isalnum():
        issues.append(Issue("error", f"tilemap name {name!r} invalid"))
    if w <= 0 or h <= 0:
        issues.append(Issue("error", f"map dimensions must be positive (got {w}x{h})"))
    if w > MAX_MAP_W or h > MAX_MAP_H:
        issues.append(Issue("error", f"map {w}x{h} exceeds max {MAX_MAP_W}x{MAX_MAP_H}"))
    if len(tiles) != w * h:
        issues.append(Issue("error", f"tile count {len(tiles)} != w*h {w*h}"))
    for i, t in enumerate(tiles):
        if t < 0 or t >= palette_size:
            issues.append(Issue("error",
                f"tile id {t} at index {i} outside palette (0..{palette_size-1})"))
    return issues


def estimate_flash_bytes(assets: List[Tuple[str, int]]) -> Tuple[int, List[Issue]]:
    """Given a list of (name, byte_count) and return total + warnings.

    Note: per-asset sprite bytes are ((w+7)//8) * h, so the caller
    pre-computes them.  This keeps validation dependency-free.
    """
    total = sum(n for _, n in assets)
    issues: List[Issue] = []
    if total > MAX_PROGMEM_BYTES:
        issues.append(Issue("error",
            f"total {total} B > PROGMEM budget {MAX_PROGMEM_BYTES} B"))
    elif total > MAX_PROGMEM_BYTES * 0.8:
        issues.append(Issue("warn",
            f"total {total} B is over 80% of PROGMEM budget "
            f"({MAX_PROGMEM_BYTES} B)"))
    return total, issues


def issues_have_error(issues: List[Issue]) -> bool:
    return any(i.level == "error" for i in issues)
