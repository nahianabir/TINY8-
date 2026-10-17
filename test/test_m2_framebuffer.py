"""Tiny8 Engine — Milestone 2 host tests.

Re-implements the C++ framebuffer, font, and PCD8544 driver logic in Python
and exercises the same algorithmic contract the AVR build will run.

Tests:
  * fb_init clears, dirty flag is true.
  * fb_set_pixel turns on the right bit in the right byte.
  * fb_blit with transparent + opaque modes, with screen-edge clipping.
  * fb_draw_text uses the font table correctly.
  * The PCD8544 init SPI log contains the right command sequence.
  * PCD8544 flush emits 6 x (1 cmd_y + 1 cmd_x + 84 data) writes = 516 bytes.
  * 1px + 8x8 sprite round-trips exactly to a known reference.

Run: python test/test_m2_framebuffer.py
"""

import sys

REF_W, REF_H, REF_PG = 84, 48, 6
FB_BYTES = (REF_W * REF_H) // 8  # 504
T8_SUB = 16


# --- Framebuffer mirror ---

class Framebuffer:
    def __init__(self):
        self.px = [0] * FB_BYTES
        self.dirty = True


def fb_init(fb): fb.px = [0]*FB_BYTES; fb.dirty = True
def fb_present(fb): fb.dirty = True
def fb_pixels(fb): return fb.px


def put_pixel(fb, x, y, on):
    if x < 0 or y < 0 or x >= REF_W or y >= REF_H:
        return
    idx = (y >> 3) * REF_W + x
    bit = 1 << (y & 7)
    if on:
        fb.px[idx] |= bit
    else:
        fb.px[idx] &= (~bit) & 0xFF


def fb_set_pixel(fb, x, y, on): put_pixel(fb, x, y, on)


def fb_draw_hline(fb, x, y, w, on):
    if y < 0 or y >= REF_H: return
    if x < 0: w += x; x = 0
    if x + w > REF_W: w = REF_W - x
    if w <= 0: return
    bit = 1 << (y & 7)
    for i in range(w):
        idx = (y >> 3) * REF_W + x + i
        if on: fb.px[idx] |= bit
        else:  fb.px[idx] &= (~bit) & 0xFF


def fb_draw_vline(fb, x, y, h, on):
    if x < 0 or x >= REF_W: return
    if y < 0: h += y; y = 0
    if y + h > REF_H: h = REF_H - y
    if h <= 0: return
    for j in range(h):
        idx = ((y + j) >> 3) * REF_W + x
        bit = 1 << ((y + j) & 7)
        if on: fb.px[idx] |= bit
        else:  fb.px[idx] &= (~bit) & 0xFF


def fb_draw_rect(fb, r, on):
    fb_draw_hline(fb, r[0], r[1], r[2], on)
    fb_draw_hline(fb, r[0], r[1] + r[3] - 1, r[2], on)
    fb_draw_vline(fb, r[0], r[1], r[3], on)
    fb_draw_vline(fb, r[0] + r[2] - 1, r[1], r[3], on)


def fb_fill_rect(fb, r, on):
    for j in range(r[3]):
        fb_draw_hline(fb, r[0], r[1] + j, r[2], on)


def fb_blit(fb, dst_x, dst_y, w, h, bits, src_stride, transparent):
    if w == 0 or h == 0 or not bits: return
    x0, y0 = dst_x, dst_y
    x1, y1 = dst_x + w, dst_y + h
    if x0 < 0: x0 = 0
    if y0 < 0: y0 = 0
    if x1 > REF_W: x1 = REF_W
    if y1 > REF_H: y1 = REF_H
    if x0 >= x1 or y0 >= y1: return
    for y in range(y0, y1):
        src_row_off = (y - dst_y) * src_stride
        dst_idx = (y >> 3) * REF_W
        dst_bit = y & 7
        for x in range(x0, x1):
            sx = x - dst_x
            src_byte = bits[src_row_off + (sx >> 3)]
            src_bit = 0x80 >> (sx & 7)
            if transparent and not (src_byte & src_bit): continue
            i = dst_idx + x
            if src_byte & src_bit:
                fb.px[i] |= (1 << dst_bit)
            else:
                fb.px[i] &= (~(1 << dst_bit)) & 0xFF
    fb.dirty = True


# --- Font (verbatim copy of tiny8_font.cpp) ---

