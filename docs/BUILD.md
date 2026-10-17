# Tiny8 Engine — Build & Flash

> **Note** — the engine builds without any PC tools.  For an
> optional lightweight GUI that manages projects, edits assets, and
> invokes the build, see [`STUDIO.md`](STUDIO.md) and
> [`../tools/tiny8_studio/README.md`](../tools/tiny8_studio/README.md).

## Prerequisites

- **Hardware**: Arduino Uno R3, PCD8544/Nokia 5110 display, 6 buttons
  (UP/DOWN/LEFT/RIGHT/A/START), piezo buzzer, breadboard + jumpers.
  See `PINS.md` for wiring.
- **Toolchain**: Arduino CLI ≥ 0.32, or Arduino IDE 1.8.x / 2.x.
  - Arduino AVR core 1.8.x
  - (Optional) `arduino-cli` for command-line builds.

## Build (command line)

```bash
# Install the AVR core (one-time).
arduino-cli core update-index
arduino-cli core install arduino:avr

# Compile only (no upload). Output goes to /tmp/build.
arduino-cli compile \
    --fqbn arduino:avr:uno \
    --build-path /tmp/build \
    --libraries <your sketchbook>/libraries \
    demo/tiny8_demo.ino

# The resulting .hex is at /tmp/build/demo/tiny8_demo.ino.hex.
```

## Flash

```bash
# Plug in the Uno and find its port.
arduino-cli board list

# Upload.
arduino-cli upload -p <COMx or /dev/ttyUSBx> --fqbn arduino:avr:uno \
    --input-dir /tmp/build demo/tiny8_demo.ino
```

If you prefer `avrdude` directly:

```bash
avrdude -p m328p -c arduino -P <port> -b 115200 \
        -U flash:w:/tmp/build/demo/tiny8_demo.ino.hex
```

## Build (Arduino IDE)

1. Copy the `src/` tree and the `demo/` tree into a single folder named
   `tiny8_demo/`.
2. Open `tiny8_demo/tiny8_demo.ino` in the IDE.
3. Select **Tools → Board → Arduino Uno**.
4. Click **Upload**.

## Host-only tests (no hardware)

```bash
# All milestones.
python test/run_all.py

# Individual milestones.
python test/test_m1_core.py
python test/test_m2_framebuffer.py
python test/test_m4_tilemap.py
python test/test_m5_entity.py
python test/test_m6_scene.py
python test/test_m7_audio.py
python test/test_m8_save.py
python test/test_m9_converter.py
python test/test_m10_demo.py
```

## Asset pipeline

```bash
# 1. Generate the demo PBM source files (one-time).
python tools/make_demo_assets.py

# 2. Convert to PROGMEM C++ headers.
python tools/sprite_convert.py \
    assets/player_idle.pbm assets/coin.pbm assets/enemy.pbm \
    assets/tile_grass.pbm assets/tile_wall.pbm \
    --out generated

python tools/sprite_convert.py assets/tilemap_demo.pbm \
    --tilemap --name demo --out generated
```

This produces `generated/player_idle.h`, `coin.h`, `enemy.h`,
`tile_grass.h`, `tile_wall.h`, and `demo_map.h`. They are referenced
from `demo/demo_assets.h`.

To convert a PNG sprite to PBM (with ImageMagick):

```bash
magick assets/foo.png -threshold 50% -compress none assets/foo.pbm
```

## Flash budget check (post-build)

After `arduino-cli compile`, look at the IDE's "Sketch uses …" line or
read the build log. The Tiny8 engine + Tiny8 Quest demo should land at
~19 KB of Flash (leaving >10 KB free for the bootloader and any extra
features).

## Memory budget

| Region | Used | Limit |
|---|---:|---:|
| Flash (engine + demo) | ~19 KB | 32 KB |
| SRAM (framebuffer + state) | ~834 B | 2 048 B |
| EEPROM (save slots) | ≤ 64 B | 1 024 B |

Stack headroom after the engine init: **> 1 200 B** (verified in
`test/test_m1_core.py` and `test/test_m2_framebuffer.py`).
