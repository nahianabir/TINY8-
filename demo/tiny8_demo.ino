// Tiny8 Engine — top-level Arduino sketch (Tiny8 Quest demo).
//
// PHYSICAL: this file is the only place that touches the Arduino runtime
// directly (setup / loop).  The engine core is reusable without it.
//
// Hooks: an Arduino Uno R3 with a PCD8544 wired as in docs/PINS.md and
// 5 buttons (UP/DOWN/LEFT/RIGHT/A) + START.  Buzzer on D6.

#include "tiny8_engine.h"
#include "tiny8_display_pcd8544.h"
#include "demo_scenes.cpp"

namespace t8 {

// One global framebuffer.
static Framebuffer g_fb;

// One global step clock.
static StepClock   g_clk;

void setup() {
    // Display.
    static const Pcd8544Pins kPins{/*clk*/13, /*din*/11, /*ce*/9, /*dc*/8, /*rst*/7, /*bl*/5};
    display_register(pcd8544_make(kPins));
    display_init();
    display_set_contrast(0x3F);

    // Audio.
    audio_init(/*buzzer pin*/6);

    // Input.
    input_init_default();

    // Engine state.
    fb_init(g_fb);
    stepclock_init(g_clk, 16);  // 60 Hz

    // Demo.
    demo_boot();
}

void loop() {
    uint8_t n = stepclock_poll(g_clk);
    input_poll();
    for (uint8_t i = 0; i < n; ++i) {
        scene_update();
    }
    if (n > 0) {
        scene_draw(g_fb);
        display_flush(g_fb);
    }
}

}  // namespace t8