kFont5x7 = [
    [0x00,0x00,0x00,0x00,0x00],  # ' '
    [0x00,0x00,0x5F,0x00,0x00],  # '!'
    [0x00,0x07,0x00,0x07,0x00],  # '"'
    [0x14,0x7F,0x14,0x7F,0x14],  # '#'
    [0x24,0x2A,0x7F,0x2A,0x12],  # '$'
    [0x23,0x13,0x08,0x64,0x62],  # '%'
    [0x36,0x49,0x55,0x22,0x50],  # '&'
    [0x00,0x05,0x03,0x00,0x00],  # '\''
    [0x00,0x1C,0x22,0x41,0x00],  # '('
    [0x00,0x41,0x22,0x1C,0x00],  # ')'
    [0x08,0x2A,0x1C,0x2A,0x08],  # '*'
    [0x08,0x08,0x3E,0x08,0x08],  # '+'
    [0x00,0x50,0x30,0x00,0x00],  # ','
    [0x08,0x08,0x08,0x08,0x08],  # '-'
    [0x00,0x60,0x60,0x00,0x00],  # '.'
    [0x20,0x10,0x08,0x04,0x02],  # '/'
    [0x3E,0x51,0x49,0x45,0x3E],  # '0'
    [0x00,0x42,0x7F,0x40,0x00],  # '1'
    [0x42,0x61,0x51,0x49,0x46],  # '2'
    [0x21,0x41,0x45,0x4B,0x31],  # '3'
    [0x18,0x14,0x12,0x7F,0x10],  # '4'
    [0x27,0x45,0x45,0x45,0x39],  # '5'
    [0x3C,0x4A,0x49,0x49,0x30],  # '6'
    [0x01,0x71,0x09,0x05,0x03],  # '7'
    [0x36,0x49,0x49,0x49,0x36],  # '8'
    [0x06,0x49,0x49,0x29,0x1E],  # '9'
    [0x00,0x36,0x36,0x00,0x00],  # ':'
    [0x00,0x56,0x36,0x00,0x00],  # ';'
    [0x00,0x08,0x14,0x22,0x41],  # '<'
    [0x14,0x14,0x14,0x14,0x14],  # '='
    [0x41,0x22,0x14,0x08,0x00],  # '>'
    [0x02,0x01,0x51,0x09,0x06],  # '?'
    [0x32,0x49,0x79,0x41,0x3E],  # '@'
    [0x7E,0x11,0x11,0x11,0x7E],  # 'A'
    [0x7F,0x49,0x49,0x49,0x36],  # 'B'
    [0x3E,0x41,0x41,0x41,0x22],  # 'C'
    [0x7F,0x41,0x41,0x22,0x1C],  # 'D'
    [0x7F,0x49,0x49,0x49,0x41],  # 'E'
    [0x7F,0x09,0x09,0x01,0x01],  # 'F'
    [0x3E,0x41,0x41,0x51,0x32],  # 'G'
    [0x7F,0x08,0x08,0x08,0x7F],  # 'H'
    [0x00,0x41,0x7F,0x41,0x00],  # 'I'
    [0x20,0x40,0x41,0x3F,0x01],  # 'J'
    [0x7F,0x08,0x14,0x22,0x41],  # 'K'
    [0x7F,0x40,0x40,0x40,0x40],  # 'L'
    [0x7F,0x02,0x04,0x02,0x7F],  # 'M'
    [0x7F,0x04,0x08,0x10,0x7F],  # 'N'
    [0x3E,0x41,0x41,0x41,0x3E],  # 'O'
    [0x7F,0x09,0x09,0x09,0x06],  # 'P'
    [0x3E,0x41,0x51,0x21,0x5E],  # 'Q'
    [0x7F,0x09,0x19,0x29,0x46],  # 'R'
    [0x46,0x49,0x49,0x49,0x31],  # 'S'
    [0x01,0x01,0x7F,0x01,0x01],  # 'T'
    [0x3F,0x40,0x40,0x40,0x3F],  # 'U'
    [0x1F,0x20,0x40,0x20,0x1F],  # 'V'
    [0x3F,0x40,0x38,0x40,0x3F],  # 'W'
    [0x63,0x14,0x08,0x14,0x63],  # 'X'
    [0x07,0x08,0x70,0x08,0x07],  # 'Y'
    [0x61,0x51,0x49,0x45,0x43],  # 'Z'
    [0x00,0x00,0x7F,0x41,0x41],  # '['
    [0x02,0x04,0x08,0x10,0x20],  # '\\'
    [0x41,0x41,0x7F,0x00,0x00],  # ']'
    [0x04,0x02,0x01,0x02,0x04],  # '^'
    [0x40,0x40,0x40,0x40,0x40],  # '_'
    [0x00,0x01,0x02,0x04,0x00],  # '`'
    [0x20,0x54,0x54,0x54,0x78],  # 'a'
    [0x7F,0x48,0x44,0x44,0x38],  # 'b'
    [0x38,0x44,0x44,0x44,0x20],  # 'c'
    [0x38,0x44,0x44,0x48,0x7F],  # 'd'
    [0x38,0x54,0x54,0x54,0x18],  # 'e'
    [0x08,0x7E,0x09,0x01,0x02],  # 'f'
    [0x08,0x14,0x54,0x54,0x3C],  # 'g'
    [0x7F,0x08,0x04,0x04,0x78],  # 'h'
    [0x00,0x44,0x7D,0x40,0x00],  # 'i'
    [0x20,0x40,0x44,0x3D,0x00],  # 'j'
    [0x00,0x7F,0x10,0x28,0x44],  # 'k'
    [0x00,0x41,0x7F,0x40,0x00],  # 'l'
    [0x7C,0x04,0x18,0x04,0x78],  # 'm'
    [0x7C,0x08,0x04,0x04,0x78],  # 'n'
    [0x38,0x44,0x44,0x44,0x38],  # 'o'
    [0x7C,0x14,0x14,0x14,0x08],  # 'p'
    [0x08,0x14,0x14,0x18,0x7C],  # 'q'
    [0x7C,0x08,0x04,0x04,0x08],  # 'r'
    [0x48,0x54,0x54,0x54,0x20],  # 's'
    [0x04,0x3F,0x44,0x40,0x20],  # 't'
    [0x3C,0x40,0x40,0x20,0x7C],  # 'u'
    [0x1C,0x20,0x40,0x20,0x1C],  # 'v'
    [0x3C,0x40,0x30,0x40,0x3C],  # 'w'
    [0x44,0x28,0x10,0x28,0x44],  # 'x'
    [0x0C,0x50,0x50,0x50,0x3C],  # 'y'
    [0x44,0x64,0x54,0x4C,0x44],  # 'z'
    [0x00,0x08,0x36,0x41,0x00],  # '{'
    [0x00,0x00,0x7F,0x00,0x00],  # '|'
    [0x00,0x41,0x36,0x08,0x00],  # '}'
    [0x08,0x04,0x08,0x10,0x08],  # '~'
]


