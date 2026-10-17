"""Tiny8 Studio — asset browser.

Lists sprites, sprite sheets, tilemaps, fonts, and audio sequences with
small previews and a footer showing total Flash usage.  Reads from the
project's asset registry; never touches the disk itself.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

from .. import theme as th
from ..assets import (
    Asset, KIND_SPRITE, KIND_SHEET, KIND_TILEMAP, KIND_FONT, KIND_AUDIO,
    ProjectAssets,
)
from ..validation import estimate_flash_bytes, MAX_PROGMEM_BYTES


class AssetBrowser(tk.Frame):
    def __init__(self, master,
                 on_open: Optional[Callable[[Asset], None]] = None,
                 on_export: Optional[Callable[[List[Asset]], None]] = None,
                 **kw):
        super().__init__(master, bg=th.BG_PANEL, **kw)
        self._on_open = on_open
        self._on_export = on_export
        self._assets: ProjectAssets = ProjectAssets(root="")
        self._build()

    def _build(self) -> None:
        # Header.
        hdr = tk.Frame(self, bg=th.BG_PANEL)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=(th.PAD, th.PAD_TIGHT))
        tk.Label(hdr, text="Assets", bg=th.BG_PANEL, fg=th.FG,
                 font=th.FONT_TITLE).pack(side=tk.LEFT)
        tk.Button(hdr, text="Export PROGMEM…", command=self._do_export,
                  **self._btn_kw(accent=True)).pack(side=tk.RIGHT)

        # Treeview.
        cols = ("kind", "name", "size", "bytes")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("T8.Treeview",
                        background=th.BG_RAISED, fieldbackground=th.BG_RAISED,
                        foreground=th.FG, rowheight=22, font=th.FONT_UI)
        style.configure("T8.Treeview.Heading",
                        background=th.BG_PANEL, foreground=th.FG,
                        font=th.FONT_UI_B)
        style.map("T8.Treeview",
                  background=[("selected", th.ACCENT)],
                  foreground=[("selected", th.FG_ON_ACC)])

        tree_holder = tk.Frame(self, bg=th.BG_PANEL)
        tree_holder.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                         padx=th.PAD, pady=th.PAD_TIGHT)
        self._tree = ttk.Treeview(tree_holder, columns=cols, show="headings",
                                  style="T8.Treeview", selectmode="browse")
        for c, label, w in [("kind", "Kind", 60), ("name", "Name", 130),
                            ("size", "Size", 90), ("bytes", "Bytes", 60)]:
            self._tree.heading(c, text=label)
            self._tree.column(c, width=w, anchor=tk.W)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(tree_holder, orient=tk.VERTICAL, command=self._tree.yview)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self._tree.config(yscrollcommand=sb.set)
        self._tree.bind("<Double-1>", self._on_double)
        # Tag colors per kind.
        self._tree.tag_configure(KIND_SPRITE,   foreground=th.FG)
        self._tree.tag_configure(KIND_SHEET,    foreground=th.FG)
        self._tree.tag_configure(KIND_TILEMAP,  foreground=th.FG)
        self._tree.tag_configure(KIND_FONT,     foreground=th.FG)
        self._tree.tag_configure(KIND_AUDIO,    foreground=th.FG)
        self._tree.tag_configure("source",      foreground=th.FG_DIM)
        self._tree.tag_configure("missing",     foreground=th.FG_WARN)

        # Preview + metadata.
        meta = tk.Frame(self, bg=th.BG_PANEL)
        meta.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=th.PAD_TIGHT)
        self._preview = tk.Canvas(meta, bg=th.BG_INPUT, highlightthickness=0,
                                  width=64, height=64, bd=0)
        self._preview.pack(side=tk.LEFT, padx=(0, 8))
        self._meta = tk.Label(meta, text="(no selection)", bg=th.BG_PANEL,
                              fg=th.FG_DIM, font=th.FONT_UI, justify=tk.LEFT,
                              anchor=tk.NW)
        self._meta.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Footer (Flash budget).
        foot = tk.Frame(self, bg=th.BG_PANEL)
        foot.pack(side=tk.BOTTOM, fill=tk.X, padx=th.PAD, pady=th.PAD)
        self._budget = tk.Label(foot, text="", bg=th.BG_PANEL, fg=th.FG_DIM,
                                font=th.FONT_UI, anchor=tk.W)
        self._budget.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _btn_kw(self, accent: bool = False) -> dict:
        return dict(
            bg=th.ACCENT if accent else th.BG_RAISED,
            fg=th.FG_ON_ACC if accent else th.FG,
            activebackground=th.ACCENT_DARK if accent else th.BG_HOVER,
            activeforeground=th.FG_ON_ACC if accent else th.FG,
            relief=tk.FLAT, bd=0, padx=10, pady=4, font=th.FONT_UI,
        )

    # --- public API ---------------------------------------------------

    def set_assets(self, assets: ProjectAssets) -> None:
        self._assets = assets
        self._tree.delete(*self._tree.get_children())
        for a in assets.items:
            size = f"{a.meta.get('w','')}x{a.meta.get('h','')}" if a.meta.get("w") else ""
            tags = [a.kind]
            if not a.exists:
                tags.append("missing")
            self._tree.insert("", tk.END, iid=a.relpath,
                              values=(a.kind, a.name, size, a.flash_bytes()),
                              tags=tags)
        self._refresh_footer()

    def selected(self) -> Optional[Asset]:
        sel = self._tree.selection()
        if not sel:
            return None
        for a in self._assets.items:
            if a.relpath == sel[0]:
                return a
        return None

    # --- handlers -----------------------------------------------------

    def _on_double(self, _ev) -> None:
        a = self.selected()
        if a and self._on_open:
            self._on_open(a)

    def _on_select(self, _ev) -> None:
        a = self.selected()
        if not a:
            return
        # Render preview.
        self._preview.delete("all")
        w = int(a.meta.get("w", 0))
        h = int(a.meta.get("h", 0))
        if w and h:
            self._render_preview(a, w, h)
        # Metadata label.
        info = [f"kind: {a.kind}", f"name: {a.name}",
                f"path: {a.relpath}"]
        if w and h:
            info.append(f"size: {w} x {h}")
        if a.flash_bytes():
            info.append(f"flash: {a.flash_bytes()} B")
        if not a.exists:
            info.append("(missing on disk)")
        self._meta.config(text="\n".join(info), fg=th.FG_WARN if not a.exists else th.FG)

    def _render_preview(self, a: Asset, w: int, h: int) -> None:
        path = a.relpath
        if not os.path.isfile(path):
            return
        # Read PBM header + bits.
        try:
            with open(path, "rb") as f:
                f.readline()
                line = f.readline()
                while line.startswith(b"#"):
                    line = f.readline()
                pw, ph = (int(x) for x in line.split())
                data = f.read()
            bits = list(data[:((pw + 7) // 8) * ph])
        except Exception:
            return
        if a.kind == KIND_TILEMAP:
            # For tilemap, draw a 1px-per-tile grid.
            if pw % 2 or ph % 2:
                return
            tw, th = pw // 2, ph // 2
            for ty in range(th):
                for tx in range(tw):
                    sx = tx * 2
                    sy = ty * 2
                    row = sy * ((pw + 7) // 8)
                    bit = 0x80 >> (sx & 7)
                    tid = 1 if (bits[row + (sx >> 3)] & bit) else 0
                    color = "#5B7CFA" if tid else "#1A1B1E"
                    self._preview.create_rectangle(tx, ty, tx + 1, ty + 1,
                                                  outline="", fill=color)
            return
        # Sprite / sheet: render at 1px per source pixel within the 64x64 canvas.
        max_dim = max(w, h, 1)
        scale = max(1, min(64 // max_dim, 8))
        ox = (64 - w * scale) // 2
        oy = (64 - h * scale) // 2
        row_bytes = (w + 7) // 8
        for y in range(h):
            for x in range(w):
                if bits[y * row_bytes + (x >> 3)] & (0x80 >> (x & 7)):
                    self._preview.create_rectangle(
                        ox + x * scale, oy + y * scale,
                        ox + (x + 1) * scale, oy + (y + 1) * scale,
                        outline="", fill=th.PX_ON)

    def _do_export(self) -> None:
        if self._on_export:
            self._on_export(self._assets.items)

    def _refresh_footer(self) -> None:
        items = [(a.name, a.flash_bytes()) for a in self._assets.items
                 if a.kind in (KIND_SPRITE, KIND_SHEET, KIND_TILEMAP, KIND_AUDIO)]
        total, issues = estimate_flash_bytes(items)
        warn = "; ".join(str(i) for i in issues) if issues else ""
        self._budget.config(
            text=f"Estimated Flash: {total} / {MAX_PROGMEM_BYTES} B   {warn}",
            fg=th.FG_ERROR if any(i.level == "error" for i in issues) else
                (th.FG_WARN if warn else th.FG_DIM),
        )