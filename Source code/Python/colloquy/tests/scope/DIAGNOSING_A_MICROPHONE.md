# Diagnosing a microphone with two channels

How to tell a faulty microphone module from a faulty channel, a faulty
wire, or no microphone at all — and what each of those looks like on this
page, so that none of them has to be worked out twice.

Everything below was learned in one afternoon (2026-09-17) taking two
MAX9814 modules apart with this scope. Section 7 is that investigation,
kept because every rule above it is traced to the run that produced it,
and because a rule with no measurement behind it is the kind this repo
has been bitten by before.

---

## 1. The one thing to know first

**An unconnected pin does not read silence. It reads the other channel.**

There is one converter behind a multiplexer, and its sample-and-hold
capacitor (about 14 pF) comes up holding the charge of the conversion
before it. A connected microphone charges it to the new voltage in
microseconds; an open pin has nothing to discharge it into, so it reports
its neighbour.

Measured here, across three runs, both pins, a strong module and a weak
one: **94 to 95 per cent** of the other channel's value. That is the 14 pF
sharing with about 0.8 pF of pin, and it is a capacitor rather than
crosstalk in the leads — the fraction is fixed whatever the source is
doing, and the direction follows the order of conversion rather than the
wiring.

So an unplugged channel does not look empty. **It looks like a second
working microphone**, with the right bias and a convincing signal. The
`independent` reading exists for exactly this and catches it.

**If you are running one microphone, wire the unused pin to GND.** A hard
ground discharges the capacitor every time, so the channel reads a flat 0
that cannot be mistaken for anything. It costs the working channel
nothing — measured, a module read 248.4 with an open neighbour and 248.4
with a grounded one. Take the wire off before plugging a microphone back
into that pin.

## 2. What a healthy MAX9814 looks like

| reading | healthy | what it means |
|---|---|---|
| resting level | **248 counts, 1.21 V** | the part biases its output at 1.25 V from an internal reference |
| tone in the room | **35** at its own frequency | with the tone at a conversational level, a metre away |
| quiet room | peak-to-peak **~294**, low frequencies loudest | the AGC winding gain up because it has nothing to hear |

That third row is the one people forget, and it is the most diagnostic of
the three. **A working MAX9814 gets noisier in silence, not quieter.**

## 3. Read the resting level before anything else

It costs nothing, it needs no sound in the room, and it separates two
faults that look alike afterwards:

- **248 counts (1.21 V) and quiet** — the amplifier is fine and the fault
  is in front of it: the capsule, or its connection to the board. The
  bias comes from inside the chip and does not depend on the element at
  all, so a dead capsule leaves this reading perfect.
- **anything else** — the fault is the amplifier, its supply, or its
  output. Go to section 5.

## 4. Two microphones, and what the comparison is for

One trace cannot answer the question that gets asked of it: a microphone
producing nothing looks exactly like a quiet room. Two in the same room
compare themselves — whatever they are biased at, one swinging while the
other does not is a fact about a microphone and not about the room.

Read `compared` for the ratio and `independent` for whether the two
readings are two readings at all. Neither is a verdict, and `independent`
in particular cannot be one: two microphones five centimetres apart on one
pure tone honestly correlate at 0.93, and two half a wavelength apart
(43 cm at 400 Hz) are honestly near −1.

**The move that settles it is one this page cannot make: swap the two
modules between the channels.** If the fault follows the module it is the
module; if it stays on the channel it is the channel or its wiring. Doing
that took twenty seconds and ended the investigation in section 7.

## 5. When the resting level is wrong

Work through these in order. Each is cheap and each rules something out.

1. **Is the output actually driving the pin?** Ground the *other* channel
   and run again. Every sample of the live pin now starts from 0 V
   instead of from near its own last value, so a high-impedance output
   reads far too low while a healthy one does not move at all. If the
   reading is unchanged, the module drives the pin properly and every
   number you have for it is honest.
2. **Is the supply there?** Wire the module's VDD into the free channel
   and run. Expect a flat 1023. Note that 1023 is the converter's own
   ceiling, so it means *at or above* 5 V — a floor, not a measurement —
   but a rail that never wavers is a rail that is fine.
3. **Does the AGC respond?** Record with a tone, stop the tone, keep
   recording. A working module's noise floor climbs within a second or
   two. One that stays flat has a gain path that is not working, whatever
   its supply is doing.
