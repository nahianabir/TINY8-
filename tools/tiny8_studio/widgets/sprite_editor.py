"""Tiny8 Studio — sprite editor frame.

Combines the PixelCanvas with a tool strip, save / export buttons, and
a small status line that surfaces byte count and engine limits.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

from .. import theme as th
from ..validation import (
    MAX_SPRITE_W, MAX_SPRITE_H, validate_sprite, issues_have_error,
)
from .pixel_canvas import PixelCanvas, TOOL_PENCIL, TOOL_ERASER


class SpriteEditor(tk.Frame):
    def __init__(self, master, on_save: Optional[Callable[[str, List[int], int, int], None]] = None,
                 **kw):
        super().__init__(master, bg=th.BG, **kw)
        self._on_save = on_save
        self._file: Optional[str] = None
        self._dirty = False
        self._build()
        self._refresh_status()

    # --- layout -------------------------------------------------------

    def _build(self) -> None:
        # Top: tool strip.
        tools = tk.Frame(self, bg=th.BG)
        tools.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=th.PAD)
        self._pencil_btn = self._tool_button(tools, "Pencil", TOOL_PENCIL)
        self._eraser_btn = self._tool_button(tools, "Eraser", TOOL_ERASER)
        tk.Frame(tools, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        tk.Button(tools, text="Clear", command=self._on_clear, **self._btn_kw()).pack(side=tk.LEFT)
        tk.Button(tools, text="Import PBM…", command=self._on_import_pbm, **self._btn_kw()).pack(side=tk.LEFT, padx=4)
        tk.Button(tools, text="Import PNG…", command=self._on_import_png, **self._btn_kw()).pack(side=tk.LEFT)
        tk.Frame(tools, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        tk.Label(tools, text="W", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT)
        self._w_var = tk.IntVar(value=8)
        tk.Spinbox(tools, from_=1, to=MAX_SPRITE_W, width=3, textvariable=self._w_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Label(tools, text="H", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT, padx=(6,0))
        self._h_var = tk.IntVar(value=8)
        tk.Spinbox(tools, from_=1, to=MAX_SPRITE_H, width=3, textvariable=self._h_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Button(tools, text="Resize", command=self._on_resize, **self._btn_kw()).pack(side=tk.LEFT, padx=4)

        # Center: the canvas.
        self._canvas = PixelCanvas(self, w=8, h=8, on_change=self._on_canvas_change)
        self._canvas.pack(side=tk.TOP, padx=th.PAD, pady=th.PAD, fill=tk.BOTH, expand=True)
        self._set_tool(TOOL_PENCIL)

        # Bottom: status + save.
        bot = tk.Frame(self, bg=th.BG)
        bot.pack(side=tk.BOTTOM, fill=tk.X, padx=th.PAD, pady=th.PAD)
        self._status = tk.Label(bot, text="", bg=th.BG, fg=th.FG_DIM,
                                font=th.FONT_UI, anchor=tk.W)
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._save_btn = tk.Button(bot, text="Save .pbm", command=self._on_save_click,
                                   state=tk.DISABLED, **self._btn_kw(accent=True))
        self._save_btn.pack(side=tk.RIGHT)

    def _btn_kw(self, accent: bool = False) -> dict:
        kw = dict(
            bg=th.ACCENT if accent else th.BG_RAISED,
            fg=th.FG_ON_ACC if accent else th.FG,
            activebackground=th.ACCENT_DARK if accent else th.BG_HOVER,
            activeforeground=th.FG_ON_ACC if accent else th.FG,
            relief=tk.FLAT, bd=0, padx=10, pady=4, font=th.FONT_UI,
        )
        return kw

    def _tool_button(self, parent, label, tool_id) -> tk.Button:
        btn = tk.Button(parent, text=label, command=lambda: self._set_tool(tool_id),
                       relief=tk.FLAT, bd=0, padx=10, pady=4, font=th.FONT_UI,
                       bg=th.BG_RAISED, fg=th.FG,
                       activebackground=th.BG_HOVER, activeforeground=th.FG)
        btn.pack(side=tk.LEFT)
        return btn

    # --- public API ---------------------------------------------------

    def load_file(self, path: str) -> None:
        """Load a PBM from disk and display it."""
        try:
            self._canvas.import_pbm(path)
        except Exception as e:
            messagebox.showerror("Import failed", str(e))
            return
        self._file = path
        self._w_var.set(self._canvas.w)
        self._h_var.set(self._canvas.h)
        self._dirty = False
        self._refresh_status()

    def current_path(self) -> Optional[str]:
        return self._file

    def current_bits(self) -> List[int]:
        return self._canvas.bits

    def current_size(self) -> tuple[int, int]:
        return self._canvas.w, self._canvas.h

    def mark_clean(self) -> None:
        self._dirty = False
        self._refresh_status()

    # --- handlers -----------------------------------------------------

    def _set_tool(self, tool_id: int) -> None:
        self._canvas.set_tool(tool_id)
        active = {"bg": th.ACCENT, "fg": th.FG_ON_ACC}
        normal = {"bg": th.BG_RAISED, "fg": th.FG}
        for btn, tid in [(self._pencil_btn, TOOL_PENCIL), (self._eraser_btn, TOOL_ERASER)]:
            style = active if tid == tool_id else normal
            btn.config(**style)

    def _on_canvas_change(self) -> None:
        self._dirty = True
        self._refresh_status()

    def _on_clear(self) -> None:
        if messagebox.askyesno("Clear", "Clear the entire canvas?"):
            self._canvas.clear()

    def _on_import_pbm(self) -> None:
        path = filedialog.askopenfilename(
            title="Open PBM",
            filetypes=[("PBM bitmap", "*.pbm"), ("All files", "*.*")],
        )
        if path:
            self.load_file(path)

    def _on_import_png(self) -> None:
        path = filedialog.askopenfilename(
            title="Open PNG",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._canvas.try_import_png(path)
        except RuntimeError as e:
            messagebox.showwarning("Pillow not installed",
                f"{e}\n\nInstall Pillow via: pip install Pillow")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))
            return
        self._w_var.set(self._canvas.w)
        self._h_var.set(self._canvas.h)
        self._dirty = True
        self._refresh_status()

    def _on_resize(self) -> None:
        try:
            w = int(self._w_var.get()); h = int(self._h_var.get())
        except tk.TclError:
            return
        if not (1 <= w <= MAX_SPRITE_W and 1 <= h <= MAX_SPRITE_H):
            messagebox.showerror("Resize",
                f"Dimensions must be 1..{MAX_SPRITE_W} x 1..{MAX_SPRITE_H}")
            return
        self._canvas.resize(w, h)
        self._dirty = True
        self._refresh_status()

    def _on_save_click(self) -> None:
        # Always prompt for a destination if no file yet, or write to
        # the existing one.
        if self._file is None:
            path = filedialog.asksaveasfilename(
                title="Save PBM",
                defaultextension=".pbm",
                filetypes=[("PBM bitmap", "*.pbm")],
            )
            if not path:
                return
            self._file = path
        bits = self._canvas.bits
        # Write the P4 PBM format (binary, 1bpp, MSB-first).
        w, h = self._canvas.w, self._canvas.h
        try:
            row_bytes = (w + 7) // 8
            with open(self._file, "wb") as f:
                f.write(f"P4\n{w} {h}\n".encode("ascii"))
                f.write(bytes(bits[:row_bytes * h]))
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return
        self._dirty = False
        self._refresh_status()
        if self._on_save:
            self._on_save(self._file, bits, w, h)

    # --- status line --------------------------------------------------

    def _refresh_status(self) -> None:
        bits = self._canvas.bits
        issues = validate_sprite(
            name=os.path.splitext(os.path.basename(self._file or "untitled"))[0],
            w=self._canvas.w, h=self._canvas.h, bits=bits)
        byte_count = len(bits)
        star = "* " if self._dirty else ""
        path = self._file or "untitled.pbm"
        msg = f"{star}{path}   {self._canvas.w}x{self._canvas.h}   {byte_count} B"
        if issues_have_error(issues):
            msg += "   " + "; ".join(str(i) for i in issues)
            self._status.config(fg=th.FG_ERROR)
            self._save_btn.config(state=tk.DISABLED)
        else:
            warns = [i for i in issues if i.level == "warn"]
            if warns:
                msg += "   " + "; ".join(str(i) for i in warns)
            self._status.config(fg=th.FG_DIM if not self._dirty else th.FG_WARN)
            self._save_btn.config(state=tk.NORMAL)
        self._status.config(text=msg)