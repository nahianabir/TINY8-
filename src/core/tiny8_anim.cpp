// Tiny8 Engine — animation player. All sequence data is in PROGMEM, so we
// index into the frames array via pgm_read_byte. On host we read normally.

#include "tiny8_anim.h"

#ifdef __AVR__
#include <avr/pgmspace.h>
#define T8_PGM(b)   pgm_read_byte(&(b))
#else
#define T8_PGM(b)   (b)
#endif

namespace t8 {

void anim_play(AnimPlayer& p, const Anim& a) {
    p.anim  = &a;
    p.idx   = 0;
    p.tick  = 0;
    p.done  = false;
}

void anim_stop(AnimPlayer& p) { p.anim = nullptr; p.done = false; }

void anim_tick(AnimPlayer& p) {
    if (!p.anim || p.done) return;
    if (++p.tick < p.anim->ticks_per_frame) return;
    p.tick = 0;
    if (p.idx + 1 >= p.anim->count) {
        if (p.anim->loop) p.idx = 0;
        else { p.done = true; return; }
    } else {
        ++p.idx;
    }
}

void anim_draw(Framebuffer& fb, int16_t x, int16_t y, const AnimPlayer& p, bool transparent) {
    if (!p.anim || !p.anim->atlas) return;
    const uint8_t fi = T8_PGM(p.anim->frames[p.idx]);
    const Sprite& atlas = *p.anim->atlas;
    const uint8_t fw = atlas.w;
    const uint8_t fh = atlas.h;
    const uint16_t col = static_cast<uint16_t>(fi) * fw;
    const uint8_t src_x = static_cast<uint8_t>(col & 7);
    const uint8_t src_y = atlas.h == 0 ? 0 : static_cast<uint8_t>((col / 8) * atlas.h);
    // Note: the simple atlas layout used here is "N frames of fw x fh,
    // arranged left-to-right, top-to-bottom in 8-pixel columns". A more
    // general atlas layout is provided by the converter tool.
    fb_blit_sub(fb, x, y, atlas, src_x, src_y, fw, fh, transparent);
}

}  // namespace t8