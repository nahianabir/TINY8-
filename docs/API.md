# Tiny8 Engine — API Reference

> **Include from your sketch:**
> ```cpp
> #include "tiny8_engine.h"
> ```
>
> For the asset formats the studio emits (`.anim.json`, multi-layer
> tilemap PBMs), see [`STUDIO.md`](STUDIO.md).

All public symbols live in the `t8` namespace.

## Engine lifecycle

```cpp
void t8::display_register(const DisplayDriver& d);
void t8::display_init();
void t8::display_flush(const Framebuffer& fb);
void t8::display_set_contrast(uint8_t v);
void t8::display_power(bool on);
```

The reference display is the PCD8544. Wire it like this:

```cpp
t8::Pcd8544Pins pins{/*clk*/13, /*din*/11, /*ce*/9, /*dc*/8, /*rst*/7, /*bl*/5};
t8::display_register(t8::pcd8544_make(pins));
t8::display_init();
t8::display_set_contrast(0x3F);
```

## Main loop

```cpp
t8::Framebuffer fb;
t8::fb_init(fb);
t8::StepClock  clk;
t8::stepclock_init(clk, 16);   // 60 Hz

t8::input_init();              // default Uno pin map
t8::scene_init();

void loop() {
    uint8_t n = t8::stepclock_poll(clk);
    t8::input_poll();
    for (uint8_t i = 0; i < n; ++i) t8::scene_update();
    if (n > 0) {
        t8::scene_draw(fb);
        t8::display_flush(fb);
    }
}
```

## Framebuffer primitives

```cpp
void t8::fb_clear(Framebuffer& fb);
void t8::fb_set_pixel(Framebuffer& fb, int16_t x, int16_t y, bool on);
void t8::fb_draw_hline(Framebuffer& fb, int16_t x, int16_t y, int16_t w, bool on);
void t8::fb_draw_vline(Framebuffer& fb, int16_t x, int16_t y, int16_t h, bool on);
void t8::fb_draw_rect (Framebuffer& fb, const Rect& r, bool on);
void t8::fb_fill_rect (Framebuffer& fb, const Rect& r, bool on);
void t8::fb_blit      (Framebuffer& fb, int16_t x, int16_t y,
                        uint8_t w, uint8_t h,
                        const uint8_t* bits, uint16_t stride_bytes,
                        bool transparent);
void t8::fb_draw_char (Framebuffer& fb, int16_t x, int16_t y, char c, bool on);
void t8::fb_draw_text (Framebuffer& fb, int16_t x, int16_t y, const char* s, bool on);
```

## Sprites

A `Sprite` is a 1-bpp bitmap in PROGMEM. Convert PNG → PBM → header with
`tools/sprite_convert.py`.

```cpp
t8::fb_blit_sprite(fb, x, y, my_sprite, /*transparent=*/true);
t8::fb_blit_sub   (fb, x, y, atlas, src_x0, src_y0, w, h, true);
```

## Animation

```cpp
const uint8_t FRAMES[] PROGMEM = { 0, 1, 2, 1 };   // 4 frames
const t8::Anim idle_anim = {
    &atlas, FRAMES, /*count=*/4, /*ticks_per_frame=*/6, /*loop=*/true
};
t8::AnimPlayer p;
t8::anim_play(p, idle_anim);
t8::anim_tick(p);
t8::anim_draw(fb, x, y, p, true);
```

## Tilemaps

```cpp
t8::TileMap map{ kDemoTiles, kDemoMapW, kDemoMapH, /*tile_px=*/8 };
t8::tilemap_draw(fb, map, cam, kDemoPalette, /*palette_size=*/2);
```

## Camera

```cpp
t8::Camera cam;
t8::cam_init(cam, world_w_px, world_h_px);
t8::cam_follow(cam, target_x_px, target_y_px, view_w_px, view_h_px);
```

## Entities

