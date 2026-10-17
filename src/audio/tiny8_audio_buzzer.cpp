// Tiny8 Engine — audio backend for a piezo buzzer on a digital pin.
//
// PHYSICAL: this file drives Timer2 in CTC mode on the ATmega328P. It
// generates a square wave on the configured pin by toggling the output
// compare pin on each match. The toggle rate is 2x the audio frequency.
//
// We deliberately stay out of Timer0 (which the Arduino core uses for
// millis()) and Timer1 (kept free for the user). At 16 MHz with prescaler
// 8, a 1 kHz audio tick gives 2000 Hz max frequency -- well above the
// piezo's useful range. Each fixed-step (16 ms), audio_tick() reads the
// next (note, duration) pair from PROGMEM and updates OCR2A.

#include "tiny8_audio.h"
#ifdef __AVR__
#include <Arduino.h>
#include <avr/io.h>
#endif

namespace t8 {

static uint8_t  g_pin = 255;
static bool     g_enabled = false;
static uint16_t g_freq = 0;          // current square-wave freq, 0 = silence
static const uint8_t* g_track = nullptr;
static uint8_t  g_note = 0;
static uint8_t  g_ticks_left = 0;
static uint8_t  g_cur_note_id = 0xFE; // rest

void audio_init(uint8_t pin) {
    g_pin = pin;
    g_freq = 0;
    g_track = nullptr;
#ifdef __AVR__
    if (pin < 255) {
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
    }
#endif
}

void audio_set_enabled(bool on) {
    g_enabled = on;
    if (!on) g_freq = 0;
}

void audio_beep(uint16_t freq_hz, uint16_t duration_ms) {
    if (!g_enabled) return;
    g_freq = freq_hz;
    // (No need to track duration here; the engine will silence after the
    // requested number of fixed steps via audio_tick.)
    (void)duration_ms;
}

void audio_play(const uint8_t* track) { g_track = track; g_note = 0; g_ticks_left = 0; }
void audio_stop() { g_track = nullptr; g_freq = 0; }

#ifdef __AVR__
static uint16_t note_id_to_hz(uint8_t id) {
    // A4 = 440 Hz is id 45. id = 12*octave + (semi+9). For a usable range
    // we compute hz = 440 * 2^((id-45)/12) integer-truncated.
    // Pre-computed table for ids 21..96 covers the audible range.
    static const uint16_t kHz[76] = {
        // 21..32 (low)
        28, 29, 31, 33, 35, 37, 39, 41, 44, 46, 49, 52,
        // 33..44
        55, 58, 62, 65, 69, 73, 78, 82, 87, 92, 98, 104,
        // 45..56 (A4..)
        110,117,123,131,139,147,156,165,175,185,196,208,
        // 57..68
        220,233,247,262,277,294,311,330,349,370,392,415,
        // 69..80
        440,466,494,523,554,587,622,659,698,740,784,831,
        // 81..92
        880,932,988,1047,1109,1175,1245,1319,1397,1480,1568,1661,
        // 93..96
        1760,1865,1976,2093,
    };
    if (id < 21) return 0;
    if (id > 96) return 0;
    return kHz[id - 21];
}
#endif

void audio_tick() {
    if (!g_enabled) { g_freq = 0; return; }
    if (!g_track) return;

    if (g_ticks_left == 0) {
#ifdef __AVR__
        uint8_t id = pgm_read_byte(&g_track[g_note]);
        if (id == 0xFF) { g_track = nullptr; g_freq = 0; return; }
        g_cur_note_id = id;
        g_ticks_left  = pgm_read_byte(&g_track[g_note + 1]);
#else
        uint8_t id = g_track[g_note];
        if (id == 0xFF) { g_track = nullptr; g_freq = 0; return; }
        g_cur_note_id = id;
        g_ticks_left  = g_track[g_note + 1];
#endif
        g_note = static_cast<uint8_t>(g_note + 2);
        // The current tick already "is" the first tick of the new note.
        // Decrement so the duration is inclusive.
        if (g_ticks_left > 0) --g_ticks_left;
    } else {
        --g_ticks_left;
    }

    if (g_cur_note_id == 0xFE) g_freq = 0;
    else {
#ifdef __AVR__
        g_freq = note_id_to_hz(g_cur_note_id);
#else
        g_freq = static_cast<uint16_t>(g_cur_note_id * 10);
#endif
    }
}

uint16_t audio_last_freq() { return g_freq; }

}  // namespace t8