"""Tiny8 Studio — host-side framebuffer simulation.

A small Python mirror of the engine's M1 (core), M2 (framebuffer),
M3 (sprite), and M4 (tilemap) modules.  Used by the studio's
preview pane to run a real (if slow) step loop on the desktop and
render to a Tkinter canvas.

These functions are not the test suite — they are a focused subset
chosen for the studio's simulation needs.  They are kept in sync
with the test mirrors in `test/test_m2_framebuffer.py` etc.; if you
change one, change the other.
"""

from __future__ import annotations

# --- constants matching the engine ------------------------------------

REF_W, REF_H, REF_PG = 84, 48, 6
FB_BYTES = (REF_W * REF_H) // 8   # 504


# --- framebuffer -------------------------------------------------------

class Framebuffer:
    def __init__(self) -> None:
        self.px:   list[int] = [0] * FB_BYTES
        self.dirty = True


def fb_init(fb) -> None:
    fb.px = [0] * FB_BYTES
    fb.dirty = True


def fb_present(fb) -> None:
    fb.dirty = True


def fb_pixels(fb) -> list[int]:
    return fb.px


def fb_set_pixel(fb, x, y, on) -> None:
    if x < 0 or y < 0 or x >= REF_W or y >= REF_H:
        return
    idx = (y >> 3) * REF_W + x
    bit = 1 << (y & 7)
    if on:
        fb.px[idx] |= bit
    else:
        fb.px[idx] &= (~bit) & 0xFF


def fb_draw_hline(fb, x, y, w, on) -> None:
    if y < 0 or y >= REF_H:
        return
    if x < 0:
        w += x; x = 0
    if x + w > REF_W:
        w = REF_W - x
    if w <= 0:
        return
    bit = 1 << (y & 7)
    for i in range(w):
        idx = (y >> 3) * REF_W + x + i
        if on:
            fb.px[idx] |= bit
        else:
            fb.px[idx] &= (~bit) & 0xFF


def fb_draw_vline(fb, x, y, h, on) -> None:
    if x < 0 or x >= REF_W:
        return
    if y < 0:
        h += y; y = 0
    if y + h > REF_H:
        h = REF_H - y
    if h <= 0:
        return
    for j in range(h):
        idx = ((y + j) >> 3) * REF_W + x
        bit = 1 << ((y + j) & 7)
        if on:
            fb.px[idx] |= bit
        else:
            fb.px[idx] &= (~bit) & 0xFF


def fb_fill_rect(fb, x, y, w, h, on) -> None:
    for j in range(h):
        fb_draw_hline(fb, x, y + j, w, on)


def fb_blit(fb, dst_x, dst_y, w, h, bits, src_stride, transparent) -> None:
    if w == 0 or h == 0 or not bits:
        return
    x0, y0 = dst_x, dst_y
    x1, y1 = dst_x + w, dst_y + h
    if x0 < 0: x0 = 0
    if y0 < 0: y0 = 0
    if x1 > REF_W: x1 = REF_W
    if y1 > REF_H: y1 = REF_H
    if x0 >= x1 or y0 >= y1:
        return
    for y in range(y0, y1):
        src_row_off = (y - dst_y) * src_stride
        dst_idx = (y >> 3) * REF_W
        dst_bit = 1 << (y & 7)
        for x in range(x0, x1):
            sx = x - dst_x
            sb_idx = src_row_off + (sx >> 3)
            if sb_idx < 0 or sb_idx >= len(bits):
                continue
            if not (bits[sb_idx] & (0x80 >> (sx & 7))):
                continue
            if transparent:
                fb.px[dst_idx + x] |= dst_bit
            else:
                fb.px[dst_idx + x] = dst_bit  # opaque override


