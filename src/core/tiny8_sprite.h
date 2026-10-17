// Tiny8 Engine — Sprite definition + blit convenience.
// A Sprite is a 1-bpp monochrome bitmap stored in PROGMEM (or any read-only
// memory on the host).  The blit just calls fb_blit with the right stride.

#ifndef TINY8_SPRITE_H
#define TINY8_SPRITE_H

#include <stdint.h>
#include "tiny8_framebuffer.h"

namespace t8 {

struct Sprite {
    uint8_t  w;        // pixels
    uint8_t  h;        // pixels
    uint16_t stride;   // bytes per row
    const uint8_t* bits;  // PROGMEM on AVR
};

inline void fb_blit_sprite(Framebuffer& fb, int16_t x, int16_t y,
                           const Sprite& s, bool transparent) {
    if (!s.bits) return;
    fb_blit(fb, x, y, s.w, s.h, s.bits, s.stride, transparent);
}

// Draw a sub-region of an atlas (sheet) at (x, y).  `src_x0, src_y0` are
// the top-left in atlas coordinates.
inline void fb_blit_sub(Framebuffer& fb, int16_t x, int16_t y,
                        const Sprite& atlas, uint8_t src_x0, uint8_t src_y0,
                        uint8_t w, uint8_t h, bool transparent) {
    if (!atlas.bits) return;
    // The blit operates on the atlas bytes, but with a pointer offset and
    // adjusted source stride so only the sub-rectangle is read.
    const uint8_t* sub_bits = atlas.bits +
        static_cast<uint16_t>(src_y0) * atlas.stride +
        (src_x0 >> 3);
    fb_blit(fb, x, y, w, h, sub_bits, atlas.stride, transparent);
}

}  // namespace t8

#endif  // TINY8_SPRITE_H