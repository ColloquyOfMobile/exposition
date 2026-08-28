# Hardware setup — audio subsystem

**What has to be plugged in before this test means anything.**

The scenario beside this one says what the run will do. This says what has
to be true of the bench first. It covers *this* test and nothing else: no
servo turns and no NeoPixel lights while it runs, so none of the
installation's own wiring is involved.

Everything here is from Thomas Erforth's *Colloquy of Mobiles — Redesign
of 2018 Version* (23.6.2026) in `Source code/Thomas/`, and from his
`AudioAnalyzerTest.cpp` firmware.

> **This is the bench, not the installation** — and since 2026-08-26
> there is a second document for the other one. The same five boards are
> now driven by the installation's *own* Arduino, on the same five pins,
> reworked into the electronics box: `hardware > electronics > dirty
> rework` is how, `as built` is what the box was before it, and `next
> pcb` is what should replace it. The bench test below is unaffected and
> stays — it asks whether the five boards work, which is a different
> question from whether they are wired into the piece correctly, and it
> can be asked in an office with the piece nowhere near.
>
> The installation's own version of the same twenty-five-answer grid is
> `tests > test audio loop`.

---

## The loop this test closes

<div style="overflow-x: auto; margin: 1rem 0;">
<svg viewBox="0 0 1240 830" role="img" aria-label="The audio subsystem drawn as a loop. A tone leaves Thomas's Mega on one of five timer pins, passes through a second-order low-pass filter board, a 22K over 3K3 divider and a GF1002 class D amplifier to a loudspeaker. It crosses the room as sound, is picked up by a MAX9814 microphone module with automatic gain control, read by one of five MSGEQ7 analysers on the analyser array, and returns to the same Mega on inputs A0 to A4. Separately, one strobe on D4 and one reset on D3 are commoned to all five analysers.">
  <defs>
    <marker id="ax" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="9" markerHeight="7" orient="auto">
      <polygon points="0,0 10,4 0,8" fill="currentColor"></polygon>
    </marker>
  </defs>

  <!-- ===== the hub, spanning both halves of the loop ===== -->
  <rect x="20" y="150" width="176" height="440" rx="4" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
  <text x="108" y="330" font-family="Chivo, sans-serif" font-size="17" font-weight="600" fill="currentColor" text-anchor="middle">Audio Mega</text>
  <text x="108" y="352" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62" text-anchor="middle">Thomas's board</text>
  <text x="108" y="368" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62" text-anchor="middle">USB &#183; 9600 baud</text>
  <text x="108" y="392" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62" text-anchor="middle">AudioAnalyzerTest</text>

  <text x="36" y="180" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" letter-spacing="1.2" fill="currentColor" opacity="0.55">OUT &#183; TIMERS</text>
  <g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor">
    <text x="36" y="202">D11</text><text x="180" y="202" text-anchor="end" opacity="0.7">160 Hz</text>
    <text x="36" y="222">D5</text><text x="180" y="222" text-anchor="end" opacity="0.7">400 Hz</text>
    <text x="36" y="242">D6</text><text x="180" y="242" text-anchor="end" opacity="0.7">1 kHz</text>
    <text x="36" y="262">D46</text><text x="180" y="262" text-anchor="end" opacity="0.7">2.5 kHz</text>
    <text x="36" y="282">D10</text><text x="180" y="282" text-anchor="end" opacity="0.7">6.25 kHz</text>
  </g>

  <text x="36" y="470" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" letter-spacing="1.2" fill="currentColor" opacity="0.55">IN &#183; ADC</text>
  <g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor">
    <text x="36" y="492">A0 &#8230; A4</text><text x="180" y="492" text-anchor="end" opacity="0.7">5 modules</text>
    <text x="36" y="516">D4</text><text x="180" y="516" text-anchor="end" opacity="0.7">STROBE</text>
    <text x="36" y="536">D3</text><text x="180" y="536" text-anchor="end" opacity="0.7">RESET</text>
  </g>

  <!-- ===== top half: out ===== -->
  <text x="228" y="46" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="600" letter-spacing="1.6" fill="currentColor" opacity="0.55">OUT &#8212; five channels, one per body</text>

  <path d="M 196 240 L 232 240" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <text x="214" y="228" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle">5 Vpp</text>

  <image href="/static/hardware/low-pass-filter-board.jpg" x="236" y="62" width="196" height="156" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="236" y="62" width="196" height="156" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <path d="M 334 218 L 334 232" stroke="currentColor" stroke-width="1.2" opacity="0.45" fill="none"></path>
  <text x="334" y="252" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Low-pass filter</text>
  <text x="334" y="268" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">2nd order, R1=R2 C1=C2</text>
  <text x="334" y="282" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">IN: 160 400 1K 2K5 6K25</text>

  <path d="M 432 140 L 486 140" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <text x="459" y="128" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle">2 Vpp</text>

  <rect x="490" y="108" width="96" height="64" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
  <text x="538" y="136" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Divider</text>
  <text x="538" y="154" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.7" text-anchor="middle">22K / 3K3</text>

  <path d="M 586 140 L 640 140" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <text x="613" y="128" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle">330 mVpp</text>

  <image href="/static/hardware/amplifier-module.jpg" x="644" y="66" width="186" height="141" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="644" y="66" width="186" height="141" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <path d="M 737 207 L 737 232" stroke="currentColor" stroke-width="1.2" opacity="0.45" fill="none"></path>
  <text x="737" y="252" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">GF1002 amplifier</text>
  <text x="737" y="268" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">class D &#183; volume pot on board</text>
  <text x="737" y="282" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">mount it next to the speaker</text>

  <path d="M 830 140 L 892 140" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <text x="861" y="128" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle">PWM</text>
  <text x="861" y="158" font-family="'IBM Plex Mono', monospace" font-size="9" fill="currentColor" opacity="0.55" text-anchor="middle">short lead</text>

  <rect x="896" y="102" width="136" height="76" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
  <text x="964" y="130" font-family="Chivo, sans-serif" font-size="14" font-weight="600" fill="currentColor" text-anchor="middle">Loudspeaker</text>
  <text x="964" y="148" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">open frame</text>
  <text x="964" y="163" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">flat 160 Hz &#8211; 6.25 kHz?</text>

  <!-- ===== the turn: through the room ===== -->
  <path d="M 1032 140 L 1128 140 L 1128 620 L 1032 620" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <rect x="1136" y="330" width="96" height="100" rx="3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="4 3"></rect>
  <text x="1184" y="362" font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">The room</text>
  <text x="1184" y="382" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">air, distance,</text>
  <text x="1184" y="396" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">everyone in it</text>
  <text x="1184" y="416" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">&#8212; not simulated</text>
  <path d="M 1136 380 L 1120 380" stroke="currentColor" stroke-width="1.2" opacity="0.5" fill="none"></path>

  <!-- ===== bottom half: back in ===== -->
  <text x="1032" y="500" text-anchor="end" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="600" letter-spacing="1.6" fill="currentColor" opacity="0.55">BACK IN &#8212; five microphones, five analysers, one strobe</text>

  <image href="/static/hardware/microphone-module.jpg" x="900" y="516" width="128" height="147" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="900" y="516" width="128" height="147" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <text x="964" y="682" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">MAX9814 microphone</text>
  <text x="964" y="698" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">AGC &#183; gain 40 dB, A/R 1:500</text>

  <path d="M 900 620 L 830 620" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <text x="865" y="608" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle">1.6 Vpp</text>

  <image href="/static/hardware/audio-analyzer-array.jpg" x="596" y="514" width="228" height="171" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="596" y="514" width="228" height="171" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <text x="710" y="704" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Audio analyser array</text>
  <text x="710" y="720" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">5 &#215; MSGEQ7, seven bands each</text>

  <path d="M 596 620 L 232 620" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>
  <text x="414" y="608" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle">5 analog &#8594; A0 &#8230; A4</text>
  <path d="M 232 620 L 196 620" stroke="currentColor" stroke-width="1.8" fill="none" marker-end="url(#ax)"></path>

  <!-- the commoned control lines -->
  <path d="M 196 528 L 300 528 L 300 468 L 710 468 L 710 508" stroke="currentColor" stroke-width="1.8" stroke-dasharray="6 4" fill="none"></path>
  <circle cx="710" cy="510" r="3.5" fill="currentColor"></circle>
  <text x="318" y="460" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.78">one strobe, one reset &#8212; commoned to all five modules</text>
  <text x="318" y="444" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.55">so one cycle through the seven bands reads every body at once</text>

  <!-- what the test asks -->
  <rect x="236" y="316" width="596" height="86" rx="4" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.45" stroke-dasharray="5 4"></rect>
  <text x="256" y="344" font-family="Chivo, sans-serif" font-size="14" font-weight="600" fill="currentColor">What the bench test asks, 25 times</text>
  <text x="256" y="366" font-family="'IBM Plex Mono', monospace" font-size="11" fill="currentColor" opacity="0.75">Does each of the five tones complete this loop and arrive in its own band</text>
  <text x="256" y="384" font-family="'IBM Plex Mono', monospace" font-size="11" fill="currentColor" opacity="0.75">on each of the five modules? heard &#183; wrong band &#183; silent</text>

  <line x1="20" y1="770" x2="1220" y2="770" stroke="currentColor" stroke-width="1" opacity="0.28"></line>
  <text x="20" y="794" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62">Boards photographed by Thomas Erforth. Five identical channels, one per body &#8212; three females, two males. Nothing in this software drives any of it yet: the test only asks whether it works.</text>
  <text x="20" y="812" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62">A failure names the broken tone-and-module pair, never the broken link: the whole loop is one measurement.</text>
