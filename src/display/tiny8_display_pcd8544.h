// Tiny8 Engine — PCD8544 / Nokia 5110 LCD driver. Reference backend.
#ifndef TINY8_DISPLAY_PCD8544_H
#define TINY8_DISPLAY_PCD8544_H

#include "tiny8_display.h"

namespace t8 {

// Pin map is configured at registration time so the same driver can be
// reused across different boards.
struct Pcd8544Pins {
    uint8_t clk;     // SPI clock  (default 13 on Uno)
    uint8_t din;     // SPI MOSI   (default 11)
    uint8_t ce;      // chip enable (default 9)
    uint8_t dc;      // data/command (default 8)
    uint8_t rst;     // reset (default 7)
    uint8_t bl;      // backlight, optional (255 to disable)
};

// Build a DisplayDriver backed by PCD8544 with the given pin assignment.
const DisplayDriver& pcd8544_make(const Pcd8544Pins& pins);

}  // namespace t8

#endif  // TINY8_DISPLAY_PCD8544_H
