// Tiny8 Engine — Arduino AVR HAL implementation.
//
// PHYSICAL: this file is only compiled into the AVR build. The host test
// uses tiny8_hal_host.cpp instead.

#include "tiny8_hal.h"
#include <Arduino.h>

namespace t8 {

void hal_pin_mode(uint8_t pin, PinMode m) {
    if (m == PinMode::Out)      pinMode(pin, OUTPUT);
    else if (m == PinMode::In)  pinMode(pin, INPUT);
    else                         pinMode(pin, INPUT_PULLUP);
}

void hal_digital_write(uint8_t pin, bool high) { digitalWrite(pin, high ? HIGH : LOW); }
bool hal_digital_read (uint8_t pin)            { return digitalRead(pin) != 0; }

uint32_t hal_millis()           { return ::millis(); }
void     hal_delay_ms(uint16_t ms) { ::delay(ms); }

void hal_spi_begin()      { SPI.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0)); SPI.begin(); }
void  hal_spi_transfer(uint8_t v) { SPI.transfer(v); }
void  hal_spi_end()        { SPI.endTransaction(); }

void hal_audio_set(bool on) { /* set by Timer2 ISR directly, see audio driver */ }

}  // namespace t8