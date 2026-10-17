// Tiny8 Engine — fixed-step game-clock with bounded catch-up.
// Host-testable. The "now" source is injected so the same logic works
// on a real Arduino (millis) and on a host (fake clock).
#ifndef TINY8_TIME_H
#define TINY8_TIME_H

#include "tiny8_types.h"

namespace t8 {

// Tick source. On AVR this is implemented in tiny8_hal_avr.cpp; on host
// the unit test drives it manually.
uint32_t hal_millis();

// Step clock. Call once per main-loop iteration with the latest millis().
// Runs 0..T8_MAX_CATCHUP steps of `dt_ms` to consume accumulated wall time.
// `out_steps` receives how many fixed steps were dispatched (0..N).
struct StepClock {
    uint32_t step_ms;        // fixed step length, e.g. 16 for ~60 Hz
    uint32_t accumulator;    // ms banked since last drain
    uint32_t last_ms;        // last wall clock we saw
    uint8_t  max_catchup;    // anti spiral-of-death
    static constexpr uint8_t kDefaultMaxCatch = 4;
};

void stepclock_init(StepClock& c, uint32_t step_ms, uint8_t max_catch = StepClock::kDefaultMaxCatch);

// Poll. Returns number of steps consumed (0..max_catchup). Caller should
// loop that many times calling its scene update.
uint8_t stepclock_poll(StepClock& c);

}  // namespace t8

#endif  // TINY8_TIME_H
