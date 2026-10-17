// Tiny8 Engine — entity pool, AABB collision, lightweight movers.
// Each entity owns: position (sub-pixel), velocity, hitbox, sprite ptr,
// and an 8-bit user tag.  No dynamic allocation.  Up to T8_MAX_ENTITIES.

#ifndef TINY8_ENTITY_H
#define TINY8_ENTITY_H

#include <stdint.h>
#include "tiny8_types.h"
#include "tiny8_rect.h"
#include "tiny8_sprite.h"

namespace t8 {

// Entity flags.
static constexpr uint8_t EF_ACTIVE   = 0x01;
static constexpr uint8_t EF_SOLID    = 0x02;   // blocks movement of other solids
static constexpr uint8_t EF_GRAVITY  = 0x04;
static constexpr uint8_t EF_ENEMY    = 0x08;
static constexpr uint8_t EF_PICKUP   = 0x10;
static constexpr uint8_t EF_PLAYER   = 0x20;

struct Entity {
    int16_t       x, y;       // sub-pixel position
    int16_t       vx, vy;     // sub-pixel velocity per step
    uint8_t       w, h;       // hitbox size in pixels
    uint8_t       flags;
    const Sprite* sprite;     // PROGMEM
    uint8_t       tag;        // user-defined
};

// Static pool.
void     ent_init(Entity ents[]);
Entity*  ent_alloc(Entity ents[]);   // returns inactive slot or nullptr
void     ent_free (Entity ents[], Entity* e);
void     ent_clear(Entity ents[]);

// Convert between sub-pixel and pixel coordinates; the "position" is the
// entity's top-left pixel; we add half-hitbox for collision conversions.
int16_t  ent_px_x(const Entity& e);  // pixel-space left
int16_t  ent_px_y(const Entity& e);
Rect     ent_aabb(const Entity& e);

// Apply gravity if EF_GRAVITY is set. v_pixel is given per step.
void     ent_apply_gravity(Entity& e, int16_t g_sub);

// Move the entity by its velocity, clamping to world bounds.  If `solid`
// is true and another solid entity blocks the destination, the move is
// reduced to the largest non-colliding delta along each axis separately
// (axis-separated slide).  Returns the Entity* that was hit (or nullptr).
Entity*  ent_move(Entity ents[], Entity& e, int16_t world_w, int16_t world_h);

// For each active entity, test overlap with all others; report
// collisions via the supplied callback (max 4 collisions per entity per
// step; more are ignored).  Returns the number of collisions found.
typedef void (*EntHitFn)(Entity& a, Entity& b, void* user);
uint8_t   ent_collide_all(Entity ents[], EntHitFn on_hit, void* user);

// Pickup scan: for each active entity with EF_PLAYER, test against every
// EF_PICKUP entity; on contact, call on_hit(player, pickup, user).
uint8_t   ent_pickup_scan(Entity ents[], EntHitFn on_hit, void* user);

}  // namespace t8

#endif  // TINY8_ENTITY_H