// Tiny8 Engine — axis-aligned bounding boxes and clipping.
// Pure C++17, no Arduino headers.
#ifndef TINY8_RECT_H
#define TINY8_RECT_H

#include "tiny8_types.h"

namespace t8 {

// Inclusive/exclusive rect. (x,y) is top-left, (x+w-1,y+h-1) is bottom-right.
struct Rect {
    int16_t x;
    int16_t y;
    int16_t w;
    int16_t h;
};

static inline bool rect_empty(const Rect& r) {
    return r.w <= 0 || r.h <= 0;
}

// AABB overlap. Touching edges do not count as overlap.
static inline bool rect_overlap(const Rect& a, const Rect& b) {
    if (rect_empty(a) || rect_empty(b)) return false;
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
}

// AABB containment.
static inline bool rect_contains(const Rect& a, int16_t px, int16_t py) {
    return px >= a.x && px < a.x + a.w && py >= a.y && py < a.y + a.h;
}

// Compute the clipped intersection of `src` against `bounds`. If no overlap,
// result has w <= 0 or h <= 0.
static inline Rect rect_clip(const Rect& src, const Rect& bounds) {
    Rect r = src;
    if (r.x < bounds.x) { r.w -= static_cast<int16_t>(bounds.x - r.x); r.x = bounds.x; }
    if (r.y < bounds.y) { r.h -= static_cast<int16_t>(bounds.y - r.y); r.y = bounds.y; }
    int16_t rbx = static_cast<int16_t>(r.x + r.w);
    int16_t bbx = static_cast<int16_t>(bounds.x + bounds.w);
    if (rbx > bbx) r.w = static_cast<int16_t>(bbx - r.x);
    int16_t rby = static_cast<int16_t>(r.y + r.h);
    int16_t bby = static_cast<int16_t>(bounds.y + bounds.h);
    if (rby > bby) r.h = static_cast<int16_t>(bby - r.y);
    if (r.w < 0) r.w = 0;
    if (r.h < 0) r.h = 0;
    return r;
}

}  // namespace t8

#endif  // TINY8_RECT_H
