#include "tiny8_scene.h"
#include "tiny8_framebuffer.h"

namespace t8 {

static Scene g_stack[T8_MAX_SCENES];
static uint8_t g_top = 0;   // index of top, also count

void scene_init() {
    for (uint8_t i = 0; i < T8_MAX_SCENES; ++i) g_stack[i] = Scene{};
    g_top = 0;
}

Err scene_push(const Scene& s) {
    if (g_top >= T8_MAX_SCENES) return Err::NoRoom;
    g_stack[g_top] = s;
    if (s.on_enter) s.on_enter(g_stack[g_top]);
    ++g_top;
    return Err::Ok;
}

Err scene_pop() {
    if (g_top == 0) return Err::BadArg;
    --g_top;
    if (g_stack[g_top].on_exit) g_stack[g_top].on_exit(g_stack[g_top]);
    g_stack[g_top] = Scene{};
    return Err::Ok;
}

Err scene_replace(const Scene& s) {
    if (g_top > 0) {
        if (g_stack[g_top - 1].on_exit) g_stack[g_top - 1].on_exit(g_stack[g_top - 1]);
        g_stack[g_top - 1] = s;
        if (s.on_enter) s.on_enter(g_stack[g_top - 1]);
    } else {
        return scene_push(s);
    }
    return Err::Ok;
}

uint8_t scene_depth() { return g_top; }

Scene* scene_top() { return g_top > 0 ? &g_stack[g_top - 1] : nullptr; }

void scene_update() {
    if (g_top == 0) return;
    if (g_stack[g_top - 1].on_update) g_stack[g_top - 1].on_update(g_stack[g_top - 1]);
}

void scene_draw(Framebuffer& fb) {
    if (g_top == 0) return;
    if (g_stack[g_top - 1].on_draw) g_stack[g_top - 1].on_draw(g_stack[g_top - 1], fb);
}

Scene scene_make(int16_t id, void* user,
                 SceneFnEnter  enter,
                 SceneFnExit   exit,
                 SceneFnUpdate update,
                 SceneFnDraw   draw) {
    Scene s{};
    s.id = id; s.user = user;
    s.on_enter = enter; s.on_exit = exit;
    s.on_update = update; s.on_draw = draw;
    return s;
}

}  // namespace t8
