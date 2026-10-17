"""Tiny8 Engine — Milestone 10 host test: full demo game integration.

Re-implements every engine API the demo uses (scene state machine,
entity pool, tilemap, audio, save, input) on top of the existing Python
mirrors, then runs a script that exercises:

  1. Boot -> menu scene.
  2. Press A -> play scene, with player + 4 coins + 1 enemy.
  3. Move player to each coin -> coin picked up.
  4. After 4 coins -> game over scene.
  5. Press A -> back to menu.

Each state is verified by checking the active scene id and the
internal counters.  This proves the demo's wiring works end-to-end
without flashing a real Uno.
"""

import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "test"))

from test_m1_core import StepClock  # noqa: E402
from test_m2_framebuffer import Framebuffer  # noqa: E402
from test_m4_tilemap import Camera, cam_init, cam_follow, tilemap_view  # noqa: E402
from test_m5_entity import (  # noqa: E402
    T8_MAX_ENTITIES, T8_SUB, EF_ACTIVE, EF_SOLID, EF_PLAYER, EF_PICKUP, EF_ENEMY,
    ent_alloc, ent_free, ent_px, ent_aabb, ent_move,
    ent_pickup_scan, rect_overlap,
)
from test_m6_scene import scene_init, scene_push, scene_pop, scene_replace, scene_top, scene_depth  # noqa: E402
from test_m7_audio import audio_init, audio_set_enabled, audio_play, audio_stop, audio_tick, audio_last_freq  # noqa: E402
from test_m8_save import save_erase, save_write, save_read  # noqa: E402


# --- Re-implement the engine wrappers the demo uses. ---

# Input (simulated by test). The C++ engine treats `pressed` as a one-shot
# edge that is recomputed by input_poll() and consumed by the next read.
# We model that here: the test sets the desired state via input_set(),
# input_poll() computes the edge into _pressed, and input_pressed() reads
# (without clearing) the edge.
_held = [False] * 6
_pressed = [False] * 6
_prev_held = [False] * 6


def input_set(btn, held):
    """Queue the held state for the next input_poll()."""
    _held[btn] = held


def input_poll():
    """Recompute the pressed edge from the held state."""
    global _prev_held, _pressed
    for i in range(6):
        _pressed[i] = _held[i] and not _prev_held[i]
        _prev_held[i] = _held[i]


def input_held(b):    return _held[b]
def input_pressed(b): return _pressed[b]


# Demo constants matching the C++ demo.
BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT, BTN_A, BTN_START = 0, 1, 2, 3, 4, 5

REF_W, REF_H = 84, 48

# Demo map: 16x8 tiles.
DEMO_MAP_W = 16
DEMO_MAP_H = 8
DEMO_TILES = []
for ty in range(DEMO_MAP_H):
    row = []
    for tx in range(DEMO_MAP_W):
        if tx == 0 or ty == 0 or tx == 15 or ty == 7: row.append(1)
        elif (tx, ty) in {(3, 3), (3, 4), (8, 2), (9, 2), (8, 3), (9, 3), (12, 5), (12, 6)}: row.append(1)
        else: row.append(0)
    DEMO_TILES.append(row)

# Music tracks.
MENU_MUSIC = [45, 8, 47, 8, 50, 8, 47, 8, 45, 16, 0xFF, 0]
PLAY_MUSIC = [50, 4, 52, 4, 53, 4, 55, 8, 53, 4, 52, 4, 50, 8, 0xFF, 0]
OVER_MUSIC = [45, 16, 0xFE, 4, 43, 16, 0xFE, 4, 41, 24, 0xFF, 0]

# --- Demo game state ---

class Game:
    def __init__(self):
        self.coins = 0
        self.lives = 3
        self.paused = False