</svg>
</div>

A tone leaves the Mega on a timer pin, crosses the room as sound, and
comes back into the same Mega on an ADC input. The test asks whether each
of the five tones completes that loop and arrives in its own band, on
each of the five modules — twenty-five answers.

---

## 1. On the bench

- **Thomas's Mega 2560**, on a USB lead, with `AudioAnalyzerTest.cpp` on
  it. This is a **third** board: not the U2D2 and not the installation's
  own Arduino. Picking the wrong lead is the most common way to lose ten
  minutes.
- **The filter board**, the five **GF1002 amplifiers**, five
  **loudspeakers**, five **MAX9814 microphone modules**, and the
  **analyser array**. Photographs and pinouts are in §4.
- **Power** for the amplifiers, separate from the Mega's USB.

**Telling the boards apart without unplugging anything:** open the port
and see what it says. The installation's Arduino greets with a line of
JSON naming its firmware version and its baud rate
(`{"hello": "colloquy of mobiles", ...}`) and then only replies to JSON.
Thomas's board clears the screen and prints
`---- Audio subsystem tester for ----`. The test checks for exactly that
banner and refuses rather than sitting there failing silently, so if it
says *"no audio tester on that port"*, the lead is right there in the
message.

**Or without opening anything at all:** every board on the bus is named
by the chip bridging it to USB, which enumerates from power alone -
`colloquy/hardware/arduino/boards.py` reads the VID and PID and says
"Arduino Mega 2560 (R3)" or "FTDI - the U2D2 is an FTDI device". That
works on a board with nothing flashed on it, which opening the port does
not. What it *cannot* say is whether the right sketch is on it; the
greeting above is for that, and the two are meant to be read together.

