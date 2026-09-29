# Sound options: five ways to give the bodies a voice

**What this is.** A comparison of five ways to make the five bodies'
voices, and to hear them, written 2026-09-29 when the question changed.
Until then the pitches were fixed by the hearing: an MSGEQ7 reports seven
fixed bands, so every voice had to sit in a band of its own, and each
pitch belonged to a timer (`drivers/audio.py`). Now that a computer can
analyse any frequency (`test goertzel ear` does it in Python), the
question is what hardware lets a body sing **any pitch**, and possibly
several at once, and gets **five microphones to the computer** so that
freedom can be heard.

It is a comparison, not a specification. The first two columns are read
out of this repository; the other three come from general knowledge of
the parts and **have not been checked against a datasheet or measured at
the rig**. Prices are rough 2026 hobby-retail figures for five bodies,
audio electronics only, speakers excluded. Check them before ordering,
for `next pcb` section 5's reason: a figure about a part you intend to buy
and a fact about the part in your hand read identically.

## The five

- **TJ's original** (reference, not a candidate). One Pro Mini in each
  body plays a `tone()` square wave on pin 9 into a SparkFun TPA2005D1,
  and an MSGEQ7 in the same body listens to band 4
  (`local/Code/Code/Units/logic35_systems/`, CODE_DOCUMENTATION §8.10, §9).
- **Thomas's chain** (as built today). Five Mega hardware timers make five
  fixed square waves; a 2nd-order low-pass per channel rounds them, a
  22K/3K3 divider sets the level, a GF1002 drives the speaker. MAX9814
  microphones feed five MSGEQ7s on one strobe (`HARDWARE_SETUP.md`,
  `dirty rework`).
- **AD9833 x 5.** One DDS chip per speaker on the Mega's SPI bus. The Mega
  sends a frequency once and the chip goes on playing a sine by itself.
- **Teensy 4.1.** One Teensy on USB to the laptop computes all five voices
  and sends them through I2S DACs (e.g. 3 x PCM5102) to the amplifiers, and
  streams the five microphones back as raw samples.
- **USB 7.1 sound card.** Python computes five channels and plays them
  through a USB card, one output per amplifier.

## Side by side

| | TJ's original | Thomas's chain | AD9833 x 5 | Teensy 4.1 | USB 7.1 card |
|---|---|---|---|---|---|
| **Price** (5 bodies, rough) | ok: EUR 100-150 (5 TPA2005D1 ~50, 5 MSGEQ7 ~25-50, 5 Pro Minis ~20-50) | good: already paid; the next PCB adds passives and 5 amp modules, ~EUR 10-30 | good: EUR 20-40, amps reused; hearing side extra | good: EUR 50-75 (Teensy ~35, 3 DACs ~15, optional ADC boards ~15); retires the 5 MSGEQ7s | ok: EUR 20-40 card and isolators; 5 mic inputs need an 8-input interface, EUR 200-300 |
| **Frequencies** | ok: any per body in principle; he used five in 1760-2637 Hz because the ear read only band 4 | poor: five fixed, 160 / 400 / 1k / 2.5k / 6.25k Hz, each locked by timer, filter and band | good: any, ~0.1 Hz steps | good: any, can glide | good: any, can glide |
| **Several tones at once** (one speaker) | no: one `tone()` per board | no: one timer per speaker | no: one chip is one tone; two chips and two resistors give two | yes: oscillators into `AudioMixer4` | yes: summed in Python |
| **Waveform** | poor: square driven into clipping, harmonics land in other bands | ok: filtered square, near a sine; harmonics reduced, not gone | good: sine from a 10-bit DAC | good: any shape, 16-bit 44.1 kHz | good: any shape, 16-24-bit |
| **Loudness** | loud: 5 Vpp square into a gain-2 amp, clipping at ~1.4 W | poor: 330 mVpp into the amp, ~24 dB below TJ's drive, no headroom in the pot | ok: ~0.6 Vpp; a small gain stage makes it up cleanly | good: PCM5102 line out, ~2 Vrms | ok: ~1 Vrms on cheap cards |
| **Hearing side** (5 mics to the computer) | poor: each body judges band 4 alone; the computer sees nothing | poor: seven band levels per body; the computer never sees the signal, so pitches stay one per band | not solved: needs a separate sampler; the Mega alone gives ~3.8 kSPS a mic, nothing above ~1.9 kHz | solved: raw samples over 480 Mbit/s USB; rate per mic still to confirm on the bench | not solved: only with the multi-input interface |
| **Programming and debugging** | hard: five firmwares on five boards with no USB; his own comments record an analyser that would not reset and a band he was unsure of | done: firmware 4, `drivers/audio.py`, `sing`, `hearing`, six hardware tests including a diagnosis | small: one SPI command in the sketch, a frequency on `speaker/on`, `audio.py` stops being a fixed table | largest: new sketch (audio library, sample streaming), new driver, Teensy upload in the flasher, analysis in Python; USB serial makes it comfortable to debug | medium: Python only, but Windows audio (device order, default device, driver updates) is hard to see into |
| **PCB complexity** (next board) | medium: five small body boards, each with processor, analyser and amp | high: five filters, five dividers, five MSGEQ7s whose support network is still missing from the design | low: five modules on headers, one SPI bus, five capacitors | medium: Teensy socket, three I2S DAC modules, mic inputs into 3.3 V pins, a level shifter if the Mega talks to it | low but messy: no audio board, adapters and isolators hanging off the laptop |
| **Unattended reliability** | poor: `tone()` tore on every NeoPixel write, so the amp was muted around each one | ok: timers are immune to interrupts; a fixed threshold in a noisy gallery is the weak spot | good: runs by itself once set; nothing on the Mega can glitch it | good: a dedicated processor with nothing else to do; one more board and firmware to keep in step | poor: depends on Windows audio for weeks, and the laptop's ground invites hum |
| **Thomas's boards** | not used | kept, all of them | filters bypassed; MSGEQ7s kept only if pitches stay one per band | filters and MSGEQ7s retired; MAX9814s kept | filters retired; mics depend on the input chosen |
| **Distance from TJ** (0 his, 5 furthest) | 0 | 2: same idea, on/off tones carrying his patterns, MSGEQ7 ears; centralised, pitches spread across bands | 2: the same on/off patterns from a cleaner generator | 4: a different machine for voice and ear, though it can play his exact square tones at his exact pitches | 5: the sound leaves the piece and lives in a laptop; his units were self-contained |
| **Time to first sound** (rough) | weeks | now; the harness measurement is still open | days, speakers only | one to two weeks, both halves | days, speakers only |

