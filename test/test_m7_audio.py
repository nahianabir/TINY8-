"""Tiny8 Engine — Milestone 7 host tests: audio sequencer.

Mirrors the C++ logic. Verifies:
  * A 4-note track advances one note per audio_tick().
  * 0xFF terminates the track and silences it.
  * 0xFE is a rest (frequency 0).
  * audio_set_enabled(false) silences everything.
"""

import sys

T8_STEP_MS = 16


g_freq = 0
g_track = None
g_note = 0
g_ticks_left = 0
g_cur_note_id = 0xFE
g_enabled = True


def audio_init(pin):
    global g_freq, g_track, g_note, g_ticks_left
    g_freq = 0; g_track = None; g_note = 0; g_ticks_left = 0


def audio_set_enabled(on):
    global g_enabled, g_freq
    g_enabled = on
    if not on: g_freq = 0


def audio_play(track):
    global g_track, g_note, g_ticks_left
    g_track = track; g_note = 0; g_ticks_left = 0


def audio_stop():
    global g_track, g_freq
    g_track = None; g_freq = 0


def audio_tick():
    global g_track, g_note, g_ticks_left, g_cur_note_id, g_freq, g_enabled
    if not g_enabled:
        g_freq = 0; return
    if g_track is None: return
    if g_ticks_left == 0:
        id_ = g_track[g_note]
        if id_ == 0xFF:
            g_track = None; g_freq = 0; return
        g_cur_note_id = id_
        g_ticks_left = g_track[g_note + 1]
        g_note += 2
        if g_ticks_left > 0:
            g_ticks_left -= 1
    else:
        g_ticks_left -= 1
    if g_cur_note_id == 0xFE:
        g_freq = 0
    else:
        g_freq = g_cur_note_id * 10


def audio_last_freq(): return g_freq


failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def test_play_track():
    audio_init(0)
    audio_set_enabled(True)
    # Notes: id 45 (A4) for 2 ticks, 0xFE rest for 1 tick, id 50 (D5) for 3 ticks, 0xFF end.
    track = [45, 2, 0xFE, 1, 50, 3, 0xFF, 0]
    audio_play(track)
    # Tick 1: load note 45 -> freq=450
    audio_tick(); check(audio_last_freq() == 450, f"tick 1 freq=450 (got {audio_last_freq()})")
    # Tick 2: still playing 45 -> freq=450
    audio_tick(); check(audio_last_freq() == 450, f"tick 2 freq=450 (got {audio_last_freq()})")
    # Tick 3: load rest -> freq=0
    audio_tick(); check(audio_last_freq() == 0, f"tick 3 freq=0 (got {audio_last_freq()})")
    # Tick 4: load note 50 -> freq=500
    audio_tick(); check(audio_last_freq() == 500, f"tick 4 freq=500 (got {audio_last_freq()})")
    # Tick 5: still note 50 -> freq=500
    audio_tick(); check(audio_last_freq() == 500, f"tick 5 freq=500 (got {audio_last_freq()})")
    # Tick 6: still note 50 -> freq=500
    audio_tick(); check(audio_last_freq() == 500, f"tick 6 freq=500 (got {audio_last_freq()})")
    # Tick 7: load 0xFF -> track=None, freq=0
    audio_tick(); check(audio_last_freq() == 0, "tick 7 -> 0xFF, freq=0")


def test_disabled_silences():
    audio_init(0)
    audio_set_enabled(False)
    track = [45, 1, 0xFF, 0]
    audio_play(track)
    audio_tick()
    check(audio_last_freq() == 0, "disabled audio always silent")


def test_note_id_table():
    # Verify the host fakes a unique freq per note id, monotonic.
    audio_init(0)
    audio_set_enabled(True)
    # Each note: 1 tick long -> the load tick is the only tick that plays.
    track = [21, 1, 22, 1, 96, 1, 0xFF, 0]
    audio_play(track)
    # Tick 1: load id 21, freq=210.
    audio_tick(); f1 = audio_last_freq()
    # Tick 2: load id 22, freq=220.
    audio_tick(); f2 = audio_last_freq()
    # Tick 3: load id 96, freq=960.
    audio_tick(); f3 = audio_last_freq()
    check(f1 == 210, f"id 21 -> 210 (got {f1})")
    check(f2 == 220, f"id 22 -> 220 (got {f2})")
    check(f3 == 960, f"id 96 -> 960 (got {f3})")


if __name__ == "__main__":
    test_play_track()
    test_disabled_silences()
    test_note_id_table()
    print(f"M7 audio: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)