# Dirty rework: Thomas's audio subsystem into the board that exists

**The report to work from with a scalpel in your hand.** It puts five
voices and five ears into the installation without waiting for a new PCB.
Everything here is reversible except five 1 mm cuts, and each of those
five cuts leaves a pad you then solder the new wire to.

What is being built is the loop `hardware setup` (under the audio bench
test) draws: a tone leaves a hardware timer, passes a low-pass filter, a
divider and an amplifier, crosses the room as sound, is picked up by a
MAX9814, read by an MSGEQ7 and comes back into the same Mega's ADC. The
difference is that the Mega is **the installation's own** rather than
Thomas's bench board, and the five bodies are the piece's five bodies.

Read `as built` first if you have not. This assumes its net map.

---

## 0. Before you start

- **Everything on hand:** the filter board, the analyser array, five
  MAX9814 modules, five GF1002 amplifiers and five speakers.
- **Flash the Mega with firmware 3** before switching anything on.
  Version 3 of `colloquy_of_mobiles.ino` expects the pin moves below;
  version 2 on a reworked board lights the wrong bodies and says nothing
  about it. The driver refuses to open a link to firmware 2 for exactly
  that reason, so the mismatch is loud in one direction and silent in the
  other.
- **Photograph `J11` and `J12` before touching them.** Each row is two
  separate nets joined by whatever is physically fitted across it, and
  the KiCad files do not say whether that is a shunt or a resistor. The
  light sensors work, so it is something. You will pull five of them out
  and you want to be able to put them back.
- **Take the board out properly.** `hardware > main pcb > unmount the
  main PCB` homes every body and the bar first, then cuts torque and
  stops the server on a page saying it is safe to disconnect. A bar
  powered down at the far end loses its turn count, and its calibration
  with it.

---

## 1. The decision behind all of it

**A tone pin is not a choice and a NeoPixel pin is.** Each of Thomas's
five tones is made by an AVR hardware timer toggling its own `OCnA`
output, and that pin is fixed in silicon: timer 1 can only come out on
D11, timer 3 on D5, timer 4 on D6, timer 5 on D46, timer 2 on D10. Four
of those five were NeoPixel lines on this board, and D4, wanted for the
analyser strobe, was a fifth.

A NeoPixel line is bit-banged and can be any pin at all.

So **the lights move and the tones do not** - and the pinout that comes
out of it is the one Thomas's own tester firmware already uses, which is
what makes his bench measurements transfer to this board unchanged. It is
also the pinout the next PCB should have, so this rework is a prototype
of that board rather than a detour.

---

## 2. What each body ends up being

| Body | Voice | Timer | Mega pin | Filter channel | Analyser module | ADC |
|---|---|---|---|---|---|---|
| **female1** | 160 Hz | T1 | **D11** | `160` | 0 | A0 |
| **female2** | 400 Hz | T3 | **D5** | `400` | 1 | A1 |
| **female3** | 1 kHz | T4 | **D6** | `1K` | 2 | A2 |
| **male1** | 2.5 kHz | T5 | **D46** | `2K5` | 3 | A3 |
| **male2** | 6.25 kHz | T2 | **D10** | `6K25` | 4 | A4 |

**Module N is body N, and it is free.** The board already had
`female1...male2/microphone/2` on A0...A4 in exactly that order, so
putting the analyser outputs where the microphones were gives the mapping
for nothing. One number then identifies a body the whole way round the
loop - out of the timer, through the room, back into the ADC.

That settles the question `hardware setup` section 6 leaves open, *which
module is which body*, by construction rather than by covering
microphones with your hand. **Confirm it once anyway** with `test audio
loop`: it is the only test that can catch a body wired to another body's
channel.