class DemoScene:
    """Re-implementation of the demo scenes. Each instance is a single
    Scene with enter/exit/update/draw hooks."""

    def __init__(self, sid, game):
        self.sid = sid
        self.g = game
        self.ents = [None] * T8_MAX_ENTITIES
        self.cam = Camera()
        self.map = {"tiles": [t for row in DEMO_TILES for t in row], "map_w": DEMO_MAP_W, "map_h": DEMO_MAP_H, "tile_px": 8}
        # Pre-spawn a player and 4 coins (always, so the menu->play swap
        # doesn't need to re-allocate).
        self._spawn_initial()

    def _spawn_initial(self):
        # Pre-populate the pool with empty entities, then mark them all
        # inactive so ent_alloc() treats them as free.
        self.ents = [dict(flags=0, x=0, y=0, vx=0, vy=0, w=8, h=8, sprite=None, tag=0) for _ in range(T8_MAX_ENTITIES)]
        for e in self.ents:
            e["flags"] = 0
        pi = ent_alloc(self.ents)
        self.ents[pi]["x"] = 16 * T8_SUB
        self.ents[pi]["y"] = 8 * T8_SUB
        self.ents[pi]["w"] = 8
        self.ents[pi]["h"] = 8
        self.ents[pi]["flags"] = EF_ACTIVE | EF_SOLID | EF_PLAYER
        for i in range(4):
            ci = ent_alloc(self.ents)
            if ci < 0: break
            self.ents[ci]["x"] = (8 + i * 16) * T8_SUB
            self.ents[ci]["y"] = (16 + (i % 2) * 8) * T8_SUB
            self.ents[ci]["w"] = 8
            self.ents[ci]["h"] = 8
            self.ents[ci]["flags"] = EF_ACTIVE | EF_PICKUP
            self.ents[ci]["tag"] = 1
        ei = ent_alloc(self.ents)
        self.ents[ei]["x"] = 80 * T8_SUB
        self.ents[ei]["y"] = 8 * T8_SUB
        self.ents[ei]["w"] = 8
        self.ents[ei]["h"] = 8
        self.ents[ei]["flags"] = EF_ACTIVE | EF_SOLID | EF_ENEMY

    def enter(self): pass
    def exit(self):  pass

    def on_pickup(self, p, c):
        self.g.coins += 1
        c["flags"] = 0

    def update(self):
        if self.sid == 1:  # menu
            if input_pressed(BTN_A) or input_pressed(BTN_START):
                self.g.coins = 0; self.g.lives = 3; self.g.paused = False
                self._spawn_initial()
                cam_init(self.cam, DEMO_MAP_W * 8, DEMO_MAP_H * 8)
                return ("replace", 2)
        elif self.sid == 2:  # play
            audio_tick()
            if input_pressed(BTN_START):
                self.g.paused = not self.g.paused
            if self.g.paused: return None
            p = self.ents[0]
            speed = 24
            p["vx"] = 0; p["vy"] = 0
            if input_held(BTN_LEFT):  p["vx"] = -speed
            if input_held(BTN_RIGHT): p["vx"] =  speed
            if input_held(BTN_UP):    p["vy"] = -speed
            if input_held(BTN_DOWN):  p["vy"] =  speed
            ent_move(self.ents, 0, DEMO_MAP_W * 8, DEMO_MAP_H * 8)
            ent_pickup_scan(self.ents, lambda a, b, u: self.on_pickup(a, b), None)
            cam_follow(self.cam, ent_px(p)[0] + p["w"]//2, ent_px(p)[1] + p["h"]//2, REF_W, REF_H)
            if self.g.coins >= 4:
                return ("replace", 3)
        elif self.sid == 3:  # over
            audio_tick()
            if input_pressed(BTN_A) or input_pressed(BTN_START):
                return ("replace", 1)
        return None

    def draw(self): return  # (no visible side effect; tested by counters.)


# --- Test driver ---

failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def run_scene(scene):
    """Update once. Returns the new scene id if a replace is requested."""
    input_poll()
    r = scene.update()
    if r is None: return scene.sid
    return r[1]


def test_full_demo_flow():
    audio_init(0); audio_set_enabled(True)
    g = Game()
    cur_sid = 1  # start at menu
    scenes = {1: DemoScene(1, g), 2: DemoScene(2, g), 3: DemoScene(3, g)}
    cur = scenes[cur_sid]
    # Step 1: menu, press A -> play.
    input_set(BTN_A, held=False)
    sid = run_scene(cur)  # warm up
    input_set(BTN_A, held=True)
    sid = run_scene(cur)
    check(sid == 2, f"menu + A -> play (got {sid})")
    cur = scenes[sid]

    # Step 2..5: walk player over each coin. We teleport the player to the
    # coin and let the next play tick pick it up.
    for i in range(4):
        c = scenes[2].ents[1 + i]  # 0 is player, 1..4 are coins
        if c is None:
            check(False, f"coin {i} exists")
            continue
        # Move player onto coin.
        cur.ents[0]["x"] = c["x"]
        cur.ents[0]["y"] = c["y"]
        cur.ents[0]["vx"] = cur.ents[0]["vy"] = 0
        sid = run_scene(cur)
        if i < 3:
            check(sid == 2, f"still in play after coin {i} (got {sid})")
        else:
            # The 4th coin completes the goal -> play -> over.
            check(sid == 3, f"play with 4 coins -> over (got {sid})")
            cur = scenes[sid]
        check(g.coins == i + 1, f"coin {i} collected (total {g.coins})")

    # Step 7: from over, press A -> menu.
    input_set(BTN_A, held=False)
    sid = run_scene(cur)  # warm up
    input_set(BTN_A, held=True)
    sid = run_scene(cur)
    check(sid == 1, f"over + A -> menu (got {sid})")


def test_save_load_round_trip_in_demo():
    # The demo doesn't actually save anything, but we can prove the save
    # API works for the kind of payload a real game would store.
    save_erase(0)
    payload = [0x00, 0x05, 0xFF]  # 3 lives, score=5, flag=FF
    check(save_write(0, payload, 3) == 0, "save_write ok")
    out = [0]*3
    check(save_read(0, out, 3) == 0, "save_read ok")
    check(out == payload, f"payload round-trips (got {out})")


def test_pause_overlay_doesnt_consume_pickup():
    g = Game()
    cur = DemoScene(2, g)
    # Place the player and coin within the 128x64 world bounds.
    cur.ents[0]["x"] = 100 * T8_SUB
    cur.ents[0]["y"] = 24 * T8_SUB
    cur.ents[1]["x"] = 100 * T8_SUB
    cur.ents[1]["y"] = 24 * T8_SUB
    # Press start to pause.
    input_set(BTN_START, held=True)
    sid = run_scene(cur)
    check(sid == 2, "still play after pause")
    check(g.paused is True, "paused")
    # While paused, coins should NOT be collected.
    input_set(BTN_START, held=True)  # still held
    sid = run_scene(cur)
    check(g.coins == 0, "no pickup while paused")
    # Unpause: release first, then press again.
    input_set(BTN_START, held=False)
    sid = run_scene(cur)  # poll: prev_held=True, held=False -> pressed=False; updates prev_held
    input_set(BTN_START, held=True)
    sid = run_scene(cur)  # poll: prev_held=False, held=True -> pressed=True -> toggle
    check(g.paused is False, "unpaused")
    sid = run_scene(cur)  # next tick: pickup scan
    check(g.coins == 1, "pickup after unpause")


if __name__ == "__main__":
    test_full_demo_flow()
    test_save_load_round_trip_in_demo()
    test_pause_overlay_doesnt_consume_pickup()
    print(f"M10 demo: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)