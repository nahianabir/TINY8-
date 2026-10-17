"""Tiny8 Studio — tilemap editor with multi-layer support.

A grid-based map editor that uses an imported sprite sheet (atlas) as
the tile source.  Tiles are placed by selecting a tile and clicking
on the map.  Supports up to `MAX_LAYERS` stacked layers, each saved
to its own 2x2-packed PBM plus a `.map.txt` marker so the converter
treats them as separate tilemaps.

Engine layout:

  TileMap layers[3];   // declared in the user's sketch
  tilemap_draw(fb, layers[i], cam, palette, palette_size);

The editor saves `<name>_L0.pbm`, `<name>_L1.pbm`, etc.  No autotile
yet — that is documented as future work in the studio README.
"""

from __future__ import annotations
import os
import tkinter as tk
import tkinter.simpledialog
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

from .. import theme as th
from ..validation import (
    MAX_MAP_W, MAX_MAP_H, MAX_TILE_IDS,
    validate_tilemap, issues_have_error,
)


SHEET_PALETTE: List[str] = [
    "#3A3D43", "#5B7CFA", "#34D399", "#FBBF24",
    "#F87171", "#A78BFA", "#22D3EE", "#F472B6",
    "#94A3B8", "#FB923C", "#10B981", "#E879F9",
    "#7DD3FC", "#FACC15", "#84CC16", "#F43F5E",
]

MAX_LAYERS = 4
LAYER_NAMES_DEFAULT = ["ground", "props", "overlay", "fx"]