> **The pitch order runs the other way from TJ's.** His firmware gave
> female1 the highest note and male2 the lowest (`act_tone_index =
> 5 - UNIT_ID`, CODE_DOCUMENTATION 9.10). His five pitches all sat inside
> one analyser band and carried no information at all; here the pitch
> *is* which body is speaking, and D11 was already female1's channel.
> Reversing it would cost five re-jumperings and buy nothing - but it is
> five re-jumperings and not a rebuild, if it turns out to matter
> musically.

---

## 3. The cuts

**Five, all on the front copper, all in one place.** The Mega shield pads
run down one column at x = 191.96 mm; the breakout header pins (`J4`,
`J8`, `J10`) run down another at x = 200.85 mm. Between them is one
straight 1 mm track per pin and nothing else - no via, no second layer, no
branch. Cut in that 8.89 mm gap and the shield pad is isolated while the
net carries on from the header pin.

Then **solder the new wire to the cut pad itself**. Nothing has to be
soldered to a lifted pin or a bent header.

<div style="overflow-x: auto; margin: 1.5rem 0;">
<svg viewBox="0 0 1010 741" role="img" aria-label="One column of Mega shield pads and one column of breakout header pins 8.89 millimetres to its right, joined one to one by twenty-six straight front-copper tracks. Five of them are cut: D11, D10, D6, D5 and D4. Wires are then taken from those cut pads out to the filter board and the analyser array, and the four NeoPixel nets they used to drive are re-driven from D14 to D17 on the J10 header.">
<defs><marker id="arw" viewBox="0 0 10 8" refX="9" refY="4" markerWidth="8" markerHeight="6" orient="auto"><polygon points="0,0 10,4 0,8" fill="currentColor"/></marker></defs>
<text x="90.0" y="26.0" font-family="Chivo, sans-serif" font-size="12" font-weight="600" fill="currentColor" opacity="0.7" text-anchor="end">the new wire</text>
<text x="300.0" y="26.0" font-family="Chivo, sans-serif" font-size="12" font-weight="600" fill="currentColor" opacity="0.7" text-anchor="middle">shield pad</text>
<text x="484.0" y="26.0" font-family="Chivo, sans-serif" font-size="12" font-weight="600" fill="currentColor" opacity="0.7" text-anchor="middle">header</text>
<text x="546.0" y="26.0" font-family="Chivo, sans-serif" font-size="12" font-weight="600" fill="currentColor" opacity="0.7" text-anchor="start">net</text>
<text x="700.0" y="26.0" font-family="Chivo, sans-serif" font-size="12" font-weight="600" fill="currentColor" opacity="0.7" text-anchor="start">what happens to it</text>
<line x1="300.0" y1="81.7" x2="470.0" y2="81.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="81.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="77.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="85.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">SCL</text>
<text x="492.0" y="85.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 1</text>
<text x="546.0" y="85.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">SCL</text>
<line x1="300.0" y1="103.7" x2="470.0" y2="103.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="103.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="99.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="107.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">SDA</text>
<text x="492.0" y="107.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 2</text>
<text x="546.0" y="107.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">SDA</text>
<line x1="300.0" y1="125.7" x2="470.0" y2="125.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="125.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="121.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="129.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">AREF</text>
<text x="492.0" y="129.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 3</text>
<text x="546.0" y="129.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">AREF</text>
<line x1="300.0" y1="147.7" x2="470.0" y2="147.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="147.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="143.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="151.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">GND</text>
<text x="492.0" y="151.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 4</text>
<text x="546.0" y="151.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">GND</text>
<text x="700.0" y="151.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">filter board ground here</text>
<line x1="300.0" y1="169.7" x2="470.0" y2="169.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="169.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="165.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="173.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D13</text>
<text x="492.0" y="173.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 5</text>
<text x="546.0" y="173.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">female3/audio</text>
<text x="700.0" y="173.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">on-board amp - leave as an input</text>
<line x1="300.0" y1="191.7" x2="470.0" y2="191.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="191.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="187.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="195.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D12</text>
<text x="492.0" y="195.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 6</text>
<text x="546.0" y="195.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">female2/audio</text>
<text x="700.0" y="195.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">on-board amp - leave as an input</text>
<line x1="300.0" y1="213.7" x2="470.0" y2="213.7" stroke="currentColor" stroke-width="2.4" opacity="0.85"/>
<rect x="372.0" y="200.7" width="26" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.1" opacity="0.5"/>
<g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><line x1="378.0" y1="206.7" x2="392.0" y2="220.7"/><line x1="378.0" y1="220.7" x2="392.0" y2="206.7"/></g>
<circle cx="300.0" cy="213.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="209.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="217.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D11</text>
<text x="492.0" y="217.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 7</text>
<text x="546.0" y="217.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.9" text-anchor="start">female1/audio</text>
<text x="700.0" y="217.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">on-board amp - leave as an input</text>
<path d="M 293.0 213.7 L 104.0 213.7" stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#arw)"/>
<text x="90.0" y="217.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.95" text-anchor="end">filter IN 160</text>
<line x1="300.0" y1="235.7" x2="470.0" y2="235.7" stroke="currentColor" stroke-width="2.4" opacity="0.85"/>
<rect x="372.0" y="222.7" width="26" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.1" opacity="0.5"/>
<g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><line x1="378.0" y1="228.7" x2="392.0" y2="242.7"/><line x1="378.0" y1="242.7" x2="392.0" y2="228.7"/></g>
<circle cx="300.0" cy="235.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="231.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="239.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D10</text>
<text x="492.0" y="239.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 8</text>
<text x="546.0" y="239.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.9" text-anchor="start">male2/neopixel</text>
<text x="700.0" y="239.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">now driven from D15</text>
<path d="M 293.0 235.7 L 104.0 235.7" stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#arw)"/>
<text x="90.0" y="239.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.95" text-anchor="end">filter IN 6K25</text>
<line x1="300.0" y1="257.7" x2="470.0" y2="257.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="257.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="253.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="261.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D9</text>
<text x="492.0" y="261.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 9</text>
<text x="546.0" y="261.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">male1/neopixel</text>
<line x1="300.0" y1="279.7" x2="470.0" y2="279.7" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="279.7" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="275.7" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="283.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D8</text>
<text x="492.0" y="283.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J4 10</text>
<text x="546.0" y="283.7" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">female3/neopixel</text>
<line x1="300.0" y1="314.9" x2="470.0" y2="314.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="314.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="310.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="318.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D7</text>
<text x="492.0" y="318.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 1</text>
<text x="546.0" y="318.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">female2/neopixel</text>
<line x1="300.0" y1="336.9" x2="470.0" y2="336.9" stroke="currentColor" stroke-width="2.4" opacity="0.85"/>
<rect x="372.0" y="323.9" width="26" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.1" opacity="0.5"/>
<g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><line x1="378.0" y1="329.9" x2="392.0" y2="343.9"/><line x1="378.0" y1="343.9" x2="392.0" y2="329.9"/></g>
<circle cx="300.0" cy="336.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="332.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="340.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D6</text>
<text x="492.0" y="340.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 2</text>
<text x="546.0" y="340.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.9" text-anchor="start">female1/neopixel</text>
<text x="700.0" y="340.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">now driven from D14</text>
<path d="M 293.0 336.9 L 104.0 336.9" stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#arw)"/>
<text x="90.0" y="340.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.95" text-anchor="end">filter IN 1K</text>
<line x1="300.0" y1="358.9" x2="470.0" y2="358.9" stroke="currentColor" stroke-width="2.4" opacity="0.85"/>
<rect x="372.0" y="345.9" width="26" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.1" opacity="0.5"/>
<g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><line x1="378.0" y1="351.9" x2="392.0" y2="365.9"/><line x1="378.0" y1="365.9" x2="392.0" y2="351.9"/></g>
<circle cx="300.0" cy="358.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="354.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="362.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D5</text>
<text x="492.0" y="362.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 3</text>
<text x="546.0" y="362.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.9" text-anchor="start">male1/bar neopixel</text>
<text x="700.0" y="362.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">now driven from D16</text>
<path d="M 293.0 358.9 L 104.0 358.9" stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#arw)"/>
<text x="90.0" y="362.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.95" text-anchor="end">filter IN 400</text>
<line x1="300.0" y1="380.9" x2="470.0" y2="380.9" stroke="currentColor" stroke-width="2.4" opacity="0.85"/>
<rect x="372.0" y="367.9" width="26" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.1" opacity="0.5"/>
<g stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><line x1="378.0" y1="373.9" x2="392.0" y2="387.9"/><line x1="378.0" y1="387.9" x2="392.0" y2="373.9"/></g>
<circle cx="300.0" cy="380.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="376.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="384.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D4</text>
<text x="492.0" y="384.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 4</text>
<text x="546.0" y="384.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.9" text-anchor="start">male2/bar neopixel</text>
<text x="700.0" y="384.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">now driven from D17</text>
<path d="M 293.0 380.9 L 104.0 380.9" stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#arw)"/>
<text x="90.0" y="384.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.95" text-anchor="end">analyser STROBE</text>
<line x1="300.0" y1="402.9" x2="470.0" y2="402.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="402.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="398.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="406.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D3</text>
<text x="492.0" y="406.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 5</text>
<text x="546.0" y="406.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">free</text>
<path d="M 293.0 402.9 L 104.0 402.9" stroke="currentColor" stroke-width="1.6" fill="none" marker-end="url(#arw)"/>
<text x="90.0" y="406.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="600" fill="currentColor" opacity="0.95" text-anchor="end">analyser RESET</text>
<line x1="300.0" y1="424.9" x2="470.0" y2="424.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="424.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="420.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="428.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D2</text>
<text x="492.0" y="428.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 6</text>
<text x="546.0" y="428.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">free</text>
<line x1="300.0" y1="446.9" x2="470.0" y2="446.9" stroke="currentColor" stroke-width="1.4" opacity="0.3" stroke-dasharray="3 3"/>
<circle cx="300.0" cy="446.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.3"/>
<rect x="466.0" y="442.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.3"/>
<text x="287.0" y="450.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.3" text-anchor="end">D1</text>
<text x="492.0" y="450.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 7</text>
<text x="546.0" y="450.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">USB TX</text>
<text x="700.0" y="450.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">leave alone</text>
<line x1="300.0" y1="468.9" x2="470.0" y2="468.9" stroke="currentColor" stroke-width="1.4" opacity="0.3" stroke-dasharray="3 3"/>
<circle cx="300.0" cy="468.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.3"/>
<rect x="466.0" y="464.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.3"/>
<text x="287.0" y="472.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.3" text-anchor="end">D0</text>
<text x="492.0" y="472.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J8 8</text>
<text x="546.0" y="472.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">USB RX</text>
<text x="700.0" y="472.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">leave alone</text>
<line x1="300.0" y1="512.9" x2="470.0" y2="512.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="512.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="508.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="516.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D14</text>
<text x="492.0" y="516.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 1</text>
<text x="546.0" y="516.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">free</text>
<text x="700.0" y="516.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="500" fill="currentColor" opacity="0.75" text-anchor="start">&#8594; J8 2   female1/neopixel</text>
<line x1="300.0" y1="534.9" x2="470.0" y2="534.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="534.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="530.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="538.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D15</text>
<text x="492.0" y="538.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 2</text>
<text x="546.0" y="538.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">free</text>
<text x="700.0" y="538.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="500" fill="currentColor" opacity="0.75" text-anchor="start">&#8594; J4 8   male2/neopixel</text>
<line x1="300.0" y1="556.9" x2="470.0" y2="556.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="556.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="552.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="560.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D16</text>
<text x="492.0" y="560.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 3</text>
<text x="546.0" y="560.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">free</text>
<text x="700.0" y="560.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="500" fill="currentColor" opacity="0.75" text-anchor="start">&#8594; J8 3   male1/bar neopixel</text>
<line x1="300.0" y1="578.9" x2="470.0" y2="578.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="578.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="574.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="582.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="600" fill="currentColor" opacity="0.85" text-anchor="end">D17</text>
<text x="492.0" y="582.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 4</text>
<text x="546.0" y="582.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.4" text-anchor="start">free</text>
<text x="700.0" y="582.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="500" fill="currentColor" opacity="0.75" text-anchor="start">&#8594; J8 4   male2/bar neopixel</text>
<line x1="300.0" y1="600.9" x2="470.0" y2="600.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="600.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="596.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="604.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D18</text>
<text x="492.0" y="604.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 5</text>
<text x="546.0" y="604.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">free</text>
<line x1="300.0" y1="622.9" x2="470.0" y2="622.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="622.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="618.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="626.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D19</text>
<text x="492.0" y="626.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 6</text>
<text x="546.0" y="626.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">free</text>
<line x1="300.0" y1="644.9" x2="470.0" y2="644.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="644.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="640.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="648.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D20</text>
<text x="492.0" y="648.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 7</text>
<text x="546.0" y="648.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">free</text>
<text x="700.0" y="648.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">= SCL, avoid</text>
<line x1="300.0" y1="666.9" x2="470.0" y2="666.9" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<circle cx="300.0" cy="666.9" r="4.4" fill="none" stroke="currentColor" stroke-width="1.6" opacity="0.85"/>
<rect x="466.0" y="662.9" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.85"/>
<text x="287.0" y="670.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11.5" font-weight="400" fill="currentColor" opacity="0.85" text-anchor="end">D21</text>
<text x="492.0" y="670.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.5" text-anchor="start">J10 8</text>
<text x="546.0" y="670.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.9" text-anchor="start">free</text>
<text x="700.0" y="670.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="10.5" font-weight="400" fill="currentColor" opacity="0.75" text-anchor="start">= SDA, avoid</text>
<line x1="240.0" y1="297.3" x2="980" y2="297.3" stroke="currentColor" stroke-width="0.8" opacity="0.16"/>
<line x1="240.0" y1="490.9" x2="980" y2="490.9" stroke="currentColor" stroke-width="0.8" opacity="0.16"/>
<line x1="60" y1="692.9" x2="980" y2="692.9" stroke="currentColor" stroke-width="1" opacity="0.25"/>
<text x="60.0" y="712.9" font-family="'IBM Plex Mono', ui-monospace, monospace" font-size="11" font-weight="400" fill="currentColor" opacity="0.6" text-anchor="start">Five cuts, all front copper, all in the same 8.89 mm gap between the two columns. Each cut pad then anchors its own new wire, so nothing has to be soldered to a lifted pin.</text>
</svg>

