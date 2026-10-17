"""Tiny8 Studio — main application window.

Layout:

  +---------------------------------------------------------------+
  | menu + toolbar                                                |
  +---------+-----------------------------------+------------------+
  | assets  |  central editor                   |  preview         |
  | browser |  (sprite OR tilemap tab)          |                  |
  +---------+-----------------------------------+------------------+
  | build diagnostics (collapsible)                              |
  +---------------------------------------------------------------+

The asset browser and diagnostics are persistent; the central editor
swaps between the SpriteEditor and TilemapEditor based on the user's
choice.
"""

from __future__ import annotations
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from . import theme as th
from .assets import Asset, KIND_SPRITE, KIND_TILEMAP, KIND_SHEET, KIND_AUDIO
from .project import (
    Project, ProjectConfig, find_project_root,
    CONFIG_FILENAME, DIR_ASSETS, DIR_GENERATED, DIR_SRC,
)
from .validation import issues_have_error
from .widgets.asset_browser import AssetBrowser
from .widgets.diagnostics import DiagnosticsPane
from .widgets.preview import PreviewPane
from .widgets.sprite_editor import SpriteEditor
from .widgets.tilemap_editor import TilemapEditor
from .widgets.animation_editor import AnimationEditor


APP_NAME = "Tiny8 Studio"
APP_VERSION = "0.2"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1180x780")
        self.minsize(960, 640)
        self.configure(bg=th.BG)
        self._project: Optional[Project] = None
        self._build_proc: Optional[subprocess.Popen] = None
        self._build()

    # --- layout -------------------------------------------------------

    def _build(self) -> None:
        self._apply_style()
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()
        self._set_status("Ready.  Use File ▸ New Project to begin.")
        self._update_title()

    def _apply_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook",     background=th.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=th.BG_PANEL, foreground=th.FG,
                         padding=(12, 6), font=th.FONT_UI_B)
        style.map("TNotebook.Tab",
                  background=[("selected", th.BG_RAISED)],
                  foreground=[("selected", th.FG)])

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, tearoff=0, bg=th.BG_PANEL, fg=th.FG,
                          activebackground=th.ACCENT, activeforeground=th.FG_ON_ACC)
        self.config(menu=menubar)

        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="New Project…", accelerator="Ctrl+N",
                          command=self._on_new_project)
        m_file.add_command(label="Open Project…", accelerator="Ctrl+O",
                          command=self._on_open_project)
        m_file.add_command(label="Close Project", command=self._on_close_project)
        m_file.add_separator()
        m_file.add_command(label="Open Project Folder", command=self._on_open_folder)
        m_file.add_separator()
        m_file.add_command(label="Quit", accelerator="Ctrl+Q", command=self.destroy)
        menubar.add_cascade(label="File", menu=m_file)

        m_edit = tk.Menu(menubar, tearoff=0)
        m_edit.add_command(label="New Sprite",  accelerator="Ctrl+S",
                          command=lambda: self._show_editor("sprite"))
        m_edit.add_command(label="New Tilemap", accelerator="Ctrl+T",
                          command=lambda: self._show_editor("tilemap"))
        m_edit.add_command(label="New Animation", accelerator="Ctrl+A",
                          command=lambda: self._show_editor("animation"))
        menubar.add_cascade(label="Edit", menu=m_edit)

        m_build = tk.Menu(menubar, tearoff=0)
        m_build.add_command(label="Export PROGMEM", accelerator="Ctrl+E",
                           command=self._on_export)
        m_build.add_command(label="Build", accelerator="Ctrl+B",
                           command=self._on_build)
        m_build.add_command(label="Stop", command=self._on_stop_build)
        menubar.add_cascade(label="Build", menu=m_build)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Open docs/BUILD.md",
                          command=lambda: self._open_path("docs/BUILD.md"))
        m_help.add_command(label="Open docs/API.md",
                          command=lambda: self._open_path("docs/API.md"))
        m_help.add_command(label="Open docs/PINS.md",
                          command=lambda: self._open_path("docs/PINS.md"))
        m_help.add_separator()
        m_help.add_command(label="About", command=self._on_about)
        menubar.add_cascade(label="Help", menu=m_help)

        # Keyboard shortcuts.
        self.bind_all("<Control-n>", lambda e: self._on_new_project())
        self.bind_all("<Control-o>", lambda e: self._on_open_project())
        self.bind_all("<Control-b>", lambda e: self._on_build())
        self.bind_all("<Control-e>", lambda e: self._on_export())
        self.bind_all("<Control-q>", lambda e: self.destroy())
        self.bind_all("<Control-s>", lambda e: self._show_editor("sprite"))
        self.bind_all("<Control-t>", lambda e: self._show_editor("tilemap"))
        self.bind_all("<Control-a>", lambda e: self._show_editor("animation"))

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg=th.BG_PANEL, height=44)
        bar.pack(side=tk.TOP, fill=tk.X)
        bar.pack_propagate(False)
        bk = dict(relief=tk.FLAT, bd=0, padx=12, pady=6, font=th.FONT_UI)
        tk.Button(bar, text="New", bg=th.BG_RAISED, fg=th.FG,
                  activebackground=th.BG_HOVER, activeforeground=th.FG,
                  command=self._on_new_project, **bk).pack(side=tk.LEFT, padx=(8, 4), pady=6)
        tk.Button(bar, text="Open", bg=th.BG_RAISED, fg=th.FG,
                  activebackground=th.BG_HOVER, activeforeground=th.FG,
                  command=self._on_open_project, **bk).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(bar, text="Sprite", bg=th.BG_RAISED, fg=th.FG,
                  activebackground=th.BG_HOVER, activeforeground=th.FG,
                  command=lambda: self._show_editor("sprite"), **bk
                  ).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(bar, text="Tilemap", bg=th.BG_RAISED, fg=th.FG,
                  activebackground=th.BG_HOVER, activeforeground=th.FG,
                  command=lambda: self._show_editor("tilemap"), **bk
                  ).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(bar, text="Animation", bg=th.BG_RAISED, fg=th.FG,
                  activebackground=th.BG_HOVER, activeforeground=th.FG,
                  command=lambda: self._show_editor("animation"), **bk
                  ).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(bar, text="Export", bg=th.BG_RAISED, fg=th.FG,
                  activebackground=th.BG_HOVER, activeforeground=th.FG,
                  command=self._on_export, **bk).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(bar, text="Build", bg=th.ACCENT, fg=th.FG_ON_ACC,
                  activebackground=th.ACCENT_DARK, activeforeground=th.FG_ON_ACC,
                  command=self._on_build, **bk).pack(side=tk.LEFT, padx=4, pady=6)
        # Right: project name.
        self._proj_label = tk.Label(bar, text="(no project)", bg=th.BG_PANEL,
                                    fg=th.FG_DIM, font=th.FONT_UI_B, padx=12)
        self._proj_label.pack(side=tk.RIGHT, pady=6)

    def _build_body(self) -> None:
        body = tk.Frame(self, bg=th.BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # 3-column layout: assets | editor | preview
        body.grid_columnconfigure(0, weight=0, minsize=320)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=0, minsize=420)
        body.grid_rowconfigure(0, weight=3, minsize=300)
        body.grid_rowconfigure(1, weight=2, minsize=200)

        # Left: asset browser.
        self._browser = AssetBrowser(body,
            on_open=self._on_open_asset,
            on_export=lambda _items: self._on_export())
        self._browser.grid(row=0, column=0, sticky="nsew", rowspan=2,
                           padx=(th.PAD, th.PAD_TIGHT), pady=th.PAD)

        # Center: editor with tabs.
        self._editor_holder = tk.Frame(body, bg=th.BG)
        self._editor_holder.grid(row=0, column=1, sticky="nsew",
                                  padx=th.PAD_TIGHT, pady=th.PAD)
        self._editor_tabs = ttk.Notebook(self._editor_holder)
        self._editor_tabs.pack(fill=tk.BOTH, expand=True)
        self._sprite_editor = SpriteEditor(self._editor_tabs,
            on_save=self._on_editor_saved)
        self._tilemap_editor = TilemapEditor(self._editor_tabs,
            on_save=self._on_editor_saved)
        self._animation_editor = AnimationEditor(self._editor_tabs,
            on_save=self._on_animation_saved)
        self._editor_tabs.add(self._sprite_editor, text="Sprite")
        self._editor_tabs.add(self._tilemap_editor, text="Tilemap")
        self._editor_tabs.add(self._animation_editor, text="Animation")

        # Right: preview.
        self._preview = PreviewPane(body)
        self._preview.grid(row=0, column=2, sticky="nsew",
                            padx=(th.PAD_TIGHT, th.PAD), pady=th.PAD)

        # Bottom: diagnostics.
        self._diagnostics = DiagnosticsPane(body)
        self._diagnostics.grid(row=1, column=1, columnspan=2, sticky="nsew",
                                padx=th.PAD_TIGHT, pady=(0, th.PAD))
        self._diagnostics._on_clear = self._diagnostics.clear

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg=th.BG_PANEL, height=24)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)
        self._status = tk.Label(bar, text="", bg=th.BG_PANEL, fg=th.FG_DIM,
                                 font=th.FONT_UI, anchor=tk.W, padx=8)
        self._status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._pill = tk.Label(bar, text=f"v{APP_VERSION}", bg=th.BG_PANEL,
                               fg=th.FG_MUTED, font=th.FONT_UI, padx=8)
        self._pill.pack(side=tk.RIGHT)

    # --- helpers ------------------------------------------------------

    def _set_status(self, text: str, level: str = "info") -> None:
        colors = {"info": th.FG_DIM, "ok": th.FG_OK, "warn": th.FG_WARN, "err": th.FG_ERROR}
        self._status.config(text=text, fg=colors.get(level, th.FG_DIM))

    def _update_title(self) -> None:
        name = self._project.config.name if self._project else None
        self.title(f"{APP_NAME} — {name}" if name else APP_NAME)
        self._proj_label.config(
            text=(self._project.config.name + "  " + self._project.root)
                 if self._project else "(no project)",
            fg=th.FG if self._project else th.FG_DIM)

    def _show_editor(self, which: str) -> None:
        idx = {"sprite": 0, "tilemap": 1, "animation": 2}.get(which, 0)
        self._editor_tabs.select(idx)

    def _on_editor_saved(self, path: str, _bits, _w, _h) -> None:
        if not self._project:
            return
        self._project.rescan()
        self._browser.set_assets(self._project.assets)
        self._set_status(f"Saved {os.path.basename(path)}", "ok")
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        sel = self._browser.selected()
        if sel and sel.exists and sel.kind in (KIND_SPRITE, KIND_SHEET, KIND_TILEMAP):
            self._preview.show_pbm(sel.relpath, kind=sel.kind)

    def _open_path(self, rel: str) -> None:
        """Open a file or folder with the OS default application."""
        if not os.path.isabs(rel):
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            full = os.path.normpath(os.path.join(base, rel))
        else:
            full = rel
        if not os.path.exists(full):
            messagebox.showerror("Not found", f"{full} does not exist")
            return
        try:
            if sys.platform == "win32":
                os.startfile(full)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", full])
            else:
                subprocess.Popen(["xdg-open", full])
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    # --- file actions -------------------------------------------------

    def _on_new_project(self) -> None:
        if self._project is not None:
            if not messagebox.askyesno("Discard current project?",
                "Opening a new project will close the current one. Continue?"):
                return
        path = filedialog.askdirectory(title="Choose empty folder for new project")
        if not path:
            return
        name = os.path.basename(os.path.normpath(path)) or "Tiny8Game"
        try:
            proj = Project.create(path, name=name)
        except FileExistsError as e:
            messagebox.showerror("Folder not empty", str(e))
            return
        except Exception as e:
            messagebox.showerror("Create failed", str(e))
            return
        self._project = proj
        self._browser.set_assets(proj.assets)
        self._update_title()
        self._diagnostics.clear()
        self._set_status(f"Created project {name} at {proj.root}", "ok")

    def _on_open_project(self) -> None:
        path = filedialog.askdirectory(title="Open Tiny8 project (folder)")
        if not path:
            return
        self._open_project_path(path)

    def _open_project_path(self, path: str) -> None:
        # If the chosen folder doesn't have project.t8p, search upwards.
        if not os.path.isfile(os.path.join(path, CONFIG_FILENAME)):
            root = find_project_root(path)
            if root is None:
                messagebox.showerror("Not a Tiny8 project",
                    f"{path} has no project.t8p")
                return
            path = root
        try:
            proj = Project(path)
            proj.load()
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
            return
        self._project = proj
        self._browser.set_assets(proj.assets)
        self._update_title()
        self._set_status(f"Opened {proj.root}", "ok")

    def _on_close_project(self) -> None:
        if not self._project:
            return
        self._project = None
        from .assets import ProjectAssets
        self._browser.set_assets(ProjectAssets(root=""))
        self._update_title()
        self._set_status("Project closed", "info")

    def _on_open_folder(self) -> None:
        if not self._project:
            messagebox.showinfo("No project", "Open a project first.")
            return
        self._open_path(self._project.root)

    def _on_open_asset(self, a: Asset) -> None:
        if a.kind == "anim":
            self._show_editor("animation")
            self._animation_editor.load_file(a.relpath)
        elif a.kind == KIND_SPRITE:
            self._show_editor("sprite")
            self._sprite_editor.load_file(a.relpath)
        elif a.kind == KIND_TILEMAP:
            self._show_editor("tilemap")
            if a.meta.get("multilayer"):
                self._tilemap_editor.load_layers(a.relpath)
            else:
                self._tilemap_editor.load_file(a.relpath)
        else:
            messagebox.showinfo("Cannot open",
                f"Cannot edit {a.kind} assets directly.")
            return
        self._refresh_preview()

    def _on_animation_saved(self, path: str, anim) -> None:
        if not self._project:
            return
        self._project.rescan()
        self._browser.set_assets(self._project.assets)
        self._set_status(f"Saved {os.path.basename(path)}", "ok")
        # Wire the preview's host simulation to the saved animation.
        sheet = os.path.join(self._project.root, DIR_ASSETS,
                              anim.atlas + ".pbm")
        if os.path.isfile(sheet):
            self._preview.set_anim(
                sheet, anim.frame_w, anim.frame_h,
                anim.frames, anim.ticks_per_frame, anim.loop,
            )

    # --- export / build ----------------------------------------------

    def _on_export(self) -> None:
        if not self._project:
            messagebox.showinfo("No project", "Open a project first.")
            return
        from .exporters import export_all_sprites
        try:
            written = export_all_sprites(self._project.root)
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return
        self._project.rescan()
        self._browser.set_assets(self._project.assets)
        if written:
            self._set_status(f"Exported {len(written)} header(s) to generated/",
                              "ok")
        else:
            self._set_status("No PBM assets to export.", "warn")

    def _on_build(self) -> None:
        if not self._project:
            messagebox.showinfo("No project", "Open a project first.")
            return
        # Always re-export before building.
        from .exporters import export_all_sprites
        try:
            export_all_sprites(self._project.root)
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return
        self._diagnostics.clear()
        self._diagnostics.feed(f"--- build {self._project.config.name} ---")
        rc = self._project.build(on_line=self._diagnostics.feed)
        if rc == 0:
            self._set_status("Build succeeded.", "ok")
        elif rc == 127:
            self._set_status("Build tool not found.  See Build ▸ Open docs/BUILD.md.",
                              "err")
        else:
            self._set_status(f"Build failed (exit {rc}).", "err")
        self._project.rescan()
        self._browser.set_assets(self._project.assets)

    def _on_stop_build(self) -> None:
        if self._build_proc and self._build_proc.poll() is None:
            try:
                self._build_proc.terminate()
            except Exception:
                pass
            self._set_status("Build terminated.", "warn")

    def _on_about(self) -> None:
        messagebox.showinfo(APP_NAME,
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A lightweight GUI for the Tiny8 game engine.\n"
            "Engine source is independent of this tool.\n\n"
            f"Python {sys.version.split()[0]}\n"
            "Tk " + str(self.tk.call("info", "patchlevel")))