**The bench is a machine of its own.** This test asks whether it is
running on it (`colloquy/machines.py`, by hostname) and not whether the
*piece* is simulated — the office desk has Thomas's boards and none of
the installation, so it is simulated in every other sense and its audio
hardware is as real as hardware gets. On the bench the port picker lists
the actual serial leads; anywhere else it offers one stand-in and the
page says `board: simulated stand-in`.

Two things follow, and both are on the page rather than in a log:

- **It is not offered on the installation's own machine at all.** That
  computer will never have these boards.
- **A port remembered from another machine is refused, not opened.** The
  chosen port lives in `params.json`, which outlives the laptop that
  chose it — a machine that ran this simulated leaves
  `simulated audio port` behind, and on the bench that would fail with a
  pyserial error naming a port nobody recognises. It says what is stored
  and what is actually there instead.

---

## 2. Speaking

Five bodies, five tones: `160 Hz`, `400 Hz`, `1 kHz`, `2.5 kHz`,
`6.25 kHz`. They are five of the MSGEQ7's seven bands, and Thomas says
why the other two are out: a typical electret microphone is only
specified from 100 Hz to 10 kHz, so 63 Hz and 16 kHz fall outside it —
and a good part of any audience cannot hear 16 kHz anyway.

### Why the filters are there

A counter makes a *square* wave — the fundamental plus every odd
harmonic. The first harmonic of each tone lands uncomfortably close to a
neighbouring band, and the MSGEQ7's own band-pass cannot separate them:

| Tone | 1st harmonic | Neighbouring band | Distance |
|---|---|---|---|
| 160 Hz | 480 Hz | 400 Hz | **80 Hz** |
| 400 Hz | 1200 Hz | 1000 Hz | **200 Hz** |
| 1000 Hz | 3000 Hz | 2500 Hz | 500 Hz |
| 2500 Hz | 7500 Hz | 6250 Hz | 1250 Hz |
| 6250 Hz | 18750 Hz | 16000 Hz | 2750 Hz |

