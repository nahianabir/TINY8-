"""Tiny8 Engine — Milestone 8 host tests: versioned save slots.

Mirrors the C++ logic with a RAM-backed store. Verifies:
  * save_read on a blank slot returns NoSave.
  * save_write then save_read round-trips the bytes.
  * Corrupting one byte causes CrcFail.
  * save_erase returns the slot to blank.
  * Wrong version returns BadVersion.
"""

import sys

T8_SAVE_SLOTS = 4
T8_SAVE_BYTES = 16
T8_SAVE_VERSION = 0x01
T8_SAVE_MAGIC = 0xA5

OK = 0
NO_SAVE = -3
CRC_FAIL = -4
BAD_VERSION = -5
BAD_ARG = -2


def crc8(data, seed=0):
    c = seed
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if (c & 0x80) else (c << 1) & 0xFF
    return c


g_store = [0xFF] * (T8_SAVE_SLOTS * T8_SAVE_BYTES)


def _off(slot): return slot * T8_SAVE_BYTES


def save_write(slot, data, n):
    if slot >= T8_SAVE_SLOTS: return BAD_ARG
    if n + 3 > T8_SAVE_BYTES: return BAD_ARG
    off = _off(slot)
    buf = [T8_SAVE_MAGIC, T8_SAVE_VERSION] + list(data[:n])
    buf.append(crc8(buf))
    for i, b in enumerate(buf):
        g_store[off + i] = b
    return OK


def save_read(slot, out, n):
    if slot >= T8_SAVE_SLOTS: return BAD_ARG
    if n + 3 > T8_SAVE_BYTES: return BAD_ARG
    off = _off(slot)
    buf = g_store[off:off + n + 3]
    if buf[0] != T8_SAVE_MAGIC:   return NO_SAVE
    if buf[1] != T8_SAVE_VERSION: return BAD_VERSION
    if crc8(buf[:n+2]) != buf[n+2]: return CRC_FAIL
    for i in range(n): out[i] = buf[2 + i]
    return OK


def save_erase(slot):
    if slot >= T8_SAVE_SLOTS: return BAD_ARG
    off = _off(slot)
    for i in range(T8_SAVE_BYTES): g_store[off + i] = 0xFF
    return OK


failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def test_blank_returns_no_save():
    for s in range(T8_SAVE_SLOTS):
        save_erase(s)
    out = [0] * 8
    check(save_read(0, out, 8) == NO_SAVE, "blank slot -> NoSave")


def test_round_trip():
    save_erase(0)
    payload = [0x10, 0x20, 0x30, 0x40]
    check(save_write(0, payload, 4) == OK, "write ok")
    out = [0] * 4
    check(save_read(0, out, 4) == OK, "read ok")
    check(out == payload, f"payload round-trips (got {out})")


def test_crc_mismatch():
    save_erase(1)
    payload = [0xAA, 0xBB, 0xCC]
    save_write(1, payload, 3)
    # Corrupt a data byte.
    g_store[_off(1) + 3] ^= 0x01
    out = [0] * 3
    check(save_read(1, out, 3) == CRC_FAIL, "corrupted byte -> CrcFail")


def test_version_mismatch():
    save_erase(2)
    payload = [0x01, 0x02]
    save_write(2, payload, 2)
    g_store[_off(2) + 1] = 0x99  # wrong version
    out = [0] * 2
    check(save_read(2, out, 2) == BAD_VERSION, "wrong version -> BadVersion")


def test_erase():
    save_erase(3)
    payload = [0xDE, 0xAD, 0xBE, 0xEF]
    save_write(3, payload, 4)
    save_erase(3)
    out = [0] * 4
    check(save_read(3, out, 4) == NO_SAVE, "erased -> NoSave")


def test_bad_slot():
    check(save_write(T8_SAVE_SLOTS, [0], 1) == BAD_ARG, "write bad slot")
    check(save_read(T8_SAVE_SLOTS, [0]*1, 1) == BAD_ARG, "read bad slot")


if __name__ == "__main__":
    test_blank_returns_no_save()
    test_round_trip()
    test_crc_mismatch()
    test_version_mismatch()
    test_erase()
    test_bad_slot()
    print(f"M8 save: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)