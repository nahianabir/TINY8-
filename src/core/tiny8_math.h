// Tiny8 Engine — fixed-point helpers (no FPU, no libgcc).
// All functions are constexpr-safe; no globals.
#ifndef TINY8_MATH_H
#define TINY8_MATH_H

#include "tiny8_types.h"

namespace t8 {

// Multiply two Q4.4 (12.4?) style values: result = (a * b) >> 4.
// For T8_SUB=16 the natural unit is 1 px = 16 sub-units (Q4 fixed point).
static inline int16_t fx_mul(int16_t a, int16_t b) {
    int32_t p = static_cast<int32_t>(a) * static_cast<int32_t>(b);
    return static_cast<int16_t>(p >> 4);
}

// Convert between pixel and sub-pixel coordinates.
static inline int16_t px_to_sub(int16_t px) { return static_cast<int16_t>(px * T8_SUB); }
static inline int16_t sub_to_px(int16_t sub) { return static_cast<int16_t>(sub / T8_SUB); }

// 8-bit CRC used for EEPROM saves. Polynomial 0x07, init 0x00.
static inline uint8_t crc8(const uint8_t* data, size_t n, uint8_t seed = 0) {
    uint8_t c = seed;
    for (size_t i = 0; i < n; ++i) {
        c ^= data[i];
        for (int b = 0; b < 8; ++b) c = (c & 0x80) ? static_cast<uint8_t>((c << 1) ^ 0x07) : static_cast<uint8_t>(c << 1);
    }
    return c;
}

}  // namespace t8

#endif  // TINY8_MATH_H
