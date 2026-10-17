// Tiny8 Engine — EEPROM save backend for AVR.
//
// PHYSICAL: requires #include <EEPROM.h>. Each write costs 3.3 ms; the
// caller is responsible for not thrashing saves inside a single frame.

#include "tiny8_save.h"
#include "tiny8_math.h"
#ifdef __AVR__
#include <EEPROM.h>
#endif

namespace t8 {

// The AVR-specific path uses the real EEPROM library. The host path
// (in tiny8_save_host.cpp) uses a RAM-backed store.

#ifdef __AVR__

static uint16_t slot_offset(uint8_t slot) {
    return static_cast<uint16_t>(slot) * T8_SAVE_BYTES;
}

Err save_write(uint8_t slot, const uint8_t* data, uint8_t n) {
    if (slot >= T8_SAVE_SLOTS) return Err::BadArg;
    if (n + 3 > T8_SAVE_BYTES) return Err::BadArg;
    uint16_t off = slot_offset(slot);
    uint8_t buf[T8_SAVE_BYTES];
    buf[0] = T8_SAVE_MAGIC;
    buf[1] = T8_SAVE_VERSION;
    for (uint8_t i = 0; i < n; ++i) buf[2 + i] = data[i];
    buf[2 + n] = crc8(buf, static_cast<size_t>(2 + n));
    for (uint8_t i = 0; i < 2 + n + 1; ++i) EEPROM.write(off + i, buf[i]);
    return Err::Ok;
}

Err save_read(uint8_t slot, uint8_t* data, uint8_t n) {
    if (slot >= T8_SAVE_SLOTS) return Err::BadArg;
    if (n + 3 > T8_SAVE_BYTES) return Err::BadArg;
    uint16_t off = slot_offset(slot);
    uint8_t buf[T8_SAVE_BYTES];
    for (uint8_t i = 0; i < 2 + n + 1; ++i) buf[i] = EEPROM.read(off + i);
    if (buf[0] != T8_SAVE_MAGIC)   return Err::NoSave;
    if (buf[1] != T8_SAVE_VERSION) return Err::BadVersion;
    uint8_t want = crc8(buf, static_cast<size_t>(2 + n));
    if (want != buf[2 + n])          return Err::CrcFail;
    for (uint8_t i = 0; i < n; ++i) data[i] = buf[2 + i];
    return Err::Ok;
}

Err save_erase(uint8_t slot) {
    if (slot >= T8_SAVE_SLOTS) return Err::BadArg;
    uint16_t off = slot_offset(slot);
    for (uint8_t i = 0; i < T8_SAVE_BYTES; ++i) EEPROM.write(off + i, 0xFF);
    return Err::Ok;
}

#else
// Host build: fall through to a RAM-backed implementation below.
#endif

}  // namespace t8
