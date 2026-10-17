"""Tiny8 Engine — Milestone 6 host tests: scene state machine.

Mirrors the C++ logic. Verifies:
  * push beyond capacity returns NoRoom.
  * enter/exit hooks fire on push and pop in the right order.
  * scene_top returns the most recent.
  * replace swaps without changing depth.
"""

import sys

T8_MAX_SCENES = 4


class Err:
    Ok = 0
    NoRoom = -1
    BadArg = -2


g_stack = [None] * T8_MAX_SCENES
g_top = 0
g_log = []


def scene_init():
    global g_top
    g_stack[:] = [None] * T8_MAX_SCENES
    g_top = 0
    g_log.clear()


def scene_push(s):
    global g_top
    if g_top >= T8_MAX_SCENES:
        return Err.NoRoom
    g_stack[g_top] = s
    if s["on_enter"]: s["on_enter"](s)
    g_top += 1
    return Err.Ok


def scene_pop():
    global g_top
    if g_top == 0: return Err.BadArg
    g_top -= 1
    s = g_stack[g_top]
    if s["on_exit"]: s["on_exit"](s)
    g_stack[g_top] = None
    return Err.Ok


def scene_replace(s):
    global g_top
    if g_top > 0:
        if g_stack[g_top - 1]["on_exit"]: g_stack[g_top - 1]["on_exit"](g_stack[g_top - 1])
        g_stack[g_top - 1] = s
        if s["on_enter"]: s["on_enter"](s)
    else:
        return scene_push(s)
    return Err.Ok


def scene_depth(): return g_top


def scene_top(): return g_stack[g_top - 1] if g_top > 0 else None


def mk_scene(sid, label):
    return dict(id=sid, user=None,
                on_enter=lambda s: g_log.append(("enter", label)),
                on_exit =lambda s: g_log.append(("exit",  label)),
                on_update=lambda s: None,
                on_draw  =lambda s, fb: None)


failed = passed = 0
def check(expr, label):
    global failed, passed
    if expr: passed += 1
    else: print("FAIL", label); failed += 1


def test_push_pop():
    scene_init()
    s1 = mk_scene(1, "menu")
    s2 = mk_scene(2, "play")
    check(scene_push(s1) == Err.Ok, "push menu")
    check(scene_push(s2) == Err.Ok, "push play")
    check(scene_depth() == 2, "depth=2")
    check(scene_top()["id"] == 2, "top is play")
    check(scene_pop() == Err.Ok, "pop play")
    check(scene_depth() == 1, "depth=1")
    check(scene_top()["id"] == 1, "top is menu")
    # Log order
    expected = [("enter","menu"), ("enter","play"), ("exit","play")]
    check(g_log == expected, f"hook order {g_log}")
    scene_pop()
    check(scene_depth() == 0, "depth=0 after pop menu")
    check(scene_pop() == Err.BadArg, "pop empty -> BadArg")


def test_push_overflow():
    scene_init()
    for i in range(T8_MAX_SCENES):
        check(scene_push(mk_scene(i, str(i))) == Err.Ok, f"push {i}")
    check(scene_push(mk_scene(99, "overflow")) == Err.NoRoom, "push overflow -> NoRoom")


def test_replace_no_depth_change():
    scene_init()
    s1 = mk_scene(1, "a")
    s2 = mk_scene(2, "b")
    s3 = mk_scene(3, "c")
    scene_push(s1)
    scene_push(s2)
    check(scene_replace(s3) == Err.Ok, "replace ok")
    check(scene_depth() == 2, "depth unchanged")
    check(scene_top()["id"] == 3, "top is c")
    expected = [("enter","a"), ("enter","b"), ("exit","b"), ("enter","c")]
    check(g_log == expected, f"replace log {g_log}")


if __name__ == "__main__":
    test_push_pop()
    test_push_overflow()
    test_replace_no_depth_change()
    print(f"M6 scene: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)