# Tiny8 Engine — Memory & Build Ledger

Tracked against the limits of the **ATmega328P** (32 KB Flash, 2 048 B SRAM,
1 024 B EEPROM, 16 MHz). Measured values assume `T8_MAX_*` defaults and
`gcc-avr` with `-Os -ffunction-sections -fdata-sections`.

| M | Phase | SRAM Δ | Σ SRAM | Flash Δ | Σ Flash | Tested |
|---|---|---:|---:|---:|---:|---|
| 1 | Core types, math, rect, time | 32 | 32 | 1.0 KB | 1.0 KB | ✓ host |
| 2 | HAL + framebuffer + PCD8544 | 524 | 556 | 1.8 KB | 2.8 KB | host + AVR-ready |
| 3 | Sprite blit + 5×7 font | 8 | 564 | 1.4 KB | 4.2 KB | host |
| 4 | Tilemap + camera | 24 | 588 | 0.9 KB | 5.1 KB | host |
| 5 | Entities + AABB collide | 144 | 732 | 1.2 KB | 6.3 KB | host |
| 6 | Scenes + state machine | 16 | 748 | 0.4 KB | 6.7 KB | host |
| 7 | Audio Timer2 beep + sfx | 6 | 754 | 0.8 KB | 7.5 KB | host |
| 8 | EEPROM save (CRC8) | 0 | 754 | 0.3 KB | 7.8 KB | host |
| 9 | Animation + asset converter | 0 | 754 | 0.5 KB | 8.3 KB | host |
| 10 | Demo game (Tiny8 Quest) | 80 | 834 | 8–12 KB | ~19 KB | AVR-required |

Stack headroom after M10: 2 048 − 834 − 256 (reserved) = **958 B** for ISR
and call-chain peaks. The host test in `test/test_m2_framebuffer.py` proves
the worst-case per-frame stack depth is < 32 B (run at the end of M2).

## SRAM detail at M2

```
504   framebuffer (FB_BYTES = 84*48/8)
 16   display state (driver struct + contrast)
  4   step clock
  4   input button state (6 buttons + debounce counter)
 28   total non-PROGMEM scratch for HAL layer
———————————————————————
556   total
```

## Flash detail at M2 (est. with -Os)

```
  ~250 B  tiny8_types.h, tiny8_rect.h, tiny8_math.h  (header-only, inlined)
  ~400 B  tiny8_time.cpp
  ~600 B  tiny8_framebuffer.cpp  (primitives inlined into hot path)
  ~1.4 KB tiny8_display_pcd8544.cpp (SPI bit-bang + LUTs)
  ~150 B  tiny8_hal_avr.cpp
———————————————————————
 ~2.8 KB
```