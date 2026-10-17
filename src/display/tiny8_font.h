// Tiny8 Engine — built-in 5×7 ASCII font (96 glyphs, space..~).
// Bit layout: row bit 0 = top, bit 6 = bottom of the 7-pixel-tall glyph.
// Each glyph is 5 columns wide, 1-byte per column, MSB = leftmost pixel.
// (Used by the framebuffer in row-major, top-down form.)
//
// This table is ~480 bytes and would be heavy in SRAM, so it is referenced
// as PROGMEM on AVR (the AVR build wraps it with PROGMEM; the host build
// uses it directly).

#ifndef TINY8_FONT_H
#define TINY8_FONT_H

#include <stdint.h>
#include "tiny8_types.h"

namespace t8 {

#ifndef TINY8_FONT_IN_RAM
// On AVR: stored in PROGMEM. On host: ordinary const data.
extern const uint8_t kFont5x7[96][5];
#else
// Test build: a copy in plain RAM.
extern uint8_t kFont5x7[96][5];
#endif

}  // namespace t8

#endif  // TINY8_FONT_H