</div>

| # | Cut the track from | to | which frees |
|---|---|---|---|
| 1 | shield pad **D11** | `J4` 7 | D11, for the 160 Hz tone |
| 2 | shield pad **D10** | `J4` 8 | D10, for the 6.25 kHz tone |
| 3 | shield pad **D6** | `J8` 2 | D6, for the 1 kHz tone |
| 4 | shield pad **D5** | `J8` 3 | D5, for the 400 Hz tone |
| 5 | shield pad **D4** | `J8` 4 | D4, for the analyser strobe |

**Why D11 is cut at all**, when it already goes to female1's audio net:
because the tone has to pass through the filter before it reaches any
amplifier. Feeding a raw square wave straight to an amp input is exactly
what the filter board exists to prevent.

**D12, D13, D22 and D23 stay connected** to female2's, female3's, male1's
and male2's on-board TPA2005D1 inputs, and are simply never driven - the
firmware leaves them as inputs. One thing to know: **D13 is the Mega's own
LED pin**, so the bootloader blinks it at every reset and female3's
on-board amplifier clicks three times. Harmless on a bench, and a reason
for the next board not to put audio on D13.

---

## 4. The wires

Twelve on the board, ten at `J11`, plus power. Nothing else is cut.

### 4a. Voices out to the filter board - 6 wires

