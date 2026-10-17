// Tiny8 Engine — display driver registry. The active driver is held in a
// single global (one pointer + one function table pointer).

#include "tiny8_display.h"

namespace t8 {

static const DisplayDriver* g_disp = nullptr;

void display_register(const DisplayDriver& d) { g_disp = &d; }
const DisplayDriver* display_active() { return g_disp; }

void display_init()          { if (g_disp && g_disp->init) g_disp->init(); }
void display_set_contrast(uint8_t v) {
    if (g_disp && g_disp->set_contrast) g_disp->set_contrast(v);
}
void display_flush(const Framebuffer& fb) {
    if (g_disp && g_disp->flush) g_disp->flush(fb_pixels(fb));
}
void display_power(bool on)  { if (g_disp && g_disp->power) g_disp->power(on); }

}  // namespace t8
