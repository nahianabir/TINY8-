"""Tiny8 Studio — headless tests.

The studio package's logic is tested without launching tkinter, so this
suite runs on a headless machine.  It covers:

  * project.create writes a valid skeleton
  * project.load round-trips the config
  * project.build surfaces "command not found" gracefully
  * validation limits match the converter's limits
  * assets.ProjectAssets.issues reports missing files
  * exporters.export_sprite and exporters.export_tilemap produce the
    same byte layout the engine expects (round-tripped through the
    converter itself)

Run:
    python tools/tiny8_studio/tests/test_tiny8_studio.py
"""

from __future__ import annotations
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

# Import the studio package (no tkinter needed for these tests).
from tiny8_studio import validation, project, assets, exporters  # type: ignore
from tiny8_studio import animation as studio_anim  # type: ignore
from tiny8_studio import simulate as studio_sim  # type: ignore
import sprite_convert as sc  # type: ignore


class TestValidationLimitsMatchConverter(unittest.TestCase):
    def test_sprite_limits_match(self):
        self.assertEqual(validation.MAX_SPRITE_W,      sc.MAX_SPRITE_W)
        self.assertEqual(validation.MAX_SPRITE_H,      sc.MAX_SPRITE_H)
        self.assertEqual(validation.MAX_PROGMEM_BYTES, sc.MAX_PROGMEM_BYTES)

    def test_sprite_byte_count(self):
        issues = validation.validate_sprite("ok", 8, 8, [0xFF] * 8)
        self.assertFalse(validation.issues_have_error(issues))
        issues = validation.validate_sprite("ok", 8, 8, [0xFF] * 4)  # short
        self.assertTrue(validation.issues_have_error(issues))

    def test_oversize_sprite(self):
        issues = validation.validate_sprite("big", 64, 1, [0] * 8)
        self.assertTrue(validation.issues_have_error(issues))

    def test_oversize_total(self):
        total, issues = validation.estimate_flash_bytes(
            [("a", 20_000), ("b", 20_000)])
        self.assertEqual(total, 40_000)
        self.assertTrue(validation.issues_have_error(issues))

    def test_undersized_total_warns(self):
        total, issues = validation.estimate_flash_bytes(
            [("a", 24_000)])
        self.assertEqual(total, 24_000)
        self.assertFalse(validation.issues_have_error(issues))
        self.assertTrue(any(i.level == "warn" for i in issues))

    def test_tilemap_palette_bounds(self):
        # Tile id 16 with palette 16 -> error.
        issues = validation.validate_tilemap("m", 4, 2,
            [0, 1, 0, 0, 0, 0, 0, 16], palette_size=16)
        self.assertTrue(validation.issues_have_error(issues))


