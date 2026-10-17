// Tiny8 Engine — step clock implementation. Host-testable.
#include "tiny8_time.h"

namespace t8 {

void stepclock_init(StepClock& c, uint32_t step_ms, uint8_t max_catch) {
    c.step_ms     = step_ms;
    c.accumulator = 0;
    c.last_ms     = hal_millis();
    c.max_catchup = max_catch ? max_catch : 1;
}

uint8_t stepclock_poll(StepClock& c) {
    uint32_t now = hal_millis();
    uint32_t delta = now - c.last_ms;
    c.last_ms = now;
    c.accumulator += delta;

    uint8_t steps = 0;
    while (c.accumulator >= c.step_ms && steps < c.max_catchup) {
        c.accumulator -= c.step_ms;
        ++steps;
    }
    // Clamp residual to one step so a long stall does not produce a burst.
    if (c.accumulator > c.step_ms) c.accumulator = c.step_ms;
    return steps;
}

}  // namespace t8
