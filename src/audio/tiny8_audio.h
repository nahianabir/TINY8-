// Tiny8 Engine — audio: beeps, SFX, and a tiny music note sequencer.
//
// Backends:
//   * tiny8_audio_buzzer.cpp  — piezo buzzer on a digital pin via Timer2 ISR
//     (AVR). Records the current "beep frequency" so the engine can poll it.
//
// Music data is stored in PROGMEM as (note_id, duration_ticks) pairs.
// 0xFF terminates a track. Note ids 0..N index into a small built-in
// equal-tempered table (A4 = 440 Hz at id 45; A0 = 27 at id 21, ...).
//
// On the host (tests), tiny8_audio_buzzer.cpp is replaced with a stub that
// just records the last requested frequency.

#ifndef TINY8_AUDIO_H
#define TINY8_AUDIO_H

#include <stdint.h>
#include "tiny8_types.h"

namespace t8 {

// Initialise the audio backend. `pin` is the buzzer digital pin (ignored
// on host).
void     audio_init(uint8_t pin);
void     audio_set_enabled(bool on);

// Play a one-shot beep. Frequency 0 = silence.
void     audio_beep(uint16_t freq_hz, uint16_t duration_ms);

// Begin a music track. `track` is a PROGMEM pointer to (note_id, ticks)
// pairs, terminated by 0xFF. A note id of 0xFE is a rest.
void     audio_play(const uint8_t* track);
void     audio_stop();

// Step the music sequencer. Call once per fixed step.
void     audio_tick();

// Host-only: peek the last requested frequency.
uint16_t audio_last_freq();

}  // namespace t8

#endif  // TINY8_AUDIO_H