| From | To |
|---|---|
| cut pad **D11** | filter board `IN 160` |
| cut pad **D5** | filter board `IN 400` |
| cut pad **D6** | filter board `IN 1K` |
| `J9` **9** (D46, uncut and already free) | filter board `IN 2K5` |
| cut pad **D10** | filter board `IN 6K25` |
| `J4` **4** (GND) | filter board `GND` |

**Each pin must feed the filter channel matching its own frequency.**
This is the trap `hardware setup` section 5 warns about, and the reason
it cannot be caught by testing: a low-pass passes anything below its
corner, so 160 Hz fed into the 6.25 kHz channel still comes out, still
lands in the 160 Hz band and still reports "heard". What is lost is the
filtering - the 6.25 kHz channel barely touches the 480 Hz first harmonic
that the 160 Hz channel exists to remove - and the symptom is poor
detection in a noisy room, months later, with nothing pointing at the
cause.

Check by ear or by scope which physical channel each `IN` pad feeds, and
then write it on the board.

### 4b. Filter out to the amplifiers - Thomas's chain, off the PCB

The five on-board TPA2005D1 amplifiers and the five `<body>/audio` nets
are **not used**. Each channel goes:

    filter OUT <channel>  ->  22K / 3K3 divider  ->  GF1002  ->  loudspeaker

