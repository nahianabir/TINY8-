// Tiny8 Engine — scrolling camera.
// Holds world-space (x, y) in pixels with optional dead-zone. The engine
// blits the tilemap shifted by -cam.x, -cam.y so the camera appears to
// follow an entity.
//
// SRAM: 6 bytes per Camera.
#ifndef TINY8_CAMERA_H
#define TINY8_CAMERA_H

#include "tiny8_types.h"
#include "tiny8_rect.h"

namespace t8 {

struct Camera {
    int16_t x;       // world-space top-left
    int16_t y;
    int16_t bounds_w;  // world width in pixels
    int16_t bounds_h;  // world height
};

// Initialise. bounds_w/h may be 0 for "no clamp".
void cam_init(Camera& c, int16_t bounds_w, int16_t bounds_h);

// Snap the camera to a target point, applying clamping against bounds.
void cam_follow(Camera& c, int16_t target_x, int16_t target_y,
                int16_t view_w, int16_t view_h);

// Translate by (dx, dy) with clamping. Used for free-scroll.
void cam_move(Camera& c, int16_t dx, int16_t dy, int16_t view_w, int16_t view_h);

}  // namespace t8

#endif  // TINY8_CAMERA_H
