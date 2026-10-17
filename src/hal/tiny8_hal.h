// Tiny8 Engine — Hardware Abstraction Layer interface.
// On AVR this is implemented by tiny8_hal_avr.cpp (Arduino digitalRead etc.).
// On host this is implemented by tiny8_hal_host.cpp (Python-driven stubs).
#ifndef TINY8_HAL_H
#define TINY8_HAL_H

#include <stdint.h>
#include "tiny8_types.h"

namespace t8 {

// GPIO direction.
enum class PinMode : uint8_t { In, Out, InPullup };

void hal_pin_mode (uint8_t pin, PinMode m);
void  hal_digital_write(uint8_t pin, bool high);
bool  hal_digital_read (uint8_t pin);

// Timing.
uint32_t hal_millis();
void     hal_delay_ms(uint16_t ms);

// SPI — the display driver uses these.
void hal_spi_begin();
void  hal_spi_transfer(uint8_t v);
void  hal_spi_end();

// Audio pin (piezo buzzer). On AVR we toggle a pin inside Timer2 ISR.
void hal_audio_set(bool on);

}  // namespace t8

#endif  // TINY8_HAL_H