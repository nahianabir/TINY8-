// Tiny8 Engine — scene state machine.
// A scene is a self-contained UI/game state with enter/exit/update/draw
// callbacks. The engine holds a stack of scenes; the top is the active
// one. Scenes are statically registered (no allocation).
//
// Built-in scene IDs: kSceneMenu, kScenePlay, kScenePause, kSceneOver.

#ifndef TINY8_SCENE_H
#define TINY8_SCENE_H

#include <stdint.h>
#include "tiny8_types.h"

namespace t8 {

// Forward decls.
struct Framebuffer;
struct Scene;

// Lifecycle hooks.
typedef void (*SceneFnEnter)(Scene& s);
typedef void (*SceneFnExit) (Scene& s);
typedef void (*SceneFnUpdate)(Scene& s);
typedef void (*SceneFnDraw) (Scene& s, Framebuffer& fb);

struct Scene {
    SceneFnEnter  on_enter;
    SceneFnExit   on_exit;
    SceneFnUpdate on_update;
    SceneFnDraw   on_draw;
    int16_t       id;            // user-defined
    void*         user;          // user state pointer
};

// Stack API.
void     scene_init();
Err      scene_push(const Scene& s);   // copies onto stack
Err      scene_pop();                  // exits current scene
Err      scene_replace(const Scene& s);
uint8_t  scene_depth();
Scene*   scene_top();

// Step the top scene.
void     scene_update();
void     scene_draw(Framebuffer& fb);

// Convenience: build a Scene from a single function pointer used for all 4 hooks.
Scene scene_make(int16_t id, void* user,
                 SceneFnEnter  enter,
                 SceneFnExit   exit,
                 SceneFnUpdate update,
                 SceneFnDraw   draw);

}  // namespace t8

#endif  // TINY8_SCENE_H
