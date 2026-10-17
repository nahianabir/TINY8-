// Tiny8 Engine — input module.
// 6 buttons: UP, DOWN, LEFT, RIGHT, A, START.
// The engine tracks "held" and "pressed" (edge) per button. The host HAL
// provides a poll function; the AVR HAL reads digitalRead() with a
// debounce counter.

#ifndef TINY8_INPUT_H
#define TINY8_INPUT_H

#include <stdint.h>
#include "tiny8_types.h"

namespace t8 {

enum Button : uint8_t {
    BTN_UP    = 0,
    BTN_DOWN  = 1,
    BTN_LEFT  = 2,
    BTN_RIGHT = 3,
    BTN_A     = 4,
    BTN_START = 5,
    BTN_COUNT = T8_INPUT_BUTTONS,
};

// Default pin assignments for the Arduino Uno (active LOW with internal
// pull-up).  Override these from your sketch by calling input_init() with
// a custom pin array.
struct InputPins {
    uint8_t pin[T8_INPUT_BUTTONS];
};

// Initialise with default Uno pin numbers.  Or call input_init(pins) with
// your own mapping.
void input_init();
void input_init(const InputPins& pins);

// Poll.  Call once per main-loop iteration before reading input.  Updates
// "held" and "pressed" state.
void input_poll();

// True if the button is currently held.
bool input_held   (Button b);
// True if the button transitioned from up to down since the last poll.
bool input_pressed(Button b);

}  // namespace t8

#endif  // TINY8_INPUT_H