4. **Is it the module or the wire?** Put a meter on the module's own
   output pin and compare with what the page reads. The same number means
   the module; different numbers mean the wire or the connector between
   them.

A resting level that is wrong **and** a signal attenuated by more than
that same factor cannot be a passive load on the output — a divider
scales bias and signal alike. Measured in section 7: bias at 0.61 of
normal with the signal at 0.22, which is 2.8× of attenuation that a
divider cannot account for, so the gain itself was down.

## 6. What each shape on the page means

| the reading | what it is |
|---|---|
| `248 to 248, swing 0` at rest, with sound | probably nothing — a flat channel is being *held* at something |
| `flat at zero` | a pin tied to ground, which is the honest way to leave one unused |
| `pinned at full scale` | at or above the converter's 5 V reference; 5 V and 6 V read alike |
| a steady voltage in between | a rail being measured, or an output that has died with its bias stuck |
| `touching both rails` | the input is clipping |
| `independent` near ±1 | the two are not two readings — see section 1 |

---

## 7. The investigation this came from

Two MAX9814 modules, one suspected dead. Called orange and grey here.
Seven runs, a 400 Hz tone from a laptop, and every number below is a
median across the run's captures.

| run | arrangement | A0 | A1 |
|---|---|---|---|
| 1 | grey on A0, orange on A1 | DC 162.8, 400 Hz 4.6 | DC 248.5, 400 Hz 22.6 |
| 2 | orange on A1, A0 open | *ghost* | DC 248.4, 400 Hz 34.9 |
| 3 | orange on A0, A1 open | DC 248.4, 400 Hz 35.1 | *ghost* |
| 4 | grey on A1, A0 open | *ghost* | DC 151.3, 400 Hz 8.8 |
| 5 | orange on A0, A1 grounded, no tone | DC 248.5, p-p 294 | flat 0 |
| 6 | grey on A0, A1 grounded | DC 151.3, 400 Hz 7.6 | flat 0 |
| 7 | grey on A0 no tone, A1 = grey's VDD | DC 152.6, p-p 4 | flat 1023 |

**What each run settled.**

- **Run 1** looked like a shared-ground fault: the two channels were
  anti-correlated at −0.97 and grey's bias was 0.42 V low. Both readings
  were real; the interpretation was wrong.
- **Run 2** was meant to prove which microphone was dead and instead
  proved the ghost: with a lead physically out, both channels showed the
  same tone at the same strength. The direction of the one-sample lag
  says which channel is the copy — the later conversion, because the
  converter cannot see the future — and read carelessly it named the
  wrong one.
- **Run 3** swapped the modules. The orange module gave **DC 248.4, p-p
  236, 400 Hz 35.1** on A0 against **248.4, 236, 34.9** on A1 — the same
  microphone, the same numbers, 0.6 per cent apart. **The channels were
  both good and the fault followed the module.** This was the run that
  ended the wiring theories.
- **Run 4** put grey on the other channel: DC 151.3 again. The fault
  followed the module in both directions.
- **Run 5** was the control for grounding: a healthy module reads the
  same with a grounded neighbour as with an open one. It also, by
  accident, recorded what a working MAX9814 does in silence — the AGC
  winds up and the noise floor climbs to p-p 294.
- **Run 6** grounded the neighbour and measured grey: **DC 151.3, to the
  tenth of a count.** A high-impedance output would have been dragged
  toward zero. It was not, so grey drives the pin properly and its
  numbers are its own.
- **Run 7** wired grey's own supply into the free channel: **5.000 V,
  flat, no ripple.** And with no tone playing, grey's noise floor was
  peak-to-peak **4 counts** where orange had reached 294.

**Conclusion: grey's MAX9814 was dead.** Powered correctly at 5 V, output
driving the pin at a low impedance, bias stuck 475 mV low, gain absent,
AGC inert. Nothing upstream left to blame. The module was replaced.

**Three things the page learned from being wrong during it**, all now
fixed:

- it called an unplugged channel "both are hearing the room";
- it called a supply rail at 5 V "nothing is driving the pin";
- it reported a graph's page controls as working while rebuilding the
  node under them, so the picture never moved.

And one thing worth keeping in mind about the whole exercise: **five of
the seven runs were about the instrument rather than the microphones.**
That is not waste. Each one removed a way of being confidently wrong, and
the two runs that actually answered the question (3 and 7) were only
readable because the other five had made the readings trustworthy.
