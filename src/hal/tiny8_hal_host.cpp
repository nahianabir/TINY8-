// Tiny8 Engine — host-side HAL stub. Used by unit tests on the PC.
#include "tiny8_hal.h"
#include "tiny8_time.h"
#include <cstdint>
#include <vector>
#include <cstdio>

namespace t8 {

static uint32_t g_host_millis = 0;
static std::vector<uint8_t> g_pin_state;
static std::vector<uint8_t> g_spi_log;
static bool g_audio_pin = false;

void hal_host_set_millis(uint32_t v) { g_host_millis = v; }
void hal_host_advance(uint32_t dt)  { g_host_millis += dt; }

// Defined here so tiny8_time.cpp can call it in the host build.
uint32_t hal_millis() { return g_host_millis; }

void hal_pin_mode(uint8_t pin, PinMode) {
    if (pin >= g_pin_state.size()) g_pin_state.resize(pin + 1, 0);
}
void hal_digital_write(uint8_t pin, bool high) {
    if (pin >= g_pin_state.size()) g_pin_state.resize(pin + 1, 0);
    g_pin_state[pin] = high ? 1 : 0;
}
bool hal_digital_read(uint8_t pin) {
    if (pin >= g_pin_state.size()) return false;
    return g_pin_state[pin] != 0;
}

void hal_delay_ms(uint16_t ms) { g_host_millis += ms; }

void hal_spi_begin()      { g_spi_log.clear(); }
void  hal_spi_transfer(uint8_t v) { g_spi_log.push_back(v); }
void  hal_spi_end()        {}

void hal_audio_set(bool on) { g_audio_pin = on; }

const std::vector<uint8_t>& hal_host_spi_log() { return g_spi_log; }
bool hal_host_audio_state() { return g_audio_pin; }
uint8_t hal_host_pin_state(uint8_t pin) {
    return pin < g_pin_state.size() ? g_pin_state[pin] : 0;
}

}  // namespace t8
