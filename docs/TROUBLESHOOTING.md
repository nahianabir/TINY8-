# Tiny8 Engine — Troubleshooting

## Build

### "avr/pgmspace.h: No such file or directory"

You're compiling on a non-AVR toolchain. The Tiny8 engine is designed for
`avr-g++` with the Arduino AVR core 1.8.x. Either:

- **Use Arduino CLI:** `arduino-cli compile --fqbn arduino:avr:uno …`
- **Use the Arduino IDE** with the Uno board selected.
- The host-only tests under `test/` deliberately compile on the PC without
  `avr/pgmspace.h` (the generated headers guard it with `#ifdef __AVR__`).

### "multiple definition of `hal_millis'"

You linked both `tiny8_hal_avr.cpp` and `tiny8_hal_host.cpp` into the
same binary. Use exactly one — `tiny8_hal_avr.cpp` for the device, the
host stub only for unit tests.

### Sketch uses > 28 KB Flash

You have too many assets. The sprite converter caps total PROGMEM at
28 672 B; reduce the number of frames in your sprite sheets, shrink tilemap
dimensions, or move rarely-used assets to a level-loaded buffer.

## Runtime (real Uno)

### Display is all-on or all-off

Check the contrast setting. `0x3F` is a safe default. The PCD8544 also
needs a reset pulse — confirm `rst` is wired to a GPIO and the initial
`pcd8544_make()` call wired it correctly.

### Display shows garbage on first frame

The PCD8544 needs the timing sequence in the right order. The
`drv_init()` function does this; if you bypass it, see the comments in
`src/display/tiny8_display_pcd8544.cpp`.

### Audio is silent

- Confirm `audio_set_enabled(true)` is called.
- Check the buzzer polarity — some piezo elements only sound on one
  polarity.
- Verify the pin is not used by another peripheral. The audio driver
  toggles the pin in software; if you also drive it with `tone()`, you
  will get contention.

### Buttons register double-presses

The `input_poll()` debounce is intentionally light (single-frame edge
detection). If your buttons bounce, add a 5–10 ms RC filter on each
input, or extend `tiny8_input.cpp` to track a per-button debounce
counter.

## Memory

### "Sketch uses 99% of SRAM" in the IDE

The framebuffer alone is **504 B**, plus ~330 B of engine state. With
the demo game, expect ~834 B. The 99% warning is conservative — your
code is fine as long as you don't allocate dynamic structures.

If you exceed it:

- Reduce `T8_MAX_ENTITIES` (each entity is 16 B).
- Reduce `T8_INPUT_BUTTONS` if you have fewer buttons.
- Use `PROGMEM` (the `const` qualifier + F() macro) for any string
  literal.
- Make sure you have **no `String` objects** — those pull in
  `malloc`-based heap and will fragment the tiny SRAM.

### "Low memory available, stability problems may occur"

This is a compiler warning when free SRAM after static allocation is
< 50 B. With Tiny8 the typical free SRAM is > 1 200 B, so the warning
is spurious. The check is conservative and assumes libc allocations
that Tiny8 does not perform.

## Tilemaps

### Tilemap renders wrong colors / wrong tiles

Check that the PBM has **even** width and height. The `--tilemap` mode
expects each 2×2 block to represent one tile. Odd dimensions cause an
error in the converter.

### Camera shows black borders

The camera clamps to world bounds, so the area outside the world is
left at 0. Fill those rows with the wall tile (id 1) by extending your
tilemap to cover the camera's full range.

## Conversions

### "asset size … exceeds PROGMEM budget"

The engine refuses to build an asset larger than 28 672 B total. Break
large atlases into smaller sheets, or use `tools/sprite_convert.py`'s
exit code 1 to fail fast in CI.

### PNG conversion produces a different-looking sprite

Use `magick assets/foo.png -threshold 50% -compress none` (no
dithering). With dithering, the converter sees a noisy PBM and the
result is blurry.

## Tests

### A host test fails on a fresh machine

Tiny8 tests have **no third-party dependencies** — only the Python
standard library. If a test fails, it's a real engine regression.
Open the test, find the assertion, and re-trace the C++ source.

### A host test passes but the demo crashes on hardware

The host tests exercise the *logic*. They don't exercise:

- SPI timing on the real bus.
- The Timer2 ISR for audio (different interrupt priority from the
  host's fake tick).
- Debounce on real buttons.

Check `docs/PINS.md` for wiring first, then re-read the `// PHYSICAL:`
comments in the C++ source for parts that need real-hardware verification.
