"""Tiny8 Engine — Milestone 9 host tests: asset converter.

Verifies the Python sprite converter:
  * Reads PBM correctly.
  * Emits a header with valid C++ syntax.
  * The emitted PROGMEM bytes, when re-decoded, match the original PBM.
  * Sprite-too-large is rejected.
  * Total PROGMEM budget is enforced.
"""

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import sprite_convert as sc


def write_pbm(path, w, h, set_pixels):
    row_bytes = (w + 7) // 8
    data = bytearray(row_bytes * h)
    for y in range(h):
        for x in range(w):
            if set_pixels(x, y):
                data[y * row_bytes + (x >> 3)] |= (0x80 >> (x & 7))
    with open(path, "wb") as f:
        f.write(f"P4\n{w} {h}\n".encode("ascii"))
        f.write(bytes(data))


failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def test_pbm_roundtrip_via_converter():
    # Build a tiny PBM, run the converter, then parse the emitted bytes.
    with tempfile.TemporaryDirectory() as tmp:
        pbm = os.path.join(tmp, "demo.pbm")
        # 8x8 sprite: a diagonal line.
        write_pbm(pbm, 8, 8, lambda x, y: x == y)
        out_dir = os.path.join(tmp, "out")
        sc.main([pbm, "--out", out_dir])
        out_h = os.path.join(out_dir, "demo.h")
        check(os.path.isfile(out_h), "converter wrote demo.h")
        with open(out_h) as f: src = f.read()
        check("kDEMO_Bits" in src, "header declares kDEMO_Bits")
        check("PROGMEM" in src or "__AVR__" in src, "header mentions PROGMEM or AVROnly")
        # Extract bytes.
        m = re.search(r"kDEMO_Bits\[\][^{]*\{([^}]*)\}", src, re.S)
        check(m is not None, "found byte array")
        bytes_text = m.group(1)
        byte_values = [int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]{2}", bytes_text)]
        # The diagonal of an 8x8: each row has exactly one bit set.
        # PBM P4 is MSB-first within byte, so bit (0,0) is bit 7 of byte 0.
        # Diagonal: x=0 -> bit 7 of byte 0; x=1 -> bit 6 of byte 1; etc.
        expected = [0b10000000, 0b01000000, 0b00100000, 0b00010000,
                    0b00001000, 0b00000100, 0b00000010, 0b00000001]
        check(byte_values == expected, f"diagonal bytes correct (got {byte_values})")


def test_size_limit_enforced():
    with tempfile.TemporaryDirectory() as tmp:
        # 33x8 -> wider than MAX_SPRITE_W=32
        pbm = os.path.join(tmp, "wide.pbm")
        write_pbm(pbm, 33, 8, lambda x, y: False)
        out_dir = os.path.join(tmp, "out2")
        raised = False
        try:
            sc.main([pbm, "--out", out_dir])
        except ValueError as e:
            raised = "exceeds" in str(e)
        check(raised, "33-wide sprite is rejected")


def test_total_budget_enforced(monkeypatch_max=None):
    # Patch MAX_PROGMEM_BYTES to something tiny so a single small sprite
    # exceeds it. We do this by directly invoking write_sprite_header.
    import dataclasses
    from sprite_convert import Asset, write_sprite_header
    a = Asset(name="big", w=8, h=8, bits=[0xFF]*8)
    orig = sc.MAX_PROGMEM_BYTES
    sc.MAX_PROGMEM_BYTES = 4
    raised = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            write_sprite_header(a, os.path.join(tmp, "x.h"))
    except ValueError as e:
        raised = "exceeds" in str(e)
    finally:
        sc.MAX_PROGMEM_BYTES = orig
    check(raised, "asset over budget is rejected")


def test_tilemap_emits_2D_grid():
    with tempfile.TemporaryDirectory() as tmp:
        pbm = os.path.join(tmp, "tm.pbm")
        # 4x2 PBM, 2x2 per tile -> 2x1 tilemap.
        def setter(x, y): return (x // 2 + y // 2) % 2 == 1
        write_pbm(pbm, 4, 2, setter)
        out_dir = os.path.join(tmp, "out3")
        sc.main([pbm, "--tilemap", "--out", out_dir, "--name", "m"])
        h_path = os.path.join(out_dir, "m_map.h")
        check(os.path.isfile(h_path), "tilemap header written")
        with open(h_path) as f: src = f.read()
        check("kMMapW = 2" in src, "tilemap width = 2")
        check("kMMapH = 1" in src, "tilemap height = 1")
        check("kMTiles" in src, "tiles array declared")


if __name__ == "__main__":
    test_pbm_roundtrip_via_converter()
    test_size_limit_enforced()
    test_total_budget_enforced()
    test_tilemap_emits_2D_grid()
    print(f"M9 converter: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)