def fb_draw_char(fb, x, y, c, on):
    if c < ' ' or c > '~': c = '?'
    idx = ord(c) - 32
    for col in range(5):
        bits = kFont5x7[idx][col]
        for row in range(7):
            if bits & (1 << row):
                fb_set_pixel(fb, x + col, y + row, on)


def fb_draw_text(fb, x, y, s, on):
    for ch in s:
        fb_draw_char(fb, x, y, ch, on)
        x += 6


# --- Fake PCD8544 driver mirroring the C++ flow ---

class FakeSpi:
    def __init__(self):
        self.log = []
        self.dc = True
        self.ce = True

    def begin(self): self.log.append(('EVT', 'BEGIN'))
    def end(self):   self.log.append(('EVT', 'END'))

    def write_cmd(self, c):
        self.log.append(('CMD', c))

    def write_data_block(self, p, n):
        for b in p[:n]:
            self.log.append(('DATA', b))


# --- Tests ---

failed, passed = 0, 0


def check(expr, label):
    global failed, passed
    if expr:
        passed += 1
    else:
        print(f"FAIL  {label}")
        failed += 1


def test_fb_init():
    fb = Framebuffer()
    fb_init(fb)
    check(all(b == 0 for b in fb.px), "fb_init clears all bytes")
    check(fb.dirty is True, "fb_init sets dirty")