def fb_blit_sprite(fb, x, y, sprite, transparent) -> None:
    if not sprite.get("bits"):
        return
    fb_blit(fb, x, y, sprite["w"], sprite["h"],
            sprite["bits"], sprite.get("stride", (sprite["w"] + 7) // 8),
            transparent)


# --- text / font (5x7 built-in) ---------------------------------------

_FONT_5x7 = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    "A": [0x7C, 0x12, 0x11, 0x12, 0x7C, 0x00, 0x00],
    "B": [0x7F, 0x49, 0x49, 0x49, 0x36, 0x00, 0x00],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22, 0x00, 0x00],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C, 0x00, 0x00],
    "E": [0x7F, 0x49, 0x49, 0x49, 0x41, 0x00, 0x00],
    "F": [0x7F, 0x09, 0x09, 0x09, 0x01, 0x00, 0x00],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A, 0x00, 0x00],
    "H": [0x7F, 0x08, 0x08, 0x08, 0x7F, 0x00, 0x00],
    "I": [0x00, 0x41, 0x7F, 0x41, 0x00, 0x00, 0x00],
    "L": [0x7F, 0x40, 0x40, 0x40, 0x40, 0x00, 0x00],
    "M": [0x7F, 0x02, 0x04, 0x02, 0x7F, 0x00, 0x00],
    "N": [0x7F, 0x04, 0x08, 0x10, 0x7F, 0x00, 0x00],
    "O": [0x3E, 0x41, 0x41, 0x41, 0x3E, 0x00, 0x00],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06, 0x00, 0x00],
    "R": [0x7F, 0x09, 0x19, 0x29, 0x46, 0x00, 0x00],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31, 0x00, 0x00],
    "T": [0x01, 0x01, 0x7F, 0x01, 0x01, 0x00, 0x00],
    "U": [0x3F, 0x40, 0x40, 0x40, 0x3F, 0x00, 0x00],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F, 0x00, 0x00],
    "W": [0x7F, 0x20, 0x18, 0x20, 0x7F, 0x00, 0x00],
    "X": [0x63, 0x14, 0x08, 0x14, 0x63, 0x00, 0x00],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07, 0x00, 0x00],
    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E, 0x00, 0x00],
    "1": [0x00, 0x42, 0x7F, 0x40, 0x00, 0x00, 0x00],
    "2": [0x62, 0x51, 0x49, 0x49, 0x46, 0x00, 0x00],
    "3": [0x22, 0x49, 0x49, 0x49, 0x36, 0x00, 0x00],
    "4": [0x18, 0x14, 0x12, 0x7F, 0x10, 0x00, 0x00],
    "5": [0x2F, 0x49, 0x49, 0x49, 0x31, 0x00, 0x00],
    "6": [0x3E, 0x49, 0x49, 0x49, 0x32, 0x00, 0x00],
    "7": [0x01, 0x71, 0x09, 0x05, 0x03, 0x00, 0x00],
    "8": [0x36, 0x49, 0x49, 0x49, 0x36, 0x00, 0x00],
    "9": [0x26, 0x49, 0x49, 0x49, 0x3E, 0x00, 0x00],
    ".": [0x00, 0x00, 0x60, 0x60, 0x00, 0x00, 0x00],
    ":": [0x00, 0x36, 0x36, 0x00, 0x00, 0x00, 0x00],
    "-": [0x08, 0x08, 0x08, 0x08, 0x08, 0x00, 0x00],
    "!": [0x00, 0x00, 0x5F, 0x00, 0x00, 0x00, 0x00],
    "?": [0x02, 0x01, 0x51, 0x09, 0x06, 0x00, 0x00],
    "/": [0x20, 0x10, 0x08, 0x04, 0x02, 0x00, 0x00],
}


def fb_draw_text(fb, x, y, text) -> None:
    cx = x
    for ch in text:
        glyph = _FONT_5x7.get(ch.upper())
        if glyph is None:
            cx += 6
            continue
        for col in range(5):
            byte = glyph[col]
            for row in range(7):
                if (byte >> row) & 1:
                    fb_set_pixel(fb, cx + col, y + row, True)
        cx += 6


# --- step clock (mirrors src/core/tiny8_time.cpp) ----------------------

class StepClock:
    def __init__(self, step_ms: int = 16, max_catch: int = 4):
        self.step_ms = step_ms
        self.accumulator = 0
        self.last_ms = 0
        self.max_catchup = max_catch

    def init(self, last_ms: int) -> None:
        self.last_ms = last_ms
        self.accumulator = 0

    def poll(self, now_ms: int) -> int:
        delta = now_ms - self.last_ms
        self.last_ms = now_ms
        self.accumulator += delta
        steps = 0
        while self.accumulator >= self.step_ms and steps < self.max_catchup:
            self.accumulator -= self.step_ms
            steps += 1
        return steps


# --- sprite and frame-stepping helpers --------------------------------

def make_sprite(w: int, h: int, bits: list[int]) -> dict:
    return {
        "w": int(w),
        "h": int(h),
        "stride": (int(w) + 7) // 8,
        "bits": list(bits),
    }


def pbm_to_sprite(path: str) -> dict:
    with open(path, "rb") as f:
        magic = f.readline().strip()
        if magic != b"P4":
            raise ValueError("not a P4 PBM")
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        w, h = (int(x) for x in line.split())
        data = f.read()
    row_bytes = (w + 7) // 8
    return make_sprite(w, h, list(data[:row_bytes * h]))


def pbm_to_sheet(path: str) -> tuple[int, int, list[int]]:
    """Read a PBM and return (w, h, bits)."""
    with open(path, "rb") as f:
        magic = f.readline().strip()
        if magic != b"P4":
            raise ValueError("not a P4 PBM")
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        w, h = (int(x) for x in line.split())
        data = f.read()
    row_bytes = (w + 7) // 8
    return w, h, list(data[:row_bytes * h])


def pbm_to_tilemap(path: str) -> tuple[int, int, list[int]]:
    """Read a 2x2-packed PBM tilemap and return (tw, th, tiles)."""
    w, h, bits = pbm_to_sheet(path)
    if w % 2 or h % 2:
        raise ValueError("tilemap source must have even w and h")
    tw, th = w // 2, h // 2
    row_bytes = (w + 7) // 8
    tiles: list[int] = []
    for ty in range(th):
        for tx in range(tw):
            sx = tx * 2
            sy = ty * 2
            row = sy * row_bytes
            bit = 0x80 >> (sx & 7)
            tiles.append(1 if (bits[row + (sx >> 3)] & bit) else 0)
    return tw, th, tiles


def framebuffer_to_pcd8544_bytes(fb) -> list[int]:
    """Mimic the PCD8544 flush: a sequence of command/data bytes.
    Returns 1 + 1 + 84 * 6 = 506 bytes per frame.
    """
    out: list[int] = []
    out.append(0x80)            # SET_Y (Y=0)
    out.append(0x40)            # SET_X (X=0)
    for col in range(REF_PG):
        for row in range(REF_W):
            out.append(fb.px[col * REF_W + row] & 0xFF)
    return out
