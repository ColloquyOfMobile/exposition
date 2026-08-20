# Colloquy of Mobiles — Hardware Setup

**What has to be plugged in, and how, before a scenario will do what it says.**

Every scenario in `colloquy/scenarios/` describes what the installation
does. This describes what has to be true of the hardware first. It is
organised by what you are about to run, so the order to read it in is:
find the thing you want to start, do what its section says, then open its
scenario and watch.

Unlike the code documentation, this page is offered on **every** machine
including the installation's own — it is the document you want open on
the machine that is wired to the thing you are wiring.

---

## The whole rig, in one drawing

Band **A** is the installation as it runs today. Bands **B** and **C**
are the audio subsystem, which nothing in the software drives yet — the
boards in them are Thomas's photographs, standing where they sit.

<div style="overflow-x: auto; margin: 1rem 0;">
<svg viewBox="0 0 1240 1010" role="img" aria-label="Schematic of the whole rig. One control laptop drives three USB leads: a U2D2 carrying the Dynamixel bus to nine servos, an Arduino Mega carrying NeoPixel groups and light sensors, and Thomas's audio Mega. The audio Mega's five timer pins feed a five-channel low-pass filter board, then dividers, then one GF1002 amplifier per body, then the speakers. On the way back, one MAX9814 microphone per body feeds the five-module analyser array, whose outputs reach A0 to A4 while strobe and reset are commoned to D4 and D3.">
  <defs>
    <marker id="rig-arrow" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="9" markerHeight="7" orient="auto">
      <polygon points="0,0 10,4 0,8" fill="currentColor"></polygon>
    </marker>
    <marker id="rig-arrow-b" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="8" markerHeight="6" orient="auto">
      <polygon points="0,0 10,4 0,8" fill="currentColor"></polygon>
    </marker>
  </defs>

  <!-- ============ band A: the three leads ============ -->
  <text x="20" y="26" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="600" letter-spacing="1.6" fill="currentColor" opacity="0.55">A &#183; THE THREE LEADS</text>

  <g fill="none" stroke="currentColor" stroke-width="1.6">
    <rect x="20" y="44" width="150" height="256" rx="4"></rect>
  </g>
  <text x="95" y="80" font-family="Chivo, sans-serif" font-size="15" font-weight="600" fill="currentColor" text-anchor="middle">Control</text>
  <text x="95" y="99" font-family="Chivo, sans-serif" font-size="15" font-weight="600" fill="currentColor" text-anchor="middle">laptop</text>
  <text x="95" y="120" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.6" text-anchor="middle">port 8087</text>

  <g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.75" text-anchor="end">
    <text x="162" y="153">USB 1</text>
    <text x="162" y="216">USB 2</text>
    <text x="162" y="279">USB 3</text>
  </g>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="170" y1="150" x2="248" y2="150"></line>
    <line x1="170" y1="213" x2="248" y2="213"></line>
    <line x1="170" y1="276" x2="248" y2="276"></line>
  </g>

  <g fill="none" stroke="currentColor" stroke-width="1.6">
    <rect x="252" y="126" width="176" height="48" rx="3"></rect>
    <rect x="252" y="189" width="176" height="48" rx="3"></rect>
    <rect x="252" y="252" width="176" height="48" rx="3"></rect>
  </g>
  <g font-family="Chivo, sans-serif" font-size="14" font-weight="600" fill="currentColor" text-anchor="middle">
    <text x="340" y="148">U2D2</text>
    <text x="340" y="211">Arduino Mega</text>
    <text x="340" y="274">Audio Mega</text>
  </g>
  <g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">
    <text x="340" y="163">Dynamixel protocol</text>
    <text x="340" y="226">JSON &#183; 57600 baud</text>
    <text x="340" y="289">text menu &#183; 9600 baud</text>
  </g>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="428" y1="150" x2="520" y2="150"></line>
    <line x1="428" y1="213" x2="520" y2="213"></line>
    <path d="M 428 276 L 496 276 L 496 318"></path>
  </g>
  <text x="506" y="281" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.75">the audio subsystem &#8212; bands B and C below</text>
  <g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">
    <text x="474" y="143">TTL bus</text>
    <text x="474" y="206">1 wire</text>
  </g>

  <g fill="none" stroke="currentColor" stroke-width="1.4">
    <rect x="524" y="118" width="250" height="64" rx="3"></rect>
    <rect x="524" y="189" width="250" height="48" rx="3"></rect>
    <rect x="798" y="189" width="200" height="48" rx="3"></rect>
  </g>
  <text x="649" y="140" font-family="Chivo, sans-serif" font-size="14" font-weight="600" fill="currentColor" text-anchor="middle">9 Dynamixel servos</text>
  <text x="649" y="157" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">female1-3 &#183; male1-2 &#183; bar</text>
  <text x="649" y="171" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">mirror1-3 (ids 2, 4, 6 &#8212; may be unwired)</text>
  <text x="649" y="211" font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">20 NeoPixel groups</text>
  <text x="649" y="227" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">head &#183; bodyO &#183; bodyP &#183; feet &#183; rings</text>
  <text x="898" y="211" font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">11 light sensors</text>
  <text x="898" y="227" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">1 per female, 4 per male</text>
  <line x1="774" y1="213" x2="792" y2="213" stroke="currentColor" stroke-width="1.4" marker-end="url(#rig-arrow-b)" fill="none"></line>

  <line x1="20" y1="330" x2="1220" y2="330" stroke="currentColor" stroke-width="1" opacity="0.28"></line>

  <!-- ============ band B: speaking ============ -->
  <text x="20" y="366" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="600" letter-spacing="1.6" fill="currentColor" opacity="0.55">B &#183; SPEAKING &#8212; five channels, one per body</text>

  <g fill="none" stroke="currentColor" stroke-width="1.6">
    <rect x="20" y="392" width="132" height="188" rx="3"></rect>
  </g>
  <text x="86" y="418" font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">Timer pins</text>
  <g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor">
    <text x="36" y="443">D11</text><text x="150" y="443" text-anchor="end" opacity="0.7">160 Hz</text>
    <text x="36" y="466">D5</text><text x="150" y="466" text-anchor="end" opacity="0.7">400 Hz</text>
    <text x="36" y="489">D6</text><text x="150" y="489" text-anchor="end" opacity="0.7">1 kHz</text>
    <text x="36" y="512">D46</text><text x="150" y="512" text-anchor="end" opacity="0.7">2.5 kHz</text>
    <text x="36" y="535">D10</text><text x="150" y="535" text-anchor="end" opacity="0.7">6.25 kHz</text>
  </g>
  <text x="86" y="562" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">CTC, free-running</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="152" y1="486" x2="228" y2="486"></line>
  </g>
  <text x="190" y="474" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">5 Vpp</text>
  <text x="190" y="502" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">square</text>

  <image href="/static/hardware/low-pass-filter-board.jpg" x="232" y="396" width="220" height="175" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="232" y="396" width="220" height="175" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <text x="342" y="592" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Low-pass filter board</text>
  <text x="342" y="608" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">2nd order &#183; R1=R2, C1=C2</text>
  <text x="342" y="622" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">IN: 160 400 1K 2K5 6K25</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="452" y1="486" x2="528" y2="486"></line>
  </g>
  <text x="490" y="474" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">2 Vpp</text>
  <text x="490" y="502" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">&#8722;20 dB</text>

  <rect x="532" y="452" width="104" height="68" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
  <text x="584" y="480" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Divider</text>
  <text x="584" y="498" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.7" text-anchor="middle">22K / 3K3</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="636" y1="486" x2="712" y2="486"></line>
  </g>
  <text x="674" y="474" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">330 mVpp</text>
  <text x="674" y="502" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">below ceiling</text>

  <image href="/static/hardware/amplifier-module.jpg" x="716" y="410" width="200" height="152" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="716" y="410" width="200" height="152" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <text x="816" y="592" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">GF1002 amplifier</text>
  <text x="816" y="608" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">class D &#183; volume pot on board</text>
  <text x="816" y="622" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">one per body</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="916" y1="486" x2="1000" y2="486"></line>
  </g>
  <text x="958" y="474" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">PWM</text>
  <text x="958" y="502" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.6" text-anchor="middle">~250 kHz</text>

  <rect x="1004" y="440" width="140" height="92" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
  <text x="1074" y="470" font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">Loudspeaker</text>
  <text x="1074" y="488" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">open frame</text>
  <text x="1074" y="503" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">160 Hz &#8211; 6.25 kHz</text>
  <text x="1074" y="518" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">untested</text>

  <text x="958" y="556" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">keep this lead short</text>

  <line x1="20" y1="652" x2="1220" y2="652" stroke="currentColor" stroke-width="1" opacity="0.28"></line>

  <!-- ============ band C: hearing ============ -->
  <text x="20" y="688" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="600" letter-spacing="1.6" fill="currentColor" opacity="0.55">C &#183; HEARING &#8212; five microphones, five analysers, one strobe</text>

  <rect x="20" y="740" width="132" height="92" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
  <text x="86" y="776" font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">The room</text>
  <text x="86" y="794" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">air, distance,</text>
  <text x="86" y="809" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">and everyone in it</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="152" y1="786" x2="228" y2="786"></line>
  </g>

  <image href="/static/hardware/microphone-module.jpg" x="232" y="706" width="140" height="161" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="232" y="706" width="140" height="161" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <text x="302" y="888" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">MAX9814 microphone</text>
  <text x="302" y="904" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">AGC &#183; gain 40 dB, A/R 1:500</text>
  <text x="302" y="918" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">one per body</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="372" y1="786" x2="452" y2="786"></line>
  </g>
  <text x="412" y="774" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">1.6 Vpp</text>

  <image href="/static/hardware/audio-analyzer-array.jpg" x="456" y="700" width="230" height="173" preserveAspectRatio="xMidYMid meet"></image>
  <rect x="456" y="700" width="230" height="173" rx="2" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.5"></rect>
  <text x="571" y="888" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Audio analyser array</text>
  <text x="571" y="904" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">5 &#215; MSGEQ7, 7 bands each</text>
  <text x="571" y="918" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">strobe &amp; reset commoned on the carrier</text>

  <g stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#rig-arrow)">
    <line x1="686" y1="786" x2="782" y2="786"></line>
  </g>
  <text x="734" y="774" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">5 analog</text>

  <rect x="786" y="716" width="200" height="140" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
  <text x="886" y="748" font-family="Chivo, sans-serif" font-size="14" font-weight="600" fill="currentColor" text-anchor="middle">Audio Mega</text>
  <text x="886" y="766" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">sensor / actor hub</text>
  <g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" text-anchor="middle">
    <text x="886" y="792">A0  A1  A2  A3  A4</text>
    <text x="886" y="814">D4 STROBE</text>
    <text x="886" y="832">D3 RESET</text>
  </g>

  <g stroke="currentColor" stroke-width="1.8" stroke-dasharray="6 4" fill="none">
    <path d="M 886 716 L 886 674 L 571 674 L 571 700"></path>
  </g>
  <circle cx="571" cy="700" r="3.5" fill="currentColor"></circle>
  <text x="600" y="666" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.75">one strobe, one reset &#8212; all five modules</text>

  <text x="1010" y="750" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.62">Reads all five at once:</text>
  <text x="1010" y="766" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.62">one cycle through the</text>
  <text x="1010" y="782" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.62">seven bands.</text>
  <text x="1010" y="812" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.62">Nothing above this</text>
  <text x="1010" y="828" font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.62">is built yet.</text>

  <line x1="20" y1="960" x2="1220" y2="960" stroke="currentColor" stroke-width="1" opacity="0.28"></line>
  <text x="20" y="984" font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62">Boards photographed by Thomas Erforth. Band A is the installation as it runs today; bands B and C are the audio subsystem, which nothing in the software drives yet.</text>
