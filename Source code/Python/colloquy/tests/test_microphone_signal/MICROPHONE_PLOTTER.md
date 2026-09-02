# Reading one microphone directly

## 0. What this answers, and where it cuts the chain

Nine things have to work for a body to hear another body sing. Every
other test in this tree reads the **analyser**, so every other test sees
the last of the nine and infers the rest. This one looks at the
microphone's own output, before the MSGEQ7 has had it.

That is the one useful place to cut, and it is a fact about this board
rather than a general principle:

- `<body>/microphone/1` comes in off the DSUB and lands on `J11`'s
  **odd** pin with **nothing fitted between them** - no preamp, no
  bias, no filter (`as built` section 6). So the odd pin *is* the
  MAX9814's output, and a clip on it is a clip on the microphone.
- The MSGEQ7's support network is the one part of this design written
  down nowhere in this repository. `next pcb` keeps it in a BOM section
  of its own for exactly that reason. It is therefore both the likeliest
  thing to be wrong and the last thing anything reading its output could
  tell you about.

**A bench that works and an installation that does not is the shape this
was written for.** The microphone module, the tone, the amplifier and
the speaker are the same objects in both places. What is different is
the wire between the body and the rack, the MSGEQ7 array, its supply and
its strobe - and all four of those are downstream of the point this test
looks at.

---

## 1. What you need

- **A second Arduino** - any 5 V board. An Uno, a Nano, a spare Mega.
  This is the recommended route and it touches nothing on the
  installation.
- The **Arduino IDE, version 2.x** (`Tools > Serial Plotter`).
- The sketch: `Source code/Arduino/microphone_plotter/`.
- A phone, and something to play through it with a broad spectrum and
  obvious dynamics. Music with a beat is ideal. A steady tone is the
  worst possible test signal here, because a steady tone and a steady
  fault look the same.
- Two clip leads.

If you have no second board, section 3 does it with the installation's
own Mega instead. It is more invasive, it costs you the analyser half of
this test, and it should be the second choice.

---

## 2. Route A - a second Arduino as a probe (recommended)

Nothing on the installation is unplugged, unsoldered, reflashed or
reconfigured. The piece keeps its port and its firmware, and the run on
the page keeps working while you do this.

### 2a. Wire it

1. **Ground first.** Probe `GND` to the rack's ground: `J9` pin 1 is the
   Mega's own, and it is the easiest one to reach. Ground goes on first
   and comes off last, every time.
2. **Probe `A0` to the body's microphone wire** - `J11`'s **odd** pin:

   | body | `J11` pin |
   |---|---|
   | female1 | 1 |
   | female2 | 3 |
   | female3 | 5 |
   | male1 | 7 |
   | male2 | 9 |

3. **Do not touch the even pins.** `J11` 2, 4, 6, 8 and 10 are A0-A4 on
   the installation's Mega, driven by the analyser modules' outputs.
   Clipping a probe onto one of those measures the MSGEQ7, which is the
   thing this test exists to stop trusting.
4. **Do not clip onto a speaker pair or onto +12 V.** The amplifier
   output is class-D and *both* of its terminals are driven; neither is
   ground. `supply setup`, on the test next door, spends a section on
   why.
5. Keep the lead to `A0` short. It is in parallel with the MSGEQ7's
   input, and half a metre of dangling wire on that node picks up the
   NeoPixel lines.

### 2b. Flash and plot

The sketch defaults to `A0` and to envelope mode, so on a probe board
there is nothing to edit.

1. Open `microphone_plotter.ino`, pick the probe's board and its port,
   upload.
2. `Tools > Serial Plotter`, and set the corner to **115200**. This is
   not the installation's 1 Mbaud - the plotter reads this sketch, not
   the driver. A window full of rubbish is always these two numbers
   disagreeing.
3. On the page, start `tests > manual tests > test microphone signal`.
   It silences every speaker and reads all five analyser modules twice a
   second, so you can watch both halves at once.
4. Play music into the body. Hold the phone 20-30 cm from the
   microphone, at a level you would talk over.

---

## 3. Route B - the installation's own Mega

Only when there is no second board. It costs the analyser half of this
test outright: while the plotter sketch is on that Mega, the strobe and
reset lines are not being driven, so the MSGEQ7s are not being clocked
and the run on the page has nothing to read. It will say so and stop.

**There is no free ADC pin on that board.** A0-A4 are the five analyser
outputs, A5-A7 the three females' photosensors and A8-A15 the two males'.
So this route borrows one, and the cheapest to borrow is a female's
photosensor.

1. **Look at `J11` rows 11-12, 13-14 and 15-16 before touching them, and
   photograph them.** Each row is two separate nets joined only by
   whatever is physically fitted across it, and this repository does not
   record whether that is a shunt or a resistor (`as built` section 2).
   Keep whatever you take off.
