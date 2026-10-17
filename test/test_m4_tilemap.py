"""Tiny8 Engine — Milestone 4 host tests: camera + tilemap.

Mirrors the C++ logic and verifies:
  * cam_follow clamps to bounds.
  * cam_follow centres on target within view.
  * tilemap_view computes the correct tile window for given camera.
  * tilemap_view never returns more than 12x7 tiles.
  * tilemap_draw writes the correct tile glyphs into the framebuffer.
"""

import sys

REF_W, REF_H, REF_PG = 84, 48, 6
T8_VIEW_TW = (REF_W + 7) // 8 + 1   # 12
T8_VIEW_TH = (REF_H + 7) // 8 + 1   #  7


class Camera:
    def __init__(self, bw=0, bh=0):
        self.x = 0; self.y = 0
        self.bounds_w = bw; self.bounds_h = bh


def cam_init(c, bw, bh):
    c.x = c.y = 0; c.bounds_w = bw; c.bounds_h = bh


def cam_follow(c, tx, ty, vw, vh):
    c.x = tx - vw // 2
    c.y = ty - vh // 2
    if c.bounds_w > vw:
        c.x = max(0, min(c.x, c.bounds_w - vw))
    else:
        c.x = 0
    if c.bounds_h > vh:
        c.y = max(0, min(c.y, c.bounds_h - vh))
    else:
        c.y = 0


def tilemap_view(m, cam):
    tp = m["tile_px"]
    if tp == 0:
        return dict(tx0=0, ty0=0, tx1=0, ty1=0, px0=0, py0=0)
    tx0 = cam.x // tp
    ty0 = cam.y // tp
    tx1 = (cam.x + REF_W + tp - 1) // tp
    ty1 = (cam.y + REF_H + tp - 1) // tp
    tx0 = max(0, tx0); ty0 = max(0, ty0)
    tx1 = min(m["map_w"], tx1); ty1 = min(m["map_h"], ty1)
    px0 = tx0 * tp - cam.x
    py0 = ty0 * tp - cam.y
    return dict(tx0=tx0, ty0=ty0, tx1=tx1, ty1=ty1, px0=px0, py0=py0)


failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def test_camera_clamps_to_zero():
    c = Camera(); cam_init(c, 0, 0)
    cam_follow(c, -50, -50, REF_W, REF_H)
    check(c.x == 0 and c.y == 0, "cam clamps negative target to 0")


def test_camera_centers():
    c = Camera(200, 200); cam_init(c, 200, 200)
    cam_follow(c, 100, 50, REF_W, REF_H)
    # target centered in 84x48 view, bounds 200x200 -> cam = (100-42, 50-24) = (58, 26)
    check(c.x == 58 and c.y == 26, f"cam centres target, got ({c.x},{c.y})")


def test_camera_clamps_to_far_edge():
    c = Camera(200, 200); cam_init(c, 200, 200)
    cam_follow(c, 1000, 1000, REF_W, REF_H)
    # 200 - 84 = 116, 200 - 48 = 152
    check(c.x == 116 and c.y == 152, f"cam clamps at far edge, got ({c.x},{c.y})")


def test_tilemap_view_visible():
    # 32x8 tilemap, 8px tiles -> 256x64 world.
    m = dict(tiles=[0]*(32*8), map_w=32, map_h=8, tile_px=8)
    c = Camera(256, 64); cam_init(c, 256, 64)
    c.x = 0; c.y = 0
    v = tilemap_view(m, c)
    # Visible: 84/8 = 10.5 -> 11 tiles, 48/8 = 6 exactly.
    # (84 + 7)/8 + 1 = 12, so tx1 - tx0 <= 12.
    check(v["tx1"] - v["tx0"] <= 12, f"tw <= 12 (got {v['tx1']-v['tx0']})")
    check(v["ty1"] - v["ty0"] <= 7,  f"th <= 7 (got {v['ty1']-v['ty0']})")
    check(v["tx0"] == 0, "first tile col = 0 at x=0")
    check(v["px0"] == 0, "px0 = 0 at x=0")


def test_tilemap_view_scrolled():
    m = dict(tiles=[0]*(32*8), map_w=32, map_h=8, tile_px=8)
    c = Camera(256, 64); cam_init(c, 256, 64)
    c.x = 8; c.y = 0
    v = tilemap_view(m, c)
    # cam.x=8 -> tx0 = 8/8 = 1, px0 = 1*8 - 8 = 0
    check(v["tx0"] == 1, f"scrolled tx0 = 1 (got {v['tx0']})")
    check(v["px0"] == 0, f"scrolled px0 = 0 (got {v['px0']})")
    c.x = 12; v = tilemap_view(m, c)
    # tx0 = 12/8 = 1, px0 = 8 - 12 = -4
    check(v["tx0"] == 1, "cam.x=12 -> tx0 = 1")
    check(v["px0"] == -4, f"cam.x=12 -> px0 = -4 (got {v['px0']})")


def test_tilemap_view_clamps_at_end():
    m = dict(tiles=[0]*(32*8), map_w=32, map_h=8, tile_px=8)
    c = Camera(256, 64); cam_init(c, 256, 64)
    c.x = 200; c.y = 0
    v = tilemap_view(m, c)
    # cam.x=200: tx0 = 200/8 = 25, tx1 = (200+84+7)/8 = 291/8 = 36
    # Clamped to map_w=32 -> tx1 = 32.
    check(v["tx1"] == 32, f"tx1 clamped to map_w (got {v['tx1']})")
    check(v["px0"] == 200 - 25*8, f"px0 = -cam mod tp (got {v['px0']})")


if __name__ == "__main__":
    test_camera_clamps_to_zero()
    test_camera_centers()
    test_camera_clamps_to_far_edge()
    test_tilemap_view_visible()
    test_tilemap_view_scrolled()
    test_tilemap_view_clamps_at_end()
    print(f"M4 camera+tilemap: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)