</svg>
</div>

---

## 0. The three boards, and which lead is which

There are up to three USB leads, and picking the wrong one is the most
common way to lose ten minutes.

| Board | What it drives | Speaks | Chosen at |
|---|---|---|---|
| **U2D2** | the nine Dynamixel servos — 3 females, 2 males, the bar, 3 mirrors | Dynamixel protocol | `hardware/u2d2/com port` (`COM4` on the installation laptop) |
| **Arduino Mega** (installation) | every NeoPixel group and every light sensor | JSON lines, 57600 baud | `hardware/arduino/com port` |
| **Arduino Mega** (Thomas's audio tester) | five tone outputs and five audio analysers | a text menu, 9600 baud | `tests/test audio subsystem/com port` |

**Telling them apart without unplugging anything:** open the port and see
what it says. The installation's Arduino answers `Hello!` and then only
replies to JSON. Thomas's board clears the screen and prints
`---- Audio subsystem tester for ----`. The audio bench test checks for
exactly that banner and refuses rather than sitting there failing
silently, so if it refuses with "no audio tester on that port", the lead
is right there in the message.

On any machine that is not the installation laptop all three are
simulated and the port list offers `simulated u2d2 port`,
`simulated arduino port` and `simulated audio port` instead.

---

## 1. Before any scenario that moves a body

Applies to: **switching on**, **one male / one female from switch-on**,
**a male calling**, **a female looking**, **the bar wandering**,
**swaying a body by hand**, and every hardware test under `tests`.

1. **Power the servos before opening the port.** A Dynamixel with no
   power answers nothing, and `init hardware` will report every one of
   them missing rather than the one that is.
2. **Check the bar is clear over its whole travel** before anything
   starts. It runs 293° from its origin — nearly a full turn of the rail
   — and it is the only body that can foul something at the far end of a
   range nobody stood and watched.
3. **Home everything first.** `hardware/bodies` → home, and
   `hardware/bar` → turn to origin. Every scenario's clock starts from
   the bodies at their origins; starting from somewhere else makes the
   first thirty seconds of any of them read wrong.
4. **The origins are calibration, not settings.** `params/<body>/dxl
   origin` is the raw servo reading when that body points where it should.
   If a body sways visibly off-centre, that number wants correcting at
   the rig — see §5.

---

## 2. Before any scenario that reads a light sensor

Applies to: **a female looking**, **pattern-reading test**, and all six
runs inside **the light-sensor sequence**.

- **The installation's Arduino must be open**, not just plugged in.
  Nothing warns you: a closed port makes every sensor read as a constant,
  and the run completes and produces a flat graph.
- **`photosensor_threashold` is one absolute number for every sensor**
  (`params`), currently 300. It is the weakest part of the light side.
  A room brighter than it was when that number was picked makes every
  female read "light" everywhere; darker, and none of them read anything.
- **Run the false-positives test first, in the room the piece will be
  shown in.** Every light off, all three females sweeping. A flat line is
  the answer you want; a hump is a direction that is too bright, and its
  position on the graph tells you where in the room to stand and look.
- **The two lower tones and the room lights are separate problems** —
  don't tune the threshold on a bench and expect it to hold in a gallery.

---

## 3. Before the audio subsystem bench test

Applies to: **the audio subsystem test**. This is the newest hardware and
the only part nobody has set up before, so it gets the most detail.

Everything below is from Thomas Erforth's *Colloquy of Mobiles — Redesign
of 2018 Version* (23.6.2026), in `Source code/Thomas/`, together with his
`AudioAnalyzerTest.cpp` firmware.

### 3.1 The idea

Each body — three females, two males — **speaks one tone and hears
through one analyser**. Five bodies, five tones, five microphones, five
analysers.

The five tones are 160 Hz, 400 Hz, 1 kHz, 2.5 kHz and 6.25 kHz. They are
five of the MSGEQ7's seven bands; the other two are unusable, and Thomas
says why: a typical electret microphone is only specified from 100 Hz to
10 kHz, so 63 Hz and 16 kHz are outside it — and a good part of the
audience cannot hear 16 kHz anyway.

### 3.2 The speaking chain

```
Arduino Mega timer  ──►  2nd-order low-pass filter  ──►  divider  ──►  GF1002 amp  ──►  loudspeaker
      5 Vpp                       2 Vpp                  330 mVpp        class D, ~250 kHz PWM
   square wave              harmonic damped >20 dB                       volume pot on board
```

**Timers.** Timers 1, 3, 4, 5 (16-bit) and 2 (8-bit) run in CTC mode.
Once initialised they cost nothing — they free-run in hardware, and the
sketch never touches them again.

**Why the filters exist.** A counter makes a *square* wave, which is the
fundamental plus every odd harmonic. The first harmonic of each tone
lands uncomfortably close to a neighbouring band, and the MSGEQ7's own
band-pass cannot separate them:

| Tone | 1st harmonic | Neighbouring band | Distance |
|---|---|---|---|
| 160 Hz | 480 Hz | 400 Hz | **80 Hz** |
| 400 Hz | 1200 Hz | 1000 Hz | **200 Hz** |
| 1000 Hz | 3000 Hz | 2500 Hz | 500 Hz |
| 2500 Hz | 7500 Hz | 6250 Hz | 1250 Hz |
| 6250 Hz | 18750 Hz | 16000 Hz | 2750 Hz |

So each channel gets a passive second-order low-pass. Both stages are
identical (R1 = R2, C1 = C2), which is what makes the board look as
regular as it does:

| Band | R | C |
|---|---|---|
| 6250 Hz | 2K2 | 10 nF |
| 2500 Hz | 1K8 | 47 nF |
| 1000 Hz | 1K2 | 150 nF |
| 400 Hz | 2K | 220 nF |
| 160 Hz | 2K2 | 470 nF |

Measured result: the first harmonic damped by more than 20 dB — under
10% of the fundamental. The output is still not a sine wave, and does not
need to be. The top two bands did not strictly need filtering; they were
given it anyway so all five tones sound alike.

**The divider.** R1/R2 = 22K/3K3, the same on all five channels, to keep
the filter output under the amplifier's maximum input **with the module's
volume control at maximum**. Exceeding it makes the amp clip, and a
clipped output is a square wave again — which throws away everything the
filter just did.

**The amplifier.** A GF1002 class-D module with its own volume pot, so
levels can still be trimmed in the room. Its output is differential PWM
at about 250 kHz: sharp edges, high currents, real EMI. **Mount the
amplifier close to its loudspeaker and keep the speaker wires short.**

**The loudspeaker.** Must be reasonably flat from 160 Hz to 6250 Hz. The
existing speakers have not been shown to be. They sit in an open frame,
which is close to an acoustic short circuit, so the two lowest tones are
the ones to test for sound pressure first.

### 3.3 The hearing chain

```
loudspeaker ──►  air  ──►  MAX9814 microphone module  ──►  MSGEQ7 analyser  ──►  Mega ADC
                              with AGC, 5 V max              1.6 Vpp            A0 … A4
```

**Microphone.** The 2018 module was a plain op-amp preamp, which in a
noisy room saturates and turns the tone back into a square wave —
undoing, at the last step, everything the filters did at the first. The
replacement is a **MAX9814**: low-noise preamp, variable-gain amp, output
amp, mic bias and automatic gain control. The AGC is the point; it is the
headroom.

Set by strapping, and these are the pins to get right:

| Pin | Tie to | Effect |
|---|---|---|
| **Gain** | GND | 50 dB |
| | VDD | **40 dB** ← Thomas's bench result |
| | float | 60 dB |
| **A/R** | GND | **1:500** ← Thomas's bench result |
| | VDD | 1:2000 |
| | float | 1:4000 |

Best results on the workbench were **gain 40 dB with A/R 1:500** — at
1:500 the gain recovers fastest after a spike. Thomas notes this must be
double-checked in the field, so treat it as a starting point rather than
a final answer.

**Analyser.** MSGEQ7, unchanged from the 2018 version. **STROBE and RESET
of all five modules are tied together** to save pins on the hub, so one
cycle through the seven bands reads all five modules at once. The five
analog outputs go to five ADC inputs.

**One property to know before writing anything that reads it:** the
MSGEQ7's internal scan rate is fast enough to catch individual points on
the *waveform* of the 160 Hz and 400 Hz signals — so repeated readings
vary depending on where in the cycle it happened to sample. Thomas's
remedy: read **four times in quick succession when expecting 160 Hz** and
**twice for 400 Hz**. In his tests 160 Hz always produced at least two
high hits out of four, and 400 Hz at least one out of two. The bench test
in this repo does not do this yet — it averages whole sweeps instead,
which is enough to say "heard" but is not the way to sample a tone
properly.

### 3.4 The four prototype boards

**Low-pass filter board** — five channels. `IN` along one edge in the
order **160, 400, 1K, 2K5, 6K25**, `OUT` on the other, GND and VDD as
marked. The five groups of yellow capacitors are the five bands; the
biggest capacitors belong to the lowest tone.

![Low-pass filter board](/static/hardware/low-pass-filter-board.jpg)

**Microphone module** — a MAX9814 breakout on a carrier. Header on the
carrier: `GND / VDD / AOUT` and `GND / Gain / VDD`, `VDD / AR / GND`.
Strap Gain and AR per the table in §3.3.

![Microphone module](/static/hardware/microphone-module.jpg)

**Amplifier module** — the GF1002 with its volume pot, on a carrier with
a screw terminal for supply and JST connectors for audio in and speaker
out (`Audio`/`GND`, `VDD`/`GND`, `ROUT+`). One of these per body, each
close to its own speaker.

![Amplifier module](/static/hardware/amplifier-module.jpg)

**Audio analyser array** — the five MSGEQ7 boards on one carrier, with
their strobe and reset commoned across the back and one JST per module
for its microphone. This single board is the whole hearing side.

![Audio analyser array](/static/hardware/audio-analyzer-array.jpg)

### 3.5 Wiring it to the Mega

From `AudioAnalyzer.h`. **These are the numbers the firmware actually
uses**, so they are what the board must be wired to:

| Timer | Tone | Mega pin |
|---|---|---|
| T1 | 160 Hz | **D11** |
| T3 | 400 Hz | **D5** |
| T4 | 1 kHz | **D6** |
| T5 | 2.5 kHz | **D46** |
| T2 | 6.25 kHz | **D10** |

| Analyser | Mega pin |
|---|---|
| STROBE (all five) | **D4** |
| RESET (all five) | **D3** |
| Module outputs 0–4 | **A0 … A4**, in ascending order |

> ### ⚠ One thing to settle with Thomas before wiring
>
> **The PDF's block diagrams and the firmware disagree about which timer
> makes which tone**, and they disagree by being exactly reversed.
>
> | | T1 | T3 | T4 | T5 | T2 |
> |---|---|---|---|---|---|
> | `AudioAnalyzer.h` | 160 Hz | 400 Hz | 1 kHz | 2.5 kHz | 6.25 kHz |
> | PDF figures 1 & 2 | 6.25 kHz | 2.5 kHz | 1 kHz | 400 Hz | 160 Hz |
>
> The firmware is self-consistent — its OCR values compute to 162, 405,
> 1012, 2530 and 6329 Hz for T1, T3, T4, T5, T2 — so the tone that comes
> out of D11 really is 160 Hz. What is unresolved is **which filter
> channel each pin is wired to**, and that is a decision about the board,
> not about the code.
>
> It matters, and **the bench test cannot catch it**: a low-pass filter
> passes anything below its corner, so 160 Hz fed into the 6.25 kHz
> channel still comes out, still lands in the 160 Hz band, and still
> reports "heard". What you lose is the filtering — the 6.25 kHz channel
> barely touches the 480 Hz first harmonic that the 160 Hz channel exists
> to remove. The symptom would be poor detection in a noisy room, months
> later, and nothing pointing at the cause.
>
> So: check by ear or by scope which physical channel each pin feeds
> before trusting the run.

### 3.6 Running it

1. Plug in Thomas's board, pick its port under
   `tests/test audio subsystem/com port`.
2. Press **start**. It silences the board, reads all five modules for
   three seconds as a floor, then holds each tone for three seconds in
   ascending pitch, reading again.
3. Read the twenty-five lines it fills in — `heard`, `wrong band`, or
   `silent`. Their meanings are in the scenario.
4. **Then find out which module is which body**, which no software here
   knows: hold one tone with `hold 160 Hz on`, cover one microphone with
   your hand, and see which module number drops. Write it down. Thomas's
   figure 2 suggests A0 is the 6.25 kHz body down to A4 at 160 Hz, but
   that is the same diagram as the disagreement above — confirm it, don't
   assume it.

---

## 4. What is not wired at all

So that time is not lost looking for it:

- **The mirrors.** Three servos exist on DXL ids 2, 4 and 6 and may not be
  connected. Nothing initialises them at startup, so unwired mirror
  servos cost nothing — but nothing drives them either, and their motion
  range in params is `0.0` because nobody has measured how far one can
  turn before it fouls. Measure it at the rig and type it in.
- **The sound channel above the hardware.** Nothing sings and nothing
  listens. The bench test in §3 talks to Thomas's board and that is the
  entire extent of audio in this software. See CODE_DOCUMENTATION §9.
- **Speakers and microphones in the installation's own tree.**
  `Hardware._speakers` is an empty list.

---

## 5. Calibration, and the units it is in

One rule, and getting it backwards is the mistake that keeps happening:

- **`dxl origin` is in raw servo units.** It is the reading a body gives
  when it points where it should. Set it with `set current position as
  dxl origin` after aiming the body by hand.
- **Everything else is in degrees of the body itself** — motion ranges,
  the bar's meeting angles, the simulator's thresholds.

Every body in the room is geared **1:3** — a female, a male and the bar
all turn three times slower than their servo. Only a mirror turns with
its own. So all five bodies sway the same 29° either side of their
origin, and the bar runs 293° from its origin to the far end.

Ranges are read from params on every use, so a number edited on the
params page takes effect on the next sway rather than at the next restart.
