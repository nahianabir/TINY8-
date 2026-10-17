"""Tiny8 Studio — exporters.

Thin glue that delegates to the existing command-line converter so we
don't fork the format.  Importing tools.sprite_convert pulls in only
the standard library.
"""

from __future__ import annotations
import os
import sys
from typing import List

from . import animation as _anim_mod

# Re-use the existing converter; the GUI must not duplicate the format.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import sprite_convert as sc  # type: ignore


def export_sprite(pbm_path: str, out_dir: str, name: str) -> str:
    """Convert a single PBM to a PROGMEM header.  Returns the header path."""
    w, h, bits = sc.read_pbm(pbm_path)
    asset = sc.Asset(name=name, w=w, h=h, bits=bits)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{name}.h")
    sc.write_sprite_header(asset, out_path)
    return out_path


def export_tilemap(pbm_path: str, out_dir: str, name: str) -> str:
    """Convert a 2x2-packed PBM tilemap to a C array header."""
    w, h, bits = sc.read_pbm(pbm_path)
    if w % 2 or h % 2:
        raise ValueError(f"{pbm_path}: tilemap input must have even w and h")
    tw, th = w // 2, h // 2
    tile_ids: List[int] = []
    for ty in range(th):
        for tx in range(tw):
            sx = tx * 2
            sy = ty * 2
            row = sy * ((w + 7) // 8)
            bit = 0x80 >> (sx & 7)
            tile_ids.append(1 if (bits[row + (sx >> 3)] & bit) else 0)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{name}_map.h")
    sc.write_tilemap_header(name, tw, th, tile_ids, out_path)
    return out_path


def export_animation(anim_path: str, out_dir: str) -> str:
    """Convert a .anim.json file to a C++ Anim struct header."""
    anim = _anim_mod.read_anim(anim_path)
    os.makedirs(out_dir, exist_ok=True)
    # The JSON's `name` field already strips `.anim.json`; if it ends
    # with `.anim` (when the JSON was written by an older caller),
    # strip that too so the output is `<name>.anim.h` not double-suffixed.
    n = anim.name
    if n.endswith(".anim"):
        n = n[: -len(".anim")]
    out_path = os.path.join(out_dir, f"{n}.anim.h")
    _anim_mod.write_anim_header(anim, out_path)
    return out_path


def export_all_sprites(project_root: str) -> List[str]:
    """Run the converter on every PBM and .anim.json in assets/.

    Multi-layer tilemaps (base + `<base>_L<n>.pbm`) are exported as
    per-layer tilemap headers so the user can stack them in their
    sketch.  The single-layer tilemap convention
    (`<name>.map.txt` marker) is preserved.
    """
    assets = os.path.join(project_root, "assets")
    out    = os.path.join(project_root, "generated")
    written: List[str] = []
    if not os.path.isdir(assets):
        return written
    seen_in_layer: set = set()
    for fn in sorted(os.listdir(assets)):
        if not fn.lower().endswith(".pbm"):
            continue
        stem = os.path.splitext(fn)[0]
        for i in range(4):
            suffix = f"_L{i}"
            if stem.endswith(suffix):
                seen_in_layer.add(fn)
                break
    for fn in sorted(os.listdir(assets)):
        full = os.path.join(assets, fn)
        if not os.path.isfile(full):
            continue
        if fn in seen_in_layer:
            continue
        if fn.lower().endswith(".pbm"):
            name = os.path.splitext(fn)[0]
            if os.path.isfile(os.path.join(assets, name + ".map.txt")):
                written.append(export_tilemap(full, out, name))
            else:
                had_layer = False
                for i in range(4):
                    lp = os.path.join(assets, f"{name}_L{i}.pbm")
                    if os.path.isfile(lp):
                        written.append(export_tilemap(lp, out, f"{name}_L{i}"))
                        had_layer = True
                # Always emit a sprite header for the base (the
                # engine may want to use it as a placeholder / debug
                # image).
                try:
                    written.append(export_sprite(full, out, name))
                except Exception:
                    pass
        elif fn.lower().endswith(".anim.json"):
            try:
                written.append(export_animation(full, out))
            except Exception:
                continue
    return written
