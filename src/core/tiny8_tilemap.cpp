#include "tiny8_tilemap.h"
#include "tiny8_sprite.h"
#include "tiny8_framebuffer.h"

namespace t8 {

void tilemap_view(const TileMap& m, const Camera& cam, TileView& v) {
    if (m.tile_px == 0) { v.tx0 = v.ty0 = v.tx1 = v.ty1 = 0; v.px0 = v.py0 = 0; return; }
    const int16_t tp = static_cast<int16_t>(m.tile_px);
    v.tx0 = static_cast<int16_t>(cam.x / tp);
    v.ty0 = static_cast<int16_t>(cam.y / tp);
    v.tx1 = static_cast<int16_t>((cam.x + REF_W + tp - 1) / tp);
    v.ty1 = static_cast<int16_t>((cam.y + REF_H + tp - 1) / tp);
    if (v.tx0 < 0) v.tx0 = 0;
    if (v.ty0 < 0) v.ty0 = 0;
    if (v.tx1 > static_cast<int16_t>(m.map_w)) v.tx1 = static_cast<int16_t>(m.map_w);
    if (v.ty1 > static_cast<int16_t>(m.map_h)) v.ty1 = static_cast<int16_t>(m.map_h);
    v.px0 = static_cast<int16_t>(v.tx0 * tp - cam.x);
    v.py0 = static_cast<int16_t>(v.ty0 * tp - cam.y);
}

void tilemap_draw(Framebuffer& fb, const TileMap& m, const Camera& cam,
                  const Sprite* const* palette, uint8_t palette_size) {
    TileView v;
    tilemap_view(m, cam, v);
    const int16_t tp = static_cast<int16_t>(m.tile_px);
    for (int16_t ty = v.ty0; ty < v.ty1; ++ty) {
        for (int16_t tx = v.tx0; tx < v.tx1; ++tx) {
            const uint8_t id = T8_TILE(m, tx, ty);
            const int16_t dx = static_cast<int16_t>(v.px0 + (tx - v.tx0) * tp);
            const int16_t dy = static_cast<int16_t>(v.py0 + (ty - v.ty0) * tp);
            if (id < palette_size && palette[id] != nullptr) {
                fb_blit_sprite(fb, dx, dy, *palette[id], true);
            } else {
                // Solid block fallback.
                Rect r{dx, dy, tp, tp};
                fb_fill_rect(fb, r, true);
            }
        }
    }
}

}  // namespace t8
