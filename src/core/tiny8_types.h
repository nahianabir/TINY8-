// Tiny8 Engine — foundational integer types and limits.
// Pure C++, host-testable. No Arduino includes.
//
// PHYSICAL: this file is shared by AVR build and host tests unchanged.

#ifndef TINY8_TYPES_H
#define TINY8_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

namespace t8 {

// Display reference target. Real driver overrides these via T8_DISPLAY_*.
static constexpr uint8_t REF_W   = 84;
static constexpr uint8_t REF_H   = 48;
static constexpr uint8_t REF_PG  = 6;     // 48 / 8
static constexpr uint16_t FB_BYTES = (REF_W * REF_H) / 8;  // 504

// Compile-time caps. Override in build flags if you need more headroom.
#ifndef T8_MAX_ENTITIES
#define T8_MAX_ENTITIES  8
#endif
#ifndef T8_MAX_ANIM
#define T8_MAX_ANIM      4
#endif
#ifndef T8_MAX_SCENES
#define T8_MAX_SCENES    4
#endif
#ifndef T8_INPUT_BUTTONS
#define T8_INPUT_BUTTONS 6
#endif
#ifndef T8_SAVE_SLOTS
#define T8_SAVE_SLOTS    4
#endif
#ifndef T8_SAVE_BYTES
#define T8_SAVE_BYTES    16
#endif

// Sub-pixel scale. 1 px == T8_SUB sub-units. Keeps velocity fractional
// without using floats. Use 16 for plenty of headroom on a 16-bit value.
static constexpr int16_t T8_SUB = 16;

// Mask helpers.
static constexpr uint8_t T8_PAGE(uint8_t y) { return static_cast<uint8_t>(y >> 3); }
static constexpr uint8_t T8_BIT (uint8_t y) { return static_cast<uint8_t>(y & 7); }

// Standard error codes returned by engine APIs.
enum class Err : int8_t {
    Ok        =  0,
    NoRoom    = -1,  // pool / scene slot exhausted
    BadArg    = -2,  // null pointer or out-of-range value
    NoSave    = -3,  // EEPROM slot blank
    CrcFail   = -4,  // EEPROM data corrupt
    BadVersion= -5,  // save block version mismatch
};

}  // namespace t8

#endif  // TINY8_TYPES_H
