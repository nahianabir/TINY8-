"""Tiny8 Studio — animation editor.

Edits a single `t8::Anim`-shaped sequence.  The user:

  * Loads a sprite sheet (PBM) as the atlas source.
  * Sets the frame width/height in pixels.
  * Clicks frames in the sheet to append them to the sequence.
  * Edits the per-frame index list, ticks_per_frame, and loop flag.
  * Previews the animation at a chosen FPS (host-side, tkinter `after`).
  * Saves to a `.anim.json` file (assets/<name>.anim.json).

The widget is self-contained: it knows nothing about the main App's
project state.  Callers wire it up with callbacks.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, List, Optional

from .. import theme as th
from ..animation import Anim, read_anim, write_anim


SHEET_HIGHLIGHT = th.ACCENT


class AnimationEditor(tk.Frame):
    def __init__(self, master,
                 on_save: Optional[Callable[[str, Anim], None]] = None,
                 **kw):
        super().__init__(master, bg=th.BG, **kw)
        self._on_save = on_save
        self._file: Optional[str] = None
        self._dirty = False
        # Sheet.
        self._sheet_path: Optional[str] = None
        self._sheet_w = self._sheet_h = 0
        self._sheet_bits: List[int] = []
        self._sheet_zoom = 4
        # Anim state.
        self._anim = Anim(name="untitled", frames=[])
        # Playback.
        self._playing = False
        self._play_idx = 0
        self._play_job: Optional[str] = None
        self._fps = 12   # host-side playback rate; 60 Hz engine tick
                         # corresponds to about 10 fps for a 6-tick anim
        self._build()
        self._refresh_sheet()
        self._refresh_frames()
        self._refresh_preview()
        self._refresh_status()

    # --- layout -------------------------------------------------------

    def _build(self) -> None:
        # Top toolbar: sheet loader + frame size + add-frame.
        top = tk.Frame(self, bg=th.BG)
        top.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=th.PAD)
        tk.Button(top, text="Open sheet…", command=self._on_open_sheet,
                  **self._btn_kw()).pack(side=tk.LEFT)
        self._sheet_lbl = tk.Label(top, text="(no sheet)", bg=th.BG,
                                   fg=th.FG_DIM, font=th.FONT_UI)
        self._sheet_lbl.pack(side=tk.LEFT, padx=8)

        tk.Frame(top, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Label(top, text="Atlas", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT)
        self._atlas_var = tk.StringVar(value=self._anim.atlas)
        tk.Entry(top, textvariable=self._atlas_var, width=18,
                bg=th.BG_INPUT, fg=th.FG, insertbackground=th.FG,
                relief=tk.FLAT, font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)

        tk.Frame(top, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Label(top, text="Frame W", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT)
        self._fw_var = tk.IntVar(value=self._anim.frame_w)
        tk.Spinbox(top, from_=1, to=32, width=3, textvariable=self._fw_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Label(top, text="H", bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT, padx=(6,0))
        self._fh_var = tk.IntVar(value=self._anim.frame_h)
        tk.Spinbox(top, from_=1, to=32, width=3, textvariable=self._fh_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Apply", command=self._on_apply_frame_size,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)

        # Middle: sheet picker (left) + frames list (middle) + preview (right).
        mid = tk.Frame(self, bg=th.BG)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                 padx=th.PAD, pady=th.PAD)

        sheet_frame = tk.LabelFrame(mid, text="Sheet (click to add frame)",
                                    bg=th.BG_PANEL, fg=th.FG, font=th.FONT_UI_B)
        sheet_frame.pack(side=tk.LEFT, fill=tk.Y)
        self._sheet_canvas = tk.Canvas(sheet_frame, bg=th.BG_INPUT,
                                        highlightthickness=0, width=200, height=200)
        self._sheet_canvas.pack(padx=4, pady=4)
        self._sheet_canvas.bind("<Button-1>", self._on_sheet_click)
        # Zoom controls for the sheet.
        zrow = tk.Frame(sheet_frame, bg=th.BG_PANEL)
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

        # Frames list.
        list_frame = tk.LabelFrame(mid, text="Frames", bg=th.BG_PANEL,
                                    fg=th.FG, font=th.FONT_UI_B)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        list_top = tk.Frame(list_frame, bg=th.BG_PANEL)
        list_top.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)
        tk.Button(list_top, text="Add", command=self._on_add_manual,
                  **self._btn_kw()).pack(side=tk.LEFT)
        tk.Button(list_top, text="Insert", command=self._on_insert,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)
        tk.Button(list_top, text="Remove", command=self._on_remove,
                  **self._btn_kw()).pack(side=tk.LEFT)
        tk.Button(list_top, text="Up", command=self._on_move_up,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)
        tk.Button(list_top, text="Down", command=self._on_move_down,
                  **self._btn_kw()).pack(side=tk.LEFT)
        tk.Frame(list_top, bg=th.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Label(list_top, text="Ticks", bg=th.BG_PANEL, fg=th.FG_DIM,
                 font=th.FONT_UI).pack(side=tk.LEFT)
        self._tpf_var = tk.IntVar(value=self._anim.ticks_per_frame)
        tk.Spinbox(list_top, from_=1, to=255, width=4, textvariable=self._tpf_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO,
                  command=self._on_tpf_change).pack(side=tk.LEFT, padx=2)
        self._loop_var = tk.BooleanVar(value=self._anim.loop)
        tk.Checkbutton(list_top, text="Loop", variable=self._loop_var,
                      bg=th.BG_PANEL, fg=th.FG, selectcolor=th.BG_INPUT,
                      activebackground=th.BG_PANEL,
                      font=th.FONT_UI, command=self._on_loop_change).pack(side=tk.LEFT, padx=8)

        # Scrollable listbox.
        list_body = tk.Frame(list_frame, bg=th.BG_PANEL)
        list_body.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self._listbox = tk.Listbox(list_body, bg=th.BG_INPUT, fg=th.FG,
                                    selectbackground=th.ACCENT,
                                    selectforeground=th.FG_ON_ACC,
                                    relief=tk.FLAT, bd=0, font=th.FONT_MONO,
                                    height=8, activestyle="dotbox")
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(list_body, orient=tk.VERTICAL, command=self._listbox.yview)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self._listbox.config(yscrollcommand=sb.set)
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        # Preview column.
        prev_frame = tk.LabelFrame(mid, text="Preview (host simulation)",
                                    bg=th.BG_PANEL, fg=th.FG, font=th.FONT_UI_B)
        prev_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        self._prev_canvas = tk.Canvas(prev_frame, bg=th.BG_INPUT,
                                        highlightthickness=0, width=128, height=128)
        self._prev_canvas.pack(padx=4, pady=4)
        # Tile index under preview.
        self._prev_idx_var = tk.StringVar(value="frame 0 / 0")
        tk.Label(prev_frame, textvariable=self._prev_idx_var, bg=th.BG_PANEL,
                 fg=th.FG_DIM, font=th.FONT_MONO).pack(side=tk.TOP, pady=(0, 4))
        # Playback controls.
        playrow = tk.Frame(prev_frame, bg=th.BG_PANEL)
        playrow.pack(side=tk.TOP, padx=4, pady=(0, 4))
        self._play_btn = tk.Button(playrow, text="Play", command=self._on_play_toggle,
                                   **self._btn_kw(accent=True))
        self._play_btn.pack(side=tk.LEFT)
        tk.Button(playrow, text="Reset", command=self._on_reset,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)
        tk.Label(playrow, text="FPS", bg=th.BG_PANEL, fg=th.FG_DIM,
                 font=th.FONT_UI).pack(side=tk.LEFT, padx=(8, 0))
        self._fps_var = tk.IntVar(value=self._fps)
        tk.Spinbox(playrow, from_=1, to=60, width=3, textvariable=self._fps_var,
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO).pack(side=tk.LEFT, padx=2)

        # Status + save.
        bot = tk.Frame(self, bg=th.BG)
        bot.pack(side=tk.BOTTOM, fill=tk.X, padx=th.PAD, pady=th.PAD)
        self._status = tk.Label(bot, text="", bg=th.BG, fg=th.FG_DIM,
                                font=th.FONT_UI, anchor=tk.W)
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._save_btn = tk.Button(bot, text="Save .anim.json",
                                   command=self._on_save_click,
                                   state=tk.DISABLED,
                                   **self._btn_kw(accent=True))
        self._save_btn.pack(side=tk.RIGHT)

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

    def current_anim(self) -> Anim:
        return self._anim

    def load_file(self, path: str) -> None:
        try:
            anim = read_anim(path)
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
            return
        # If a sibling sheet exists, use it.
        sheet = os.path.join(os.path.dirname(path), anim.atlas + ".pbm")
        if os.path.isfile(sheet):
            self._load_sheet(sheet)
        self._anim = anim
        self._atlas_var.set(anim.atlas)
        self._fw_var.set(anim.frame_w)
        self._fh_var.set(anim.frame_h)
        self._tpf_var.set(anim.ticks_per_frame)
        self._loop_var.set(anim.loop)
        self._file = path
        self._dirty = False
        self._stop_playback()
        self._refresh_sheet()
        self._refresh_frames()
        self._refresh_preview()
        self._refresh_status()

    def mark_clean(self) -> None:
        self._dirty = False
        self._refresh_status()

    # --- sheet --------------------------------------------------------

    def _on_open_sheet(self) -> None:
        path = filedialog.askopenfilename(
            title="Open sprite sheet (PBM)",
            filetypes=[("PBM bitmap", "*.pbm"), ("All files", "*.*")],
        )
        if not path:
            return
        if self._load_sheet(path):
            self._dirty = True
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
        # Auto-fill atlas name from the sheet basename if blank.
        if not self._atlas_var.get().strip():
            self._atlas_var.set(os.path.splitext(os.path.basename(path))[0])
        return True

    def _on_zoom_change(self) -> None:
        self._sheet_zoom = max(1, min(16, int(self._zoom_var.get())))
        self._refresh_sheet()

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
        for y in range(self._sheet_h):
            row = y * row_bytes
            for x in range(self._sheet_w):
                if self._sheet_bits[row + (x >> 3)] & (0x80 >> (x & 7)):
                    c.create_rectangle(x * z, y * z, (x + 1) * z, (y + 1) * z,
                                       outline="", fill=th.PX_ON)
        # Outline each frame.
        fw = max(1, int(self._fw_var.get()))
        fh = max(1, int(self._fh_var.get()))
        for ty in range(self._sheet_h // fh):
            for tx in range(self._sheet_w // fw):
                c.create_rectangle(tx * fw * z, ty * fh * z,
                                   (tx + 1) * fw * z, (ty + 1) * fh * z,
                                   outline=th.PX_GRID)

    def _on_sheet_click(self, ev) -> None:
        if not self._sheet_bits:
            return
        z = self._sheet_zoom
        sx = ev.x // z
        sy = ev.y // z
        if sx < 0 or sy < 0:
            return
        fw = max(1, int(self._fw_var.get()))
        fh = max(1, int(self._fh_var.get()))
        if sx >= self._sheet_w or sy >= self._sheet_h:
            return
        if sx + fw > self._sheet_w: sx = self._sheet_w - fw
        if sy + fh > self._sheet_h: sy = self._sheet_h - fh
        cols = self._sheet_w // fw
        idx = (sy // fh) * cols + (sx // fw)
        self._anim.frames.append(int(idx))
        self._anim.atlas = self._atlas_var.get().strip() or self._anim.atlas
        self._dirty = True
        self._refresh_frames()
        self._refresh_preview()
        self._refresh_status()

    def _on_apply_frame_size(self) -> None:
        try:
            fw = int(self._fw_var.get()); fh = int(self._fh_var.get())
        except tk.TclError:
            return
        if not (1 <= fw <= 32 and 1 <= fh <= 32):
            messagebox.showerror("Frame size", "Frame size must be 1..32")
            return
        self._anim.frame_w = fw
        self._anim.frame_h = fh
        self._anim.atlas = self._atlas_var.get().strip() or self._anim.atlas
        self._dirty = True
        self._refresh_sheet()
        self._refresh_frames()
        self._refresh_preview()
        self._refresh_status()

    # --- frames list --------------------------------------------------

    def _refresh_frames(self) -> None:
        self._listbox.delete(0, tk.END)
        for i, f in enumerate(self._anim.frames):
            self._listbox.insert(tk.END, f"  {i:2d}: frame {f}")
        if self._anim.frames:
            self._listbox.selection_set(0)
        self._refresh_status()

    def _on_listbox_select(self, _ev) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        self._play_idx = int(sel[0])
        self._refresh_preview()

    def _on_add_manual(self) -> None:
        try:
            v = int(tk.simpledialog.askstring("Add frame", "Frame index:",
                                              parent=self, initialvalue="0") or 0)
        except (tk.TclError, ValueError):
            return
        self._anim.frames.append(v)
        self._dirty = True
        self._refresh_frames()
        self._refresh_preview()
        self._refresh_status()

    def _on_insert(self) -> None:
        sel = self._listbox.curselection()
        try:
            v = int(tk.simpledialog.askstring("Insert frame", "Frame index:",
                                              parent=self, initialvalue="0") or 0)
        except (tk.TclError, ValueError):
            return
        pos = int(sel[0]) if sel else len(self._anim.frames)
        self._anim.frames.insert(pos, v)
        self._dirty = True
        self._refresh_frames()
        self._listbox.selection_set(pos)
        self._refresh_preview()
        self._refresh_status()

    def _on_remove(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._anim.frames):
            del self._anim.frames[idx]
            self._dirty = True
            self._refresh_frames()
            self._refresh_preview()
            self._refresh_status()

    def _on_move_up(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx <= 0:
            return
        self._anim.frames[idx - 1], self._anim.frames[idx] = (
            self._anim.frames[idx], self._anim.frames[idx - 1])
        self._dirty = True
        self._refresh_frames()
        self._listbox.selection_set(idx - 1)
        self._refresh_status()

    def _on_move_down(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self._anim.frames) - 1:
            return
        self._anim.frames[idx + 1], self._anim.frames[idx] = (
            self._anim.frames[idx], self._anim.frames[idx + 1])
        self._dirty = True
        self._refresh_frames()
        self._listbox.selection_set(idx + 1)
        self._refresh_status()

    def _on_tpf_change(self) -> None:
        try:
            v = max(1, min(255, int(self._tpf_var.get())))
        except tk.TclError:
            return
        self._anim.ticks_per_frame = v
        self._dirty = True
        self._refresh_status()

    def _on_loop_change(self) -> None:
        self._anim.loop = bool(self._loop_var.get())
        self._dirty = True
        self._refresh_status()

    # --- playback -----------------------------------------------------

    def _on_play_toggle(self) -> None:
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        if not self._anim.frames:
            return
        self._playing = True
        self._play_btn.config(text="Stop")
        self._tick()

    def _stop_playback(self) -> None:
        self._playing = False
        self._play_btn.config(text="Play")
        if self._play_job is not None:
            try:
                self.after_cancel(self._play_job)
            except tk.TclError:
                pass
            self._play_job = None

    def _on_reset(self) -> None:
        self._stop_playback()
        self._play_idx = 0
        if self._anim.frames:
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(0)
        self._refresh_preview()

    def _tick(self) -> None:
        if not self._playing:
            return
        if self._anim.frames:
            self._play_idx = (self._play_idx + 1) % len(self._anim.frames)
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(self._play_idx)
            self._listbox.see(self._play_idx)
            self._refresh_preview()
        try:
            fps = max(1, min(60, int(self._fps_var.get())))
        except tk.TclError:
            fps = self._fps
        delay = int(1000 / fps)
        self._play_job = self.after(delay, self._tick)

    # --- preview ------------------------------------------------------

    def _refresh_preview(self) -> None:
        c = self._prev_canvas
        c.delete("all")
        if not self._anim.frames or not self._sheet_bits:
            c.create_text(64, 64, text="(no frames)",
                          fill=th.FG_DIM, font=th.FONT_UI)
            self._prev_idx_var.set("frame 0 / 0")
            c.config(width=128, height=128)
            return
        idx = self._play_idx if self._playing else (
            int(self._listbox.curselection()[0]) if self._listbox.curselection() else 0)
        idx = max(0, min(len(self._anim.frames) - 1, idx))
        frame_id = self._anim.frames[idx]
        fw = self._anim.frame_w
        fh = self._anim.frame_h
        cols = max(1, self._sheet_w // fw)
        tx = frame_id % cols
        ty = frame_id // cols
        # Determine scale to fit the 128x128 canvas.
        scale = max(1, min(128 // max(1, fw), 128 // max(1, fh)))
        # Center the frame.
        out_w = fw * scale
        out_h = fh * scale
        ox = (128 - out_w) // 2
        oy = (128 - out_h) // 2
        c.config(width=128, height=128)
        # Blit the frame from the sheet.
        row_bytes = (self._sheet_w + 7) // 8
        for y in range(fh):
            row = (ty * fh + y) * row_bytes
            for x in range(fw):
                sx = tx * fw + x
                if self._sheet_bits[row + (sx >> 3)] & (0x80 >> (sx & 7)):
                    c.create_rectangle(ox + x * scale, oy + y * scale,
                                       ox + (x + 1) * scale, oy + (y + 1) * scale,
                                       outline="", fill=th.PX_ON)
        self._prev_idx_var.set(f"frame {idx + 1} / {len(self._anim.frames)}  "
                                f"(id {frame_id})")

    # --- save ---------------------------------------------------------

    def _on_save_click(self) -> None:
        if self._file is None:
            path = filedialog.asksaveasfilename(
                title="Save animation",
                defaultextension=".anim.json",
                filetypes=[("Tiny8 animation", "*.anim.json")],
            )
            if not path:
                return
            self._file = path
        self._anim.name = os.path.splitext(os.path.basename(self._file))[0]
        self._anim.atlas = self._atlas_var.get().strip() or "atlas"
        self._anim.frame_w = int(self._fw_var.get())
        self._anim.frame_h = int(self._fh_var.get())
        self._anim.ticks_per_frame = max(1, int(self._tpf_var.get()))
        self._anim.loop = bool(self._loop_var.get())
        try:
            write_anim(self._file, self._anim)
        except OSError as e:
            messagebox.showerror("Save failed", str(e))
            return
        self._dirty = False
        self._refresh_status()
        if self._on_save:
            self._on_save(self._file, self._anim)

    # --- status -------------------------------------------------------

    def _refresh_status(self) -> None:
        star = "* " if self._dirty else ""
        path = self._file or "untitled.anim.json"
        n = len(self._anim.frames)
        msg = (f"{star}{path}   atlas={self._anim.atlas or '?'}  "
                f"frame={self._anim.frame_w}x{self._anim.frame_h}  "
                f"frames={n}  ticks={self._anim.ticks_per_frame}  "
                f"loop={'yes' if self._anim.loop else 'no'}")
        issues = []
        if not self._anim.frames:
            issues.append("no frames")
        if not self._anim.atlas:
            issues.append("no atlas")
        if not (1 <= self._anim.frame_w <= 32 and 1 <= self._anim.frame_h <= 32):
            issues.append("frame size out of bounds")
        if issues:
            msg += "   " + "; ".join(issues)
            self._status.config(fg=th.FG_ERROR)
            self._save_btn.config(state=tk.DISABLED)
        else:
            self._status.config(fg=th.FG_DIM if not self._dirty else th.FG_WARN,
                                text=msg)
            self._save_btn.config(state=tk.NORMAL)
