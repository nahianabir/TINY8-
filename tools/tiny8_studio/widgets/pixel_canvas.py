"""Tiny8 Studio — pixel-art canvas widget.

A small monochrome canvas for editing 1-bpp sprites.  Supports:

  * Pencil and eraser tools.
  * Configurable pixel zoom (1..16).
  * Optional grid overlay.
  * Clear canvas.
  * Get / set bit access for round-tripping with the engine.
  * Optional Pillow-based PNG import.

The widget is a plain tkinter.Canvas; each pixel is a small rectangle.
We avoid PhotoImage scaling so the canvas works without any image
library.
"""

from __future__ import annotations
import tkinter as tk
from typing import Callable, List, Optional, Tuple

from .. import theme as th


# Tools
TOOL_PENCIL = 1
TOOL_ERASER = 2


class PixelCanvas(tk.Frame):
    """A monochrome pixel-art editor."""

    def __init__(self, master, w: int = 8, h: int = 8,
                 on_change: Optional[Callable[[], None]] = None,
                 zoom: int = 8,
                 **kw):
        super().__init__(master, bg=th.BG_PANEL, **kw)
        # NOTE: do NOT name these `_w`/`_h` — that shadows tkinter's
        # internal widget id attribute and breaks the parent of any
        # child widget created later.
        self._pw = max(1, w)
        self._ph = max(1, h)
        self._zoom = max(1, min(16, zoom))
        self._show_grid = True
        self._tool = TOOL_PENCIL
        self._on_change = on_change or (lambda: None)
        self._bits: List[int] = [0] * ((self._pw + 7) // 8 * self._ph)
        self._cell_rects: List[List[int]] = []
        self._build()

    # --- public API --------------------------------------------------

    @property
    def w(self) -> int: return self._pw
    @property
    def h(self) -> int: return self._ph
    @property
    def bits(self) -> List[int]:
        return list(self._bits)
    @property
    def zoom(self) -> int: return self._zoom
    @property
    def show_grid(self) -> bool: return self._show_grid
    @property
    def tool(self) -> int: return self._tool

    def set_zoom(self, z: int) -> None:
        self._zoom = max(1, min(16, z))
        self._redraw_canvas()

    def set_tool(self, t: int) -> None:
        self._tool = t
        self._refresh_cursor()

    def toggle_grid(self) -> None:
        self._show_grid = not self._show_grid
        self._redraw_canvas()

    def clear(self) -> None:
        self._bits = [0] * ((self._pw + 7) // 8 * self._ph)
        self._redraw_pixels()
        self._notify()

    def resize(self, w: int, h: int) -> None:
        """Resize the canvas; preserves the top-left sub-region."""
        w = max(1, w); h = max(1, h)
        old = self._bits
        old_w, old_h = self._pw, self._ph
        new = [0] * ((w + 7) // 8 * h)
        cw = min((old_w + 7) // 8, (w + 7) // 8)
        for y in range(min(old_h, h)):
            old_row = y * ((old_w + 7) // 8)
            new_row = y * ((w + 7) // 8)
            for x in range(cw):
                new[new_row + x] = old[old_row + x]
        self._pw, self._ph = w, h
        self._bits = new
        self._redraw_canvas()

    def set_bits(self, bits: List[int]) -> None:
        expected = ((self._pw + 7) // 8) * self._ph
        if len(bits) != expected:
            raise ValueError(f"expected {expected} bytes, got {len(bits)}")
        self._bits = list(bits)
        self._redraw_pixels()
        self._notify()

    def set_pixel(self, x: int, y: int, on: bool) -> None:
        if not (0 <= x < self._pw and 0 <= y < self._ph):
            return
        row = (y >> 3)
        idx = row * ((self._pw + 7) // 8) + x
        bit = 0x80 >> (x & 7)
        if on:
            self._bits[idx] |= bit
        else:
            self._bits[idx] &= (~bit) & 0xFF
        self._update_cell(x, y)
        self._notify()

    def get_pixel(self, x: int, y: int) -> bool:
        if not (0 <= x < self._pw and 0 <= y < self._ph):
            return False
        idx = (y >> 3) * ((self._pw + 7) // 8) + x
        return bool(self._bits[idx] & (0x80 >> (x & 7)))

    # --- import -------------------------------------------------------

    def import_pbm(self, path: str) -> None:
        """Import a P4 PBM file.  Resizes the canvas if needed."""
        with open(path, "rb") as f:
            magic = f.readline().strip()
            if magic != b"P4":
                raise ValueError("not a P4 PBM file")
            line = f.readline()
            while line.startswith(b"#"):
                line = f.readline()
            w, h = (int(x) for x in line.split())
            data = f.read()
        expected = ((w + 7) // 8) * h
        if len(data) < expected:
            raise ValueError("truncated PBM")
        self._pw, self._ph = w, h
        self._bits = list(data[:expected])
        self._redraw_canvas()

    def try_import_png(self, path: str, threshold: int = 128) -> None:
        """Optional: requires Pillow.  Threshold -> monochrome."""
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            raise RuntimeError("PNG import requires Pillow (pip install Pillow)")
        img = Image.open(path).convert("L")
        if img.width > 32 or img.height > 32:
            raise ValueError(f"image {img.width}x{img.height} exceeds 32x32")
        self._pw, self._ph = img.width, img.height
        bits = [0] * ((self._pw + 7) // 8 * self._ph)
        for y in range(self._ph):
            for x in range(self._pw):
                v = img.getpixel((x, y))
                if v >= threshold:
                    idx = (y >> 3) * ((self._pw + 7) // 8) + x
                    bits[idx] |= (0x80 >> (x & 7))
        self._bits = bits
        self._redraw_canvas()

    # --- internals ----------------------------------------------------

    def _notify(self) -> None:
        try:
            self._on_change()
        except Exception:
            pass

    def _build(self) -> None:
        # Toolbar with zoom + grid controls.
        bar = tk.Frame(self, bg=th.BG_PANEL)
        bar.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=th.PAD_TIGHT)
        tk.Label(bar, text="Zoom", bg=th.BG_PANEL, fg=th.FG_DIM,
                 font=th.FONT_UI).pack(side=tk.LEFT)
        self._zoom_var = tk.IntVar(value=self._zoom)
        tk.Spinbox(bar, from_=1, to=16, width=3, textvariable=self._zoom_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO, command=self._on_zoom_spin).pack(side=tk.LEFT, padx=4)
        self._grid_var = tk.BooleanVar(value=self._show_grid)
        tk.Checkbutton(bar, text="Grid", variable=self._grid_var,
                      bg=th.BG_PANEL, fg=th.FG, selectcolor=th.BG_INPUT,
                      activebackground=th.BG_PANEL,
                      font=th.FONT_UI, command=self._on_grid_toggle).pack(side=tk.LEFT, padx=8)

        # Canvas itself, in a sunken frame.
        wrap = tk.Frame(self, bg=th.BORDER, bd=1)
        wrap.pack(side=tk.TOP, padx=th.PAD, pady=th.PAD_TIGHT)
        self._canvas = tk.Canvas(wrap, bg=th.BG_INPUT, highlightthickness=0,
                                 width=self._pw * self._zoom + 1,
                                 height=self._ph * self._zoom + 1)
        self._canvas.pack(padx=1, pady=1)
        self._canvas.bind("<Button-1>", self._on_canvas_click)
        self._canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self._redraw_canvas()

    def _on_zoom_spin(self) -> None:
        self.set_zoom(int(self._zoom_var.get()))

    def _on_grid_toggle(self) -> None:
        self._show_grid = bool(self._grid_var.get())
        self._redraw_canvas()

    def _refresh_cursor(self) -> None:
        cur = "pencil" if self._tool == TOOL_PENCIL else "dotbox"
        try:
            self._canvas.config(cursor=cur)
        except tk.TclError:
            pass

    def _redraw_canvas(self) -> None:
        self._canvas.config(width=self._pw * self._zoom + 1,
                            height=self._ph * self._zoom + 1)
        self._canvas.delete("all")
        self._cell_rects = [[0] * self._pw for _ in range(self._ph)]
        for y in range(self._ph):
            for x in range(self._pw):
                rx = x * self._zoom
                ry = y * self._zoom
                rid = self._canvas.create_rectangle(
                    rx, ry, rx + self._zoom, ry + self._zoom,
                    outline="", fill=th.PX_OFF, tags=("cell",))
                self._cell_rects[y][x] = rid
        self._redraw_pixels()
        if self._show_grid:
            self._draw_grid()

    def _draw_grid(self) -> None:
        z = self._zoom
        for x in range(self._pw + 1):
            self._canvas.create_line(x * z, 0, x * z, self._ph * z,
                                     fill=th.PX_GRID)
        for y in range(self._ph + 1):
            self._canvas.create_line(0, y * z, self._pw * z, y * z,
                                     fill=th.PX_GRID)

    def _redraw_pixels(self) -> None:
        for y in range(self._ph):
            for x in range(self._pw):
                self._update_cell(x, y)

    def _update_cell(self, x: int, y: int) -> None:
        rid = self._cell_rects[y][x]
        if rid == 0:
            return
        self._canvas.itemconfig(rid, fill=th.PX_ON if self.get_pixel(x, y) else th.PX_OFF)

    def _canvas_xy_to_cell(self, px: int, py: int) -> Tuple[int, int]:
        z = self._zoom
        return min(self._pw - 1, max(0, px // z)), min(self._ph - 1, max(0, py // z))

    def _on_canvas_click(self, ev):
        x, y = self._canvas_xy_to_cell(ev.x, ev.y)
        on = (self._tool == TOOL_PENCIL)
        self.set_pixel(x, y, on)

    def _on_canvas_drag(self, ev):
        x, y = self._canvas_xy_to_cell(ev.x, ev.y)
        on = (self._tool == TOOL_PENCIL)
        self.set_pixel(x, y, on)