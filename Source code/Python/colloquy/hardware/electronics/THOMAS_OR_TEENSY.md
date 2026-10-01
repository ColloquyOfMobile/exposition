# Thomas or Teensy: one main PCB, two ways to make sound

**A specification for the main PCB that tests both sound solutions on one
board, one at a time.** In **Thomas mode** it is Thomas Erforth's chain as
the v2 board draws it: the Mega makes five fixed tones on its hardware
timers, five passive filters round them, five MSGEQ7s hear them. In
**Teensy mode** a Teensy 4.1 makes the voices at any pitch through three
I2S DACs and samples all five microphones for the laptop to analyse.
**Changing mode is moving one shunt.** Every connection to the other
boards is the one the v2 board already makes, pin for pin, and every
part that has an SMD version is SMD so the assembler places it.

Written 2026-10-01. It is a solution beside `next pcb`, `one board per
body`, `opencm and pro minis` and `ad9833 dual mode`, and it is built on
two of them: Thomas mode **is** `next pcb` as the v2 project
(`CAD/KiCad/electronic box v2/colloquy-control-v2/`) drew and routed it,
and Teensy mode is the Teensy column of `sound options` made into a
circuit. Read those for anything this does not repeat. It does not
include the AD9833: `sound options` already says why the hearing side
decides it, and only the Teensy changes the hearing side.

> **Decided 2026-10-01: one mode for the whole board, never both at
> once.** Both solutions have to be testable on the same PCB, but not at
> the same time. So the mode is one net, set by one shunt, and it moves
> all five voices together. A body cannot be left in the other mode, and
> no arrangement of the board sends two voices down one cable.

**What is sourced and what is not.** The connector pinouts and every
Thomas-mode value are read out of the v2 project's `circuit.json` (its
connectivity contract, itself built from `next_pcb.net`).
`pytest_tests/hardware/test_thomas_or_teensy.py` holds section 2's tables
to that file, so this copy cannot drift from the copper. The Teensy's I2S
pins were read out of PJRC's Audio library (`output_i2s.cpp`,
`output_i2s_hex.cpp`), its ADC pin map out of the ADC library's channel
tables, and the rest of the Teensy facts off PJRC's Teensy 4.1 page, all
on 2026-10-01. The PCM5102A circuit is TI's (SLAS859C, figure 33 and the
pin table), and the MSGEQ7's SOIC package is in Mixed Signal
Integration's datasheet (3/2022, ordering information). **Everything
else about a part is marked *check*** — the relays, the op-amp, the logic
buffers, the LDO, capacitor stock — for `next pcb` section 5's reason: a
figure about a part you intend to buy and a fact about the part in your
hand read identically.

---

## 0. The idea in one paragraph

**Everything that is not sound is the same in both modes.** The Mega
drives the NeoPixels and reads the photosensors on firmware 4, the U2D2
masters the servos, and the harness, its four DSUBs and the boards behind
them do not change. The sound has **two complete chains on the board**,
and they meet in exactly two places. **Outward**, a relay contact per
body chooses which chain's output reaches that body's line-out
conductor; all five move on one net, set by one shunt. **Inward**, each
body's microphone conductor tees into both ears through a resistor each,
with no switch at all: an ear that nobody is reading costs nothing, and
a switch in the receive path would be one more thing for a quiet
microphone to be blamed on. **Released, the relays are Thomas mode**, so
Thomas mode needs nothing powered and nothing fitted beyond the v2
board's own parts. The Teensy socket may be empty.

---

## 1. The two modes at a glance

**Drawn.** The same board and the same harness in both modes; only the
shunt differs. Solid boxes work in that mode, dashed ones are fitted or
socketed and idle. One body stands for all five. The MODE net is also
read by both processors (section 4e), which is not drawn.

