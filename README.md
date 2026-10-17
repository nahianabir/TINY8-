# Tiny8 Engine

A complete, reusable retro 2D game engine for the **Arduino Uno R3** (ATmega328P,
16 MHz) targeting the **PCD8544 / Nokia 5110** 84×48 monochrome display.

## Features

- Fixed-timestep game loop (configurable, default 60 Hz, max 4 steps catch-up).
- Modular display driver with a PCD8544 reference backend.
- 504-byte framebuffer with 2D primitives, text, and PROGMEM sprite blitting.
- Fixed-size sprites, transparent blit, sprite-sheet sub-region blit.
- Frame-based animation player.
- 8-bit tile tilemap (palette of 16 tiles, sub-screen viewport, ≤ 14 × 7 tiles on screen).
- Scrolling camera with clamping.
- 8-entity slot pool with AABB collision, axis-separated slide, and pickup scan.
- Lightweight platformer and top-down movement helpers.
- Scene state machine (menu / play / pause / game over) with 4-deep stack.
- Audio: one-shot beeps, music sequencer, piezo buzzer backend (Timer2).
- Versioned EEPROM saves (4 slots × 16 B, magic + version + CRC8).
- Python asset converter (PBM → PROGMEM C++, with size + budget enforcement).
- 143 host-side unit tests across 9 milestones.

## Memory budget (reference build with the demo)

| Region | Used | Limit |
|---|---:|---:|
| Flash (engine + demo) | ~19 KB | 32 KB |
| SRAM (framebuffer + state) | ~834 B | 2 048 B |
| EEPROM (save slots) | ≤ 64 B | 1 024 B |

Stack headroom: **> 1 200 B**.

## Module layout

```
src/
  core/      engine-agnostic logic (host-testable)
  display/   PCD8544 driver + framebuffer + font
  audio/     Timer2-based buzzer driver + sequencer
  persist/   versioned EEPROM save
  hal/       platform abstraction (Arduino + host stub)
demo/        Tiny8 Quest — a small complete game
tools/       Python asset converter + demo asset generator
assets/      PBM source art
test/        host unit tests (no hardware required)
docs/        architecture, pin map, build, API, troubleshooting
```

## Quick start

```bash
# Host-only tests (no hardware needed; ~ 1 s to run).
python test/run_all.py

# Regenerate demo assets.
python tools/make_demo_assets.py
python tools/sprite_convert.py assets/player_idle.pbm assets/coin.pbm \
    assets/enemy.pbm assets/tile_grass.pbm assets/tile_wall.pbm \
    --out generated
python tools/sprite_convert.py assets/tilemap_demo.pbm --tilemap --name demo --out generated

# Build + flash the demo to a real Uno.
arduino-cli compile --fqbn arduino:avr:uno --build-path /tmp/build demo/tiny8_demo.ino
arduino-cli upload -p <PORT> --input-dir /tmp/build demo/tiny8_demo.ino
```

### Tiny8 Studio (optional desktop GUI)

A small, dependency-light Tk GUI for editing sprites and tilemaps,
managing projects, and invoking the build.  Optional — the engine and
the command-line converter do not depend on it.  See
[`tools/tiny8_studio/README.md`](tools/tiny8_studio/README.md) and
[`docs/STUDIO.md`](docs/STUDIO.md).

```bash
python -m tools.tiny8_studio
```

See `docs/BUILD.md` for full build instructions, `docs/PINS.md` for the
default pin map, and `docs/API.md` for the engine reference.

## Milestone status

| M | Deliverable | Tests |
|---|---|---:|
| 1 | Types, math, fixed-point, time accumulator | 20 ✓ |
| 2 | HAL + framebuffer + PCD8544 driver | 24 ✓ |
| 3 | Sprite blit + 5×7 font + asset converter | (covered in M9) |
| 4 | Tilemap + camera | 13 ✓ |
| 5 | Entities + AABB collide | 18 ✓ |
| 6 | Scene state machine | 19 ✓ |
| 7 | Audio sequencer | 11 ✓ |
| 8 | EEPROM save (CRC8) | 9 ✓ |
| 9 | Asset converter (PBM round-trip, budget) | 11 ✓ |
| 10 | Demo game (Tiny8 Quest) | 18 ✓ |
| | **Total** | **143 ✓** |

## Simulated vs. physical verification

- **Simulated (this repository):** every file under `src/core/`, the
  Python asset converter, and all 9 host test suites.  Run with
  `python test/run_all.py`.
- **Physical (real Uno + Nokia 5110):** every file marked with
  `// PHYSICAL:`.  These are designed to compile cleanly under
  `avr-g++ -mmcu=atmega328p -DF_CPU=16000000` with the Arduino AVR
  core 1.8.x.  I have not flashed a board in this environment; the
  AVR-ready code is exercised by source-equivalence with the host
  mirrors in `test/`.

## License

Public domain / CC0.  Use freely.