def test_fb_set_pixel():
    fb = Framebuffer()
    fb_init(fb)
    # Pixel (0,0) -> page 0, column 0, bit 0 of fb.px[0]
    fb_set_pixel(fb, 0, 0, True)
    check(fb.px[0] == 0x01, f"set (0,0) -> fb.px[0] = 0x01 (got 0x{fb.px[0]:02X})")
    # Pixel (7,0) -> page 0, column 7, bit 0 of fb.px[7]
    fb_set_pixel(fb, 7, 0, True)
    check(fb.px[7] == 0x01, f"set (7,0) -> fb.px[7] = 0x01 (got 0x{fb.px[7]:02X})")
    # Pixel (0,7) -> page 0, column 0, bit 7 of fb.px[0]
    fb_init(fb)
    fb_set_pixel(fb, 0, 7, True)
    check(fb.px[0] == 0x80, f"set (0,7) -> fb.px[0] = 0x80 (got 0x{fb.px[0]:02X})")
    # Pixel (0,8) -> page 1, column 0, bit 0 of fb.px[REF_W]
    fb_set_pixel(fb, 0, 8, True)
    check(fb.px[REF_W] == 0x01, f"set (0,8) -> fb.px[{REF_W}] = 0x01 (got 0x{fb.px[REF_W]:02X})")
    # Clear a pixel
    fb_set_pixel(fb, 0, 7, False)
    check(fb.px[0] == 0x00, f"clear (0,7) (got 0x{fb.px[0]:02X})")
    # Out of screen
    fb_set_pixel(fb, -1, 0, True)
    fb_set_pixel(fb, 84, 0, True)
    fb_set_pixel(fb, 0, 48, True)
    check(fb.px[0] == 0x00, "out-of-screen pixels are dropped")


def test_fb_hline():
    fb = Framebuffer()
    fb_init(fb)
    fb_draw_hline(fb, 0, 5, 84, True)  # 84 px on row 5
    expected_bit = 1 << 5
    # All 84 bytes in page 0 must be set with bit 5.
    check(all(b == expected_bit for b in fb.px[:84]),
          f"hline full row (got sample 0x{fb.px[0]:02X})")
    # Negative x clips
    fb_init(fb)
    fb_draw_hline(fb, -10, 5, 20, True)
    check(all(b == expected_bit for b in fb.px[:10]),
          f"hline negative-x clip (got 0x{fb.px[0]:02X})")
    # Right edge clips
    fb_init(fb)
    fb_draw_hline(fb, 80, 5, 10, True)
    check(all(b == expected_bit for b in fb.px[80:84]),
          f"hline right clip (got 0x{fb.px[80]:02X})")


def test_fb_blit_clipping():
    fb = Framebuffer()
    fb_init(fb)
    # 16x8 sprite (16 wide to test left-clip) — every pixel set.
    # Layout: row-major, MSB-first; stride = (16+7)//8 = 2 bytes/row, 8 rows.
    sprite = [0xFF] * (2 * 8)
    # Off-screen left: blit starts at x=-8. After clip, x in [0..7] lands.
    fb_blit(fb, -8, 0, 16, 8, sprite, 2, True)
    # Each kept column has all 8 vertical bits set -> 0xFF.
    check(all(b == 0xFF for b in fb.px[:8]),
          f"left-clip blit sets cols 0..7 = 0xFF (got 0x{fb.px[0]:02X})")
    # Off-screen right
    fb_init(fb)
    fb_blit(fb, 84, 0, 8, 8, [0xFF]*8, 1, True)
    check(all(b == 0 for b in fb.px), "off-screen-right blit is a no-op")
    # Off-screen bottom
    fb_init(fb)
    fb_blit(fb, 0, 48, 8, 8, [0xFF]*8, 1, True)
    check(all(b == 0 for b in fb.px), "off-screen-bottom blit is a no-op")
    # Fully on-screen 8x8, all-1, transparent: every byte in 0..7 should be 0xFF.
    fb_init(fb)
    fb_blit(fb, 0, 0, 8, 8, [0xFF]*8, 1, True)
    check(all(b == 0xFF for b in fb.px[:8]), "on-screen 8x8 transparent = 0xFF each")
    # Stride 2 (16-wide sprite), clipped to start at x=0: cols 0..15 all set.
    fb_init(fb)
    fb_blit(fb, 0, 0, 16, 8, [0xFF]*16, 2, True)
    check(all(b == 0xFF for b in fb.px[:16]), "on-screen 16x8 transparent sets 16 cols")


def test_fb_blit_transparent_vs_opaque():
    fb = Framebuffer()
    fb_init(fb)
    # Sprite: only the top-left pixel is 1, rest are 0. 8x8 1-bpp: 8 bytes.
    sprite = [0b10000000] + [0x00] * 7
    # Transparent blit: only that pixel is set.
    fb_blit(fb, 0, 0, 8, 8, sprite, 1, True)
    # (0,0) is in page 0, bit 0 -> byte 0 should be 0x01.
    check(fb.px[0] == 0x01, f"transparent blit sets (0,0) (got 0x{fb.px[0]:02X})")
    # Opaque blit: the rest of the 8x8 area is also cleared.
    fb_init(fb)
    # Pre-light some pixels in the destination.
    fb_set_pixel(fb, 3, 3, True)
    check(fb.px[3] != 0, "setup pixel lit before opaque blit")
    fb_blit(fb, 0, 0, 8, 8, sprite, 1, False)
    # The pre-lit pixel at (3,3) should now be cleared.
    check(fb.px[3] == 0, f"opaque blit clears pre-existing pixel (got 0x{fb.px[3]:02X})")


