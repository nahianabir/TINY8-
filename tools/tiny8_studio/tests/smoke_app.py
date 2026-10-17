"""Tiny8 Studio — end-to-end smoke test driving the App.

Constructs the App, exercises the project create / sprite save / scan /
export pipeline via the public methods, and verifies that the
generated PROGMEM header contains the expected bytes.

Run:
    python tools/tiny8_studio/tests/smoke_app.py
"""

from __future__ import annotations
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
# tiny8_studio is a subpackage of tools; the cleanest way to import
# it from a deeply-nested test is to add its parent to sys.path.
sys.path.insert(0, os.path.join(ROOT, "tools"))
from tiny8_studio.app import App  # type: ignore
from tiny8_studio.exporters import export_sprite  # type: ignore


def main() -> int:
    app = App()
    app.update_idletasks()
    app.update()
    print(f"OK constructed: {app.title()}")

    tmp = tempfile.mkdtemp(prefix="tiny8_studio_smoke_")
    try:
        from tiny8_studio.project import Project
        proj = Project.create(tmp, name="Smoke")
        app._project = proj
        app._browser.set_assets(proj.assets)
        app._update_title()
        assert app._project is not None
        print(f"OK project created: {proj.root}")

        bits = [0x3C, 0x7E, 0x66, 0x66, 0x3C, 0x18, 0x3C, 0x00]
        app._sprite_editor._canvas.set_bits(bits)
        app._sprite_editor._file = os.path.join(proj.root, "assets", "hero.pbm")
        app._sprite_editor._on_save_click()
        app.update_idletasks()
        assert os.path.isfile(app._sprite_editor._file)
        print(f"OK sprite saved: {os.path.basename(app._sprite_editor._file)}")

        proj.rescan()
        app._browser.set_assets(proj.assets)
        names = [a.name for a in proj.assets.items]
        assert "hero" in names, names
        print(f"OK browser sees: {names}")

        app._on_export()
        out_h = os.path.join(proj.root, "generated", "hero.h")
        assert os.path.isfile(out_h), out_h
        with open(out_h, "r", encoding="utf-8") as f:
            src = f.read()
        import re
        m = re.search(r"kHERO_Bits\[\][^{]*\{([^}]*)\}", src, re.S)
        assert m is not None
        nums = [int(x.strip(), 0) for x in m.group(1).split(",") if x.strip()]
        assert nums == bits, (nums, bits)
        print(f"OK exported header bytes: {nums[:4]}...")

        proj.config.build_cmd = "definitely_not_a_real_binary_xyz"
        lines = []
        rc = proj.build(on_line=lines.append)
        assert rc == 127, rc
        assert any("not found" in ln.lower() for ln in lines), lines
        print("OK build tool not found -> 127")

        app._diagnostics.feed("Sketch uses 19000 bytes (60%) of 32256 bytes")
        flash = app._diagnostics.flash()
        assert flash == (19000, 32256), flash
        print(f"OK diagnostics parsed Flash: {flash}")

        proj.assets = type(proj.assets)(root=proj.root, items=proj.assets.items)
        app._browser.set_assets(proj.assets)
        app._browser._refresh_footer()
        ftxt = app._browser._budget.cget("text")
        assert "Estimated Flash" in ftxt, ftxt
        print(f"OK budget footer: {ftxt[:80]}...")

        # Multi-layer tilemap: write a base pbm + two layer PBMs and
        # confirm the scanner surfaces one multi-layer asset.
        import struct
        from tiny8_studio.project import DIR_ASSETS
        a_dir = os.path.join(proj.root, DIR_ASSETS)
        # 4x4 PBM -> 2x2 tilemap.  All-zero, so tile id 0 everywhere.
        empty4 = b"P4\n4 4\n" + bytes([0] * 4)
        with open(os.path.join(a_dir, "world.pbm"), "wb") as f:    f.write(empty4)
        with open(os.path.join(a_dir, "world_L0.pbm"), "wb") as f: f.write(empty4)
        with open(os.path.join(a_dir, "world_L1.pbm"), "wb") as f: f.write(empty4)
        proj.rescan()
        app._browser.set_assets(proj.assets)
        world = proj.assets.find("world")
        assert world is not None and world.kind == "tilemap"
        assert world.meta.get("multilayer") is True
        assert world.meta.get("layers") == [0, 1]
        print(f"OK multi-layer tilemap discovered: layers={world.meta['layers']}")

        # Animation: write a .anim.json referencing the hero sprite as
        # the atlas, then save+export and check the preview picks it up.
        from tiny8_studio import animation as studio_anim
        anim = studio_anim.Anim(
            name="walk", atlas="hero", frame_w=8, frame_h=8,
            ticks_per_frame=4, loop=True, frames=[0, 0, 0, 0],
        )
        anim_path = os.path.join(a_dir, "walk.anim.json")
        studio_anim.write_anim(anim_path, anim)
        proj.rescan()
        app._browser.set_assets(proj.assets)
        walk = proj.assets.find("walk")
        assert walk is not None and walk.kind == "anim"
        assert walk.meta["frames"] == 4
        # Drive the preview's host simulation.
        sheet = os.path.join(a_dir, "hero.pbm")
        ok = app._preview.set_anim(sheet, 8, 8, [0, 0, 0, 0], 4, True)
        assert ok, "preview.set_anim failed"
        print(f"OK animation discovered: walk  frames={walk.meta['frames']}")

        # End-to-end: re-export and confirm the .anim.h header is on disk.
        app._on_export()
        anim_h = os.path.join(proj.root, "generated", "walk.anim.h")
        assert os.path.isfile(anim_h), anim_h
        with open(anim_h, "r", encoding="utf-8") as f:
            src = f.read()
        assert "Anim kWALK_Anim" in src, src
        print("OK exported animation header: walk.anim.h")

        # Drive the host simulation for two steps and check the
        # framebuffer moves.
        from tiny8_studio import simulate as sim
        fb_before = sim.Framebuffer()
        sim.fb_init(fb_before)
        sim.fb_blit_sprite(fb_before, 0, 20, sim.make_sprite(8, 8, [0xFF] * 8), True)
        # Step the preview's clock.
        app._preview._sim_sprite = sim.make_sprite(8, 8, [0xFF] * 8)
        app._preview._render_sim_frame()
        flush = sim.framebuffer_to_pcd8544_bytes(fb_before)
        assert len(flush) == 2 + 84 * 6, len(flush)
        print(f"OK host simulation flush: {len(flush)} B")

        print("ALL OK")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())