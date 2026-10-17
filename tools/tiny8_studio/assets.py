"""Tiny8 Studio — project asset registry.

A Project owns an asset list.  Each asset has a kind (sprite, sheet,
tilemap, font, audio) and a path on disk relative to the project root.
The registry computes the Flash cost (PROGMEM bytes) and surfaces
missing-file issues without touching the GUI layer.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .validation import Issue


KIND_SPRITE   = "sprite"
KIND_SHEET    = "sheet"
KIND_TILEMAP  = "tilemap"
KIND_FONT     = "font"
KIND_AUDIO    = "audio"
KIND_ANIM     = "anim"


@dataclass
class Asset:
    kind:   str
    name:   str             # basename without extension
    relpath: str            # path relative to project root
    meta:   dict = field(default_factory=dict)   # free-form (w, h, frames, ...)

    @property
    def exists(self) -> bool:
        return os.path.isfile(self.relpath)

    def flash_bytes(self) -> int:
        """Return the on-flash cost of this asset's exported form."""
        if self.kind in (KIND_SPRITE, KIND_SHEET):
            w = int(self.meta.get("w", 0))
            h = int(self.meta.get("h", 0))
            if w <= 0 or h <= 0:
                return 0
            return ((w + 7) // 8) * h
        if self.kind == KIND_TILEMAP:
            return int(self.meta.get("count", 0))
        if self.kind == KIND_AUDIO:
            # Each (id, ticks) pair is 2 bytes; rough estimate.
            return int(self.meta.get("bytes", 0))
        if self.kind == KIND_ANIM:
            return int(self.meta.get("frames", 0))
        return 0


@dataclass
class ProjectAssets:
    """List of assets with helpers to compute totals and report issues."""
    root: str
    items: List[Asset] = field(default_factory=list)

    def add(self, a: Asset) -> None:
        self.items.append(a)

    def find(self, name: str) -> Optional[Asset]:
        for a in self.items:
            if a.name == name:
                return a
        return None

    def total_flash(self) -> int:
        return sum(a.flash_bytes() for a in self.items)

    def issues(self) -> List[Issue]:
        out: List[Issue] = []
        seen = set()
        for a in self.items:
            if a.name in seen:
                out.append(Issue("warn", f"duplicate asset name {a.name!r}"))
            seen.add(a.name)
            if not a.exists:
                out.append(Issue("warn", f"missing file: {a.relpath}"))
        return out
