"""Run all Tiny8 Engine host tests in sequence.

Exits 0 iff all suites pass.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(__file__)


def run(name):
    path = os.path.join(HERE, name)
    print(f"\n=== {name} ===")
    r = subprocess.run([sys.executable, path], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr: print("STDERR:", r.stderr, end="")
    return r.returncode


def main():
    tests = [
        "test_m1_core.py",
        "test_m2_framebuffer.py",
        "test_m4_tilemap.py",
        "test_m5_entity.py",
        "test_m6_scene.py",
        "test_m7_audio.py",
        "test_m8_save.py",
        "test_m9_converter.py",
        "test_m10_demo.py",
    ]
    failed = []
    for t in tests:
        rc = run(t)
        if rc != 0:
            failed.append(t)
    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    print("ALL SUITES PASS")


if __name__ == "__main__":
    main()