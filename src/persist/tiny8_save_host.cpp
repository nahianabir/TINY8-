// Tiny8 Engine — host-side save backend (RAM-backed).
// Compiled into the host test build only.

#include "tiny8_save.h"
#include "tiny8_math.h"
#include <vector>

namespace t8 {

#ifdef __AVR__
#error "This file is host-only. Do not compile on AVR."
#endif

static std::vector<uint8_t> g_store(T8_SAVE_SLOTS * T8_SAVE_BYTES, 0xFF);

static uint16_t slot_offset(uint8_t slot) {
    return static_cast<uint16_t>(slot) * T8_SAVE_BYTES;
}

Err save_write(uint8_t slot, const uint8_t* data, uint8_t n) {
    if (slot >= T8_SAVE_SLOTS) return Err::BadArg;
    if (n + 3 > T8_SAVE_BYTES) return Err::BadArg;
    const uint16_t off = slot_offset(slot);
    uint8_t buf[T8_SAVE_BYTES];
    buf[0] = T8_SAVE_MAGIC;
    buf[1] = T8_SAVE_VERSION;
    for (uint8_t i = 0; i < n; ++i) buf[2 + i] = data[i];
    buf[2 + n] = crc8(buf, static_cast<size_t>(2 + n));
    for (uint8_t i = 0; i < 2 + n + 1; ++i) g_store[off + i] = buf[i];
    return Err::Ok;
}

Err save_read(uint8_t slot, uint8_t* data, uint8_t n) {
    if (slot >= T8_SAVE_SLOTS) return Err::BadArg;
    if (n + 3 > T8_SAVE_BYTES) return Err::BadArg;
    const uint16_t off = slot_offset(slot);
    uint8_t buf[T8_SAVE_BYTES];
    for (uint8_t i = 0; i < 2 + n + 1; ++i) buf[i] = g_store[off + i];
    if (buf[0] != T8_SAVE_MAGIC)   return Err::NoSave;
    if (buf[1] != T8_SAVE_VERSION) return Err::BadVersion;
    uint8_t want = crc8(buf, static_cast<size_t>(2 + n));
    if (want != buf[2 + n])          return Err::CrcFail;
    for (uint8_t i = 0; i < n; ++i) data[i] = buf[2 + i];
    return Err::Ok;
}

Err save_erase(uint8_t slot) {
    if (slot >= T8_SAVE_SLOTS) return Err::BadArg;
    const uint16_t off = slot_offset(slot);
    for (uint8_t i = 0; i < T8_SAVE_BYTES; ++i) g_store[off + i] = 0xFF;
    return Err::Ok;
}

}  // namespace t8