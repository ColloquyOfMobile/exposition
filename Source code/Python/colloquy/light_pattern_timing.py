# -*- coding: utf-8 -*-
# Source code/Python/colloquy/light_pattern_timing.py

"""How long a male's blink pattern takes, and how long he then stays dark.

The pattern *values* live in `Colloquy.light_patterns`; this is the clock
they are sent on. Both halves of the exchange need it - the male to time
his burst, the female to know how wide a bit is when she bins her samples
- so it lives in one place rather than as a number written twice.

All of it is TJ's, read off `local/Code/Code/Units/logic35_systems/`:

- Everything in that firmware runs on one 50ms tick
  (`time_sampleInterval`, logic35_systems.ino:20), and the pattern is
  transmitted one sample per tick.
- The tables Python copied are the 10-step ones, which are commented out
  there; the active `com_pattern_count` is 40, and those 40-sample arrays
  are exactly the 10-step ones upsampled x4. So one logical bit is 4
  samples - 200ms - and a whole pattern is 2s.
- `act_transmit_light()` (act_light.ino) sends the 40 samples once,
  starting from index 0, and switches the light off at the end. The next
  burst starts when `timer_search` reaches
  `(com_pattern_count * 2) + sense_light_pattern_threshold` = 87 ticks
  (Logic_male.ino:112), i.e. 4.35s after the last one began, leaving
  2.35s of darkness in between.

The gap is part of the message, not a pause between messages. It frames
the burst: a window that straddles it reads dark where the pattern says
lit, so only one alignment can match. Blinking seamlessly instead - which
is what this port did first - makes every rotation of the pattern equally
plausible, and the phase ambiguity that follows is self-inflicted.

(TJ's male also spends the gap listening for the female to sing the same
pattern back, `sense_sound_active`; this port has no sound channel, so
here the gap is only silence.)
"""

# One firmware tick: how often TJ samples and how long one transmitted
# sample lasts.
SAMPLE_INTERVAL = 0.05

# The 40-sample tables are the 10 written-down bits, each held for 4 ticks.
BITS = 10
SAMPLES_PER_BIT = 4

# ... which makes a bit 200ms and the whole pattern 2s.
BIT_DURATION = SAMPLE_INTERVAL * SAMPLES_PER_BIT
BURST_DURATION = BIT_DURATION * BITS

# TJ's own expression for the interval between bursts, in ticks:
# (com_pattern_count * 2) + sense_light_pattern_threshold.
PATTERN_SAMPLES = BITS * SAMPLES_PER_BIT
MATCH_THRESHOLD_SAMPLES = 7
CYCLE_DURATION = (
    (PATTERN_SAMPLES * 2) + MATCH_THRESHOLD_SAMPLES
) * SAMPLE_INTERVAL

# What is left of the cycle once the burst has been sent: the silence.
GAP_DURATION = CYCLE_DURATION - BURST_DURATION
