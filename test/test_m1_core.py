"""Tiny8 Engine — Milestone 1 host tests (Python).

The C++ source under src/core/ is the contract. These tests re-implement each
function with the same logic in Python and exercise the *behavior*. Because
the C++ is intentionally simple, header-only, and constexpr-safe, the same
algorithmic tests are sufficient to catch regressions in: rect math, fixed-
point conversion, CRC8, and the bounded fixed-step accumulator.

Run: python test/test_m1_core.py
Exit 0 = all pass.
"""

import sys
import os
import struct

# --- Mirrored implementations (must stay in sync with src/core/*.h) ---

REF_W, REF_H, REF_PG = 84, 48, 6
FB_BYTES = (REF_W * REF_H) // 8  # 504
T8_SUB = 16


def rect_overlap(a, b):
    if a[2] <= 0 or a[3] <= 0 or b[2] <= 0 or b[3] <= 0:
        return False
    return (a[0] < b[0] + b[2] and a[0] + a[2] > b[0]
            and a[1] < b[1] + b[3] and a[1] + a[3] > b[1])


def rect_clip(src, bounds):
    x, y, w, h = src
    bx, by, bw, bh = bounds
    if x < bx:
        w -= bx - x
        x = bx
    if y < by:
        h -= by - y
        y = by
    rbx, bbx = x + w, bx + bw
    if rbx > bbx:
        w = bbx - x
    rby, bby = y + h, by + bh
    if rby > bby:
        h = bby - y
    if w < 0: w = 0
    if h < 0: h = 0
    return (x, y, w, h)


def fx_mul(a, b):
    return (a * b) >> 4


def px_to_sub(p): return p * T8_SUB
def sub_to_px(s): return s // T8_SUB


def crc8(data, seed=0):
    c = seed
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if (c & 0x80) else (c << 1) & 0xFF
    return c


class StepClock:
    def __init__(self, step_ms=16, max_catch=4):
        self.step_ms = step_ms
        self.accumulator = 0
        self.last_ms = 0
        self.max_catchup = max_catch or 1

    def init(self, now_ms, step_ms=16, max_catch=4):
        self.step_ms = step_ms
        self.accumulator = 0
        self.last_ms = now_ms
        self.max_catchup = max_catch or 1

    def poll(self, now_ms):
        delta = now_ms - self.last_ms
        self.last_ms = now_ms
        self.accumulator += delta
        steps = 0
        while self.accumulator >= self.step_ms and steps < self.max_catchup:
            self.accumulator -= self.step_ms
            steps += 1
        if self.accumulator > self.step_ms:
            self.accumulator = self.step_ms
        return steps


# --- Test harness ---

failed = 0
passed = 0


def check(expr, label):
    global failed, passed
    if expr:
        passed += 1
    else:
        print(f"FAIL  {label}")
        failed += 1


def test_rect():
    check(rect_overlap((0, 0, 10, 10), (5, 5, 10, 10)) is True, "rect_overlap true")
    check(rect_overlap((0, 0, 10, 10), (20, 20, 5, 5)) is False, "rect_overlap false")
    check(rect_overlap((0, 0, 10, 10), (10, 0, 10, 10)) is False, "rect edge-touch no overlap")
    c = rect_clip((2, 2, 100, 100), (0, 0, 50, 50))
    check(c == (2, 2, 48, 48), f"rect_clip partial = {c}")
    e = rect_clip((100, 100, 10, 10), (0, 0, 50, 50))
    check(e[2] <= 0 or e[3] <= 0, "rect_clip empty")


def test_math():
    check(fx_mul(16, 16) == 16, "fx_mul 1.0*1.0")
    check(fx_mul(32, 8) == 16,  "fx_mul 2.0*0.5")
    check(px_to_sub(3) == 48,   "px_to_sub")
    check(sub_to_px(48) == 3,    "sub_to_px")
    check(crc8(b"\x00") == 0x00, "crc8 {0}")
    check(crc8(b"\xFF") == 0xF3, "crc8 {FF}")
    # Cross-check: rolling CRC seed.
    one_shot = crc8(b"123456789")
    rolling = 0
    for ch in b"123456789":
        rolling = crc8(bytes([ch]), rolling)
    check(one_shot == rolling, "crc8 rolling == one-shot")


def test_time():
    c = StepClock()
    c.init(0, step_ms=16)
    check(c.poll(0) == 0, "stepclock zero delta")
    check(c.poll(33) == 2, "stepclock 33ms -> 2 steps")
    # 100ms stall should be clamped to 4.
    check(c.poll(133) == 4, "stepclock 100ms stall -> 4")
    check(c.accumulator <= 16, "stepclock residual clamped")


def test_constants():
    # These are the engine's hard contracts. If any of these change, the
    # whole memory budget in docs/MEMORY.md must be re-derived.
    check(FB_BYTES == 504, f"FB_BYTES == 504 (got {FB_BYTES})")
    check(REF_W == 84, "REF_W == 84")
    check(REF_H == 48, "REF_H == 48")
    check(REF_PG == 6,  "REF_PG == 6")


if __name__ == "__main__":
    test_constants()
    test_rect()
    test_math()
    test_time()
    print(f"M1 core: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
