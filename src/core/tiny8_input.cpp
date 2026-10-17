#include "tiny8_input.h"
#include "tiny8_hal.h"

namespace t8 {

static bool g_held[T8_INPUT_BUTTONS];
static bool g_pressed[T8_INPUT_BUTTONS];
static InputPins g_pins;

// Default Uno pin map: 2,3,4,5,A0,A1.  Active LOW (the hal_read returns
// LOW when pressed because the buttons short the pin to GND and the
// internal pull-up holds it HIGH otherwise).
static const InputPins kDefaults = {{ 2, 3, 4, 5, A0, A1 }};

void input_init() { input_init(kDefaults); }

void input_init(const InputPins& pins) {
    g_pins = pins;
    for (uint8_t i = 0; i < T8_INPUT_BUTTONS; ++i) {
        hal_pin_mode(g_pins.pin[i], PinMode::InPullup);
        g_held[i] = false;
        g_pressed[i] = false;
    }
}

void input_poll() {
    for (uint8_t i = 0; i < T8_INPUT_BUTTONS; ++i) {
        const bool now = !hal_digital_read(g_pins.pin[i]);  // active LOW
        g_pressed[i] = now && !g_held[i];
        g_held[i] = now;
    }
}

bool input_held   (Button b) { return b < T8_INPUT_BUTTONS && g_held[b]; }
bool input_pressed(Button b) { return b < T8_INPUT_BUTTONS && g_pressed[b]; }

}  // namespace t8
