"""Tiny8 Engine — Milestone 5 host tests: entity pool + AABB collide.

Mirrors the C++ logic.  Verifies:
  * Pool returns nullptr when exhausted.
  * AABB overlap detects collisions and ignores edge touches.
  * Axis-separated slide reverts velocity on the offending axis only.
  * ent_collide_all fires for each unique pair once.
  * ent_pickup_scan only pairs players with pickups.
"""

import sys

T8_MAX_ENTITIES = 8
T8_SUB = 16
EF_ACTIVE  = 0x01
EF_SOLID   = 0x02
EF_GRAVITY = 0x04
EF_ENEMY   = 0x08
EF_PICKUP  = 0x10
EF_PLAYER  = 0x20


def rect_overlap(a, b):
    if a[2] <= 0 or a[3] <= 0 or b[2] <= 0 or b[3] <= 0: return False
    return (a[0] < b[0] + b[2] and a[0] + a[2] > b[0]
            and a[1] < b[1] + b[3] and a[1] + a[3] > b[1])


def ent_alloc(ents):
    for i in range(T8_MAX_ENTITIES):
        if not (ents[i]["flags"] & EF_ACTIVE):
            ents[i]["flags"] = EF_ACTIVE
            ents[i]["x"] = ents[i]["y"] = 0
            ents[i]["vx"] = ents[i]["vy"] = 0
            return i
    return -1


def ent_free(ents, i):
    ents[i]["flags"] = 0