So each channel gets a passive second-order low-pass. Both stages are
identical — `R1 = R2`, `C1 = C2` — which is what makes the board look as
regular as it does:

| Band | R1 = R2 | C1 = C2 |
|---|---|---|
| 6250 Hz | 2K2 | 10 nF |
| 2500 Hz | 1K8 | 47 nF |
| 1000 Hz | 1K2 | 150 nF |
| 400 Hz | 2K | 220 nF |
| 160 Hz | 2K2 | 470 nF |

Measured result: the first harmonic damped by more than 20 dB, under 10%
of the fundamental. The output is still not a sine wave, and does not
need to be. The top two bands did not strictly need filtering; they were
given it anyway so all five tones sound alike.

### Divider, amplifier, speaker

- **Divider** — `R1/R2 = 22K/3K3`, the same on all five channels, sized
  to keep the filter output under the amplifier's maximum input **with
  the module's volume control at maximum**. Exceed it and the amp clips,
  and a clipped output is a square wave again — throwing away everything
  the filter just did.
- **Amplifier** — a GF1002 class-D module with its own volume pot, so
  levels can still be trimmed in the room. Its output is differential PWM
  at about 250 kHz: sharp edges, high currents, real EMI. **Mount the
  amplifier close to its loudspeaker and keep the speaker wires short.**
- **Loudspeaker** — must be reasonably flat from 160 Hz to 6250 Hz, and
  the existing ones have not been shown to be. They sit in an open frame,
  close to an acoustic short circuit, so **test the two lowest tones for
  sound pressure first**.

---

## 3. Hearing

The 2018 module was a plain op-amp preamp, which in a noisy room
saturates and turns the tone back into a square wave — undoing at the
last step everything the filters did at the first. The replacement is a
**MAX9814**: low-noise preamp, variable-gain amp, output amp, mic bias
and automatic gain control. The AGC is the point; it is the headroom.

### Strapping the MAX9814

| Pin | Tie to | Effect | |
|---|---|---|---|
| **Gain** | GND | 50 dB | |
| | VDD | 40 dB | ← Thomas's bench result |
| | float | 60 dB | |
| **A/R** | GND | 1:500 | ← Thomas's bench result |
| | VDD | 1:2000 | |
| | float | 1:4000 | |

At 1:500 the gain recovers fastest after a spike. Thomas notes both must
be double-checked in the field, so treat them as a starting point rather
than a final answer.

### The analyser array

MSGEQ7, unchanged from the 2018 version. **STROBE and RESET of all five
modules are tied together** to save pins on the hub, so one cycle through
the seven bands reads all five modules at once. The five analog outputs
go to five ADC inputs.

**One property to know before writing anything that reads it:** the
MSGEQ7's internal scan rate is fast enough to catch individual points on
the *waveform* of the 160 Hz and 400 Hz signals — so repeated readings
vary depending on where in the cycle it happened to sample. Thomas's
remedy: read **four times in quick succession when expecting 160 Hz** and
**twice for 400 Hz**. In his tests 160 Hz always gave at least two high
hits out of four, and 400 Hz at least one out of two. *This test does not
do that yet* — it averages whole sweeps instead, which is enough to say
"heard" but is not how to sample a tone.

---

## 4. The four boards

**The pin names are on the photographs.** They are Thomas's own, drawn
over his figures 4 to 7, and they are the reason to look at a picture
here rather than at a table — a label sits beside the header it names, at
the end of the board it is actually on. The prose under each one repeats
them so they can be searched for, but the picture is what to hold the
board against. (If a photograph ever comes back bare, it has been pulled
out of the PDF as an embedded image rather than rendered — see
`extract_hardware_photos.py` at the repository root.)

**Low-pass filter board** — five channels. `IN` along one edge in the
order **160, 400, 1K, 2K5, 6K25**, `OUT` on the other, GND and VDD as
marked. The five groups of yellow capacitors are the five bands; the
biggest capacitors belong to the lowest tone.

![Low-pass filter board — Figure 4, pin labels as marked](/static/hardware/low-pass-filter-board.jpg)

**Microphone module** — a MAX9814 breakout on a carrier. Header:
`GND / VDD / AOUT`, plus `Gain` and `AR` to strap per §3. The strap table
is on the photograph too: `AR` to GND is 1:500, to VDD 1:2000, floating
1:4000; `Gain` to GND is 50 dB, to VDD 40 dB, floating 60 dB.

