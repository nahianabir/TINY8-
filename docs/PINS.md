# Tiny8 Engine — Pin Map (Arduino Uno R3, ATmega328P)

All pin assignments live in `demo/tiny8_demo.ino` and are easy to change.
The defaults below match the documented reference build.

## PCD8544 (Nokia 5110) — reference display

| Signal | Uno pin | Notes |
|---|---|---|
| CLK    | D13 | SPI SCK |
| DIN    | D11 | SPI MOSI |
| CE     | D9  | chip enable, active LOW |
| DC     | D8  | data/command |
| RST    | D7  | reset, active LOW |
| BL     | D5  | backlight (set to 255 to disable) |

The display is driven at **4 MHz** (`SPI_CLOCK_DIV4`). The full 504-byte
flush completes in **≈ 1.0 ms** (504 × 8 bits / 4 MHz = 1.008 ms).

## Buttons (active LOW with internal pull-up)

| Button  | Default pin |
|---|---|
| UP      | D2 |
| DOWN    | D3 |
| LEFT    | D4 |
| RIGHT   | D5 |
| A       | A0 |
| START   | A1 |

Override the pin map from your sketch:

```cpp
#include "tiny8_input.h"
t8::InputPins my = {{ 2, 3, 4, 5, A0, A1 }};
t8::input_init(my);
```

## Piezo buzzer

| Signal | Uno pin |
|---|---|
| Buzzer + | D6 |
| Buzzer − | GND |

The audio driver drives the pin directly via Timer2 in CTC mode at a
configurable rate. Use a piezo transducer (not a speaker) for clean
square-wave output.

## Wiring notes

- The PCD8544 operates at **3.3 V**. Power the display from the 3.3 V
  pin, not 5 V. Level-shift the SPI lines with a simple resistive divider
  (1 kΩ / 2 kΩ) on DIN, CLK, DC, CE, RST.
- Tie the display's GND to the Uno's GND.
- The BL pin drives a transistor or MOSFET for backlight control; a
  direct GPIO will work for low-current displays. Set `Pcd8544Pins.bl = 255`
  in the pin struct to disable backlight control entirely.
- For buttons, wire each between the pin and GND. The internal pull-up
  is enabled by `input_init()`.

## Power budget

- ATmega328P at 16 MHz: ~15 mA active.
- PCD8544 backlight at full brightness: ~20 mA.
- Total: comfortably under USB's 500 mA limit.
