// Tiny8 Engine — single 504-byte monochrome framebuffer + 2D primitives.
// Pure C++, no Arduino headers — host-testable.
#ifndef TINY8_FRAMEBUFFER_H
#define TINY8_FRAMEBUFFER_H

#include <stdint.h>
#include "tiny8_types.h"
#include "tiny8_rect.h"

namespace t8 {

// The framebuffer is laid out as 6 pages of 84 bytes (one bit per pixel).
// PCD8544 native layout: byte (page*W + x) holds 8 vertical pixels of column
// x, page p. Bit 0 of that byte == top pixel of the column; bit 7 == bottom.
struct Framebuffer {
    uint8_t px[FB_BYTES];
    bool    dirty;     // hint to display driver
};

// Lifecycle.
void     fb_init(Framebuffer& fb);
void     fb_clear(Framebuffer& fb);
void     fb_present(Framebuffer& fb);    // marks dirty; driver pulls via flush

// Primitives. (x,y) in pixels. Coordinates outside the screen are clipped.
void     fb_set_pixel(Framebuffer& fb, int16_t x, int16_t y, bool on);
void     fb_draw_hline(Framebuffer& fb, int16_t x, int16_t y, int16_t w, bool on);
void     fb_draw_vline(Framebuffer& fb, int16_t x, int16_t y, int16_t h, bool on);
void     fb_draw_rect (Framebuffer& fb, const Rect& r, bool on);   // outline
void     fb_fill_rect (Framebuffer& fb, const Rect& r, bool on);

// Bitmap blit. `bits` is a row-major buffer; width rounded up to 8 bits.
// If `transparent` is true, zero bits are skipped (leaves fb pixel untouched).
// If false, the entire rectangle is overwritten.
//
// `src_stride_bytes` is the byte distance from one row to the next in `bits`
// (allows a sub-region of a larger atlas without copying).
void fb_blit(Framebuffer& fb,
             int16_t dst_x, int16_t dst_y,
             uint8_t w, uint8_t h,
             const uint8_t* bits,
             uint16_t src_stride_bytes,
             bool transparent);

// 1-bit ASCII font blit. `font_5x7` is a 5×7 table, 5 bytes per glyph,
// 96 glyphs starting at space (0x20).
void fb_draw_char(Framebuffer& fb, int16_t x, int16_t y, char c, bool on);
void fb_draw_text (Framebuffer& fb, int16_t x, int16_t y, const char* s, bool on);

// Direct access — only for the display driver to call after present.
const uint8_t* fb_pixels(const Framebuffer& fb);

}  // namespace t8

#endif  // TINY8_FRAMEBUFFER_H