## Distance from TJ

The repository already left TJ's architecture - one Mega in the rack and a
Python brain, where he had a processor in every body - so every option
except his own starts at 2. What the scale measures is how much of the
*sound path* is still recognisably his.

**Hardware distance is not sound distance.** The Teensy is far from TJ in
parts, but it can reproduce his square waves at 1760-2637 Hz exactly,
which Thomas's chain cannot: his pitches all sit in one analyser band, and
that chain needs one band per voice. If what matters to him is what the
room hears rather than what is in the rack, that is the argument for it.

## Reading it

**The hearing side decides it.** "Any frequency, analysed on the
computer" needs two things: the pitches free, and the microphone signals
on the computer. Only the Teensy does both. The AD9833 and the USB card
free the speakers only, and with MSGEQ7s still as the ears their seven
fixed bands put the pitch constraint straight back.

- **Teensy 4.1, if the goal is any frequency.** It keeps sound off the
  Mega, so NeoPixel interrupts can never touch it again (the reason
  CODE_DOCUMENTATION 9.13 went void stays true). It costs about what the
  analyser half of Thomas's chain cost, and its board is simpler than the
  filter bank. The risk is that it is the most new code: prove it with one
  Teensy, one DAC and one speaker before committing. Its pins are 3.3 V
  and **not 5 V tolerant**, which is a new way to break something in a
  rack where everything else is 5 V.
- **Not the AD9833 on its own.** It frees the speakers cleanly and
  cheaply, but fixing the ears means adding a sampler, and the best
  sampler here is a Teensy - which could then play the tones too. It is
  still the right choice if the piece keeps one pitch per body and only
  wants a clean sine.
- **Thomas's chain stays the fallback.** It works today and every link of
  it is covered by a hardware test. Its weak points are known: five fixed
  pitches, about 24 dB quieter than TJ's (`dirty rework` section 7), and an
  analyser network not yet specified for the next PCB
  (`docs/ELECTRONICS_REVIEW.md`). Whatever replaces it is proven on the
  bench before it is unwired.
- **The USB card is a bench tool.** Cheap for trying pitches and mixes
  this week with no firmware. Not for an unattended exhibition: it depends
  on Windows audio and the laptop's ground, and it does nothing for the
  microphones.
- **TJ's original is the reference.** Loudest of the five, but the sound
  half is where his own notes say it was fragile (CODE_DOCUMENTATION
  §8.10).
