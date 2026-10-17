# Tiny8 Studio

Tiny8 Studio is a lightweight desktop GUI for authoring Tiny8 engine
games on the development PC.  The engine itself is unchanged; the
studio is a separate Python package under `tools/tiny8_studio/` that
emits the same PROGMEM headers the command-line converter produces.

> **Scope** — the studio is a productivity layer, not a host runtime.
> It does not run the engine's 60 Hz loop on the desktop, does not
> emulate audio, and does not draw to the actual PCD8544.  See the
> [Host simulation](#host-simulation) section for what it *does*
> do and what it *doesn't*.

## Architecture

```
   ┌────────────────────────────┐
   │     tools/tiny8_studio/    │
   ├────────────────────────────┤
   │  app.py            Tk root │
   │  project.py        disk IO │
   │  assets.py         registry│
   │  validation.py     budgets │
   │  exporters.py  ─── uses ───┐
   │  animation.py        C++  │
   │  simulate.py       engine │
   │  widgets/         framebuf│
   │    sprite_editor  mirror   │
   │    tilemap_editor          │
   │    animation_editor        │
   │    asset_browser           │
   │    diagnostics             │
   │    pixel_canvas            │
   │    preview                 │
   └────────────────────────────┘
                  │
                  ▼  (no engine import)
   ┌────────────────────────────┐
   │      tools/sprite_convert  │  (CLI, std-lib only)
   │      src/                  │  (engine C++ source)
   └────────────────────────────┘
```

The studio is **fully decoupled from `src/`**.  Removing the entire
`tools/tiny8_studio/` directory does not affect the engine, the
converter, or the demo game.  Similarly, the studio never imports
`src/` — it ships its own Python mirrors of the framebuffer, blit,
font, and step clock in `tools/tiny8_studio/simulate.py` so the
host-side preview is testable without a compiler.

## Project layout

A Tiny8 project is just a folder:

```
MyGame/
├── project.t8p     # JSON: name, fqbn, build command, etc.
├── src/            # user C++ source files (your .ino)
├── assets/         # PBM sprite art + .anim.json
└── generated/      # PROGMEM headers produced by the studio
```

`project.t8p` schema:

| Field         | Type   | Default                                                |
|---------------|--------|--------------------------------------------------------|
| `name`        | string | folder name                                            |
| `board`       | string | `uno`                                                  |
| `fqbn`        | string | `arduino:avr:uno`                                      |
| `build_cmd`   | string | `arduino-cli compile --fqbn {fqbn} --build-path {build_path} {sketch}` |
| `build_path`  | string | `build`                                                |
| `sketch`      | string | `src/main.ino`                                         |
| `extra`       | object | free-form metadata                                     |

The studio creates a starter `src/main.ino` for new projects that
includes `tiny8_engine.h` and demonstrates `stepclock_init` /
`fb_init`.  Edit it to register your display, audio, and scenes.

## Editor features

### Sprite editor

- Pencil / eraser / clear.
- Import from PBM (binary 1-bpp, the engine's format) or PNG
  (via Pillow, optional).
- 1–16× zoom, configurable grid.
- Per-sprite Flash cost and budget warning in the status bar.
- Save to `assets/<name>.pbm`.

### Tilemap editor (multi-layer)

- Sprite-sheet picker with selectable frame size (1–16 px).
- Up to **4 stacked layers** (ground, props, overlay, fx).  The user
  picks the active layer in the layer panel; the map canvas shows
  all layers composited.
- Paint / erase / drag to fill rectangles.
- Save produces a 2x2-packed PBM per layer: `<name>_L0.pbm`,
  `<name>_L1.pbm`, etc.  The browser shows a single multi-layer
  asset; the exporter writes one map header per layer so the user
  can stack `t8::TileMap layers[4];` in their sketch.

**Pixel preview:** the sheet canvas blits the actual sheet pixels
(1 bpp, white on black) and the selected-tile pane shows the chosen
tile at 1× and 4× so the user can see what they are placing.

### Animation editor

- Loads a sprite sheet (atlas) as the frame source.
- Configurable frame size (1–32 × 1–32 px).
- Click frames in the atlas to append them to the sequence.
- Per-frame list with Add / Insert / Remove / Up / Down.
- `ticks_per_frame` and `loop` toggle.
- Host-side playback at a chosen FPS (1–60).  The same framebuffer
  the engine uses is the rendering target.
- Saves to `assets/<name>.anim.json`; on export the studio emits a
  C++ `<name>.anim.h` containing `t8::Anim k{N}Anim` and the frame
  index array in PROGMEM.  The user includes both
  `<atlas>.h` and `<name>.anim.h` in their sketch.

## Asset formats

| Extension   | Recognised as       | Notes                              |
|-------------|---------------------|------------------------------------|
| `.pbm`      | sprite              | P4 binary, 1 bpp, MSB-first        |
| `.pbm` + `<name>.map.txt` | tilemap  | 2x2 packed, top-left pixel = id    |
| `<name>_L<n>.pbm`        | multi-layer tilemap layer | suffix `_L0.._L3`     |
| `.anim.json`| animation           | See schema below                   |
| `.h`        | generated header    | Listed in browser as `source`       |
| `.png`      | sprite (import)     | Optional Pillow                    |

### `.anim.json` schema (version 1)

```json
{
  "version": 1,
  "atlas": "player_atlas",
  "frame_w": 8,
  "frame_h": 8,
  "ticks_per_frame": 6,
  "loop": true,
  "frames": [0, 1, 2, 1]
}
```

`atlas` is the **basename** of the sprite sheet's C++ header
(no extension).  The exporter produces
`k{atlas.upper()}_Sprite` (matching the engine's own converter) and
`k{N}_Anim`.  See `src/core/tiny8_anim.h` for the engine struct.

## Host simulation

The preview pane can run a real step-clock loop on the desktop.
When you click **Simulate**, the studio:

1. Initialises a 504-byte framebuffer (`sim.Framebuffer`).
2. Starts a `StepClock` with `step_ms = 16` (the engine's cadence).
3. Each host tick (every 16 ms via `tk.after`):
   - Drains the step clock (up to 4 catch-up steps, matching the
     engine's anti-spiral cap).
   - Advances the simulation time, the sprite's x position, and the
     animation frame index.
   - Calls a draw callback (default: a moving sprite + border +
     `fb_draw_text` overlay) that uses the same `fb_blit` /
     `fb_blit_sprite` the engine uses on the Uno.
   - Renders the resulting framebuffer into a 3×-scaled Tk canvas.
   - Captures a fake PCD8544 flush (1 SET_Y byte + 1 SET_X byte +
     504 data bytes = 506 B) and shows the length and a 1-byte
     hash in the status label.

The simulation is **not** a real-time emulator.  The Tk `after`
callback can drift, the 16 ms cadence is honoured when the host is
fast enough, and audio is not modelled.  The user cannot trust it
to validate timing — only the visual output.

A user-supplied draw callback is supported via
`PreviewPane.set_draw_callback(cb)`.  The callback receives the
`sim.Framebuffer` and the simulation time in ms.

## Keyboard shortcuts

| Shortcut | Action               |
|----------|----------------------|
| Ctrl+N   | New project          |
| Ctrl+O   | Open project         |
| Ctrl+S   | Open sprite editor   |
| Ctrl+T   | Open tilemap editor  |
| Ctrl+A   | Open animation editor|
| Ctrl+E   | Export PROGMEM       |
| Ctrl+B   | Build                |
| Ctrl+Q   | Quit                 |

## Build & diagnostics

`Build ▸ Build` (Ctrl+B) runs the configured build command.  The
studio:

1. Re-exports PROGMEM first, so the build sees the latest assets.
2. Streams stdout/stderr to the diagnostics pane.
3. Parses Arduino CLI's `Sketch uses 12345 bytes (38%) of 32256
   bytes` and `Global variables use 1234 bytes...` lines.
4. Warns (yellow) when SRAM usage exceeds 75% of the budget and
   errors (red) when Flash exceeds 95% of the user's configured
   `MAX_PROGMEM_BYTES` (28 KB by default, matching the engine's
   `tiny8_config.h`).

## What the studio is *not*

- **Autotile / 16-bit tile selection.**  Use Tiled or LDTk and
  export a 2x2-packed PBM.
- **Frame-by-frame pixel editing inside the animation editor.**
  Frames are picked from an existing sheet; the sprite editor is
  the right tool to author individual frames.
- **True 60 Hz hardware emulation.**  The simulation runs as fast
  as the host Tk loop, not at the Uno's 16 ms cadence.  Audio and
  button debounce are not modelled.
- **Coupled to the engine.**  Removing `tools/tiny8_studio/` does
  not change `src/`, the converter, or the demo game.  The studio
  reads the same PBM and outputs the same PROGMEM headers the
  command-line converter does.

## Testing

```bash
# Unit tests (headless, no Tk event loop).
python tools/tiny8_studio/tests/test_tiny8_studio.py

# End-to-end smoke test: builds the App, exercises create →
# edit-sprite → save → export → multi-layer-tilemap → animation
# → host simulation → build-not-found.
python tools/tiny8_studio/tests/smoke_app.py
```

29 unit tests cover project lifecycle, validation limits, exporter
round-trips, animation format round-trip, multi-layer discovery and
export, and parity with the engine's own Python test mirrors
(`test_m2_framebuffer.py`).