The divider keeps the filter output under the GF1002's maximum input
**with the module's volume control at maximum**. Exceed it and the
amplifier clips, and a clipped output is a square wave again - throwing
away everything the filter just did. Start every volume pot at minimum
and bring it up.

Mount each GF1002 **close to its own loudspeaker** and keep the speaker
leads short: its output is differential PWM at about 250 kHz, with sharp
edges, high currents and real EMI.

> **This is where the bench and the installation part company.** In the
> installation the amplifier is on the PCB and its output travels the
> whole length of a DSUB cable to the body, which is exactly what
> Thomas's note says not to do. See `next pcb` section 3: the existing
> harness can already carry line level and power to a remote amplifier,
> on conductors that are there.

### 4c. Ears - 10 wires at `J11`, and no cuts at all

`J11`'s five microphone rows are each **two separate nets**, with the body
on the odd pin and the Mega's ADC on the even one. So the analyser goes
*into the gap*:

1. Remove whatever is fitted across `J11` rows **1-2, 3-4, 5-6, 7-8,
   9-10** (female1, female2, female3, male1, male2). Keep them.
2. `J11` **1, 3, 5, 7, 9** - each body's microphone wire, in off the DSUB
   - to the analyser array's microphone input for modules **0, 1, 2, 3,
   4** respectively.
