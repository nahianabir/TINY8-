#include "tiny8_camera.h"

namespace t8 {

void cam_init(Camera& c, int16_t bw, int16_t bh) {
    c.x = c.y = 0;
    c.bounds_w = bw;
    c.bounds_h = bh;
}

static inline int16_t clamp_i(int16_t v, int16_t lo, int16_t hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void cam_follow(Camera& c, int16_t tx, int16_t ty, int16_t vw, int16_t vh) {
    c.x = static_cast<int16_t>(tx - vw / 2);
    c.y = static_cast<int16_t>(ty - vh / 2);
    if (c.bounds_w > vw) c.x = clamp_i(c.x, 0, static_cast<int16_t>(c.bounds_w - vw));
    else                  c.x = 0;
    if (c.bounds_h > vh) c.y = clamp_i(c.y, 0, static_cast<int16_t>(c.bounds_h - vh));
    else                  c.y = 0;
    if (c.x < 0) c.x = 0;
    if (c.y < 0) c.y = 0;
}

void cam_move(Camera& c, int16_t dx, int16_t dy, int16_t vw, int16_t vh) {
    cam_follow(c, static_cast<int16_t>(c.x + dx + vw / 2),
                  static_cast<int16_t>(c.y + dy + vh / 2), vw, vh);
}

}  // namespace t8
