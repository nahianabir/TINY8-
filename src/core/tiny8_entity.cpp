#include "tiny8_entity.h"

namespace t8 {

void ent_init(Entity ents[]) {
    for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
        ents[i].flags = 0;
        ents[i].sprite = nullptr;
    }
}

void ent_clear(Entity ents[]) { ent_init(ents); }

Entity* ent_alloc(Entity ents[]) {
    for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
        if (!(ents[i].flags & EF_ACTIVE)) {
            ents[i].flags = EF_ACTIVE;
            ents[i].x = ents[i].y = 0;
            ents[i].vx = ents[i].vy = 0;
            ents[i].tag = 0;
            return &ents[i];
        }
    }
    return nullptr;
}

void ent_free(Entity ents[], Entity* e) {
    if (!e) return;
    e->flags = 0;
    e->sprite = nullptr;
}

int16_t ent_px_x(const Entity& e) { return static_cast<int16_t>(e.x / T8_SUB); }
int16_t ent_px_y(const Entity& e) { return static_cast<int16_t>(e.y / T8_SUB); }

Rect ent_aabb(const Entity& e) {
    Rect r;
    r.x = ent_px_x(e);
    r.y = ent_px_y(e);
    r.w = e.w;
    r.h = e.h;
    return r;
}

void ent_apply_gravity(Entity& e, int16_t g) {
    if (e.flags & EF_GRAVITY) {
        e.vy = static_cast<int16_t>(e.vy + g);
        // Cap to terminal velocity.
        if (e.vy > 240) e.vy = 240;
        if (e.vy < -240) e.vy = -240;
    }
}

Entity* ent_move(Entity ents[], Entity& e, int16_t world_w, int16_t world_h) {
    // X axis first.
    e.x = static_cast<int16_t>(e.x + e.vx);
    if (e.x < 0) e.x = 0;
    if (e.x + e.w * T8_SUB > world_w * T8_SUB) e.x = static_cast<int16_t>(world_w * T8_SUB - e.w * T8_SUB);
    Entity* hit_x = nullptr;
    if (e.flags & EF_SOLID) {
        Rect a = ent_aabb(e);
        for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
            Entity& o = ents[i];
            if (&o == &e) continue;
            if (!(o.flags & EF_ACTIVE) || !(o.flags & EF_SOLID)) continue;
            if (rect_overlap(a, ent_aabb(o))) { hit_x = &o; break; }
        }
    }
    if (hit_x) { e.x = static_cast<int16_t>(e.x - e.vx); e.vx = 0; }

    e.y = static_cast<int16_t>(e.y + e.vy);
    if (e.y < 0) e.y = 0;
    if (e.y + e.h * T8_SUB > world_h * T8_SUB) e.y = static_cast<int16_t>(world_h * T8_SUB - e.h * T8_SUB);
    Entity* hit_y = nullptr;
    if (e.flags & EF_SOLID) {
        Rect a = ent_aabb(e);
        for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
            Entity& o = ents[i];
            if (&o == &e) continue;
            if (!(o.flags & EF_ACTIVE) || !(o.flags & EF_SOLID)) continue;
            if (rect_overlap(a, ent_aabb(o))) { hit_y = &o; break; }
        }
    }
    if (hit_y) { e.y = static_cast<int16_t>(e.y - e.vy); e.vy = 0; }

    return hit_x ? hit_x : hit_y;
}

uint8_t ent_collide_all(Entity ents[], EntHitFn on_hit, void* user) {
    uint8_t n = 0;
    for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
        Entity& a = ents[i];
        if (!(a.flags & EF_ACTIVE)) continue;
        Rect ra = ent_aabb(a);
        for (uint8_t j = i + 1; j < T8_MAX_ENTITIES; ++j) {
            Entity& b = ents[j];
            if (!(b.flags & EF_ACTIVE)) continue;
            if (rect_overlap(ra, ent_aabb(b))) {
                on_hit(a, b, user);
                if (++n == 255) return n;
            }
        }
    }
    return n;
}

uint8_t ent_pickup_scan(Entity ents[], EntHitFn on_hit, void* user) {
    uint8_t n = 0;
    for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
        Entity& a = ents[i];
        if (!(a.flags & EF_ACTIVE) || !(a.flags & EF_PLAYER)) continue;
        Rect ra = ent_aabb(a);
        for (uint8_t j = 0; j < T8_MAX_ENTITIES; ++j) {
            Entity& b = ents[j];
            if (&a == &b) continue;
            if (!(b.flags & EF_ACTIVE) || !(b.flags & EF_PICKUP)) continue;
            if (rect_overlap(ra, ent_aabb(b))) {
                on_hit(a, b, user);
                if (++n == 255) return n;
            }
        }
    }
    return n;
}

}  // namespace t8