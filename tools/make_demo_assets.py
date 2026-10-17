#!/usr/bin/env python3
"""Generate demo PBM assets for the Tiny8 engine.

Produces the assets used by the M10 demo game (Tiny8 Quest):
  * player_idle.pbm      8x8, a small "knight" silhouette
  * coin.pbm             8x8, a ring
  * enemy.pbm            8x8, a goblin-like shape
  * tile_grass.pbm       8x8, a grass tile
  * tile_wall.pbm        8x8, a wall tile
  * tilemap_demo.pbm     32x16 (2 px per tile = 16x8 tilemap), the demo map

Run:  python tools/make_demo_assets.py
"""

import os
import sys

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT, exist_ok=True)


def write_pbm(path, w, h, set_pixels):
    """set_pixels(x, y) -> bool: True for set, False for clear."""
    row_bytes = (w + 7) // 8
    data = bytearray(row_bytes * h)
    for y in range(h):
        for x in range(w):
            if set_pixels(x, y):
                data[y * row_bytes + (x >> 3)] |= (0x80 >> (x & 7))
    with open(path, "wb") as f:
        f.write(f"P4\n{w} {h}\n".encode("ascii"))
        f.write(bytes(data))


# 8x8 player — a small head with eyes and a sword.
def player(x, y):
    if y == 0:        return 0b00111100 & (1 << (7 - x)) != 0  # helmet
    if y == 1:        return 0b01111110 & (1 << (7 - x)) != 0
    if y == 2:        return 0b01100110 & (1 << (7 - x)) != 0  # face
    if y == 3:        return 0b01100110 & (1 << (7 - x)) != 0
    if y == 4:        return 0b00111100 & (1 << (7 - x)) != 0
    if y == 5:        return 0b00011000 & (1 << (7 - x)) != 0  # body
    if y == 6:        return 0b00111100 & (1 << (7 - x)) != 0
    return x == 0 and y == 4  # sword bit


# 8x8 coin — a ring.
def coin(x, y):
    cx, cy = 3.5, 3.5
    d2 = (x - cx) ** 2 + (y - cy) ** 2
    return 2.5 < d2 < 7.5


# 8x8 enemy — horns and body.
def enemy(x, y):
    if y == 0 and x in (1, 6): return True
    if y == 1 and x in (1, 6): return True
    if y == 2: return 2 <= x <= 5
    if y == 3: return 1 <= x <= 6 and x not in (2, 5)
    if y == 4: return 1 <= x <= 6
    if y == 5: return 0 <= x <= 7
    if y == 6: return x in (1, 3, 5, 7)
    return False


# 8x8 grass tile.
def grass(x, y):
    return (x + y) % 3 == 0 and y < 6


# 8x8 wall tile.
def wall(x, y):
    # brick pattern.
    if y % 4 == 0: return True
    if (y // 4) % 2 == 0:
        return x != 4
    return x >= 4


# 16x8 tile map (32x16 PBM, 2 px per tile). 0 = grass, 1 = wall.
def tile_at(tx, ty):
    # Border wall.
    if tx == 0 or ty == 0 or tx == 15 or ty == 7: return 1
    # A few internal walls.
    for (wx, wy) in [(3, 3), (3, 4), (8, 2), (9, 2), (8, 3), (9, 3), (12, 5), (12, 6)]:
        if (tx, ty) == (wx, wy): return 1
    return 0


def tilemap_set(x, y):
    # x in [0..31], y in [0..15], each 2x2 block = 1 tile.
    if x % 2 != 0 or y % 2 != 0: return False
    return tile_at(x // 2, y // 2) == 1


def main():
    write_pbm(os.path.join(OUT, "player_idle.pbm"), 8, 8, lambda x, y: bool(player(x, y)))
    write_pbm(os.path.join(OUT, "coin.pbm"),         8, 8, lambda x, y: bool(coin(x, y)))
    write_pbm(os.path.join(OUT, "enemy.pbm"),        8, 8, lambda x, y: bool(enemy(x, y)))
    write_pbm(os.path.join(OUT, "tile_grass.pbm"),   8, 8, grass)
    write_pbm(os.path.join(OUT, "tile_wall.pbm"),    8, 8, wall)
    write_pbm(os.path.join(OUT, "tilemap_demo.pbm"), 32, 16, tilemap_set)
    print("Wrote demo PBM assets to", os.path.abspath(OUT))
    for n in os.listdir(OUT):
        sz = os.path.getsize(os.path.join(OUT, n))
        print(f"  {n:24s}  {sz} B")


if __name__ == "__main__":
    main()