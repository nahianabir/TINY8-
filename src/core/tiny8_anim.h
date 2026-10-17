// Tiny8 Engine — frame-based animation player over a Sprite atlas.
// Each Anim references an atlas sprite (PROGMEM) and an array of frame
// indices. A small player struct holds current/timer state.
//
// SRAM cost per playing animation: 5 bytes.

#ifndef TINY8_ANIM_H
#define TINY8_ANIM_H

#include <stdint.h>
#include "tiny8_types.h"
#include "tiny8_sprite.h"

namespace t8 {

// Sequence description in PROGMEM: array of frame indices into the atlas.
struct Anim {
    const Sprite*     atlas;
    const uint8_t*    frames;     // PROGMEM; length given by `count`
    uint8_t           count;
    uint8_t           ticks_per_frame;   // in fixed steps
    bool              loop;
};

// Player state.
struct AnimPlayer {
    const Anim* anim;        // nullptr = inactive
    uint8_t     idx;         // current frame index
    uint8_t     tick;        // ticks into the current frame
    bool        done;        // set when a non-looping anim completes
};

void anim_play(AnimPlayer& p, const Anim& a);
void anim_stop(AnimPlayer& p);

// Advance one fixed step. If the player has ticked enough frames, advance
// the frame index (wrapping if loop, or marking done).
void anim_tick(AnimPlayer& p);

// Render the current frame to the framebuffer at (x, y), respecting the
// sprite's transparency.
void anim_draw(Framebuffer& fb, int16_t x, int16_t y, const AnimPlayer& p, bool transparent);

}  // namespace t8

#endif  // TINY8_ANIM_H