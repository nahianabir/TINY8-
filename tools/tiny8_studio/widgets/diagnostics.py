"""Tiny8 Studio — build diagnostics.

A read-only scrolling log that subscribes to the project's build
process.  Parses arduino-cli's output for Flash / SRAM usage and
surfaces a one-line summary above the log.
"""

from __future__ import annotations
import re
import tkinter as tk
from typing import Callable, Optional

from .. import theme as th


# Regexes lifted from the arduino-cli output format.
RE_FLASH  = re.compile(r"Sketch uses\s+(\d+)\s+bytes.*?of\s+(\d+)", re.I)
RE_SRAM   = re.compile(r"Global variables use\s+(\d+)\s+bytes.*?of\s+(\d+)", re.I)


class DiagnosticsPane(tk.Frame):
    def __init__(self, master, on_clear: Optional[Callable[[], None]] = None,
                 **kw):
        super().__init__(master, bg=th.BG, **kw)
        self._on_clear = on_clear
        self._build()

    def _build(self) -> None:
        hdr = tk.Frame(self, bg=th.BG)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=th.PAD)
        tk.Label(hdr, text="Build", bg=th.BG, fg=th.FG,
                 font=th.FONT_TITLE).pack(side=tk.LEFT)
        if self._on_clear:
            tk.Button(hdr, text="Clear", command=self._on_clear, **self._btn_kw()
                     ).pack(side=tk.RIGHT)

        self._summary = tk.Label(self, text="(no build yet)",
                                 bg=th.BG, fg=th.FG_DIM, font=th.FONT_UI,
                                 anchor=tk.W)
        self._summary.pack(side=tk.TOP, fill=tk.X, padx=th.PAD, pady=(0, 4))

        wrap = tk.Frame(self, bg=th.BORDER, bd=1)
        wrap.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                  padx=th.PAD, pady=(0, th.PAD))
        self._log = tk.Text(wrap, bg=th.BG_INPUT, fg=th.FG,
                            insertbackground=th.FG,
                            font=th.FONT_MONO, relief=tk.FLAT, wrap=tk.NONE)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self._log.yview)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self._log.config(yscrollcommand=sb.set)
        self._log.config(state=tk.DISABLED)
        # Tag colors.
        self._log.tag_configure("err", foreground=th.FG_ERROR)
        self._log.tag_configure("warn", foreground=th.FG_WARN)
        self._log.tag_configure("ok", foreground=th.FG_OK)
        self._log.tag_configure("cmd", foreground=th.ACCENT)
        self._latest_flash = self._latest_sram = None

    def _btn_kw(self) -> dict:
        return dict(
            bg=th.BG_RAISED, fg=th.FG,
            activebackground=th.BG_HOVER, activeforeground=th.FG,
            relief=tk.FLAT, bd=0, padx=10, pady=4, font=th.FONT_UI,
        )

    # --- public API ---------------------------------------------------

    def feed(self, line: str) -> None:
        """Append a line of build output.  Called from the build runner."""
        tag = ""
        low = line.lower()
        if "error" in low or "failed" in low:
            tag = "err"
        elif "warning" in low:
            tag = "warn"
        elif low.startswith("$"):
            tag = "cmd"
        elif "exit 0" in low:
            tag = "ok"
        m = RE_FLASH.search(line)
        if m:
            self._latest_flash = (int(m.group(1)), int(m.group(2)))
            tag = "ok"
        m = RE_SRAM.search(line)
        if m:
            self._latest_sram = (int(m.group(1)), int(m.group(2)))
            tag = "ok"
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, line + "\n", tag)
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)
        self._refresh_summary()

    def clear(self) -> None:
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)
        self._summary.config(text="(cleared)", fg=th.FG_DIM)
        self._latest_flash = self._latest_sram = None

    def flash(self) -> Optional[tuple[int, int]]:
        return self._latest_flash

    def sram(self) -> Optional[tuple[int, int]]:
        return self._latest_sram

    def _refresh_summary(self) -> None:
        parts = []
        if self._latest_flash:
            used, total = self._latest_flash
            pct = 100 * used / max(1, total)
            parts.append(f"Flash: {used}/{total} B ({pct:.0f}%)")
        if self._latest_sram:
            used, total = self._latest_sram
            pct = 100 * used / max(1, total)
            parts.append(f"SRAM:  {used}/{total} B ({pct:.0f}%)")
        if not parts:
            self._summary.config(text="(build output will appear here)",
                                 fg=th.FG_DIM)
        else:
            self._summary.config(text="   ".join(parts), fg=th.FG)