![Microphone module — Figure 5, pin labels as marked](/static/hardware/microphone-module.jpg)

**Amplifier module** — the GF1002 with its volume pot, on a carrier with
a screw terminal for supply and JST connectors for audio in and speaker
out (`Audio`/`GND`, `VDD`/`GND`, `ROUT+`). One per body, each close to
its own speaker.

![Amplifier module — Figure 6, pin labels as marked](/static/hardware/amplifier-module.jpg)

**Audio analyser array** — the five MSGEQ7 boards on one carrier, strobe
and reset commoned across the back, one JST per module for its
microphone. This single board is the whole hearing side.

![Audio analyser array — Figure 7, pin labels as marked](/static/hardware/audio-analyzer-array.jpg)

---

## 5. Wiring it to the Mega

From `AudioAnalyzer.h`. **These are the numbers the firmware actually
uses**, so they are what the board must be wired to:

| Timer | Tone | Mega pin | Analyser band |
|---|---|---|---|
| T1 | 160 Hz | **D11** | 1 |
| T3 | 400 Hz | **D5** | 2 |
| T4 | 1 kHz | **D6** | 3 |
| T5 | 2.5 kHz | **D46** | 4 |
| T2 | 6.25 kHz | **D10** | 5 |
| — | STROBE, all five | **D4** | — |
| — | RESET, all five | **D3** | — |
| — | Module outputs 0–4 | **A0 … A4** | — |

Note the menu counts *timers*, not pitches, and timer 2 is the 8-bit one
— so `E2` is the top tone, 6.25 kHz, and not the second one up.

> ### ⚠ Settle this with Thomas before wiring
>
> **The PDF's block diagrams and the firmware disagree about which timer
> makes which tone**, and they disagree by being exactly reversed.
>
> | Source | T1 | T3 | T4 | T5 | T2 |
> |---|---|---|---|---|---|
> | `AudioAnalyzer.h` | 160 Hz | 400 Hz | 1 kHz | 2.5 kHz | 6.25 kHz |
> | PDF figures 1 & 2 | **6.25 kHz** | **2.5 kHz** | 1 kHz | **400 Hz** | **160 Hz** |
>
> The firmware is self-consistent — its OCR values compute to 162, 405,
> 1012, 2530 and 6329 Hz for T1, T3, T4, T5, T2 — so the tone that comes
> out of D11 really is 160 Hz. What is unresolved is **which filter
> channel each pin is wired to**, and that is a decision about the board,
> not about the code.
>
> **This test cannot catch it.** A low-pass passes anything below its
> corner, so 160 Hz fed into the 6.25 kHz channel still comes out, still
> lands in the 160 Hz band, and still reports "heard". What you lose is
> the filtering — the 6.25 kHz channel barely touches the 480 Hz first
> harmonic that the 160 Hz channel exists to remove. The symptom would be
> poor detection in a noisy room, months later, and nothing pointing at
> the cause.
>
> So check by ear or by scope which physical channel each pin feeds
> before trusting a run.

---

## 6. Running it

1. Plug in Thomas's board and pick its port under `com port`.
2. Press **start**. It silences the board, reads all five modules for
   three seconds as a floor, then holds each tone for three seconds in
   ascending pitch, reading again.
3. Read the twenty-five lines it fills in — `heard`, `wrong band`, or
   `silent`. Their meanings are in the scenario.
4. **Then find out which module is which body**, which no software *on
   this board* knows: hold one tone with `hold 160 Hz on`, cover one
   microphone with your hand, and see which module number drops. Write it
   down.

Thomas's figure 2 suggests `A0` is the 6.25 kHz body down to `A4` at
160 Hz — but that is the same diagram as the disagreement above. Confirm
it; don't assume it.

> **In the installation this one is settled by construction.** The
> electronics box already had `female1 … male2/microphone/2` on A0–A4 in
> body order, and the analyser modules took their places — so module N is
> body N, and one number identifies a body the whole way round the loop.
> That is luck rather than design, and `tests > test audio loop` is what
> confirms it: it is the only test that knows which body is which, and so
> the only one that can catch a body wired to another body's channel.

**Against the stand-in it passes every time, all twenty-five.** It
answers the same menu but has no room in it — no air, no distance, no
microphone that can be deaf. A green run there says the test drives the
menu correctly and nothing whatever about anybody's wiring, which is why
the page says which board it is talking to before it says anything else.