2. Remove what is fitted across **`J11` 11-12** - female1's photosensor.
   Pin 12 is A5, and it is now disconnected from everything.
3. Jumper the body's microphone pin (`J11` 1, 3, 5, 7 or 9, per the
   table above) to **`J11` pin 12**.
4. In the sketch, `#define MIC_PIN A5`. Upload it to the installation's
   Mega.
5. Plot as in 2b. `test microphone signal` will not be able to read the
   analysers; that is expected on this route.

### Putting it back

1. `drivers > arduino > flash firmware` puts firmware 4 back on the
   board in one press, and ends by reopening the port - so the outcome
   line is the board saying in its own words which firmware it is now
   running.
2. Confirm on `drivers > arduino`: **in sync: yes**, and *board says:
   firmware 4 at 1000000 baud*.
3. Remove the jumper and refit what you took off `J11` 11-12.
4. Check female1's photosensor is reading again -
   `tests > manual tests > test sensors`, hand over the sensor, watch the
   number fall.

---

## 4. The four traces

The plotter draws four series per window of 20 ms:

| trace | what it is |
|---|---|
| `min` | the quietest sample in that window |
| `max` | the loudest |
| `mean` | the average - the signal's DC level |
| `bias1v25` | a flat reference at **256** |

`min` and `max` are the pair you watch: sound is the two of them opening
away from each other and closing again, in time with the music. `mean` is
the slow one and it should not move at all.

**256 is where the MAX9814 sits when it hears nothing.** Its output is
biased at 1.25 V, and 1.25 V read against a 5 V reference to ten bits is
256. That is the entire reason for the fourth trace: the other three
should be arranged around it, and a plot centred anywhere else has
answered the question before you have played a note.

> On a 3.3 V probe board the arithmetic is different - 1.25 V is about
> 388 counts there, and the reference line will be in the wrong place.
> Use a 5 V board, or read the bias line as decoration.

**Switch to `#define MODE WAVE` to see the waveform itself**, in bursts
of 400 samples. Envelope mode cannot tell a real tone from mains hum or
from NeoPixel switching noise picked up off the wire; wave mode makes
them look nothing like each other. It is the mode for "there is
*something* there, but is it sound?".

---

## 5. What a working microphone looks like

- **Quiet room, nothing playing.** `mean` sits on 256. `min` and `max`
  hug it, and over a second or two they drift *apart* rather than
  together - the AGC is winding the gain up towards its 40 dB strap
  because it has nothing to hear, so room noise grows into a visible
  band. That growth is itself a sign of life.
- **Music at conversational level, 20-30 cm away.** `min` and `max` open
  out immediately and follow the beat. The shape on the screen is
  recognisably the music.
- **After a loud passage stops**, the envelope shrinks over about a
  second and then room noise creeps back. That is the AGC's release, set
  to 1:500 by the `A/R` strap to ground. It is expected, and it is not a
  fault.
- **Neither extreme is ever reached.** The module does not swing to
  either rail. A trace pinned at 0 or at 1023 is a fault every time,
  never a loud noise.

---

## 6. What each failure shape means

| the plot | what it is |
|---|---|
| dead flat at 0 | no supply to the module, or `AOUT`/`GND` not reaching this pin. Check +5 V at the body - `B-J4` carries no power at all, which is `next pcb` section 5's whole subject. |
| dead flat at 1023 | the pin is being pulled up. A pull-up enabled by mistake, or the wrong wire. |
| flat near 512, unmoving | 512 is half rail, not 1.25 V. You are not on a MAX9814 output. |
| wandering slowly over the whole range, unrelated to sound | nothing is connected. A floating ADC pin does not read silence, it reads whatever it likes. Check the clip, and check ground went on. |
| `mean` on 256, but nothing moves however loud you play | powered and biased and deaf. The microphone element, or the `Gain` strap. |
| fast noise unrelated to the music | picked up off the wire rather than out of the air. Shorten the probe lead, and try again with the NeoPixels off. Wave mode tells the two apart. |
| **the plot moves, the analyser bands do not** | **the fault is between the microphone wire and the MSGEQ7** - its input network, its supply, or the strobe on D4. This is the row this test exists for. |
| the plot moves and the bands move | this microphone is fine. Go to `tests > autotests > test audio bringup`, which takes the rest of the chain apart. |

---

## 7. What this cannot tell you

- **Whether the analyser's support network is right.** It can only tell
  you that the fault is on that side of the cut. What is fitted around
  the MSGEQ7 is recorded nowhere here; look at the board.
- **Which band a tone lands in, or which body's ear hears which body's
  voice.** That is `test audio loop` and `test audio bringup`, and both
  need firmware 4 on the installation's own Mega.
- **How loud anything is.** Counts on an ADC behind an automatic gain
  control are not a sound pressure measurement, and the AGC exists
  precisely to flatten the thing a level reading would be measuring -
  see `test audio at 12v` for what that costs and how it is worked
  around.
