// Tiny8 Engine — framebuffer implementation.
//
// Optimised for the ATmega328P:
//   * Primitives in-place mutate the page-oriented byte buffer.
//   * No function calls in the hot blit path other than fb_blit itself.
//   * All clipping is branch-light; expected to run < 0.5 ms for a 16×16 sprite.

#include "tiny8_framebuffer.h"
#include <string.h>

namespace t8 {

static constexpr int16_t kW = REF_W;   // 84
static constexpr int16_t kH = REF_H;   // 48

void fb_init(Framebuffer& fb)   { memset(fb.px, 0, FB_BYTES); fb.dirty = true; }
void fb_clear(Framebuffer& fb)  { memset(fb.px, 0, FB_BYTES); fb.dirty = true; }
void fb_present(Framebuffer& fb){ fb.dirty = true; }
const uint8_t* fb_pixels(const Framebuffer& fb) { return fb.px; }

// ---------- primitives ----------

static inline void put_pixel_unchecked(Framebuffer& fb, int16_t x, int16_t y, bool on) {
    if (x < 0 || y < 0 || x >= kW || y >= kH) return;
    const uint16_t idx = static_cast<uint16_t>((y >> 3) * kW + x);
    const uint8_t  bit = static_cast<uint8_t>(1u << (y & 7));
    if (on) fb.px[idx] |= bit; else fb.px[idx] &= static_cast<uint8_t>(~bit);
}

void fb_set_pixel(Framebuffer& fb, int16_t x, int16_t y, bool on) {
    put_pixel_unchecked(fb, x, y, on);
}

void fb_draw_hline(Framebuffer& fb, int16_t x, int16_t y, int16_t w, bool on) {
    if (y < 0 || y >= kH) return;
    if (x < 0) { w += x; x = 0; }
    if (x + w > kW) w = static_cast<int16_t>(kW - x);
    if (w <= 0) return;
    const uint8_t bit = static_cast<uint8_t>(1u << (y & 7));
    for (int16_t i = 0; i < w; ++i) {
        const uint16_t idx = static_cast<uint16_t>((y >> 3) * kW + x + i);
        if (on) fb.px[idx] |= bit; else fb.px[idx] &= static_cast<uint8_t>(~bit);
    }
}

void fb_draw_vline(Framebuffer& fb, int16_t x, int16_t y, int16_t h, bool on) {
    if (x < 0 || x >= kW) return;
    if (y < 0) { h += y; y = 0; }
    if (y + h > kH) h = static_cast<int16_t>(kH - y);
    if (h <= 0) return;
    for (int16_t j = 0; j < h; ++j) {
        const uint16_t idx = static_cast<uint16_t>(((y + j) >> 3) * kW + x);
        const uint8_t  bit = static_cast<uint8_t>(1u << ((y + j) & 7));
        if (on) fb.px[idx] |= bit; else fb.px[idx] &= static_cast<uint8_t>(~bit);
    }
}

void fb_draw_rect(Framebuffer& fb, const Rect& r, bool on) {
    if (rect_empty(r)) return;
    fb_draw_hline(fb, r.x,         r.y,         r.w, on);
    fb_draw_hline(fb, r.x,         r.y + r.h - 1, r.w, on);
    fb_draw_vline(fb, r.x,         r.y,         r.h, on);
    fb_draw_vline(fb, r.x + r.w - 1, r.y,       r.h, on);
}

void fb_fill_rect(Framebuffer& fb, const Rect& r, bool on) {
    for (int16_t j = 0; j < r.h; ++j) fb_draw_hline(fb, r.x, r.y + j, r.w, on);
}

// ---------- bitmap blit ----------
//
// Source layout:
//   * `bits` is row-major, MSB-first within each byte (bit 7 = leftmost pixel
//     of that byte).  This matches the PCD8544 native orientation and is the
//     convention the sprite converter writes.
//   * `src_stride_bytes` is the byte distance between the start of one row
//     and the start of the next. For typical 1-bpp sprites it equals
//     (width + 7) / 8.
//
// Destination layout:
//   * Pixel (x, y) lives in byte `(y>>3) * kW + x`, bit `y & 7`.

void fb_blit(Framebuffer& fb,
             int16_t dst_x, int16_t dst_y,
             uint8_t w, uint8_t h,
             const uint8_t* bits,
             uint16_t src_stride_bytes,
             bool transparent) {
    if (w == 0 || h == 0 || !bits) return;

    // Clip against the screen.
    int16_t x0 = dst_x, y0 = dst_y;
    int16_t x1 = static_cast<int16_t>(dst_x + w);
    int16_t y1 = static_cast<int16_t>(dst_y + h);
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > kW) x1 = kW;
    if (y1 > kH) y1 = kH;
    if (x0 >= x1 || y0 >= y1) return;

    for (int16_t y = y0; y < y1; ++y) {
        const uint16_t src_row_off = static_cast<uint16_t>(
            (static_cast<uint16_t>(y - dst_y)) * src_stride_bytes);
        const uint16_t dst_idx = static_cast<uint16_t>((y >> 3) * kW);
        const uint8_t  dst_bit = static_cast<uint8_t>(y & 7);
        for (int16_t x = x0; x < x1; ++x) {
            const uint8_t  sx      = static_cast<uint8_t>(x - dst_x);
            const uint8_t  src_byte = bits[src_row_off + (sx >> 3)];
            const uint8_t  src_bit  = static_cast<uint8_t>(0x80u >> (sx & 7));
            if (transparent && !(src_byte & src_bit)) continue;
            const uint16_t i = static_cast<uint16_t>(dst_idx + x);
            if (src_byte & src_bit) fb.px[i] |=  static_cast<uint8_t>(1u << dst_bit);
            else                     fb.px[i] &= static_cast<uint8_t>(~(1u << dst_bit));
        }
    }
    fb.dirty = true;
}

// ---------- text ----------
//
// The 5×7 font lives in PROGMEM. We keep its declaration in tiny8_font.h
// so this file stays free of large const tables.
extern const uint8_t kFont5x7[96][5];

void fb_draw_char(Framebuffer& fb, int16_t x, int16_t y, char c, bool on) {
    if (c < 32 || c > 127) c = '?';
    const uint8_t idx = static_cast<uint8_t>(c - 32);
    // 5 columns of 1-byte font data, 1 px space on the right.
    for (uint8_t col = 0; col < 5; ++col) {
        const uint8_t bits = kFont5x7[idx][col];
        for (uint8_t row = 0; row < 7; ++row) {
            if (bits & (1u << row)) fb_set_pixel(fb, static_cast<int16_t>(x + col), static_cast<int16_t>(y + row), on);
        }
    }
}

void fb_draw_text(Framebuffer& fb, int16_t x, int16_t y, const char* s, bool on) {
    if (!s) return;
    while (*s) {
        fb_draw_char(fb, x, y, *s++, on);
        x = static_cast<int16_t>(x + 6);
    }
}

}  // namespace t8
