// Tiny8 Engine — Milestone 1 host unit tests.
// Compiles on PC with:  g++ -std=c++17 -I src -I src/core test/test_m1_core.cpp
//                      src/core/tiny8_time.cpp src/hal/tiny8_hal_host.cpp -o test_m1
// Run: ./test_m1
//
// PHYSICAL: this test is not flashed to the Uno. It exercises the same C++
// the device runs, so the AVR binary is validated by source equivalence.
#include "tiny8_types.h"
#include "tiny8_rect.h"
#include "tiny8_math.h"
#include "tiny8_time.h"

#include <cassert>
#include <cstdio>

using namespace t8;

static int g_failed = 0;
static int g_passed = 0;

#define T_CHECK(expr) do {                                                   \
    if (!(expr)) {                                                           \
        std::printf("FAIL  %s:%d  %s\n", __FILE__, __LINE__, #expr);         \
        ++g_failed;                                                          \
    } else { ++g_passed;                                                     \
    }                                                                        \
} while (0)

static void test_rect() {
    Rect a{0, 0, 10, 10};
    Rect b{5, 5, 10, 10};
    Rect c{20, 20, 5,  5};
    T_CHECK(rect_overlap(a, b) == true);
    T_CHECK(rect_overlap(a, c) == false);
    T_CHECK(rect_overlap(b, c) == false);

    // Edge-touching should not be overlap.
    Rect e1{0, 0, 10, 10};
    Rect e2{10, 0, 10, 10};
    T_CHECK(rect_overlap(e1, e2) == false);

    // Clip intersection.
    Rect clip = rect_clip(Rect{2, 2, 100, 100}, Rect{0, 0, 50, 50});
    T_CHECK(clip.x == 2 && clip.y == 2 && clip.w == 48 && clip.h == 48);

    // Empty after clip.
    Rect empty = rect_clip(Rect{100, 100, 10, 10}, Rect{0, 0, 50, 50});
    T_CHECK(rect_empty(empty));
}

static void test_math() {
    // fx_mul basic — Q4 fixed point, 1.0 == 16 sub-units.
    T_CHECK(fx_mul(16, 16) == 16);      // 1.0 * 1.0 == 1.0
    T_CHECK(fx_mul(32, 8)  == 16);      // 2.0 * 0.5 == 1.0

    // Sub-pixel.
    T_CHECK(px_to_sub(3) == 48);
    T_CHECK(sub_to_px(48) == 3);

    // CRC8 — poly 0x07, init 0x00. Computed by hand: crc({FF}) = 0xF3.
    uint8_t z = 0, f = 0xFF;
    T_CHECK(crc8(&z, 1) == 0x00);
    T_CHECK(crc8(&f, 1) == 0xF3);
}

static void test_time() {
    StepClock c;
    hal_host_set_millis(0);
    stepclock_init(c, 16);  // ~60 Hz

    // First poll: zero delta, zero steps.
    T_CHECK(stepclock_poll(c) == 0);

    // 33 ms → 2 steps.
    hal_host_advance(33);
    T_CHECK(stepclock_poll(c) == 2);

    // 100 ms stall: bounded by max_catchup=4 → 4 steps, accumulator clamped.
    hal_host_advance(100);
    T_CHECK(stepclock_poll(c) == 4);
    T_CHECK(c.accumulator <= 16);
}

int main() {
    test_rect();
    test_math();
    test_time();
    std::printf("M1 core: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
