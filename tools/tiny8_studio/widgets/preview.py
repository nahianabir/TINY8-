"""Tiny8 Studio — preview frame with host simulation.

Three renderings of a selected PBM:

  * Native (1:1) — 84x48 canvas (the PCD8544 framebuffer size).
  * Scaled (4x) — enlarged for inspection.
  * Simulated — when the user toggles "Simulate", the studio runs a
    step-clock loop on the host using the same framebuffer and blit
    code the engine uses, draws the loaded sprite moving across the
    screen, and shows a captured PCD8544-flush byte stream.

The label below the canvas is explicit: this is a *host simulation*,
not the real-time loop that runs on the ATmega328P.  The step-clock
in particular uses the same algorithm the engine uses (bounded
catch-up) but is not pinned to the 16 ms cadence the AVR runs.
"""

from __future__ import annotations
import os
import time
import tkinter as tk
from typing import Callable, Optional

from .. import theme as th
from .. import simulate as sim


class PreviewPane(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=th.BG, **kw)
        # Simulation state.
        self._sim_sprite: Optional[dict] = None
        self._sim_anim_frames: list[int] = []
        self._sim_sheet: Optional[tuple[int, int, list[int]]] = None
        self._sim_fw = self._sim_fh = 8
        self._sim_ticks_per_frame = 6
        self._sim_loop = True
        self._sim_running = False
        self._sim_job: Optional[str] = None
        self._sim_clock = sim.StepClock(step_ms=16, max_catch=4)
        self._sim_t_ms = 0
        self._sim_frame_idx = 0
        self._sim_frame_tick = 0
        self._sim_x = 0
        self._sim_vx = 0.1   # px per ms
        self._last_tick_ms = 0
        self._sim_draw_cb: Optional[Callable[[sim.Framebuffer, int], None]] = None
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="Preview", bg=th.BG, fg=th.FG,
                 font=th.FONT_TITLE).pack(side=tk.TOP, anchor=tk.W, padx=th.PAD)
        tk.Label(self,
                 text="Host simulation runs the same framebuffer and blit code as "
                      "the engine, but it is not real-time.  On the Uno the loop runs "
                      "at 16 ms per step.",
                 bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI, justify=tk.LEFT,
                 wraplength=520, anchor=tk.W).pack(side=tk.TOP, anchor=tk.W,
                                                   padx=th.PAD, pady=(0, 4))

        body = tk.Frame(self, bg=th.BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=th.PAD, pady=th.PAD)

        # Native.
        nf = tk.LabelFrame(body, text="Native (1:1)", bg=th.BG_PANEL, fg=th.FG,
                           font=th.FONT_UI_B)
        nf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._native = tk.Canvas(nf, bg=th.BG_INPUT, highlightthickness=0,
                                 width=84, height=48)
        self._native.pack(padx=4, pady=4)

        # Scaled.
        sf = tk.LabelFrame(body, text="Scaled (4x)", bg=th.BG_PANEL, fg=th.FG,
                           font=th.FONT_UI_B)
        sf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self._scaled = tk.Canvas(sf, bg=th.BG_INPUT, highlightthickness=0,
                                 width=84 * 4, height=48 * 4)
        self._scaled.pack(padx=4, pady=4)

        # Sim + flush.
        simf = tk.LabelFrame(body, text="Host simulation", bg=th.BG_PANEL, fg=th.FG,
                              font=th.FONT_UI_B)
        simf.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        controls = tk.Frame(simf, bg=th.BG_PANEL)
        controls.pack(side=tk.TOP, padx=4, pady=4, fill=tk.X)
        self._sim_btn = tk.Button(controls, text="Simulate", command=self._on_toggle,
                                  **self._btn_kw(accent=True))
        self._sim_btn.pack(side=tk.LEFT)
        tk.Button(controls, text="Reset", command=self._on_reset,
                  **self._btn_kw()).pack(side=tk.LEFT, padx=4)
        tk.Label(controls, text="vx (px/ms)", bg=th.BG_PANEL, fg=th.FG_DIM,
                 font=th.FONT_UI).pack(side=tk.LEFT, padx=(8, 0))
        self._vx_var = tk.DoubleVar(value=self._sim_vx)
        tk.Spinbox(controls, from_=0.0, to=1.0, increment=0.05, width=5,
                  textvariable=self._vx_var, format="%.2f",
                  bg=th.BG_INPUT, fg=th.FG, buttonbackground=th.BG_RAISED,
                  font=th.FONT_MONO,
                  command=self._on_vx_change).pack(side=tk.LEFT, padx=2)
        self._sim_canvas = tk.Canvas(simf, bg=th.BG_INPUT, highlightthickness=0,
                                      width=84 * 3, height=48 * 3)
        self._sim_canvas.pack(padx=4, pady=4)
        # Captured PCD8544 flush bytes (last frame).
        flush_row = tk.Frame(simf, bg=th.BG_PANEL)
        flush_row.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 4))
        tk.Label(flush_row, text="PCD8544 flush (last frame):",
                 bg=th.BG_PANEL, fg=th.FG_DIM, font=th.FONT_UI).pack(side=tk.LEFT)
        self._flush_var = tk.StringVar(value="(none)")
        self._flush_lbl = tk.Label(flush_row, textvariable=self._flush_var,
                                    bg=th.BG_PANEL, fg=th.FG, font=th.FONT_MONO)
        self._flush_lbl.pack(side=tk.LEFT, padx=6)

        self._status = tk.Label(self, text="(no asset)", bg=th.BG, fg=th.FG_DIM,
                                 font=th.FONT_UI, anchor=tk.W)
        self._status.pack(side=tk.BOTTOM, fill=tk.X, padx=th.PAD, pady=th.PAD)

    def _btn_kw(self, accent: bool = False) -> dict:
        return dict(
            bg=th.ACCENT if accent else th.BG_RAISED,
            fg=th.FG_ON_ACC if accent else th.FG,
            activebackground=th.ACCENT_DARK if accent else th.BG_HOVER,
            activeforeground=th.FG_ON_ACC if accent else th.FG,
            relief=tk.FLAT, bd=0, padx=10, pady=4, font=th.FONT_UI,
        )

    # --- public API ---------------------------------------------------

    def show_pbm(self, path: str, kind: str = "sprite") -> None:
        if not os.path.isfile(path):
            self._status.config(text=f"missing: {path}", fg=th.FG_WARN)
            return
        try:
            w, h, bits = sim.pbm_to_sheet(path)
        except Exception as e:
            self._status.config(text=f"error: {e}", fg=th.FG_ERROR)
            return
        self._native.delete("all")
        self._native.config(width=84, height=48)
        self._draw_bits(self._native, bits, w, h, 1, ox=0, oy=0)
        self._scaled.delete("all")
        scale = 4
        self._scaled.config(width=w * scale, height=h * scale)
        self._draw_bits(self._scaled, bits, w, h, scale, ox=0, oy=0)
        self._stop_sim()
        self._sim_sprite = sim.make_sprite(w, h, bits)
        self._sim_anim_frames = []
        self._sim_t_ms = 0
        self._sim_x = 0
        self._render_sim_idle()
        self._status.config(text=f"{os.path.basename(path)}   {w}x{h}   "
                                  f"({len(bits)} B 1bpp)", fg=th.FG_DIM)

    def show_bits(self, bits, w: int, h: int, label: str = "current") -> None:
        self._native.delete("all")
        self._native.config(width=84, height=48)
        self._draw_bits(self._native, bits, w, h, 1, ox=0, oy=0)
        self._scaled.delete("all")
        scale = 4
        self._scaled.config(width=w * scale, height=h * scale)
        self._draw_bits(self._scaled, bits, w, h, scale, ox=0, oy=0)
        self._stop_sim()
        self._sim_sprite = sim.make_sprite(w, h, bits)
        self._sim_anim_frames = []
        self._render_sim_idle()
        self._status.config(text=f"{label}   {w}x{h}   {len(bits)} B", fg=th.FG_DIM)

    def set_anim(self, sheet_path: str, frame_w: int, frame_h: int,
                 frames: list[int], ticks_per_frame: int, loop: bool) -> bool:
        try:
            w, h, bits = sim.pbm_to_sheet(sheet_path)
        except Exception as e:
            self._status.config(text=f"anim error: {e}", fg=th.FG_ERROR)
            return False
        self._sim_sheet = (w, h, bits)
        self._sim_fw = frame_w
        self._sim_fh = frame_h
        self._sim_anim_frames = list(frames)
        self._sim_ticks_per_frame = ticks_per_frame
        self._sim_loop = loop
        self._sim_sprite = None
        self._sim_frame_idx = 0
        self._sim_frame_tick = 0
        self._sim_t_ms = 0
        self._sim_x = 0
        self._render_sim_idle()
        return True

    def set_draw_callback(self, cb: Optional[Callable[[sim.Framebuffer, int], None]]) -> None:
        self._sim_draw_cb = cb

    # --- simulation --------------------------------------------------

    def _on_vx_change(self) -> None:
        try:
            v = float(self._vx_var.get())
        except (tk.TclError, ValueError):
            return
        self._sim_vx = max(0.0, min(1.0, v))

    def _on_toggle(self) -> None:
        if self._sim_running:
            self._stop_sim()
        else:
            self._start_sim()

    def _start_sim(self) -> None:
        if not self._sim_sprite and not self._sim_anim_frames:
            return
        self._sim_running = True
        self._sim_btn.config(text="Stop")
        self._sim_clock.init(int(time.monotonic() * 1000))
        self._last_tick_ms = self._sim_clock.last_ms
        self._tick()

    def _stop_sim(self) -> None:
        self._sim_running = False
        self._sim_btn.config(text="Simulate")
        if self._sim_job is not None:
            try:
                self.after_cancel(self._sim_job)
            except tk.TclError:
                pass
            self._sim_job = None

    def _on_reset(self) -> None:
        self._stop_sim()
        self._sim_t_ms = 0
        self._sim_x = 0
        self._sim_frame_idx = 0
        self._sim_frame_tick = 0
        self._render_sim_idle()

    def _tick(self) -> None:
        if not self._sim_running:
            return
        now = int(time.monotonic() * 1000)
        steps = self._sim_clock.poll(now)
        for _ in range(steps):
            self._sim_t_ms += self._sim_clock.step_ms
            self._sim_x = (self._sim_x + self._sim_vx * self._sim_clock.step_ms)
            if self._sim_anim_frames:
                self._sim_frame_tick += 1
                if self._sim_frame_tick >= self._sim_ticks_per_frame:
                    self._sim_frame_tick = 0
                    if self._sim_frame_idx + 1 >= len(self._sim_anim_frames):
                        if self._sim_loop:
                            self._sim_frame_idx = 0
                    else:
                        self._sim_frame_idx += 1
        self._render_sim_frame()
        self._sim_job = self.after(16, self._tick)

    def _render_sim_idle(self) -> None:
        fb = sim.Framebuffer()
        sim.fb_init(fb)
        self._sim_canvas.delete("all")
        self._render_fb_into(self._sim_canvas, fb, scale=3, ox=0, oy=0)
        flush = sim.framebuffer_to_pcd8544_bytes(fb)
        self._flush_var.set(f"{len(flush)} B (idle)")

    def _render_sim_frame(self) -> None:
        fb = sim.Framebuffer()
        sim.fb_init(fb)
        if self._sim_draw_cb is not None:
            self._sim_draw_cb(fb, self._sim_t_ms)
        else:
            self._builtin_draw(fb)
        self._sim_canvas.delete("all")
        self._render_fb_into(self._sim_canvas, fb, scale=3, ox=0, oy=0)
        flush = sim.framebuffer_to_pcd8544_bytes(fb)
        h = sum(flush) & 0xFF
        self._flush_var.set(f"{len(flush)} B  hash=0x{h:02X}")

    def _builtin_draw(self, fb) -> None:
        sim.fb_draw_hline(fb, 0, 0, sim.REF_W, True)
        sim.fb_draw_hline(fb, 0, sim.REF_H - 1, sim.REF_W, True)
        sim.fb_draw_vline(fb, 0, 0, sim.REF_H, True)
        sim.fb_draw_vline(fb, sim.REF_W - 1, 0, sim.REF_H, True)
        sprite = None
        if self._sim_anim_frames and self._sim_sheet:
            fw = self._sim_fw
            fh = self._sim_fh
            sw, sh, bits = self._sim_sheet
            cols = max(1, sw // fw)
            fid = self._sim_anim_frames[self._sim_frame_idx]
            tx = fid % cols
            ty = fid // cols
            row_bytes = (sw + 7) // 8
            sub_bits = []
            for y in range(fh):
                row_off = (ty * fh + y) * row_bytes + (tx * fw >> 3)
                sub_bits.append(bits[row_off])
            sprite = sim.make_sprite(fw, fh, sub_bits)
        elif self._sim_sprite:
            sprite = self._sim_sprite
        if sprite is not None:
            x = int(self._sim_x) % (sim.REF_W + sprite["w"])
            if x > sim.REF_W:
                x = x - sim.REF_W - sprite["w"]
            sim.fb_blit_sprite(fb, x, 20, sprite, True)
        sim.fb_draw_text(fb, 2, 2, "TINY8 STUDIO")
        sim.fb_draw_text(fb, 2, sim.REF_H - 10, f"T={self._sim_t_ms}ms")

    # --- drawing helpers ---------------------------------------------

    def _draw_bits(self, c, bits, w, h, scale, ox=0, oy=0) -> None:
        row_bytes = (w + 7) // 8
        for y in range(h):
            row = y * row_bytes
            for x in range(w):
                if bits[row + (x >> 3)] & (0x80 >> (x & 7)):
                    c.create_rectangle(
                        ox + x * scale, oy + y * scale,
                        ox + (x + 1) * scale, oy + (y + 1) * scale,
                        outline="", fill=th.PX_ON)

    def _render_fb_into(self, c, fb, scale, ox, oy) -> None:
        sw, sh = sim.REF_W, sim.REF_H
        c.config(width=sw * scale + ox * 2, height=sh * scale + oy * 2)
        for y in range(sh):
            for x in range(sw):
                if fb.px[(y >> 3) * sw + x] & (1 << (y & 7)):
                    c.create_rectangle(
                        ox + x * scale, oy + y * scale,
                        ox + (x + 1) * scale, oy + (y + 1) * scale,
                        outline="", fill=th.PX_ON)
