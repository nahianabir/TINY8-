// Tiny8 Engine — tilemap (1 byte per tile, 2 px per tile minimum).
// Designed for top-down or platformer backgrounds.  Tiles are referenced
// by an 8-bit id; the engine treats ids 0..1 as the two built-in tile
// glyphs (grass/wall for the demo) but in general the user supplies a
// 16-element tile palette (one Sprite per id).
//
// The full tilemap is stored in PROGMEM; only the camera + the visible
// 14×6-tile window are kept in SRAM.

#ifndef TINY8_TILEMAP_H
#define TINY8_TILEMAP_H

#include <stdint.h>
#include "tiny8_types.h"
#include "tiny8_camera.h"

namespace t8 {

// Map definition.  Pass `tiles` pointing into PROGMEM.
struct TileMap {
    const uint8_t* tiles;     // PROGMEM; map_w * map_h entries
    uint16_t map_w;
    uint16_t map_h;
    uint8_t  tile_px;         // tile edge length in pixels (e.g. 8)
};

// Compute the camera-clipped rectangle of tiles currently visible, in
// tile-space.  The result has w <= 14 and h <= 6 for a 84x48 screen.
struct TileView {
    int16_t tx0, ty0;        // first visible tile
    int16_t tx1, ty1;        // one past last
    int16_t px0, py0;        // pixel offset of the first tile (may be negative)
};

// Maximum tiles on screen for the reference 84x48 display at 8px tiles.
static constexpr int16_t T8_VIEW_TW = (REF_W + 7) / 8 + 1;   // 12
static constexpr int16_t T8_VIEW_TH = (REF_H + 7) / 8 + 1;   //  7

void tilemap_view(const TileMap& m, const Camera& cam, TileView& v);

#ifdef __AVR__
#include <avr/pgmspace.h>
#define T8_TILE(m, x, y)  pgm_read_byte(&(m).tiles[(y) * (m).map_w + (x)])
#else
#define T8_TILE(m, x, y)  ((m).tiles[(y) * (m).map_w + (x)])
#endif

// Render the visible region of `m` into `fb`, using the supplied tile
// palette (an array of 16 Sprite*).  Tiles with id >= palette_size are
// drawn as solid 8x8 blocks.
struct Sprite;

void tilemap_draw(Framebuffer& fb, const TileMap& m, const Camera& cam,
                  const Sprite* const* palette, uint8_t palette_size);

}  // namespace t8

#endif  // TINY8_TILEMAP_H
