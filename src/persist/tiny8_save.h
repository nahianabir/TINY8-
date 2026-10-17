// Tiny8 Engine — versioned EEPROM save slots.
//
// Each slot is T8_SAVE_BYTES long. Layout:
//   [0]   magic     = 0xA5
//   [1]   version   = T8_SAVE_VERSION
//   [2..N-2]        user data
//   [N-1] crc8      of bytes 0..N-2
//
// A slot is "blank" if the magic byte is not 0xA5 (factory erased EEPROM
// reads 0xFF).  A slot is "valid" if magic, version, and CRC all match.
// On a bad version or CRC, load returns CrcFail / BadVersion.

#ifndef TINY8_SAVE_H
#define TINY8_SAVE_H

#include <stdint.h>
#include "tiny8_types.h"

namespace t8 {

static constexpr uint8_t T8_SAVE_VERSION = 0x01;
static constexpr uint8_t T8_SAVE_MAGIC   = 0xA5;

Err save_write (uint8_t slot, const uint8_t* data, uint8_t n);
Err save_read  (uint8_t slot, uint8_t* data, uint8_t n);   // returns NoSave if blank
Err save_erase (uint8_t slot);

}  // namespace t8

#endif  // TINY8_SAVE_H