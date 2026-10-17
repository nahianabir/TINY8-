// Tiny8 Engine — display driver abstraction.
#ifndef TINY8_DISPLAY_H
#define TINY8_DISPLAY_H

#include <stdint.h>
#include "tiny8_framebuffer.h"

namespace t8 {

// Driver contract. A backend only needs to provide these.
struct DisplayDriver {
    void (*init)();
    void (*set_contrast)(uint8_t v);
    void (*flush)(const uint8_t* fb_bytes);   // 504 bytes
    void (*power)(bool on);
    uint8_t width;
    uint8_t height;
    uint8_t pages;
};

// Public entrypoints. They dispatch to whichever driver was registered.
void  display_register(const DisplayDriver& d);
void  display_init();
void  display_flush(const Framebuffer& fb);
void  display_set_contrast(uint8_t v);
void  display_power(bool on);
const DisplayDriver* display_active();

}  // namespace t8

#endif  // TINY8_DISPLAY_H