```cpp
t8::Entity ents[T8_MAX_ENTITIES];
t8::ent_init(ents);

t8::Entity* p = t8::ent_alloc(ents);
p->x = 16 * t8::T8_SUB; p->y = 8 * t8::T8_SUB;
p->w = 8; p->h = 8;
p->flags = t8::EF_ACTIVE | t8::EF_SOLID | t8::EF_PLAYER;
p->sprite = &kPLAYER_Sprite;

t8::ent_apply_gravity(*p, /*g_sub=*/8);
t8::ent_move(ents, *p, world_w, world_h);
t8::ent_pickup_scan(ents, on_pickup, nullptr);
```

## Scenes

```cpp
static void menu_enter(t8::Scene& s) { /* … */ }
static void menu_exit (t8::Scene& s) { /* … */ }
static void menu_update(t8::Scene& s) { /* … */ }
static void menu_draw  (t8::Scene& s, t8::Framebuffer& fb) { /* … */ }

t8::scene_init();
t8::scene_push(t8::scene_make(1, nullptr, menu_enter, menu_exit,
                              menu_update, menu_draw));
```

## Audio

```cpp
t8::audio_init(/*buzzer_pin=*/6);
t8::audio_set_enabled(true);
t8::audio_beep(880, 40);   // 880 Hz for 40 ms

// Music tracks live in PROGMEM, each entry is (note_id, duration_ticks).
const uint8_t kTrack[] PROGMEM = { 45, 4, 47, 4, 50, 8, 0xFF, 0 };
t8::audio_play(kTrack);
```

Call `t8::audio_tick()` once per fixed step. Note id 0xFE = rest, 0xFF = end.

## Saves (EEPROM)

```cpp
uint8_t data[3] = { 0x03, 0x05, 0x00 };   // lives, score, flags
t8::save_write(0, data, 3);
t8::Err err = t8::save_read(0, data, 3);
if (err == t8::Err::Ok) { /* … */ }
```

Each slot is 16 B; 4 slots use 64 B of EEPROM.

## Input

```cpp
t8::input_init();
void loop() {
    t8::input_poll();
    if (t8::input_pressed(t8::BTN_A))  { /* A just pressed */ }
    if (t8::input_held  (t8::BTN_LEFT)){ /* D-pad left held */ }
}
```

## Compile-time limits

Override the defaults in `src/core/tiny8_types.h` or via build flags:

| Macro | Default | Notes |
|---|---:|---|
| `T8_MAX_ENTITIES` | 8 | entity pool size |
| `T8_MAX_ANIM` | 4 | anim players |
| `T8_MAX_SCENES` | 4 | scene stack depth |
| `T8_INPUT_BUTTONS` | 6 | button count |
| `T8_SAVE_SLOTS` | 4 | EEPROM save slots |
| `T8_SAVE_BYTES` | 16 | bytes per slot |

## Asset file formats

### Sprite (PBM P4)

- 1 bit per pixel, MSB-first within each byte.
- Width and height each ≤ 32 (engine limit).
- `tools/sprite_convert.py sprite.pbm --out generated/`
  → `generated/sprite.h` with `kSPRITE_W`, `kSPRITE_H`, `kSPRITE_Stride`,
  `kSPRITE_Bits[]` (PROGMEM on AVR), and a ready-to-use `kSPRITE_Sprite`.

### Tilemap (PBM P4 with `--tilemap`)

- 2×2 source pixels per tile; the top-left pixel of each 2×2 block
  encodes the tile id (0 or 1 in the demo).
- `tools/sprite_convert.py tilemap.pbm --tilemap --name demo --out gen/`
  → `gen/demo_map.h` with `kDEMOMapW`, `kDEMOMapH`, `kDEMOTiles[]`.

### Sprite sheet (atlas)

A wide PBM holding N frames side by side, each 8 px wide. Use
`fb_blit_sub(fb, x, y, atlas, src_x0, src_y0, w, h, true)` to draw a
single frame.
