# Tiny8 Studio

A lightweight desktop GUI for the [Tiny8 game engine](../../README.md).
It runs on the development PC, not on the Arduino.

The studio is **strictly optional** — the engine, the command-line
asset converter, and the demo game all work without it.  When you do
use the studio, the engine source itself is untouched; the studio is a
separate package under `tools/tiny8_studio/`.

For the full feature list, scope, and limitations, see
[`docs/STUDIO.md`](../../docs/STUDIO.md).

## Constraints

- **Python 3.10+** with the standard library only.
- **Tkinter** is part of the standard library on Windows / macOS; on
  Debian/Ubuntu install `python3-tk`.
- **Pillow** is *optional* — only required for PNG import.  If missing,
  the GUI shows a clear message and PBM import still works.
- No electron, no Qt, no web server.  Startup is < 1 s on a typical
  laptop.  Idle RAM is < 60 MB.

## Install (optional Pillow)

```bash
pip install Pillow
```

## Run

```bash
# From the project root.
python -m tools.tiny8_studio
# or
python tools/tiny8_studio/__main__.py
```

A sample project (with a multi-layer tilemap and an animation) is one
command away:

```bash
python tools/tiny8_studio/tests/make_sample_project.py sample_project
python -m tools.tiny8_studio
# File ▸ Open Project… → choose the sample_project folder
```

## Features (summary)

1. **Project Manager** — new / open / close / build on disk.
2. **Sprite Editor** — pencil / eraser, 1–16× zoom, grid, PNG
   import (with Pillow), PBM export.
3. **Tilemap Editor** — sprite-sheet picker, multi-layer maps (up to
   4 layers, with selected-tile preview at 1× and 4×), paint /
   erase / drag, per-layer save.
4. **Animation Editor** — pick frames from a sheet to build a
   `t8::Anim` sequence; play back at a chosen FPS on the host;
   export to a C++ `Anim` header.
5. **Asset Browser** — sprites, sheets, tilemaps, audio, animations,
   and generated headers; inline preview and Flash budget.
6. **Game Preview** — native, scaled, and a **host simulation** that
   runs the engine's framebuffer and blit code, with a captured
   PCD8544-flush byte stream.
7. **Build & Diagnostics** — runs the configured command, parses
   Arduino CLI's Sketch-uses / Global-variables lines, and warns
   when the Flash budget is exceeded.

See [`docs/STUDIO.md`](../../docs/STUDIO.md) for the in-depth
description of each feature, the project file format, the
keyboard shortcuts, and the explicit list of what the studio does
*not* do.

## Testing

```bash
python tools/tiny8_studio/tests/test_tiny8_studio.py
python tools/tiny8_studio/tests/smoke_app.py
```

The unit suite is fully headless.  The smoke test constructs the App
in a temporary `Tk()` root and exercises create-project → edit-sprite
→ save → scan → export → multi-layer-tilemap → animation → host
simulation → build-not-found.
