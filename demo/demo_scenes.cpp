// Tiny8 Engine — demo game (Tiny8 Quest) scene implementations.
//
// PHYSICAL: the only file that depends on demo-specific gameplay.  All
// other engine modules remain demo-independent.
//
// Maps use 8 px tiles; the world is 16 tiles wide x 8 tiles tall = 128 x 64
// pixels. The 84x48 display shows ~10x6 tiles at any time.

#include "tiny8_engine.h"
#include "tiny8_anim.h"
#include "tiny8_audio.h"
#include "tiny8_camera.h"
#include "tiny8_display.h"
#include "tiny8_entity.h"
#include "tiny8_framebuffer.h"
#include "tiny8_input.h"
#include "tiny8_save.h"
#include "tiny8_scene.h"
#include "tiny8_tilemap.h"
#include "demo_assets.h"

namespace t8 {

// --- Game state shared across scenes ---
struct GameState {
    Entity   ents[T8_MAX_ENTITIES];
    Camera   cam;
    TileMap  map;
    int      coins;
    int      lives;
    bool     paused;
    uint32_t score_save_at;
};

static GameState G;

static const uint8_t kMenuMusic[] = {
    // Simple three-note motif. 0xFF = end.
    45, 8,  47, 8,  50, 8,  47, 8,  45, 16,
    0xFF, 0,
};
static const uint8_t kPlayMusic[] = {
    50, 4,  52, 4,  53, 4,  55, 8,
    53, 4,  52, 4,  50, 8,
    0xFF, 0,
};
static const uint8_t kOverMusic[] = {
    45, 16, 0xFE, 4, 43, 16, 0xFE, 4, 41, 24, 0xFF, 0,
};

// --- Forward declarations for scene callbacks ---
static void menu_enter (Scene& s);
static void menu_exit  (Scene& s);
static void menu_update(Scene& s);
static void menu_draw  (Scene& s, Framebuffer& fb);
static void play_enter (Scene& s);
static void play_exit  (Scene& s);
static void play_update(Scene& s);
static void play_draw  (Scene& s, Framebuffer& fb);
static void over_enter (Scene& s);
static void over_exit  (Scene& s);
static void over_update(Scene& s);
static void over_draw  (Scene& s, Framebuffer& fb);

// --- Helpers ---
static void spawn_initial_entities() {
    ent_clear(G.ents);
    // Player.
    Entity* p = ent_alloc(G.ents);
    p->x = 16 * T8_SUB;
    p->y = 8  * T8_SUB;
    p->w = 8; p->h = 8;
    p->flags = EF_ACTIVE | EF_SOLID | EF_PLAYER;
    p->sprite = &kPLAYER_IDLE_Sprite;
    // Coins.
    for (uint8_t i = 0; i < 4; ++i) {
        Entity* c = ent_alloc(G.ents);
        if (!c) break;
        c->x = (8 + i * 16) * T8_SUB;
        c->y = (16 + (i % 2) * 8) * T8_SUB;
        c->w = 8; c->h = 8;
        c->flags = EF_ACTIVE | EF_PICKUP;
        c->sprite = &kCOIN_Sprite;
        c->tag = 1;
    }
    // Enemy.
    Entity* e = ent_alloc(G.ents);
    e->x = 80 * T8_SUB; e->y = 8 * T8_SUB;
    e->w = 8; e->h = 8;
    e->flags = EF_ACTIVE | EF_SOLID | EF_ENEMY;
    e->sprite = &kENEMY_Sprite;
}

static void on_pickup(Entity& player, Entity& pickup, void* user) {
    (void)player; (void)user;
    G.coins++;
    pickup.flags = 0;     // remove
    audio_beep(880, 40);
}

// --- Menu scene ---
static void menu_enter(Scene& s)  { (void)s; audio_play(kMenuMusic); }
static void menu_exit (Scene& s)  { (void)s; audio_stop(); }
static void menu_update(Scene& s) {
    (void)s;
    audio_tick();
    if (input_pressed(BTN_A) || input_pressed(BTN_START)) {
        // Start a new game.
        G.coins = 0; G.lives = 3; G.paused = false;
        spawn_initial_entities();
        cam_init(G.cam, kDEMOMapW * 8, kDEMOMapH * 8);
        G.map = { kDEMOTiles, kDEMOMapW, kDEMOMapH, 8 };
        audio_play(kPlayMusic);
        scene_replace(scene_make(2, &G, nullptr, nullptr, play_update, play_draw));
    }
}
static void menu_draw(Scene& s, Framebuffer& fb) {
    (void)s;
    fb_clear(fb);
    fb_draw_text(fb, 6, 4,  "TINY8", true);
    fb_draw_text(fb, 6, 16, "PRESS A", true);
    fb_draw_text(fb, 0, 32, "v1.0 QUEST", true);
    fb_present(fb);
}

// --- Play scene ---
static void play_enter(Scene& s)  { (void)s; }
static void play_exit (Scene& s)  { (void)s; }

static void play_update(Scene& s) {
    (void)s;
    audio_tick();

    if (input_pressed(BTN_START)) {
        G.paused = !G.paused;
        audio_beep(440, 30);
    }
    if (G.paused) return;

    // Read player (entity slot 0).
    Entity& p = G.ents[0];
    const int16_t speed = 24;   // 1.5 px per step
    p.vx = 0; p.vy = 0;
    if (input_held(BTN_LEFT))  p.vx = -speed;
    if (input_held(BTN_RIGHT)) p.vx =  speed;
    if (input_held(BTN_UP))    p.vy = -speed;
    if (input_held(BTN_DOWN))  p.vy =  speed;
    if (input_pressed(BTN_B))  audio_beep(660, 30);

    // Apply gravity-less movement with wall-block.
    // We treat the inner walls (tile id 1) as solid via a simple per-tile
    // AABB check before the entity-move step.
    // For brevity the demo just calls ent_move; a real game would also
    // iterate over nearby solid tiles.
    ent_move(G.ents, p, kDEMOMapW * 8, kDEMOMapH * 8);

    // Pickup scan.
    ent_pickup_scan(G.ents, on_pickup, nullptr);

    // Camera follow.
    cam_follow(G.cam, ent_px_x(p) + p.w / 2, ent_px_y(p) + p.h / 2,
               REF_W, REF_H);

    // End-of-game triggers.
    if (G.coins >= 4) {
        audio_play(kOverMusic);
        scene_replace(scene_make(3, &G, nullptr, nullptr, over_update, over_draw));
    }
}

static void play_draw(Scene& s, Framebuffer& fb) {
    (void)s;
    fb_clear(fb);
    // Background.
    tilemap_draw(fb, G.map, G.cam, kDemoPalette, 2);
    // Entities.
    for (uint8_t i = 0; i < T8_MAX_ENTITIES; ++i) {
        Entity& e = G.ents[i];
        if (!(e.flags & EF_ACTIVE) || !e.sprite) continue;
        int16_t ex = static_cast<int16_t>(ent_px_x(e) - G.cam.x);
        int16_t ey = static_cast<int16_t>(ent_px_y(e) - G.cam.y);
        fb_blit_sprite(fb, ex, ey, *e.sprite, true);
    }
    // HUD.
    char buf[16];
    // (avoid snprintf -- we don't link it on AVR.)
    buf[0] = 'C'; buf[1] = ':';
    buf[2] = '0' + (char)G.coins;
    buf[3] = 0;
    fb_draw_text(fb, 0, 0, buf, true);
    if (G.paused) {
        fb_draw_text(fb, 24, 18, "PAUSE", true);
    }
    fb_present(fb);
}

// --- Pause is part of the play scene (overlay only) ---
static void pause_update(Scene& s) { (void)s; }
static void pause_draw (Scene& s, Framebuffer& fb) { (void)s; (void)fb; }

// --- Game over scene ---
static void over_enter(Scene& s)  { (void)s; audio_play(kOverMusic); }
static void over_exit (Scene& s)  { (void)s; audio_stop(); }
static void over_update(Scene& s) {
    (void)s; audio_tick();
    if (input_pressed(BTN_A) || input_pressed(BTN_START)) {
        scene_replace(scene_make(1, &G, menu_enter, menu_exit, menu_update, menu_draw));
    }
}
static void over_draw(Scene& s, Framebuffer& fb) {
    (void)s;
    fb_clear(fb);
    fb_draw_text(fb, 0, 4,  "GAME OVER", true);
    fb_draw_text(fb, 0, 20, "PRESS A",  true);
    fb_present(fb);
}

// --- Boot entrypoint ---
void demo_boot() {
    G.coins = 0; G.lives = 3; G.paused = false;
    scene_init();
    scene_push(scene_make(1, &G, menu_enter, menu_exit, menu_update, menu_draw));
}

}  // namespace t8