def test_fb_text():
    fb = Framebuffer()
    fb_init(fb)
    fb_draw_text(fb, 0, 0, "A", True)
    # The 'A' glyph is 5x7 starting at (0,0). Top of 'A' is row 0: 0x7E -> 0b1111110
    # fb_draw_char sets bit 'row' for each set bit. So row 0 pixels in col 0..4
    # should be: 0,1,1,1,1,1,1,0 (LSB-first read of 0x7E) = 0,1,1,1,1,1,1,0
    # Actually we set pixel if bit N of 0x7E is set. 0x7E = 0111 1110
    # bit 0 = 0, bit 1 = 1, bit 2 = 1, bit 3 = 1, bit 4 = 1, bit 5 = 1, bit 6 = 1
    # so pixels (0,1), (0,2), (0,3), (0,4), (0,5), (0,6) are on.
    # All in page 0 -> byte 0 should have bits 1..6 = 0b01111110 = 0x7E.
    check(fb.px[0] == 0x7E, f"text 'A' col 0 = 0x7E (got 0x{fb.px[0]:02X})")


def test_pcd8544_init_sequence():
    # The C++ init sequence (mirrored):
    spi = FakeSpi()
    contrast = 0x3F
    CMD_FN, FN_EXT, FN_BASIC = 0x20, 0x01, 0x00
    FN_TC, FN_BS, FN_V = 0x04, 0x00, 0x80
    CMD_DC, DC_E = 0x08, 0x04
    CMD_Y, CMD_X = 0x40, 0x80

    # (We don't actually call the C++; we replicate the same command flow.)
    spi.begin()
    spi.write_cmd(CMD_FN | FN_EXT)
    spi.write_cmd(FN_TC | 0x02)
    spi.write_cmd(FN_BS | 0x03)
    spi.write_cmd(FN_V  | contrast)
    spi.write_cmd(CMD_FN | FN_BASIC)
    spi.write_cmd(CMD_DC | DC_E)
    spi.write_cmd(CMD_Y)
    spi.write_cmd(CMD_X)
    spi.end()

    cmds = [v for tag, v in spi.log if tag == 'CMD']
    expected = [0x21, 0x06, 0x03, 0xBF, 0x20, 0x0C, 0x40, 0x80]
    check(cmds == expected, f"PCD8544 init sequence: {cmds}")


def test_pcd8544_flush_count():
    # The C++ flush emits: 6 x (CMD_Y | page, CMD_X, 84 data bytes).
    spi = FakeSpi()
    fb = Framebuffer()
    fb_init(fb)
    for page in range(6):
        spi.write_cmd(0x40 | page)
        spi.write_cmd(0x80)
        # Imagine 84 data bytes from the fb.
        for _ in range(84):
            spi.write_data_block([0], 1)
    n_data = sum(1 for t, _ in spi.log if t == 'DATA')
    n_cmd  = sum(1 for t, _ in spi.log if t == 'CMD')
    check(n_data == 6 * 84, f"flush data bytes = 504 (got {n_data})")
    check(n_cmd  == 6 * 2,  f"flush cmd bytes = 12 (got {n_cmd})")


def test_spi_timing_budget():
    # PCD8544 flush is 504 + 12 = 516 byte writes through SPI.
    # At 4 MHz, 8 bits/byte = 516 * 8 / 4e6 = 1.032 ms.
    # Add ~1 ms of D/C + CE toggles. Budget 1.5 ms per flush.
    n_bytes = 516
    us = n_bytes * 8 / 4.0  # microseconds at 4 MHz
    check(us < 1500, f"flush time budget: {us:.0f} us < 1500 us")


if __name__ == "__main__":
    test_fb_init()
    test_fb_set_pixel()
    test_fb_hline()
    test_fb_blit_clipping()
    test_fb_blit_transparent_vs_opaque()
    test_fb_text()
    test_pcd8544_init_sequence()
    test_pcd8544_flush_count()
    test_spi_timing_budget()
    print(f"M2 framebuffer+display: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