3. Analyser array module **0-4** output to `J11` **2, 4, 6, 8, 10**, which
   is A0-A4.

Leave the photosensor rows (`J11` 11-16) and the whole of `J12` exactly as
they are.

### 4d. Analyser control and power - 4 wires

| From | To |
|---|---|
| cut pad **D4** | analyser array `STROBE` (commoned to all five modules) |
| `J8` **5** (D3, free) | analyser array `RESET` (commoned) |
| `J9` **35** | analyser array `VDD` |
| `J9` **1** | analyser array `GND` |

`J9` 35 and `J9` 1 are the Mega's own 5 V and ground rather than the
board's +5 V rail - which is fine: five MSGEQ7s draw a few milliamps, and
the two grounds are common through the shield's `GND1` pad anyway.

### 4e. The lights, moved - 4 wires

All four are short hops between two pins of the same header column:

| From | To | Which net |
|---|---|---|
| `J10` **1** (D14) | `J8` **2** | `female1/neopixel` |
| `J10` **2** (D15) | `J4` **8** | `male2/neopixel` |
| `J10` **3** (D16) | `J8` **3** | `male1/bar neopixel` |
| `J10` **4** (D17) | `J8` **4** | `male2/bar neopixel` |

`female2`, `female3` and `male1`'s body strips stay on D7, D8 and D9 and
are not touched.

