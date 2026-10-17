// Tiny8 Engine — PCD8544 / Nokia 5110 driver.
//
// PHYSICAL: this driver is exercised on the host through the host HAL
// stub, which records every SPI transfer. The same C++ runs on the AVR
// with the real Arduino SPI library.

#include "tiny8_display_pcd8544.h"
#include "tiny8_hal.h"
// On AVR, the HAL implementation already pulled in <Arduino.h>. No direct
// dependency here keeps the host test free of Arduino headers.

namespace t8 {

// PCD8544 command set.
static constexpr uint8_t CMD_FN  = 0x20;
static constexpr uint8_t FN_EXT  = 0x01;
static constexpr uint8_t FN_BASIC= 0x00;
static constexpr uint8_t FN_PD   = 0x04;     // power down
static constexpr uint8_t FN_V    = 0x80;     // set Vop (contrast)
static constexpr uint8_t FN_TC   = 0x04;     // temperature coefficient
static constexpr uint8_t FN_BS   = 0x00;     // bias
static constexpr uint8_t CMD_DC  = 0x08;     // display control
static constexpr uint8_t DC_E    = 0x04;     // enable
static constexpr uint8_t CMD_Y   = 0x40;     // set Y page
static constexpr uint8_t CMD_X   = 0x80;     // set X column

static Pcd8544Pins g_pins;
static uint8_t     g_contrast = 0x3F;   // mid value

static void write_cmd(uint8_t c) {
    hal_digital_write(g_pins.dc, false);
    hal_digital_write(g_pins.ce, false);
    hal_spi_transfer(c);
    hal_digital_write(g_pins.ce, true);
}

static void write_data_block(const uint8_t* p, uint16_t n) {
    hal_digital_write(g_pins.dc, true);
    hal_digital_write(g_pins.ce, false);
    for (uint16_t i = 0; i < n; ++i) hal_spi_transfer(p[i]);
    hal_digital_write(g_pins.ce, true);
}

static void drv_init() {
    hal_pin_mode(g_pins.clk, PinMode::Out);
    hal_pin_mode(g_pins.din, PinMode::Out);
    hal_pin_mode(g_pins.ce,  PinMode::Out);
    hal_pin_mode(g_pins.dc,  PinMode::Out);
    hal_pin_mode(g_pins.rst, PinMode::Out);
    if (g_pins.bl != 255) {
        hal_pin_mode(g_pins.bl, PinMode::Out);
        hal_digital_write(g_pins.bl, true);
    }

    hal_digital_write(g_pins.rst, false);
    hal_delay_ms(20);
    hal_digital_write(g_pins.rst, true);

    hal_spi_begin();
    write_cmd(CMD_FN | FN_EXT);
    write_cmd(FN_TC | 0x02);                 // temperature coeff
    write_cmd(FN_BS | 0x03);                 // bias 1:48
    write_cmd(FN_V  | g_contrast);
    write_cmd(CMD_FN | FN_BASIC);
    write_cmd(CMD_DC | DC_E);
    write_cmd(CMD_Y);
    write_cmd(CMD_X);
    hal_spi_end();
}

static void drv_contrast(uint8_t v) {
    g_contrast = v;
    hal_spi_begin();
    write_cmd(CMD_FN | FN_EXT);
    write_cmd(FN_V | v);
    write_cmd(CMD_FN | FN_BASIC);
    hal_spi_end();
}

static void drv_flush(const uint8_t* fb) {
    hal_spi_begin();
    for (uint8_t page = 0; page < 6; ++page) {
        write_cmd(static_cast<uint8_t>(CMD_Y | page));
        write_cmd(CMD_X);
        write_data_block(fb + page * 84, 84);
    }
    hal_spi_end();
}

static void drv_power(bool on) {
    hal_spi_begin();
    write_cmd(CMD_FN | (on ? FN_BASIC : FN_PD));
    hal_spi_end();
}

// Single instance returned by the factory.
static const DisplayDriver g_pcd8544_drv = {
    &drv_init,
    &drv_contrast,
    &drv_flush,
    &drv_power,
    84, 48, 6,
};

const DisplayDriver& pcd8544_make(const Pcd8544Pins& pins) {
    g_pins = pins;
    return g_pcd8544_drv;
}

}  // namespace t8