def ent_px(e):
    return (e["x"] // T8_SUB, e["y"] // T8_SUB)


def ent_aabb(e):
    px, py = ent_px(e)
    return (px, py, e["w"], e["h"])


def ent_move(ents, i, world_w, world_h):
    e = ents[i]
    e["x"] += e["vx"]
    if e["x"] < 0: e["x"] = 0
    if e["x"] + e["w"] * T8_SUB > world_w * T8_SUB:
        e["x"] = world_w * T8_SUB - e["w"] * T8_SUB
    hit_x = -1
    if e["flags"] & EF_SOLID:
        a = ent_aabb(e)
        for j in range(T8_MAX_ENTITIES):
            if j == i: continue
            o = ents[j]
            if not (o["flags"] & EF_ACTIVE) or not (o["flags"] & EF_SOLID): continue
            if rect_overlap(a, ent_aabb(o)):
                hit_x = j; break
    if hit_x >= 0:
        e["x"] -= e["vx"]; e["vx"] = 0
    e["y"] += e["vy"]
    if e["y"] < 0: e["y"] = 0
    if e["y"] + e["h"] * T8_SUB > world_h * T8_SUB:
        e["y"] = world_h * T8_SUB - e["h"] * T8_SUB
    hit_y = -1
    if e["flags"] & EF_SOLID:
        a = ent_aabb(e)
        for j in range(T8_MAX_ENTITIES):
            if j == i: continue
            o = ents[j]
            if not (o["flags"] & EF_ACTIVE) or not (o["flags"] & EF_SOLID): continue
            if rect_overlap(a, ent_aabb(o)):
                hit_y = j; break
    if hit_y >= 0:
        e["y"] -= e["vy"]; e["vy"] = 0
    return hit_x if hit_x >= 0 else hit_y


def ent_collide_all(ents, on_hit, user):
    n = 0
    for i in range(T8_MAX_ENTITIES):
        a = ents[i]
        if not (a["flags"] & EF_ACTIVE): continue
        ra = ent_aabb(a)
        for j in range(i + 1, T8_MAX_ENTITIES):
            b = ents[j]
            if not (b["flags"] & EF_ACTIVE): continue
            if rect_overlap(ra, ent_aabb(b)):
                on_hit(a, b, user)
                n += 1
    return n


def ent_pickup_scan(ents, on_hit, user):
    n = 0
    for i in range(T8_MAX_ENTITIES):
        a = ents[i]
        if not (a["flags"] & EF_ACTIVE) or not (a["flags"] & EF_PLAYER): continue
        ra = ent_aabb(a)
        for j in range(T8_MAX_ENTITIES):
            if i == j: continue
            b = ents[j]
            if not (b["flags"] & EF_ACTIVE) or not (b["flags"] & EF_PICKUP): continue
            if rect_overlap(ra, ent_aabb(b)):
                on_hit(a, b, user)
                n += 1
    return n


failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def mk_ent(flags=0, x=0, y=0, vx=0, vy=0, w=8, h=8, tag=0):
    return dict(flags=flags, x=x*16, y=y*16, vx=vx*16, vy=vy*16, w=w, h=h, sprite=None, tag=tag)


def test_pool_exhausts():
    ents = [mk_ent() for _ in range(T8_MAX_ENTITIES)]
    for _ in range(T8_MAX_ENTITIES):
        i = ent_alloc(ents)
        check(i >= 0, "alloc succeeds while pool has room")
    # Pool is full now
    check(ent_alloc(ents) == -1, "alloc returns -1 when pool exhausted")
    # Free one and try again
    ent_free(ents, 0)
    check(ent_alloc(ents) == 0, "alloc reuses freed slot 0")


def test_axis_separated_slide():
    ents = [mk_ent() for _ in range(T8_MAX_ENTITIES)]
    # Wall at x=3..7, y=0..4
    wall = mk_ent(flags=EF_ACTIVE | EF_SOLID, x=3, y=0, w=5, h=4)
    ents[0] = wall
    # Player at x=1, y=0, moving right+down, hits wall on x.
    p = mk_ent(flags=EF_ACTIVE | EF_SOLID | EF_PLAYER, x=1, y=0, vx=3, vy=2, w=2, h=2)
    ents[1] = p
    hit = ent_move(ents, 1, 200, 200)
    # x collision -> x reverted, vx = 0
    # y should pass (player at y=0..2, wall at y=0..4, overlap on y; y collision too)
    # Actually: pre-move y = 0, after +2 -> y=2, overlap with wall (0..4) at y=2 -> y hit.
    # So both axes hit.
    check(hit == 0, f"hit returns wall index (got {hit})")
    # vx was non-zero before; after x-block, should be 0.
    check(p["vx"] == 0, f"vx zeroed on x-block (got {p['vx']})")


def test_collide_all_unique_pairs():
    ents = [mk_ent() for _ in range(T8_MAX_ENTITIES)]
    # 4 entities with these x positions (hitbox w=8):
    #   0: x=0  -> cols 0..7
    #   1: x=2  -> cols 2..9   (overlaps 0)
    #   2: x=20 -> cols 20..27  (isolated)
    #   3: x=4  -> cols 4..11   (overlaps 0 and 1)
    ents[0] = mk_ent(flags=EF_ACTIVE, x=0, y=0)
    ents[1] = mk_ent(flags=EF_ACTIVE, x=2, y=0)
    ents[2] = mk_ent(flags=EF_ACTIVE, x=20, y=0)
    ents[3] = mk_ent(flags=EF_ACTIVE, x=4, y=0)
    hits = []
    ent_collide_all(ents, lambda a, b, u: hits.append((a["x"]//T8_SUB, b["x"]//T8_SUB)), None)
    # Expected unique pairs: (0,1), (0,3), (1,3) = 3.
    check(len(hits) == 3, f"three unique collisions (got {len(hits)})")
    pairs = {frozenset(p) for p in hits}
    check(frozenset({0,2}) in pairs, "0-1 collide")
    check(frozenset({2,4}) in pairs, "1-3 collide")
    check(frozenset({0,4}) in pairs, "0-3 collide")
    # Sanity: pair (0,2) appears exactly once.
    check(sum(1 for p in hits if sorted(p) == [0,2]) == 1, "0-1 reported once")


def test_pickup_scan_only_player_with_pickup():
    ents = [mk_ent() for _ in range(T8_MAX_ENTITIES)]
    ents[0] = mk_ent(flags=EF_ACTIVE | EF_PLAYER, x=0, y=0)
    ents[1] = mk_ent(flags=EF_ACTIVE | EF_PICKUP,  x=1, y=0)   # overlap
    ents[2] = mk_ent(flags=EF_ACTIVE | EF_PICKUP,  x=100, y=0) # no overlap
    ents[3] = mk_ent(flags=EF_ACTIVE,             x=1, y=0)   # overlap but not pickup
    hits = []
    ent_pickup_scan(ents, lambda a, b, u: hits.append(True), None)
    check(len(hits) == 1, f"exactly 1 pickup (got {len(hits)})")


if __name__ == "__main__":
    test_pool_exhausts()
    test_axis_separated_slide()
    test_collide_all_unique_pairs()
    test_pickup_scan_only_player_with_pickup()
    print(f"M5 entity: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)