> **Watch the two up-rings.** The board calls D4 `male2/bar neopixel` and
> D5 `male1/bar neopixel`; the sketch built those two strips the other way
> round and has done since long before any of this. The rework keeps each
> strip on the wire it was actually driving, so nothing in the room
> changes - but if the up-rings come out on the wrong male, the fix is to
> swap `MALE1_UP_RING_NEOPIXEL_PIN` and `MALE2_UP_RING_NEOPIXEL_PIN` in
> the sketch, and then the net names were right all along.

---

## 5. In each body

Replace the bare microphone with a **MAX9814** module:

- **Power it from the DSUB**, which already carries +5 V and GND to every
  body.
- **`AOUT` onto the existing microphone wire** - the one landing on
  `J11`'s odd pin for that body.
- **Strap `Gain` to VDD** (40 dB) and **`A/R` to GND** (1:500). Thomas's
  bench results, and he says both must be re-checked in the field, so
  treat them as a starting point rather than an answer.

The speakers, for this pass, are Thomas's five next to their GF1002s.
Getting them back into the bodies is `next pcb` section 3's question, not
this one's.

---

## 6. Switching on

1. Flash firmware 3 and open the page. `drivers > arduino` should say
   **in sync: yes** and *board says: firmware 3 at 1000000 baud*. If it
   refuses to open the port it will name the mismatch.
2. `drivers > all audio > silence every speaker`, then **`read every
   microphone`**. Five rows of seven numbers. All five near-identical and
   low is a quiet room read correctly. A row of zeros or a row of 1023s is
   that module, its supply, or its ADC wire.
3. `drivers > female1 > speaker > on`. You should hear 160 Hz from
   female1's speaker and nothing else. Read the microphones again: band 1
   should have jumped on every module.
4. Walk the other four, one at a time.
5. Then run **`tests > test audio loop`**: twenty-five verdicts in about
   twenty-two seconds. Its scenario says what each one means.

**Reading the first run.** `wrong band` naming a neighbour is a body on
the wrong filter channel - section 4a. `silent` across one *row* of five
is that body's voice; `silent` down one *column* of five is that body's
ear. Silent everywhere is power, ground, or the strobe.

---

## 7. What this rework does not answer

- **Whether the loudspeakers are up to it.** They sit in an open frame,
  close to an acoustic short circuit, and have never been shown to be
  flat from 160 Hz to 6.25 kHz. Test the two lowest tones for sound
  pressure first.
- **Whether an MSGEQ7 can hear a body across a gallery full of
  visitors.** The hearing side inherits a fixed absolute threshold, which
  is already the weakest part of the light side (CODE_DOCUMENTATION 8.2)
  and a microphone in a room full of people is worse.
- **How to sample a tone properly.** The MSGEQ7's internal scan is fast
  enough to catch individual points on the *waveform* of the two lowest
  tones, so single readings of a steady 160 Hz vary with where in the
  cycle they landed. Thomas's remedy is four reads in quick succession at
  160 Hz and two at 400. Nothing here does that yet: `test audio loop`
  averages whole sweeps, which is enough to say "heard" and nowhere near
  enough to decode anything.
- **Anything above the wiring.** No body sings a pattern, nobody listens
  for one, and `Female.Reinforcement` still raises on its first tick.
  CODE_DOCUMENTATION section 9 is the list; this rework is its first row.