<div style="overflow-x: auto; margin: 1rem 0;">
<svg viewBox="0 0 1300 880" role="img" aria-label="Block diagram of the main PCB in its two modes. In both, the laptop talks over USB to the Mega 2560, which drives the NeoPixels and reads the photosensors, and to the U2D2, which drives the Dynamixel servos; the harness and the bodies are the same. Thomas mode: the Mega makes five fixed tones on hardware timers, five RC low-pass filters shape them, and the mode relays, left released by one shunt set to THOMAS, send them down the line-out conductors to each body's divider, amplifier and speaker. Each body's MAX9814 microphone comes back up the harness to five MSGEQ7 analysers read by the Mega on A0 to A4. The Teensy socket may be empty, and the DACs and anti-alias buffers are idle. Teensy mode: the shunt is moved to TEENSY. The Teensy 4.1, on its own USB lead, makes the voices at any pitch through three PCM5102A DACs over I2S, and the mode relays, pulled in by the shunt, send those down the same line-out conductors. The same microphone conductors feed five anti-alias buffers into the Teensy's analog pins 14 to 18, which stream the samples to the laptop. The filters and MSGEQ7s are fitted and idle.">
<defs>
<marker id="tt-ax" viewBox="0 0 10 8" refX="9" refY="4" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="8" orient="auto"><polygon points="0,0 10,4 0,8" fill="currentColor"></polygon></marker>
</defs>
<!-- ================= THOMAS MODE ================= -->
<g>
<text x="20" y="26" font-family="'IBM Plex Mono', monospace" font-size="12" font-weight="600" letter-spacing="1.4" fill="currentColor" opacity="0.7">THOMAS MODE &#183; Thomas's chain, exactly as the v2 board draws it</text>
<rect x="20" y="150" width="110" height="120" rx="4" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
<rect x="165" y="40" width="705" height="352" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<rect x="890" y="40" width="50" height="352" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.6"></rect>
<rect x="960" y="40" width="320" height="352" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<text x="180" y="58" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" opacity="0.55" fill="currentColor" text-anchor="start">MAIN PCB</text>
<text x="975" y="58" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" opacity="0.55" fill="currentColor" text-anchor="start">BODY &#215; 5</text>
<text x="915" y="250" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">DSUB</text>
<text x="915" y="263" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">harness</text>
<text x="915" y="276" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">fixed</text>
<g fill="none" stroke="currentColor">
<path d="M 130 175 H 145 V 110 H 188" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 130 210 H 150 V 240 H 188" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 130 245 H 140 V 350 H 188" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 80 H 988" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 105 H 368" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 530 105 H 573" stroke-width="2.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 215 H 360 V 160 H 368" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 530 160 H 573" stroke-width="2.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 620 200 V 184" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 665 132 H 988" stroke-width="2.4" marker-end="url(#tt-ax)"></path>
<path d="M 990 320 H 560" stroke-width="2.4"></path>
<path d="M 560 320 H 532" stroke-width="2.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 560 320 V 270 H 532" stroke-width="2.4" marker-end="url(#tt-ax)"></path>
<path d="M 370 270 H 345 V 150 H 322" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 370 320 H 335 V 265 H 322" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 358 H 1148" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
</g>
<circle cx="560" cy="320" r="4" fill="currentColor"></circle>
<rect x="190" y="65" width="130" height="100" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="190" y="200" width="130" height="80" rx="3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5"></rect>
<rect x="190" y="335" width="130" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="370" y="85" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="370" y="140" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5"></rect>
<rect x="575" y="85" width="90" height="97" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="580" y="200" width="80" height="30" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="370" y="250" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="370" y="300" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5"></rect>
<rect x="990" y="66" width="110" height="28" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="990" y="115" width="80" height="36" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="1085" y="115" width="80" height="36" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="1180" y="115" width="85" height="36" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="990" y="305" width="110" height="30" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="1150" y="345" width="120" height="28" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<text x="75" y="205" font-family="Chivo, sans-serif" font-size="15" font-weight="600" fill="currentColor" text-anchor="middle">Laptop</text>
<text x="75" y="225" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">Python program</text>
<text x="75" y="252" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">2 USB leads</text>
<text x="255" y="100" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Mega 2560</text>
<text x="255" y="120" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">firmware 4</text>
<text x="255" y="136" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">lights, sensors,</text>
<text x="255" y="151" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">tones, bands</text>
<text x="255" y="232" font-family="Chivo, sans-serif" font-size="13" font-weight="600" opacity="0.6" fill="currentColor" text-anchor="middle">Teensy 4.1</text>
<text x="255" y="252" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.5" fill="currentColor" text-anchor="middle">socket may be</text>
<text x="255" y="266" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.5" fill="currentColor" text-anchor="middle">empty</text>
<text x="255" y="360" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">U2D2</text>
<text x="450" y="103" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">5 &#215; RC low-pass</text>
<text x="450" y="118" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.62" fill="currentColor" text-anchor="middle">fixed pitch</text>
<text x="450" y="158" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" opacity="0.6" fill="currentColor" text-anchor="middle">3 &#215; PCM5102A</text>
<text x="450" y="173" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.5" fill="currentColor" text-anchor="middle">unused</text>
<text x="620" y="118" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">mode</text>
<text x="620" y="134" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">relays</text>
<text x="620" y="156" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">3 &#215; DPDT</text>
<text x="620" y="220" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="700" fill="currentColor" text-anchor="middle">THOMAS</text>
<text x="450" y="268" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">5 &#215; MSGEQ7</text>
<text x="450" y="283" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.62" fill="currentColor" text-anchor="middle">7 bands each</text>
<text x="450" y="318" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" opacity="0.6" fill="currentColor" text-anchor="middle">5 &#215; anti-alias</text>
<text x="450" y="333" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.5" fill="currentColor" text-anchor="middle">unpowered</text>
<text x="1045" y="84" font-family="Chivo, sans-serif" font-size="11" fill="currentColor" text-anchor="middle">pixels &#183; photos</text>
<text x="1030" y="131" font-family="Chivo, sans-serif" font-size="12" fill="currentColor" text-anchor="middle">divider</text>
<text x="1030" y="145" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">22K / 3K3</text>
<text x="1125" y="131" font-family="Chivo, sans-serif" font-size="12" fill="currentColor" text-anchor="middle">amplifier</text>
<text x="1125" y="145" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">+ 470 &#181;F</text>
<text x="1222" y="137" font-family="Chivo, sans-serif" font-size="12" fill="currentColor" text-anchor="middle">speaker</text>
<text x="1045" y="324" font-family="Chivo, sans-serif" font-size="11.5" fill="currentColor" text-anchor="middle">MAX9814 mic</text>
<text x="1210" y="363" font-family="Chivo, sans-serif" font-size="11" fill="currentColor" text-anchor="middle">Dynamixel servo</text>
<text x="345" y="98" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">tones</text>
<text x="780" y="124" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">line out</text>
<text x="480" y="74" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">NeoPixels &#183; photosensors</text>
<text x="620" y="245" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">one shunt</text>
<text x="760" y="312" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">microphone</text>
<text x="480" y="352" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">Dynamixel data</text>
<text x="780" y="148" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">2.5 Vpp on 2.5 V</text>
<text x="366" y="201" font-family="'IBM Plex Mono', monospace" font-size="9" opacity="0.75" fill="currentColor" text-anchor="start">I2S</text>
<text x="349" y="241" font-family="'IBM Plex Mono', monospace" font-size="9" opacity="0.75" fill="currentColor" text-anchor="start">A0&#8211;A4</text>
<text x="340" y="313" font-family="'IBM Plex Mono', monospace" font-size="9" opacity="0.75" fill="currentColor" text-anchor="start">14&#8211;18</text>
<text x="975" y="386" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="start">+5 V &#183; +12 V &#183; GND on every cable</text>
</g>
<!-- ================= TEENSY MODE ================= -->
<g>
<text x="20" y="446" font-family="'IBM Plex Mono', monospace" font-size="12" font-weight="600" letter-spacing="1.4" fill="currentColor" opacity="0.7">TEENSY MODE &#183; any pitch, the microphones sampled on the laptop</text>
<rect x="20" y="570" width="110" height="120" rx="4" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
<rect x="165" y="460" width="705" height="352" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<rect x="890" y="460" width="50" height="352" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.6"></rect>
<rect x="960" y="460" width="320" height="352" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<text x="180" y="478" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" opacity="0.55" fill="currentColor" text-anchor="start">MAIN PCB</text>
<text x="975" y="478" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" opacity="0.55" fill="currentColor" text-anchor="start">BODY &#215; 5</text>
<text x="915" y="670" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">DSUB</text>
<text x="915" y="683" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">harness</text>
<text x="915" y="696" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">fixed</text>
<g fill="none" stroke="currentColor">
<path d="M 130 595 H 145 V 530 H 188" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 130 630 H 150 V 660 H 188" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 130 665 H 140 V 770 H 188" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 500 H 988" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 525 H 368" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 530 525 H 573" stroke-width="2.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 635 H 360 V 580 H 368" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 530 580 H 573" stroke-width="2.4" marker-end="url(#tt-ax)"></path>
<path d="M 620 620 V 604" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 665 552 H 988" stroke-width="2.4" marker-end="url(#tt-ax)"></path>
<path d="M 990 740 H 560" stroke-width="2.4"></path>
<path d="M 560 740 H 532" stroke-width="2.4" marker-end="url(#tt-ax)"></path>
<path d="M 560 740 V 690 H 532" stroke-width="2.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 370 690 H 345 V 570 H 322" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.4" marker-end="url(#tt-ax)"></path>
<path d="M 370 740 H 335 V 685 H 322" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
<path d="M 320 778 H 1148" stroke-width="1.4" marker-end="url(#tt-ax)"></path>
</g>
<circle cx="560" cy="740" r="4" fill="currentColor"></circle>
<rect x="190" y="485" width="130" height="100" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="190" y="620" width="130" height="80" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="190" y="755" width="130" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="370" y="505" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5"></rect>
<rect x="370" y="560" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="575" y="505" width="90" height="97" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="580" y="620" width="80" height="30" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="370" y="670" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5"></rect>
<rect x="370" y="720" width="160" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="990" y="486" width="110" height="28" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="990" y="535" width="80" height="36" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="1085" y="535" width="80" height="36" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="1180" y="535" width="85" height="36" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="990" y="725" width="110" height="30" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="1150" y="765" width="120" height="28" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<text x="75" y="625" font-family="Chivo, sans-serif" font-size="15" font-weight="600" fill="currentColor" text-anchor="middle">Laptop</text>
<text x="75" y="645" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">Python program</text>
<text x="75" y="672" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">3 USB leads</text>
<text x="255" y="520" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Mega 2560</text>
<text x="255" y="540" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">firmware 4</text>
<text x="255" y="556" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">lights, sensors</text>
<text x="255" y="652" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">Teensy 4.1</text>
<text x="255" y="670" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">voices and ears</text>
<text x="255" y="685" font-family="'IBM Plex Mono', monospace" font-size="10.5" opacity="0.62" fill="currentColor" text-anchor="middle">3.3 V</text>
<text x="255" y="780" font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">U2D2</text>
<text x="450" y="523" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" opacity="0.6" fill="currentColor" text-anchor="middle">5 &#215; RC low-pass</text>
<text x="450" y="538" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.5" fill="currentColor" text-anchor="middle">unused</text>
<text x="450" y="578" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">3 &#215; PCM5102A</text>
<text x="450" y="593" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.62" fill="currentColor" text-anchor="middle">any pitch</text>
<text x="620" y="538" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">mode</text>
<text x="620" y="554" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">relays</text>
<text x="620" y="576" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">3 &#215; DPDT</text>
<text x="620" y="640" font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="700" fill="currentColor" text-anchor="middle">TEENSY</text>
<text x="450" y="688" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" opacity="0.6" fill="currentColor" text-anchor="middle">5 &#215; MSGEQ7</text>
<text x="450" y="703" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.5" fill="currentColor" text-anchor="middle">fitted, idle</text>
<text x="450" y="738" font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle">5 &#215; anti-alias</text>
<text x="450" y="753" font-family="'IBM Plex Mono', monospace" font-size="10" opacity="0.62" fill="currentColor" text-anchor="middle">buffer, 3.3 V</text>
<text x="1045" y="504" font-family="Chivo, sans-serif" font-size="11" fill="currentColor" text-anchor="middle">pixels &#183; photos</text>
<text x="1030" y="551" font-family="Chivo, sans-serif" font-size="12" fill="currentColor" text-anchor="middle">divider</text>
<text x="1030" y="565" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">22K / 3K3</text>
<text x="1125" y="551" font-family="Chivo, sans-serif" font-size="12" fill="currentColor" text-anchor="middle">amplifier</text>
<text x="1125" y="565" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="middle">+ 470 &#181;F</text>
<text x="1222" y="557" font-family="Chivo, sans-serif" font-size="12" fill="currentColor" text-anchor="middle">speaker</text>
<text x="1045" y="744" font-family="Chivo, sans-serif" font-size="11.5" fill="currentColor" text-anchor="middle">MAX9814 mic</text>
<text x="1210" y="783" font-family="Chivo, sans-serif" font-size="11" fill="currentColor" text-anchor="middle">Dynamixel servo</text>
<text x="345" y="518" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">tones</text>
<text x="780" y="544" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">line out</text>
<text x="480" y="494" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">NeoPixels &#183; photosensors</text>
<text x="620" y="665" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">one shunt</text>
<text x="760" y="732" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">microphone</text>
<text x="480" y="772" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">Dynamixel data</text>
<text x="780" y="568" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.75" fill="currentColor" text-anchor="middle">2.5 Vpp on 0 V</text>
<text x="366" y="621" font-family="'IBM Plex Mono', monospace" font-size="9" opacity="0.75" fill="currentColor" text-anchor="start">I2S</text>
<text x="349" y="661" font-family="'IBM Plex Mono', monospace" font-size="9" opacity="0.75" fill="currentColor" text-anchor="start">A0&#8211;A4</text>
<text x="340" y="733" font-family="'IBM Plex Mono', monospace" font-size="9" opacity="0.75" fill="currentColor" text-anchor="start">14&#8211;18</text>
<text x="975" y="806" font-family="'IBM Plex Mono', monospace" font-size="9.5" opacity="0.62" fill="currentColor" text-anchor="start">+5 V &#183; +12 V &#183; GND on every cable</text>
</g>
<!-- ================= LEGEND ================= -->
<g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.75">
<rect x="20" y="848" width="28" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<text x="56" y="860">working in this mode</text>
<rect x="250" y="848" width="28" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.6"></rect>
<text x="286" y="860">fitted or socketed, idle in this mode</text>
<line x1="580" y1="856" x2="620" y2="856" stroke="currentColor" stroke-width="2.4"></line>
<text x="628" y="860">audio</text>
<line x1="700" y1="856" x2="740" y2="856" stroke="currentColor" stroke-width="1.4"></line>
<text x="748" y="860">digital, sensors, servo data</text>
<circle cx="980" cy="856" r="4" fill="currentColor"></circle>
<text x="992" y="860">a dot joins; a crossing does not</text>
</g>
</svg>
</div>

| | Thomas mode | Teensy mode |
|---|---|---|
| voice | Mega timers on `D11`, `D5`, `D6`, `D46`, `D10`, five passive low-passes | Teensy 4.1, I2S, three PCM5102A DACs |
| pitch | 160 / 400 / 1000 / 2500 / 6250 Hz, fixed by timer and filter | any, per body, in software; sine by default |
| ear | five MSGEQ7s, seven bands each, Mega `A0`–`A4` | five anti-alias buffers, Teensy pins 14–18, raw samples to the laptop |
| analysis | band levels, in firmware and `drivers/audio.py` | Goertzel bins in Python (`test_goertzel_ear`'s `goertzel.py`) |
| line out | about 2.5 Vpp, on 2.5 V DC while a tone sounds, 0 V between | about 2.5 Vpp by default, centred on 0 V always |
| Mega firmware | 4, unmodified | 4, unmodified (lights and sensors only) |
| Teensy | not needed; the socket may be empty | fitted, with its own USB lead |
| USB leads from the rack | 2: Mega, U2D2 | 3: Mega, U2D2, Teensy |
| the other chain | DACs and buffers unpowered | filters undriven, MSGEQ7s fitted and idle |
| harness and bodies | unchanged | unchanged |

**The body cannot tell the two modes apart** except by what it hears.
Both put line level on the same conductor, referenced to the same audio
return, into the same 22K/3K3 divider and the same amplifier
(`next pcb` section 3). Teensy mode differs in one way the body will
notice, and it is an improvement: Thomas's line sits at 0 V between
tones and jumps to 2.5 V when a timer starts, which the amplifier's input
capacitor hears as a thump; the DAC's line is centred on 0 V throughout.

---

## 2. What does not change: the interface, pin for pin

**This board keeps every connection the v2 board makes to the outside
world.** Same outline, same fixed connectors in the same places with the
same footprints, same nets on the same pins. The positions are in
`MECHANICAL_REVIEW.md` and are not repeated; the nets are below, copied
from `circuit.json` and held to it by the test.

### The four body connectors (DSUB-15)

| Pin | `J5` female1 | `J1` female2 | `A-J3` female3, male1 | `B-J4` male1, male2 |
|---|---|---|---|---|
| shell | `GND` | `GND` | `GND` | `GND` |
| 1 | `female1/spare1` | `female2/spare1` | `GND` | `male1/aux` |
| 2 | `female1/spare2` | `female2/spare2` | `+12V` | `male1/audio return` |
| 3 | `female1/spare3` | `female2/spare3` | `female3/microphone` | `male2/neopixel` |
| 4 | `female1/audio return` | `female2/audio return` | `female3/photosensor` | `male2/photosensor/B` |
| 5 | `female1/photosensor` | `female2/photosensor` | `female3/audio return` | `male2/photosensor/D` |
| 6 | `female1/microphone` | `female2/microphone` | `male1/neopixel` | `male2/line out` |
| 7 | `+12V` | `+12V` | `male1/photosensor/B` | `centre/spare1` |
| 8 | `GND` | `GND` | `male1/photosensor/D` | `male2/bar neopixel` |
| 9 | `female1/spare4` | `female2/spare4` | `+5V` | `male1/line out` |
| 10 | `female1/spare5` | `female2/spare5` | `dxl_data` | `male2/microphone` |
| 11 | `female1/spare6` | `female2/spare6` | `female3/neopixel` | `male2/photosensor/A` |
| 12 | `female1/line out` | `female2/line out` | `female3/line out` | `male2/photosensor/C` |
| 13 | `female1/neopixel` | `female2/neopixel` | `male1/microphone` | `male2/aux` |
| 14 | `dxl_data` | `dxl_data` | `male1/photosensor/A` | `male2/audio return` |
| 15 | `+5V` | `+5V` | `male1/photosensor/C` | `male1/bar neopixel` |

**Five conductors change source with the mode, and nothing else does**:
the five `line out`s (`J5` 12, `J1` 12, `A-J3` 12, `B-J4` 9, `B-J4` 6).
The five `microphone` conductors feed both ears in both modes. Every
other pin carries in both modes exactly what it carries on the v2 board,
and `B-J4` still carries **no power** and still gets that printed beside
it (`next pcb` section 6).

### The other connectors

| Connector | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| `J7` servo bus, JST EH 3 | `GND` | `+12V` | `dxl_data` | | | |
| `J2` DC jack | `+5V` | `GND` | | | | |
| `J6` screw bridge | `GND` | `GND` | `+5V` | `GND` | `+5V` | `+5V` |
| `Extra2` female1's spares | `female1/spare1` | `female1/spare2` | `female1/spare3` | `female1/spare4` | `female1/spare5` | `female1/spare6` |
| `Extra1` female2's spares | `female2/spare1` | `female2/spare2` | `female2/spare3` | `female2/spare4` | `female2/spare5` | `female2/spare6` |
| `Extra3` the males' one spare | `centre/spare1` | | | | | |

### And everything else the v2 board fixed

- **The Mega**, carried as a shield on the **back** of the board, in the
  v2 footprint and position, with every pin firmware 4 uses on the net
  the v2 board gives it (section 3's table).
- **The U2D2 mount** `M1`, padless; the U2D2's real connection is `J7`.
- **Both 5 V rails kept apart**: the board's `+5V` (jack, NeoPixels,
  body supplies) and `MEGA_5V` (the Mega's own, which also feeds the
  MSGEQ7s, as on v2). `RS1` still pulls `D2` up to `MEGA_5V`.
- **One bond between analogue and power ground**, `JP1`, and one bond
  per body from audio return to AGND (`JP2`–`JP6`).
- **The mounting holes**: `H1`–`H4`, the U2D2's four, the jack's
  locating hole (`MECHANICAL_REVIEW.md`).

**None of the four harness boards changes.** `center`, `female static`,
`female base` and `male static` see the same conductors carrying the same
kinds of signal, and the body end is `next pcb` section 3's assembly in
both modes.

---

## 3. Thomas mode: the v2 chain, in SMD

**Electrically, this is the v2 board.** The same Mega pins, the same
filter values, the same MSGEQ7 support network, the same build-out. The
one addition in the signal path is a relay contact between each filter's
output and its 100 R build-out — a fraction of an ohm (*check* against
the relay chosen) in series with a 25 kΩ body divider. **The acceptance
test is `next pcb` section 1's**: firmware 4 runs unmodified, and every
hardware test that passes on the v2 board passes here with the Teensy
socket empty.

### The Mega pins, unchanged

Read out of `circuit.json`; the test holds this table to it.

| Mega pin | Net | |
|---|---|---|
| `D2` | `amp shutdown` | reserved, 10 K up to `MEGA_5V` (`next pcb` section 4) |
| `D3` | `analyser/reset` | |
| `D4` | `analyser/strobe` | |
| `D5` | `male2/tone` | 400 Hz, `OC3A` |
| `D6` | `female1/tone` | 1 kHz, `OC4A` |
| `D7` | `female2/neopixel/driven` | through 330 R |
| `D8` | `female3/neopixel/driven` | through 330 R |
| `D9` | `male1/neopixel/driven` | through 330 R |
| `D10` | `female3/tone` | 6.25 kHz, `OC2A` |
| `D11` | `male1/tone` | 160 Hz, `OC1A` |
| `D14` | `female1/neopixel/driven` | through 330 R |
| `D15` | `male2/neopixel/driven` | through 330 R |
| `D16` | `male1/bar neopixel/driven` | through 330 R |
| `D17` | `male2/bar neopixel/driven` | through 330 R |
| `D24` | `male1/aux driven` | through 330 R, state LED or a mute |
| `D25` | `male2/aux driven` | through 330 R |
| `D46` | `female2/tone` | 2.5 kHz, `OC5A` |
| `A0` | `female1/analyser out` | module 0 |
| `A1` | `female2/analyser out` | module 1 |
| `A2` | `female3/analyser out` | module 2 |
| `A3` | `male1/analyser out` | module 3 |
| `A4` | `male2/analyser out` | module 4 |
| `A5` | `female1/photosensor` | 10 K provisional load |
| `A6` | `female2/photosensor` | |
| `A7` | `female3/photosensor` | |
| `A8` | `male1/photosensor/A` | |
| `A9` | `male1/photosensor/B` | |
| `A10` | `male1/photosensor/C` | |
| `A11` | `male1/photosensor/D` | |
| `A12` | `male2/photosensor/A` | |
| `A13` | `male2/photosensor/B` | |
| `A14` | `male2/photosensor/C` | |
| `A15` | `male2/photosensor/D` | |

**Three Mega pins are new, and firmware 4 touches none of them**: `D18`
and `D19` (Serial1, the reserved link of section 4f) and `D30` (the MODE
sense of section 4e). All three are unconnected on the v2 board and
absent from `colloquy_of_mobiles.ino`; the test checks both.

### One channel, five times

| Part | Value | Package | Note |
|---|---|---|---|
| filter R, two stages | `R1 = R2`, per channel below | 0603, 1 % | |
| filter C, two stages | `C1 = C2`, per channel below | see below | **C0G/NP0 or PPS film, 5 %**, never X7R |
| filter output test pad | | pad | the voice before it leaves, silkscreened `<pitch> — <pin>` |
| build-out | 100 R | 0805 | after the relay's common contact, so it serves both modes |
| microphone attenuator | 47 K series, 6K8 shunt to AGND | 0603 | 0.126, as v2 |
| attenuator bypass | solder jumper, **open** | SMD pads | `JS1`–`JS5`, bridged only after measuring |
| input coupling | 100 nF | 0603 X7R | |
| MSGEQ7 | `MSGEQ7N` | **SOIC-8, 150 mil** | in the datasheet's ordering table beside the DIP |
| clock | 200 K 1 % and 33 pF C0G | 0603 | 33 pF includes stray: keep both against pin 8 |
| supply bypass | 100 nF, `MEGA_5V` to AGND | 0603 | against pins 1 and 2 |
| reference bypass | 100 nF, pin 6 to AGND | 0603 | pin 6 is a 2.5 V reference, **never grounded** |
| analyser output test pad | | pad | `module <n> — <body>` |

| Channel | Mega pin | `R1 = R2` | `C1 = C2` |
|---|---|---|---|
| male1, 160 Hz | `D11` | 2K2 | 470 nF |
| male2, 400 Hz | `D5` | 2K | 220 nF |
| female1, 1 kHz | `D6` | 1K2 | 150 nF |
| female2, 2.5 kHz | `D46` | 1K8 | 47 nF |
| female3, 6.25 kHz | `D10` | 2K2 | 10 nF |

**Why never X7R in a filter.** Each corner sits at its own tone, so the
capacitor's value decides how much of the fundamental comes through.
An X7R part loses a good part of its capacitance with DC across it, and
these carry 2.5 V of DC whenever a tone sounds; the tone's level would
then depend on the capacitor's voltage rating and case size. C0G is
flat. **470 nF, 220 nF and 150 nF in C0G are large parts** (1210 to
1812, *check* the assembler's stock); a PPS film SMD part is the fallback
at the same value. Pick the part first and give its own footprint.

**MSGEQ7 in SOIC, and what that costs.** The v2 board sockets a DIP so a
bad chip is a pull and a push. A soldered SOIC is a hot-air job instead,
which matters with a part whose counterfeits are common. So: buy the
five and a spare from an authorised distributor, and prove one finished
channel before the board is ordered (`docs/ELECTRONICS_REVIEW.md`
section 1). If the assembler cannot source `MSGEQ7N`, a combined
SOIC-8/DIP-8 footprint takes either, with a socket for the DIP.

---

## 4. Teensy mode: the new chain

### 4a. The Teensy 4.1 and its socket

**Teensy 4.1, not 4.0**: the Audio library's six-channel output uses
`OUT1B` on pin 32, which only the 4.1 brings to its edge, and `sound
options` priced the 4.1. It sits in **two 1×24 female headers** on the
**front** of the board, its USB connector at the top edge (section 6).

**It is powered by its own USB lead and nothing else.** PJRC: *"power
should not be applied to VIN while a USB cable is used"*, unless the
VIN/VUSB pads underneath are cut. So this board takes 5 V **from** `VIN`
(for the DACs' LDO, section 4b) and never puts anything **onto** it, and
nobody has to cut a Teensy to fit one.

**Its pins are not 5 V tolerant**, PJRC again: *"Do not drive any digital
pin higher than 3.3V"*, and the same for the analog pins. On a board
where everything else is 5 V, that rule decides section 4e.

| Teensy pin | Use | Note |
|---|---|---|
| 0 | `RX1`, from Mega `D18` | reserved link, through a buffer (4f) |
| 1 | `TX1`, to Mega `D19` | reserved link, through a buffer (4f) |
| 2 | `XSMT`, all three DACs | 10 K down to GND: **muted until the sketch un-mutes** |
| 3 | MODE sense | through a buffer (4e) |
| 7 | `OUT1A`, I2S data, DAC A | female1 left, female2 right; 33 R at the Teensy |
| 32 | `OUT1B`, I2S data, DAC B | female3 left, male1 right; 33 R |
| 9 | `OUT1C`, I2S data, DAC C | male2 left, bench out right; 33 R |
| 20 | `LRCLK1` | to all three DACs; 33 R |
| 21 | `BCLK1` | to all three DACs; 33 R |
| 23 | `MCLK1` | driven by the Audio library, **connected to nothing**, and lost as an analog pin |
| 14 | `A0`, female1 microphone | |
| 15 | `A1`, female2 microphone | |
| 16 | `A2`, female3 microphone | |
| 17 | `A3`, male1 microphone | |
| 18 | `A4`, male2 microphone | |
| 19 | `A5`, bench microphone | section 4c |
| 22 | `A8` | spare analog, to a test pad |
| 6 | `OUT1D` | **left free**: it is where a fourth DAC would go |
| 13 | LED | nothing; the bootloader blinks it, `next pcb` section 1's reason |
| `VIN` | 5 V from USB | the DAC LDO's input, and nothing feeds it |
| `3.3V` | the op-amps and the Teensy-side buffers | so their outputs can never exceed the Teensy's own rail |

**The microphones are on `A0`–`A4` in body order**, the same five
numbers and the same order as on the Mega, so module N is body N on both
processors. They are also where the ADC library's tables put both of the
Teensy's converters: **pins 14 to 23 reach either ADC, 24 to 27 reach
only one**, so the five can be split across the two and sampled in pairs.
The I2S clocks take 20, 21 and 23 out of that range; of the seven left,
the microphones take 14–18, the bench input 19, and 22 is spare.

### 4b. The voice: three PCM5102A

Three stereo DACs on one I2S port make six channels: five bodies and a
bench output. The Audio library's `AudioOutputI2SHex` drives exactly
pins 7, 32 and 9 with `BCLK` 21 and `LRCLK` 20 (`output_i2s_hex.cpp`,
`output_i2s.cpp`).

| Part | Value | Package | Note |
|---|---|---|---|
| DAC ×3 | PCM5102A | TSSOP-20 | |
| `SCK` (pin 12) | to GND | | 3-wire I2S: the internal PLL makes its clocks from `BCK` |
| `FMT` (16), `FLT` (11), `DEMP` (10) | to GND | | I2S; normal-latency filter; no de-emphasis |
| `XSMT` (17) | Teensy pin 2, 10 K down | | soft mute; the pull-down holds it muted while the Teensy boots, resets or is absent |
| supply `AVDD`, `CPVDD`, `DVDD` | 3.3 V from the DAC LDO | | 0.1 µF and 10 µF at each, per TI's figure 33 |
| `LDOO` (18) | 0.1 µF to GND | 0603 | TI: *"Should be used with a 0.1-µF decoupling cap"* |
| charge pump | 2.2 µF `CAPP`–`CAPM`, 2.2 µF `VNEG` to GND | 0603/0805 X7R | |
| output filter, per channel | 470 R series, 2.2 nF C0G to AGND | 0603 | TI's own recommended output filter |
| DAC LDO | 3.3 V, ≥ 200 mA, low noise | SOT-23-5 | input from Teensy `VIN`; TLV755 or AP2112 class, *check* |

**Why a separate LDO.** The three DACs draw about 20 mA each and 30 mA
at most at 48 kHz (TI's supply table: `DVDD` 8 mA typical and 13 mA
maximum playing a tone, `AVDD` plus `CPVDD` 11 and 16 mA), so the
Teensy's own 3.3 V could carry them — PJRC recommends at most 250 mA
from it. A regulator of their own keeps
the Teensy's digital noise off the DACs' analogue supply, and fed from
`VIN` it is still off whenever the Teensy is.

**No coupling capacitor, no bias.** The PCM5102A's outputs are centred
on ground by its own negative charge pump, which is what lets the relay
take either chain's output straight. TI rates them for loads down to
**1 kΩ**; the body divider is 25 kΩ.

**The level is a number in software, not a resistor.** Full scale is
2.1 Vrms, about 5.9 Vpp, and the body was sized for 2.5 Vpp
(`next pcb` section 3). So the sketch caps every voice at **2.5 Vpp by
default (about −7.5 dBFS)** and a setting lifts it. That headroom — up
to 7.5 dB above Thomas's line level on the same body — is the first
remedy if `next pcb` section 3's harness measurement comes back weak,
and Thomas mode has no such remedy. It is also the one way Teensy mode
can overdrive a body, which is why the default is Thomas's level.

**Start Teensy mode at Thomas's five pitches.** Then the first comparison
between the two modes changes one thing at a time: same pitch, same
body, same speaker, a sine instead of a filtered square, a Goertzel bin
instead of an MSGEQ7 band. Freeing the pitches comes after.

### 4c. The ear: five buffers with anti-alias filters

Per microphone, plus one for the bench input:

| Part | Value | Package | Note |
|---|---|---|---|
| input resistors | 10 K, 10 K | 0603, 1 % | Sallen–Key unity gain; also the fault limit, below |
| feedback capacitor | 2.2 nF C0G | 0603 | from the junction of the two resistors to the op-amp output |
| ground capacitor | 1 nF C0G to AGND | 0603 | at the op-amp's input |
| op-amp | one section, rail-to-rail in and out, at 3.3 V | MCP6004 class, SOIC-14, *check* | two quads: six sections used, two spare (follower, input to AGND) |
| ADC isolation | 100 R, then 1 nF C0G to AGND at the Teensy pin | 0603 | the sampling capacitor's kick lands on 1 nF, not on the op-amp |

**The filter**: about **10.7 kHz, Q 0.74**. That is above Thomas's
highest pitch (6.25 kHz) and above the electret's specified 10 kHz, and
about 12 dB down by 22 kHz. Second order is enough for a tone detector
that bins narrowly; it is not enough for a recording, and nobody is
making one. **It is DC-coupled on purpose**: the MAX9814's 1.25 V bias
reaches the ADC, so the bias itself is a reading — a module whose bias
sits 475 mV low is the dead one (`diagnosing a microphone`, 2026-09-17),
and the Teensy sees that without a scope.

**Range, without gain or attenuation.** The MAX9814 swings its output
about its 1.25 V bias by at most about 2 Vpp (*check* against its
datasheet), so the ADC sees roughly 0.25 to 2.25 V, inside 0 to 3.3 V
with room either side.

**Both ears start with a resistor**, so neither adds capacitance to the
microphone cable. That matters because the MAX9814 drives at most 200 pF
(`docs/ELECTRONICS_REVIEW.md` section 4) and the cable is all of that
budget. The microphone sees at least 10 kΩ from this ear at any
frequency and about 54 kΩ from the MSGEQ7's, about 8.4 kΩ for the two
together, above its 5 kΩ minimum. **Bridging an attenuator bypass
(`JS1`–`JS5`) changes that**: the MSGEQ7 side drops to its 6K8 shunt, and
near the top of the band the two ears together approach 4 kΩ. Measure
before bridging one, which `CIRCUIT_NOTES.md` already asks.

**A fault on a microphone conductor cannot reach the Teensy.** The
op-amp runs from the Teensy's own 3.3 V, so its output cannot exceed the
Teensy's rail; 5 V wired onto a microphone pin by mistake reaches the
op-amp's input through 20 kΩ, about 70 µA into its clamp (*check* the
op-amp's input current rating). With the Teensy absent the same 20 kΩ is
what the microphone sees, and the MSGEQ7s hear it as before.

**The bench microphone input** is a JST EH 3 with **the same pin order
as `female base`'s microphone socket** (GND, 5 V, signal), so any body's
MAX9814 module plugs straight into the rack, on its own 5 V from the
board's `+5V`. With **the bench output** — DAC C's right channel, a JST
EH 2 carrying line level and AGND, for a powered speaker — Teensy mode
can be proved end to end on the bench before any body is connected.

### 4d. The mode relays

| Part | Value | Package | Note |
|---|---|---|---|
| relays ×3 | 2 Form C (DPDT) signal relay, 5 V coil | SMD; Omron G6K-2F-Y or Panasonic TQ2SA class, *check* | gold-clad contacts rated for dry circuits, *check* |
| contacts | **NC to the filter output, NO to the DAC output, common to the 100 R build-out** | | released is Thomas |
| allocation | relay 1: female1, female2; relay 2: female3, male1; relay 3: male2 and one spare pole | | the spare pole is left open |
| coil driver | N-channel logic-level MOSFET, low side, 100 R to its gate | SOT-23 | gate on MODE |
| flyback diode ×3 | across each coil | SOD-123 | |
| coil supply | board `+5V` | | three coils at roughly 30–40 mA each, *check* |
| MODE net | 100 K down to GND | 0603 | no shunt reads as Thomas |
| mode header | 1×3, 2.54 mm: `THOMAS` (GND) — MODE — `TEENSY` (`+5V`) | SMD header with pegs, or THT | one shunt |

**Relays rather than an analogue switch IC, because of the two
signals' shapes.** Thomas's line sits between 0 and 5 V; the DAC's swings
both sides of 0 V. A switch IC on a single 5 V supply cannot pass a
negative signal, so it would need the DAC's output re-biased to 2.5 V —
and that bias cannot hold up against the body divider's 25 kΩ to the
audio return without a buffer per channel. A relay contact passes both
as a wire would, adds no distortion and no rail, and when released is
not in the DAC's circuit at all. **Released is Thomas mode**, so Thomas
mode depends on no coil, no supply and no Teensy: with the Teensy socket
empty this is the v2 board.

**One shunt, for the reason `ad9833 dual mode` gives for its jumpers**: a
shunt is visible across the room, cannot be set wrong by software, and
moves every body at once. Five shunts, one per body, would be five
things that can disagree, and the 2026-10-01 decision is that they never
may. A relay that fails to pull in is a fault rather than a setting, and
it shows on its body's line-out test pad (section 7).

### 4e. Three supplies, and what crosses between them

**Three supplies come and go independently**: the board's `+5V` (the
jack), `MEGA_5V` (the Mega's USB) and the Teensy's (its own USB). The
rule, generalising the v2 board's `RS1` correction: **no logic signal
crosses from one to another except through a buffer that tolerates an
unpowered side**, so no processor is ever half-powered through its own
pins. SN74LV1T34-class single buffers do it — 5.5 V-tolerant inputs on
any supply, and partial-power-down outputs (*check*) — each with its
input held by 100 kΩ to GND, so an absent source reads as a steady low
rather than a floating pin.

| Signal | From | To | Buffer powered by |
|---|---|---|---|
| MODE | the shunt | Mega `D30` | `MEGA_5V` |
| MODE | the shunt | Teensy pin 3 | Teensy 3.3 V |
| link, Mega to Teensy | Mega `D18` (`TX1`) | Teensy pin 0 (`RX1`) | Teensy 3.3 V |
| link, Teensy to Mega | Teensy pin 1 (`TX1`) | Mega `D19` (`RX1`) | `MEGA_5V` |

**Why both processors read MODE.** In the wrong mode both chains fail the
same way: silence. A Mega asked to sound a tone in Teensy mode still
starts its timer and reports it sounding; a Teensy asked to sing in
Thomas mode still fills its buffers. This repository has been bitten by
exactly that, a board that answers cheerfully and is wrong, so each
processor can read the one net that decides it and say so — the Mega
from firmware 5, the Teensy from its first sketch.

**Three analogue crossings are left, and each is safe on its own terms**:
the Mega's tone pins into the filters (as on every board so far), the
microphones into the op-amps through 20 kΩ (4c), and the DACs' outputs,
which reach the harness only through a relay contact that is open
unless the coils are powered.

### 4f. The reserved link

Mega Serial1 (`D18`, `D19`) to Teensy Serial1 (pins 0, 1), through
section 4e's buffers. **Nothing uses it yet.** It is there because two
USB devices cannot share a clock edge, and in TJ's protocol a sound
message *is* a light message: the Mega blinks a ring and the Teensy
sings the same bits, and a millisecond-true link between them may be
wanted before any firmware asks. Two buffers is the whole cost.

**It collides with `ad9833 dual mode`**, which puts its RS-485 bridge on
the same two Mega pins because Serial1 is the only hardware port the
Mega has left whole. The two are alternative solutions; if they are
ever wanted on one board, this link is the one that moves (to I2C on
`D20`/`D21` with a level translator), since RS-485 needs the hardware
UART and this does not.

---

## 5. SMD, and what stays through-hole

**Every resistor, capacitor, IC, relay, diode and transistor is SMD and
placed by the assembler.** What stays through-hole is a short list, and
every item on it is a connector, a socket for a module, or a fixed
footprint that is part of the enclosure interface:

| Through-hole | Why |
|---|---|
| four DSUB-15s | fixed footprints and positions; the harness plugs into them |
| `J2` DC jack, `J6` screw bridge | fixed footprints |
| `J7` JST EH 3 | the U2D2's lead; the same family as every body connector |
| Mega mating headers, on the back | five 1×8, one 1×10, one 2×18, the ICSP 2×3 (v2 `ASSEMBLY_NOTES.md`) |
| Teensy sockets | two 1×24 female headers |
| bench microphone, bench output | JST EH 3 and EH 2, so body parts plug in |
| mode header | only if the SMD version with locating pegs is not available |

Most assemblers fit through-hole parts as well, at extra cost; all of
these are large pads and easy by hand otherwise. **Packages**: 0603 for
signal resistors and capacitors, 0805 for the build-outs and NeoPixel
series resistors, **1206 for the eleven photosensor loads `RP1`–`RP11`**
(still 10 K provisional, and they are the parts somebody will replace by
hand at calibration), 1206 for the 0 R ground bonds `JP1`–`JP6` (so a
grounding experiment is one part lifted), and an SMD aluminium can for
the 470 µF bulk capacitor (25 V, for margin on a 5 V rail). Test points
are bare pads.

---

## 6. Placement

The outline, the fixed connectors, the Mega, the U2D2 and the four new
mounting holes are where `MECHANICAL_REVIEW.md` puts them. What is new
has to fit around them, and SMD frees most of the area the v2 board's
through-hole filters and sockets took.

- **The Teensy on the front, its USB at the top edge**, so its lead
  leaves beside the Mega's. Two spans of top edge are free:
  x 106–140 mm (between the U2D2's envelope and the Mega's) and
  x 196–240 mm (between the Mega's and `H2`'s keep-out). A Teensy 4.1 is
  about 61 × 18 mm (*check*); either takes it upright. **Whether the
  enclosure lets a third lead out there is a dry-fit question** —
  the Mega's USB overhangs that edge, which suggests it is open, and
  does not establish it.
- **The analogue parts belong to v2's AGND region**: the filters, the
  MSGEQ7s, the relays' signal side, the DAC output filters and the
  anti-alias buffers. `JP1` stays the only bond, and **the three DACs sit
  beside it**, analogue side in the region and digital side toward the
  Teensy, so the I2S return current crosses the bond rather than
  circling the region.
- **The I2S lines are the noisiest new signals** — `BCLK` is about 2.8
  MHz at 44.1 kHz. Keep them short, over unbroken ground, away from the
  microphone inputs and the MSGEQ7 clock pins, with their 33 R at the
  Teensy end.
- **The relays near the DSUBs' line-out pins**, so the stretch of copper
  shared by both chains is short. The mode header where a hand reaches
  it with the board in the rack.
- **The coil supply and its return off the AGND region**: the coils
  switch tens of milliamps, rarely, and that current has no business
  under an MSGEQ7.

---

## 7. Test points and silkscreen

Every v2 test pad stays: filter outputs, analyser outputs, `STROBE`,
`RESET`, `SHUTDOWN`, and the four rails. Added:

| Where | Why |
|---|---|
| line out ×5, after the relay and before the 100 R | **what is actually leaving**, in either mode; a relay that did not move shows here |
| DAC output ×5, after the 470 R | the Teensy's voice before the relay |
| Teensy ADC input ×6, after the 100 R | the ear as the ADC sees it, bias and all |
| MODE | which way the shunt is, with a meter |
| `BCLK`, `LRCLK` | silence from an unclocked DAC reads like silence from a muted one |
| Teensy 3.3 V, DAC 3.3 V | two more rails, each with its own pad |

Silkscreen, because each of these is a fault that reads as something else:

- **The mode header, in large type**: `THOMAS ◂ ▸ TEENSY`, and beside it
  `NO SHUNT = THOMAS`.
- **Each line out**: its body, both sources and both pins — `female1 —
  D6 1 kHz | DAC A L`.
- **Each Teensy ear**: `female1 — Teensy 14 (A0)`, beside the Mega's
  `module 0 — female1`.
- **`3.3 V — NOT 5 V TOLERANT`** across the Teensy's socket, and the
  Teensy-powered parts outlined with **`TEENSY USB POWER`**, so
  nobody probes 5 V onto them looking for a rail.
- Everything `next pcb` section 6 asked for: `B-J4 — NO POWER`,
  `MEGA 5V` and `BOARD +5V` spelled out, `LINE OUT` and `AUDIO RTN` on
  the old speaker pair, `D2 D3 D4 — AUDIO CONTROL`.

---

## 8. Software, in each mode

None of it is needed to build the board; all of it is needed to use
Teensy mode.

- **Thomas mode is the program as it is**: firmware 4, `drivers/audio.py`,
  `sing`, `hearing`, the audio hardware tests. Nothing changes.
- **Firmware 5, when it comes, reads `D30`**, names the mode in its
  greeting, and refuses `<body>/speaker` in Teensy mode rather than
  report a tone that is not reaching anybody. A version bump, for the
  usual reason.
- **A Teensy sketch** (a new folder under `Source code/Arduino/`): five
  sine oscillators into `AudioOutputI2SHex`, the five microphones
  streamed as raw samples over USB serial, the greeting with its
  firmware version and the MODE it reads, `XSMT` held low unless MODE
  says Teensy. Its rate per microphone is the one number to measure
  first (`sound options`: "rate per mic still to confirm on the bench");
  five at 44.1 kSPS across the two converters is the design point.
- **A driver node beside `drivers/arduino`**, with its own port picker.
  `boards.KNOWN_DEVICES` gains PJRC's vendor id (`0x16C0`, *check* the
  product ids), so the Teensy is named on the USB list and never offered
  as the Arduino. Flashing goes through `flasher/base.py`, whose shape
  already takes any sketch on any lead; the Teensy's upload tool is the
  part to *check*.
- **The analysis is already written**: `test_goertzel_ear`'s `goertzel.py`
  runs bins on samples in Python, and its `HEARD_RATIO` and
  `leakage()` findings carry over. In Teensy mode `drivers/audio.py`'s
  pitch column becomes a setting with no band to stay inside, since the
  ear is a bin and a bin goes anywhere.
- **`drivers/hearing/` stops being emulated in Teensy mode first**: it
  is the mode where the microphones reach the program at all.

---

## 9. Changing mode

**Thomas to Teensy:**

1. Stop the piece from the page.
2. Fit the Teensy if it is not fitted — with the board powered down,
   since a module pushed into a live socket meets its pins in no
   particular order — and plug in its USB lead.
3. Move the shunt to `TEENSY`. The relays click.
4. On the bench output with a module on the bench microphone, or on one
   body: one tone out, heard by the Teensy's own ear, before running
   anything else.

**Teensy to Thomas** is the shunt back to `THOMAS`. The Teensy may stay
in its socket: its outputs reach nothing with the relays released, and
its ear listening costs nothing.

**What a mismatch does.** The shunt on `THOMAS` while the program drives
the Teensy, or on `TEENSY` while it drives the Mega's tones, gives
**silence and nothing worse** — no level on any conductor that is not
there in normal use. Silence is also what a dead amplifier gives, which
is why both processors read MODE (4e), and why the line-out test pads
exist (7).

---

## 10. Bring-up

1. **Bare board**, before anything is fitted: continuity and isolation
   as in the v2 README, plus the Teensy's 3.3 V and the DAC rail
   isolated from both 5 V rails, and MODE reading 0 V with no shunt.
2. **Thomas mode with the Teensy socket empty.** Firmware 4, then
   `test audio loop` and `test audio bringup` exactly as on the v2
   board. This proves the board before the new half is involved.
3. **Fit the Teensy, shunt still on `THOMAS`.** With a blank sketch: DAC
   rail at 3.3 V, `XSMT` low, no voltage on any line out but Thomas's.
4. **Teensy mode on the bench**: bench output to a powered speaker, a
   MAX9814 on the bench input, one tone heard.
5. **One body at a time**, line-out test pad first.
6. **`next pcb` section 3's harness measurement**, in both modes. It was
   always the one to do first, and Teensy mode adds a remedy (4b).

---

## 11. Parts added for Teensy mode, rough

Hobby-retail figures for 2026, to be checked before ordering. Thomas
mode's parts are the v2 BOM in the packages of section 3.

| | Qty | Rough total |
|---|---|---|
| Teensy 4.1 and two 1×24 sockets | 1 | EUR 35–45 |
| PCM5102A and its passives | 3 | EUR 8–15 |
| DAC LDO | 1 | EUR 0.5 |
| MCP6004-class quad op-amp and the twelve-part filter per channel | 2 | EUR 3–5 |
| DPDT signal relays, diodes, MOSFET | 3 | EUR 8–15 |
| single buffers | 4 | EUR 1–2 |
| bench connectors, mode header and shunt | | EUR 2 |
| **total, Teensy mode** | | **about EUR 60–85** |

In line with `sound options`' Teensy column (EUR 50–75 with DAC
modules). **Thomas mode alone costs nothing extra**: the board can be
ordered with the Teensy socket empty and the Teensy, its DACs and its
buffers fitted later — or ordered fully assembled, since unpowered they
are inert.

---

## 12. What is open

- **The part checks** marked *check*: the relays' contacts and coil
  current, the op-amp's input current, the buffers' partial-power-down
  behaviour, the LDO, C0G stock at 150–470 nF, the Teensy's dimensions
  and USB ids, the MAX9814's 2 Vpp.
- **The sampling rate actually achieved**, five microphones streamed
  over USB at once (section 8).
- **The harness measurement** (`next pcb` section 3), in both modes.
- **The enclosure opening** for a third USB lead (section 6).
- **The amplifier module and its rail**, still `next pcb` section 5's;
  nothing here depends on it.
- **The photosensor loads**, still the v2 board's provisional 10 K.
- **Protection** on the supply branches (`docs/ELECTRONICS_REVIEW.md`
  section 3): not designed here, and no worse than on v2.
- **A netlist.** This is the specification; the v2 project's
  `circuit.json` is the contract it extends, and drawing this board is
  adding Teensy mode's sheets and relays to that project and changing
  its footprints to section 5's.