class TilemapEditor(tk.Frame):
    def __init__(self, master,
                 on_save: Optional[Callable[[str, List[int], int, int], None]] = None,
                 **kw):
        super().__init__(master, bg=th.BG, **kw)
        self._on_save = on_save
        # Sheet.
        self._sheet_path: Optional[str] = None
        self._sheet_w = self._sheet_h = 0
        self._sheet_bits: List[int] = []
        self._sheet_zoom = 4
        # Tile size.
        self._tile_w = self._tile_h = 8
        # Map size and per-layer data.
        self._map_w = 16
        self._map_h = 8
        self._layers: List[List[int]] = [
            [0] * (self._map_w * self._map_h) for _ in range(MAX_LAYERS)
        ]
        self._layer_count = 3
        self._active_layer = 0
        self._selected_tile = 0
        self._file: Optional[str] = None
        self._dirty = False
        self._zoom = 8
        self._build()
        self._refresh_status()

    # --- layout -------------------------------------------------------

    def _build(self) -> None:
        # Top controls.
        top = tk.Frame(self, bg=th.BG)
        top.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=th.PAD)
        tk.Button(top, text="Open sprite sheet…", command=self._on_open_sheet,
                  **self._btn_kw()).pack(side=tk.LEFT)
        self._sheet_lbl = tk.Label(top, text="(no sheet)", bg=th.BG,
                                   fg=th.FG_DIM, font=th.FONT_UI)
        self._sheet_lbl.pack(side=tk.LEFT, padx=8)

        tk.Frame(top, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Label(top, text="Tile W", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT)
        self._tw_var = tk.IntVar(value=self._tile_w)
        tk.Spinbox(top, from_=1, to=16, width=3, textvariable=self._tw_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Label(top, text="H", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT, padx=(6,0))
        self._th_var = tk.IntVar(value=self._tile_h)
        tk.Spinbox(top, from_=1, to=16, width=3, textvariable=self._th_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Apply", command=self._on_apply_tile_size,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)

        tk.Frame(top, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Label(top, text="Map W", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT)
        self._mw_var = tk.IntVar(value=self._map_w)
        tk.Spinbox(top, from_=1, to=MAX_MAP_W, width=4, textvariable=self._mw_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Label(top, text="H", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT, padx=(6,0))
        self._mh_var = tk.IntVar(value=self._map_h)
        tk.Spinbox(top, from_=1, to=MAX_MAP_H, width=4, textvariable=self._mh_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Resize", command=self._on_resize_map,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)

        # Body: sheet | map+selected | layers.
        body = tk.Frame(self, bg=th.BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                  padx=th.PAD, pady=th.PAD)

        # Sheet.
        sheet_outer = tk.LabelFrame(body, text="Sheet (click to pick tile)",
                                     bg=th.BG_PANEL, fg=th.FG, font=th.FONT_UI_B)
        sheet_outer.pack(side=tk.LEFT, fill=tk.Y)
        self._sheet_canvas = tk.Canvas(sheet_outer, bg=th.BG_INPUT,
                                        highlightthickness=0, width=200, height=200)
        self._sheet_canvas.pack(padx=4, pady=4)
        self._sheet_canvas.bind("<Button-1>", self._on_sheet_click)
        zrow = tk.Frame(sheet_outer, bg=th.BG_PANEL)
        zrow.pack(fill=tk.X, padx=4, pady=(0, 4))
        tk.Label(zrow, text="Zoom", bg=th.BG_PANEL, fg=th.FG_DIM,
                 font=th.FONT_UI).pack(side=tk.LEFT)
        self._zoom_var = tk.IntVar(value=self._sheet_zoom)
        for z in (1, 2, 4, 8, 16):
            tk.Radiobutton(zrow, text=f"{z}x", variable=self._zoom_var, value=z,
                          bg=th.BG_PANEL, fg=th.FG, selectcolor=th.BG_INPUT,
                          activebackground=th.BG_PANEL,
                          indicatoron=False, font=th.FONT_UI,
                          command=self._on_zoom_change).pack(side=tk.LEFT, padx=2)

        # Map + selected-tile preview.
        map_col = tk.Frame(body, bg=th.BG)
        map_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        map_frame = tk.LabelFrame(map_col, text="Map", bg=th.BG_PANEL,
                                   fg=th.FG, font=th.FONT_UI_B)
        map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._map_canvas = tk.Canvas(map_frame, bg=th.BG_INPUT,
                                      highlightthickness=0)
        self._map_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._map_canvas.bind("<Button-1>", self._on_map_click)
        self._map_canvas.bind("<B1-Motion>", self._on_map_drag)
        sel_outer = tk.LabelFrame(map_col, text="Selected tile",
                                    bg=th.BG_PANEL, fg=th.FG, font=th.FONT_UI_B)
        sel_outer.pack(side=tk.TOP, fill=tk.X, pady=(8, 0))
        self._sel_canvas_1x = tk.Canvas(sel_outer, bg=th.BG_INPUT,
                                          highlightthickness=0, width=64, height=32)
        self._sel_canvas_1x.pack(side=tk.LEFT, padx=4, pady=4)
        self._sel_canvas_4x = tk.Canvas(sel_outer, bg=th.BG_INPUT,
                                          highlightthickness=0, width=64 * 4,
                                          height=32 * 4)
        self._sel_canvas_4x.pack(side=tk.LEFT, padx=4, pady=4)
        self._sel_lbl = tk.Label(sel_outer, text="tile 0", bg=th.BG_PANEL,
                                  fg=th.FG_DIM, font=th.FONT_MONO)
        self._sel_lbl.pack(side=tk.LEFT, padx=8)

        # Layers column.
        layers_frame = tk.LabelFrame(body, text="Layers", bg=th.BG_PANEL,
                                      fg=th.FG, font=th.FONT_UI_B)
        layers_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        ltop = tk.Frame(layers_frame, bg=th.BG_PANEL)
        ltop.pack(fill=tk.X, padx=4, pady=4)
        tk.Button(ltop, text="+ Layer", command=self._on_add_layer,
                  **self._btn_kw()).pack(side=tk.LEFT)
        tk.Button(ltop, text="-", command=self._on_remove_layer,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)
        self._layers_list = tk.Listbox(layers_frame, bg=th.BG_INPUT, fg=th.FG,
                                        selectbackground=th.ACCENT,
                                        selectforeground=th.FG_ON_ACC,
                                        relief=tk.FLAT, bd=0,
                                        font=th.FONT_MONO, height=8,
                                        activestyle="dotbox")
        self._layers_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._layers_list.bind("<<ListboxSelect>>", self._on_layer_select)
        self._refresh_layers_list()

        # Bottom: status + save.
        bot = tk.Frame(self, bg=th.BG)
        bot.pack(side=tk.BOTTOM, fill=tk.X, padx=th.PAD, pady=th.PAD)
        self._status = tk.Label(bot, text="", bg=th.BG, fg=th.FG_DIM,
                                font=th.FONT_UI, anchor=tk.W)
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._save_btn = tk.Button(bot, text="Save layers", command=self._on_save_click,
                                   state=tk.DISABLED, **self._btn_kw(accent=True))
        self._save_btn.pack(side=tk.RIGHT)

        self._redraw_map()

    def _btn_kw(self, accent: bool = False) -> dict:
        return dict(
            bg=th.ACCENT if accent else th.BG_RAISED,
            fg=th.FG_ON_ACC if accent else th.FG,
            activebackground=th.ACCENT_DARK if accent else th.BG_HOVER,
            activeforeground=th.FG_ON_ACC if accent else th.FG,
            relief=tk.FLAT, bd=0, padx=10, pady=4, font=th.FONT_UI,
        )

    # --- public API ---------------------------------------------------

    def current_path(self) -> Optional[str]:
        return self._file

    def current_size(self) -> tuple[int, int]:
        return self._map_w, self._map_h

    def current_layers(self) -> List[List[int]]:
        return [list(layer) for layer in self._layers[:self._layer_count]]

    def load_file(self, pbm_path: str) -> None:
        try:
            with open(pbm_path, "rb") as f:
                magic = f.readline().strip()
                if magic != b"P4":
                    raise ValueError("not a P4 PBM")
                line = f.readline()
                while line.startswith(b"#"):
                    line = f.readline()
                w, h = (int(x) for x in line.split())
                data = f.read()
            if w % 2 or h % 2:
                raise ValueError("tilemap source must have even w and h")
            tw, th = w // 2, h // 2
            bits = list(data[:((w + 7) // 8) * h])
            tiles = []
            for ty in range(th):
                for tx in range(tw):
                    sx = tx * 2
                    sy = ty * 2
                    row = sy * ((w + 7) // 8)
                    bit = 0x80 >> (sx & 7)
                    tiles.append(1 if (bits[row + (sx >> 3)] & bit) else 0)
            self._map_w, self._map_h = tw, th
            self._mw_var.set(tw)
            self._mh_var.set(th)
            for i in range(MAX_LAYERS):
                self._layers[i] = [0] * (tw * th)
            self._layers[0] = tiles
            self._layer_count = 3
            self._file = pbm_path
            self._dirty = False
            self._refresh_layers_list()
            self._redraw_map()
            self._refresh_selected_tile()
            self._refresh_status()
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def load_layers(self, base_path: str) -> bool:
        base, _ = os.path.splitext(base_path)
        loaded = 0
        for i in range(MAX_LAYERS):
            path = f"{base}_L{i}.pbm"
            if not os.path.isfile(path):
                self._layers[i] = [0] * (self._map_w * self._map_h)
                continue
            try:
                with open(path, "rb") as f:
                    magic = f.readline().strip()
                    if magic != b"P4":
                        continue
                    line = f.readline()
                    while line.startswith(b"#"):
                        line = f.readline()
                    w, h = (int(x) for x in line.split())
                    data = f.read()
                if w % 2 or h % 2:
                    continue
                tw, th = w // 2, h // 2
                bits = list(data[:((w + 7) // 8) * h])
                tiles = []
                for ty in range(th):
                    for tx in range(tw):
                        sx = tx * 2; sy = ty * 2
                        row = sy * ((w + 7) // 8)
                        bit = 0x80 >> (sx & 7)
                        tiles.append(1 if (bits[row + (sx >> 3)] & bit) else 0)
                if (tw, th) != (self._map_w, self._map_h):
                    if loaded == 0:
                        self._map_w, self._map_h = tw, th
                        self._mw_var.set(tw)
                        self._mh_var.set(th)
                        for j in range(MAX_LAYERS):
                            self._layers[j] = [0] * (tw * th)
                self._layers[i] = tiles
                loaded += 1
            except Exception:
                continue
        if loaded > 0:
            self._file = base_path
            self._dirty = False
            self._refresh_layers_list()
            self._redraw_map()
            self._refresh_selected_tile()
            self._refresh_status()
            return True
        return False

    def mark_clean(self) -> None:
        self._dirty = False
        self._refresh_status()

    # --- handlers -----------------------------------------------------

    def _on_open_sheet(self) -> None:
        path = filedialog.askopenfilename(
            title="Open sprite sheet (PBM)",
            filetypes=[("PBM bitmap", "*.pbm"), ("All files", "*.*")],
        )
        if not path:
            return
        if self._load_sheet(path):
            self._dirty = True
            self._refresh_sheet()
            self._refresh_selected_tile()
            self._refresh_status()

    def _load_sheet(self, path: str) -> bool:
        try:
            with open(path, "rb") as f:
                f.readline()
                line = f.readline()
                while line.startswith(b"#"):
                    line = f.readline()
                w, h = (int(x) for x in line.split())
                data = f.read()
            row_bytes = (w + 7) // 8
            expected = row_bytes * h
            if len(data) < expected:
                raise ValueError("truncated sheet")
        except Exception as e:
            messagebox.showerror("Sheet load failed", str(e))
            return False
        self._sheet_path = path
        self._sheet_w = w
        self._sheet_h = h
        self._sheet_bits = list(data[:expected])
        self._sheet_lbl.config(text=os.path.basename(path), fg=th.FG)
        return True

    def _on_zoom_change(self) -> None:
        self._sheet_zoom = max(1, min(16, int(self._zoom_var.get())))
        self._refresh_sheet()

    def _on_apply_tile_size(self) -> None:
        try:
            tw = int(self._tw_var.get()); th = int(self._th_var.get())
        except tk.TclError:
            return
        if not (1 <= tw <= 16 and 1 <= th <= 16):
            messagebox.showerror("Tile size", "Tile size must be 1..16")
            return
        self._tile_w, self._tile_h = tw, th
        self._refresh_sheet()
        self._refresh_selected_tile()
        self._redraw_map()
        self._refresh_status()

    def _on_resize_map(self) -> None:
        try:
            w = int(self._mw_var.get()); h = int(self._mh_var.get())
        except tk.TclError:
            return
        if not (1 <= w <= MAX_MAP_W and 1 <= h <= MAX_MAP_H):
            messagebox.showerror("Map size",
                f"Map must be 1..{MAX_MAP_W} x 1..{MAX_MAP_H}")
            return
        for i in range(MAX_LAYERS):
            new = [0] * (w * h)
            for y in range(min(self._map_h, h)):
                for x in range(min(self._map_w, w)):
                    new[y * w + x] = self._layers[i][y * self._map_w + x]
            self._layers[i] = new
        self._map_w, self._map_h = w, h
        self._dirty = True
        self._redraw_map()
        self._refresh_status()

    def _on_sheet_click(self, ev) -> None:
        if not self._sheet_bits:
            return
        z = self._sheet_zoom
        sx = ev.x // z
        sy = ev.y // z
        if sx < 0 or sy < 0:
            return
        tw = self._tile_w; th = self._tile_h
        if sx >= self._sheet_w: sx = self._sheet_w - 1
        if sy >= self._sheet_h: sy = self._sheet_h - 1
        cols = self._sheet_w // tw
        self._selected_tile = max(0, min(MAX_TILE_IDS - 1,
                                          (sy // th) * cols + (sx // tw)))
        self._refresh_sheet()
        self._refresh_selected_tile()
        self._refresh_status()

    def _on_map_click(self, ev) -> None:
        self._paint_at_event(ev)

    def _on_map_drag(self, ev) -> None:
        self._paint_at_event(ev)

    def _paint_at_event(self, ev) -> None:
        z = self._zoom
        tx = ev.x // z
        ty = ev.y // z
        if 0 <= tx < self._map_w and 0 <= ty < self._map_h:
            layer = self._layers[self._active_layer]
            layer[ty * self._map_w + tx] = self._selected_tile
            self._dirty = True
            self._redraw_map()
            self._refresh_status()

    # --- layers -------------------------------------------------------

    def _refresh_layers_list(self) -> None:
        self._layers_list.delete(0, tk.END)
        for i in range(self._layer_count):
            name = LAYER_NAMES_DEFAULT[i] if i < len(LAYER_NAMES_DEFAULT) else f"L{i}"
            self._layers_list.insert(tk.END, f"  {i}: {name}")
        if self._layer_count > 0:
            self._layers_list.selection_clear(0, tk.END)
            self._layers_list.selection_set(self._active_layer)

    def _on_layer_select(self, _ev) -> None:
        sel = self._layers_list.curselection()
        if not sel:
            return
        self._active_layer = int(sel[0])
        self._redraw_map()
        self._refresh_selected_tile()
        self._refresh_status()

    def _on_add_layer(self) -> None:
        if self._layer_count >= MAX_LAYERS:
            return
        self._layer_count += 1
        self._layers[self._layer_count - 1] = [0] * (self._map_w * self._map_h)
        self._active_layer = self._layer_count - 1
        self._dirty = True
        self._refresh_layers_list()
        self._redraw_map()
        self._refresh_status()

    def _on_remove_layer(self) -> None:
        if self._layer_count <= 1:
            return
        i = self._layer_count - 1
        self._layers[i] = [0] * (self._map_w * self._map_h)
        self._layer_count -= 1
        if self._active_layer >= self._layer_count:
            self._active_layer = self._layer_count - 1
        self._dirty = True
        self._refresh_layers_list()
        self._redraw_map()
        self._refresh_status()

    # --- save ---------------------------------------------------------

    def _on_save_click(self) -> None:
        if self._file is None:
            base = filedialog.asksaveasfilename(
                title="Save tilemap layers (base path)",
                defaultextension=".pbm",
                filetypes=[("PBM bitmap", "*.pbm")],
            )
            if not base:
                return
            self._file = base
        base = self._file
        for i in range(MAX_LAYERS):
            suffix = f"_L{i}.pbm"
            if base.endswith(suffix):
                base = base[: -len(suffix)] + ".pbm"
                break
        try:
            for i in range(self._layer_count):
                path = base[: -len(".pbm")] + f"_L{i}.pbm"
                self._write_layer(path, self._layers[i])
                marker = os.path.splitext(path)[0] + ".map.txt"
                with open(marker, "w", encoding="utf-8") as f:
                    f.write("tilemap\n")
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return
        self._dirty = False
        self._refresh_status()
        if self._on_save:
            self._on_save(self._file, self._layers[self._active_layer],
                          self._map_w, self._map_h)

    def _write_layer(self, path: str, tiles: List[int]) -> None:
        pw = self._map_w * 2
        ph = self._map_h * 2
        row_bytes = (pw + 7) // 8
        data = bytearray(row_bytes * ph)
        for ty in range(self._map_h):
            for tx in range(self._map_w):
                tid = tiles[ty * self._map_w + tx]
                for dy in range(2):
                    for dx in range(2):
                        sx = tx * 2 + dx
                        sy = ty * 2 + dy
                        idx = sy * row_bytes + (sx >> 3)
                        bit = 0x80 >> (sx & 7)
                        if tid:
                            data[idx] |= bit
        with open(path, "wb") as f:
            f.write(f"P4\n{pw} {ph}\n".encode("ascii"))
            f.write(bytes(data))

    # --- drawing ------------------------------------------------------

    def _refresh_sheet(self) -> None:
        c = self._sheet_canvas
        c.delete("all")
        z = self._sheet_zoom
        if not self._sheet_bits:
            c.create_text(100, 100, text="(no sheet loaded)",
                          fill=th.FG_DIM, font=th.FONT_UI)
            c.config(width=200, height=200)
            return
        c.config(width=self._sheet_w * z + 2, height=self._sheet_h * z + 2)
        row_bytes = (self._sheet_w + 7) // 8
        # Blit the actual sheet pixels (not coloured swatches) so the
        # user sees what they are picking.
        for y in range(self._sheet_h):
            row = y * row_bytes
            for x in range(self._sheet_w):
                if self._sheet_bits[row + (x >> 3)] & (0x80 >> (x & 7)):
                    c.create_rectangle(x * z, y * z, (x + 1) * z, (y + 1) * z,
                                       outline="", fill=th.PX_ON)
        tw, th = self._tile_w, self._tile_h
        for ty in range(self._sheet_h // th):
            for tx in range(self._sheet_w // tw):
                c.create_rectangle(tx * tw * z, ty * th * z,
                                   (tx + 1) * tw * z, (ty + 1) * th * z,
                                   outline=th.PX_GRID)
        cols = self._sheet_w // tw
        if cols > 0:
            sx = (self._selected_tile % cols) * tw * z
            sy = (self._selected_tile // cols) * th * z
            c.create_rectangle(sx, sy,
                               sx + tw * z, sy + th * z,
                               outline=th.ACCENT, width=2)

    def _refresh_selected_tile(self) -> None:
        c1, c4 = self._sel_canvas_1x, self._sel_canvas_4x
        c1.delete("all"); c4.delete("all")
        if not self._sheet_bits:
            c1.create_text(32, 16, text="(none)", fill=th.FG_DIM, font=th.FONT_UI)
            return
        tw, th = self._tile_w, self._tile_h
        cols = max(1, self._sheet_w // tw)
        tx = self._selected_tile % cols
        ty = self._selected_tile // cols
        c1.config(width=tw, height=th)
        row_bytes = (self._sheet_w + 7) // 8
        for y in range(th):
            row = (ty * th + y) * row_bytes
            for x in range(tw):
                sx = tx * tw + x
                if self._sheet_bits[row + (sx >> 3)] & (0x80 >> (sx & 7)):
                    c1.create_rectangle(x, y, x + 1, y + 1,
                                        outline="", fill=th.PX_ON)
        scale = 4
        out_w = tw * scale
        out_h = th * scale
        c4.config(width=out_w, height=out_h)
        for y in range(th):
            row = (ty * th + y) * row_bytes
            for x in range(tw):
                sx = tx * tw + x
                if self._sheet_bits[row + (sx >> 3)] & (0x80 >> (sx & 7)):
                    c4.create_rectangle(x * scale, y * scale,
                                        (x + 1) * scale, (y + 1) * scale,
                                        outline="", fill=th.PX_ON)
        self._sel_lbl.config(text=f"tile {self._selected_tile}  "
                                  f"({tw}x{th})  layer L{self._active_layer}")

    def _redraw_map(self) -> None:
        c = self._map_canvas
        c.delete("all")
        z = self._zoom
        c.config(width=self._map_w * z + 1, height=self._map_h * z + 1)
        for layer_idx in range(self._layer_count):
            tiles = self._layers[layer_idx]
            for ty in range(self._map_h):
                for tx in range(self._map_w):
                    tid = tiles[ty * self._map_w + tx]
                    if tid == 0:
                        if layer_idx == 0:
                            c.create_rectangle(tx * z, ty * z,
                                               tx * z + z, ty * z + z,
                                               outline="", fill=th.BG_INPUT)
                        continue
                    color = SHEET_PALETTE[tid % len(SHEET_PALETTE)]
                    c.create_rectangle(tx * z, ty * z,
                                       tx * z + z, ty * z + z,
                                       outline="", fill=color)
        if 0 <= self._active_layer < self._layer_count:
            c.create_rectangle(0, 0, self._map_w * z, self._map_h * z,
                               outline=th.ACCENT, width=1)
        for x in range(self._map_w + 1):
            c.create_line(x * z, 0, x * z, self._map_h * z, fill=th.PX_GRID)
        for y in range(self._map_h + 1):
            c.create_line(0, y * z, self._map_w * z, y * z, fill=th.PX_GRID)

    def _refresh_status(self) -> None:
        issues = validate_tilemap(
            name=os.path.splitext(os.path.basename(self._file or "untitled"))[0],
            w=self._map_w, h=self._map_h,
            tiles=self._layers[self._active_layer] if self._layer_count else [],
            palette_size=MAX_TILE_IDS)
        star = "* " if self._dirty else ""
        path = self._file or "untitled.pbm"
        bytes_total = sum(len(layer) for layer in self._layers[:self._layer_count])
        msg = (f"{star}{path}   map {self._map_w}x{self._map_h}  "
                f"layers {self._layer_count}  "
                f"active L{self._active_layer}  "
                f"tile {self._selected_tile}  "
                f"({bytes_total} B)")
        if issues_have_error(issues):
            msg += "   " + "; ".join(str(i) for i in issues)
            self._status.config(fg=th.FG_ERROR)
            self._save_btn.config(state=tk.DISABLED)
        else:
            self._status.config(fg=th.FG_DIM if not self._dirty else th.FG_WARN,
                                text=msg)
            self._save_btn.config(state=tk.NORMAL)