class TestProjectLifecycle(unittest.TestCase):
    def test_create_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = project.Project.create(tmp, name="Hello")
            self.assertTrue(os.path.isfile(proj.config_path))
            self.assertTrue(os.path.isdir(os.path.join(tmp, "src")))
            self.assertTrue(os.path.isdir(os.path.join(tmp, "assets")))
            self.assertTrue(os.path.isdir(os.path.join(tmp, "generated")))

            # Reload and verify config round-trips.
            proj2 = project.Project(tmp)
            proj2.load()
            self.assertEqual(proj2.config.name, "Hello")
            self.assertEqual(proj2.config.fqbn, "arduino:avr:uno")

    def test_create_refuses_non_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "sentinel"), "w") as f:
                f.write("x")
            with self.assertRaises(FileExistsError):
                project.Project.create(tmp, name="X")

    def test_scan_picks_up_sprites(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            # Write a tiny PBM.
            with open(os.path.join(assets_dir, "foo.pbm"), "wb") as f:
                f.write(b"P4\n8 8\n" + bytes([0xFF] * 8))
            proj.rescan()
            self.assertIsNotNone(proj.assets.find("foo"))
            self.assertEqual(proj.assets.find("foo").meta["w"], 8)

    def test_scan_picks_up_tilemap_via_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            with open(os.path.join(assets_dir, "level.pbm"), "wb") as f:
                f.write(b"P4\n4 2\n" + bytes([0xFF] * 2))
            with open(os.path.join(assets_dir, "level.map.txt"), "w") as f:
                f.write("tilemap\n")
            proj.rescan()
            level = proj.assets.find("level")
            self.assertIsNotNone(level)
            self.assertEqual(level.kind, assets.KIND_TILEMAP)

    def test_issues_reports_missing(self):
        a = assets.Asset(kind=assets.KIND_SPRITE, name="x",
                         relpath="does/not/exist.pbm", meta={"w": 1, "h": 1})
        pa = assets.ProjectAssets(root="/", items=[a])
        iss = pa.issues()
        self.assertTrue(any("missing" in i.msg for i in iss))


class TestBuildCommandNotFound(unittest.TestCase):
    def test_unknown_command_returns_127(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = project.Project.create(tmp, name="X")
            proj.config.build_cmd = "definitely_not_a_real_binary_xyz"
            lines = []
            rc = proj.build(on_line=lines.append)
            self.assertEqual(rc, 127)
            self.assertTrue(any("ERROR" in ln for ln in lines))


class TestExportersRoundTrip(unittest.TestCase):
    """The GUI exporters must produce the same bytes the engine reads."""

    def test_sprite_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets_dir = os.path.join(tmp, "assets")
            out_dir    = os.path.join(tmp, "generated")
            os.makedirs(assets_dir)
            bits = [0b10000001, 0b01000010, 0b00100100, 0b00011000,
                    0b00011000, 0b00100100, 0b01000010, 0b10000001]
            with open(os.path.join(assets_dir, "arrow.pbm"), "wb") as f:
                f.write(b"P4\n8 8\n" + bytes(bits))
            header = exporters.export_sprite(
                os.path.join(assets_dir, "arrow.pbm"), out_dir, "arrow")
            self.assertTrue(os.path.isfile(header))
            # Sanity-check the header: contains expected identifiers.
            with open(header, "r", encoding="utf-8") as f:
                src = f.read()
            self.assertIn("kARROW_Bits", src)
            # The converter emits `kARROW_W      = 8;` with column-aligned
            # spaces; allow any whitespace between the name and the value.
            import re
            self.assertRegex(src, r"kARROW_W\s*=\s*8")
            self.assertRegex(src, r"kARROW_H\s*=\s*8")

    def test_tilemap_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets_dir = os.path.join(tmp, "assets")
            out_dir    = os.path.join(tmp, "generated")
            os.makedirs(assets_dir)
            # 4x2 tiles -> 8x4 PBM.  Tile 1 in top row middle, others 0.
            # We can just call sprite_convert via the GUI helper.
            grid = [[0, 1, 1, 0], [0, 0, 0, 0]]
            src = bytearray()
            for row in grid:
                for _ in range(2):
                    bits = []
                    for t in row:
                        bits += [1 if t else 0, 1 if t else 0]
                    byte = 0
                    for i, b in enumerate(bits):
                        if b: byte |= 0x80 >> i
                    src.append(byte)
            with open(os.path.join(assets_dir, "lvl.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes(src))
            header = exporters.export_tilemap(
                os.path.join(assets_dir, "lvl.pbm"), out_dir, "lvl")
            self.assertTrue(os.path.isfile(header))
            with open(header, "r", encoding="utf-8") as f:
                hsrc = f.read()
            self.assertIn("kLVLMapW = 4", hsrc)
            self.assertIn("kLVLMapH = 2", hsrc)
            # The tile ids should reflect the grid: 0,1,1,0,0,0,0,0.
            import re
            arr = re.search(r"kLVLTiles\[\][^{]*\{([^}]*)\}", hsrc, re.S)
            self.assertIsNotNone(arr)
            nums = [int(x.strip(), 0) for x in arr.group(1).split(",") if x.strip()]
            self.assertEqual(nums, [0, 1, 1, 0, 0, 0, 0, 0])

    def test_export_all_sprites_returns_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            with open(os.path.join(assets_dir, "a.pbm"), "wb") as f:
                f.write(b"P4\n8 8\n" + bytes([0xFF] * 8))
            # b.pbm: 4x2 tiles -> 8x4 px source.  row_bytes = 1, h = 4
            # (each tile row = 2 px; 2 tile rows = 4 px).  So 4 bytes.
            with open(os.path.join(assets_dir, "b.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            with open(os.path.join(assets_dir, "b.map.txt"), "w") as f:
                f.write("tilemap\n")
            written = exporters.export_all_sprites(tmp)
            self.assertEqual(len(written), 2)
            self.assertTrue(any(w.endswith("a.h")   for w in written))
            self.assertTrue(any(w.endswith("b_map.h") for w in written))


class TestSampleProjectMaker(unittest.TestCase):
    def test_make_sample_writes_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = sys.modules[__name__].__dict__.get("__main__")
            from tools.tiny8_studio.tests import make_sample_project  # type: ignore
            target = os.path.join(tmp, "sample")
            code = make_sample_project.main(target)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(os.path.join(target, "assets", "player.pbm")))
            self.assertTrue(os.path.isfile(os.path.join(target, "assets", "level.pbm")))
            self.assertTrue(os.path.isfile(os.path.join(target, "assets", "level.map.txt")))


class TestAnimationFormat(unittest.TestCase):
    def test_round_trip(self):
        a = studio_anim.Anim(
            name="walk", atlas="player", frame_w=8, frame_h=8,
            ticks_per_frame=6, loop=True,
            frames=[0, 1, 2, 1],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "walk.anim.json")
            studio_anim.write_anim(path, a)
            b = studio_anim.read_anim(path)
            self.assertEqual(b.name, "walk")
            self.assertEqual(b.atlas, "player")
            self.assertEqual(b.frames, [0, 1, 2, 1])
            self.assertEqual(b.ticks_per_frame, 6)
            self.assertEqual(b.loop, True)
            self.assertEqual(b.flash_bytes(), 4)

    def test_emit_header_matches_engine_struct(self):
        a = studio_anim.Anim(
            name="walk", atlas="player", frame_w=8, frame_h=8,
            ticks_per_frame=6, loop=True,
            frames=[0, 1, 2, 1],
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "walk.anim.h")
            studio_anim.write_anim_header(a, out)
            with open(out, "r", encoding="utf-8") as f:
                src = f.read()
            # Engine struct fields (whitespace-tolerant).
            import re
            self.assertRegex(src, r"kWALK_FrameW\s*=\s*8")
            self.assertRegex(src, r"kWALK_FrameH\s*=\s*8")
            self.assertRegex(src, r"kWALK_Ticks\s*=\s*6")
            self.assertRegex(src, r"kWALK_Loop\s*=\s*true")
            self.assertRegex(src, r"kWALK_FrameCount\s*=\s*4")
            self.assertIn("kPLAYER_SPRITE", src)
            self.assertIn("PROGMEM", src)
            # In-namespace declaration (engine convention).
            self.assertRegex(src, r"\bAnim kWALK_Anim\b")
            # Frame list.
            self.assertIn("0, 1, 2, 1", src)

    def test_emit_rejects_bad_frame_size(self):
        a = studio_anim.Anim(name="x", atlas="a", frame_w=64, frame_h=8,
                              frames=[0])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                studio_anim.write_anim_header(a, os.path.join(tmp, "x.h"))

    def test_emit_rejects_empty(self):
        a = studio_anim.Anim(name="x", atlas="a", frame_w=8, frame_h=8,
                              frames=[])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                studio_anim.write_anim_header(a, os.path.join(tmp, "x.h"))


class TestSimulateMatchesEngine(unittest.TestCase):
    """The host simulation must agree with the engine's test mirror on
    the same inputs.  We import the engine's existing mirrors and
    assert our sim returns the same results for the same operations.
    """

    def test_blit_transparent(self):
        # Make the engine's test mirrors importable.
        test_dir = os.path.join(ROOT, "test")
        if test_dir not in sys.path:
            sys.path.insert(0, test_dir)
        import test_m2_framebuffer as engine_m2  # type: ignore
        bits = [0x80]
        efb = engine_m2.Framebuffer()
        engine_m2.fb_init(efb)
        engine_m2.fb_blit(efb, 0, 0, 1, 1, bits, 1, True)
        sfb = studio_sim.Framebuffer()
        studio_sim.fb_init(sfb)
        studio_sim.fb_blit(sfb, 0, 0, 1, 1, bits, 1, True)
        self.assertEqual(sfb.px, efb.px)

    def test_blit_clips_to_screen(self):
        # 2 source bytes (one per row) for a 2x2 sprite; all bits set.
        bits = [0xFF, 0xFF]
        efb = studio_sim.Framebuffer()
        studio_sim.fb_init(efb)
        # Sprite at (-1, -1) with 2x2 bits.  Only the (0, 0) destination
        # pixel is in bounds.
        studio_sim.fb_blit(efb, -1, -1, 2, 2, bits, 1, True)
        # (0, 0) -> y=0, bit 1<<0 = 0x01.
        self.assertEqual(efb.px[0], 0x01)
        # Out of bounds writes do not crash.
        studio_sim.fb_blit(efb, 90, 50, 2, 2, bits, 1, True)
        self.assertEqual(efb.px[0], 0x01)

    def test_step_clock_bounded_catchup(self):
        c = studio_sim.StepClock(step_ms=16, max_catch=4)
        c.init(0)
        # First poll at +100 ms with 4 max catchup -> exactly 4 steps.
        n = c.poll(100)
        self.assertEqual(n, 4)
        # Consume remaining: 100 - 64 = 36 ms; should consume 2 more.
        n2 = c.poll(100)
        self.assertEqual(n2, 2)

    def test_pcd8544_flush_is_504_plus_command(self):
        fb = studio_sim.Framebuffer()
        studio_sim.fb_init(fb)
        # Touch one bit in each column of each page.
        for y in range(studio_sim.REF_H):
            studio_sim.fb_set_pixel(fb, 0, y, True)
        flush = studio_sim.framebuffer_to_pcd8544_bytes(fb)
        # 2 command bytes + 84 * 6 data bytes.
        self.assertEqual(len(flush), 2 + 84 * 6)
        # Command bytes.
        self.assertEqual(flush[0], 0x80)  # SET_Y (Y=0)
        self.assertEqual(flush[1], 0x40)  # SET_X (X=0)

    def test_pbm_to_tilemap(self):
        # 2x2 tiles = 4x4 PBM.  Each tile's top-left pixel is sampled
        # at the (2*tx, 2*ty) coordinate.  The PBM is MSB-first so a
        # set bit at (sx, sy) appears in row `sy` byte at position
        # `0x80 >> (sx & 7)`.
        #
        # We want tile ids [0, 1, 0, 1] for (col, row) = (0,0), (1,0),
        # (0,1), (1,1).  So:
        #   tile (1, 0) -> sx=2, sy=0 -> row 0 bit 2 -> 0x20
        #   tile (1, 1) -> sx=2, sy=2 -> row 2 bit 2 -> 0x20
        bits = [0x20, 0x20, 0x20, 0x20]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tm.pbm")
            with open(path, "wb") as f:
                f.write(b"P4\n4 4\n" + bytes(bits))
            tw, th, tiles = studio_sim.pbm_to_tilemap(path)
            self.assertEqual((tw, th), (2, 2))
            self.assertEqual(tiles, [0, 1, 0, 1])


class TestMultiLayerTilemapDiscovery(unittest.TestCase):
    def test_scan_picks_up_multi_layer_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            # world.pbm placeholder + world_L0.pbm, world_L1.pbm.
            with open(os.path.join(assets_dir, "world.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            with open(os.path.join(assets_dir, "world_L0.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            with open(os.path.join(assets_dir, "world_L1.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            proj = project.Project(tmp)
            proj.load()
            world = proj.assets.find("world")
            self.assertIsNotNone(world)
            self.assertEqual(world.kind, assets.KIND_TILEMAP)
            self.assertTrue(world.meta.get("multilayer"))
            self.assertEqual(world.meta.get("layers"), [0, 1])

    def test_export_multi_layer_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            with open(os.path.join(assets_dir, "world.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            with open(os.path.join(assets_dir, "world_L0.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            with open(os.path.join(assets_dir, "world_L1.pbm"), "wb") as f:
                f.write(b"P4\n8 4\n" + bytes([0xFF] * 4))
            written = exporters.export_all_sprites(tmp)
            # world sprite + world_L0 map + world_L1 map.
            names = sorted(os.path.basename(p) for p in written)
            self.assertIn("world.h", names)
            self.assertIn("world_L0_map.h", names)
            self.assertIn("world_L1_map.h", names)

    def test_scan_picks_up_anim_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            a = studio_anim.Anim(name="walk", atlas="player",
                                  frame_w=8, frame_h=8,
                                  ticks_per_frame=4, loop=True,
                                  frames=[0, 1, 2])
            studio_anim.write_anim(os.path.join(assets_dir, "walk.anim.json"), a)
            proj = project.Project(tmp)
            proj.load()
            walk = proj.assets.find("walk")
            self.assertIsNotNone(walk)
            self.assertEqual(walk.kind, "anim")
            self.assertEqual(walk.meta["frames"], 3)
            self.assertEqual(walk.flash_bytes(), 3)

    def test_export_anim_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            project.Project.create(tmp, name="X")
            assets_dir = os.path.join(tmp, "assets")
            a = studio_anim.Anim(name="walk", atlas="player",
                                  frame_w=8, frame_h=8,
                                  ticks_per_frame=4, loop=True,
                                  frames=[0, 1, 2])
            studio_anim.write_anim(os.path.join(assets_dir, "walk.anim.json"), a)
            written = exporters.export_all_sprites(tmp)
            names = [os.path.basename(p) for p in written]
            self.assertIn("walk.anim.h", names)
            with open(os.path.join(tmp, "generated", "walk.anim.h"), "r", encoding="utf-8") as f:
                src = f.read()
            self.assertRegex(src, r"\bAnim kWALK_Anim\b")


if __name__ == "__main__":
    # Ensure the tools dir is on sys.path so sprite_convert is importable.
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    unittest.main(verbosity=2)
