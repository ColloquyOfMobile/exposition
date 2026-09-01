# Supply setup — running the amplifiers at 12 V

What this test measures, how to wire it, and the seven ways to destroy
something doing so. Read the second half before the first.

## 0. Read this first — 2026-09-01, one module destroyed

> **This document told somebody to do something that broke the hardware,
> and `measure at 12 V` is refused until that cannot happen again.**
>
> On 2026-09-01 the +12 V was brought to one GF1002's VDD/GND terminal,
> exactly as section 3 below instructs. The module died the instant the
> rail came up. Nothing else was damaged — Mega, filter board, analyser
> array and microphones all still answer.
>
> **The wiring was right. The number was wrong.** This document used to
> say the amplifier module was "specified 4.5–15 V". It had no source:
> `git log -S` puts the claim in the commit that *decided the rail for
> the next board*, where it was a **specification for a module still to
> be bought**, and it was then copied here as a **statement of fact about
> the modules already on this bench**. Those two sentences read alike and
> are opposite in kind — one is a requirement you impose, the other is a
> property you have to go and check. The GF1002's real rating is still
> not recorded anywhere in this repository. What the bench has
> established is that it is a 5 V-class part.
>
> `docs/errors/2026-09-01-01.txt` is the report.
>
> **What now stops it.** The rating is a recorded fact about the module
> in your hand — `params > audio > amplifier module` and
> `amplifier max supply volts`, which ship as `GF1002` and `5.0`. Any
> pass above that is refused instantly. `measure at 5 V` still runs.
> Raising the number is a deliberate press **against a datasheet or a
> part marking**, never against another document in this repository —
> which is the whole of the mistake above.

---

`hardware > electronics > next pcb` section 5 reasons that the
amplifiers should run from **+12 V**: the same acoustic power at about
40% of the current, on a conductor the NeoPixels never touch. That
reasoning is about current and is untouched by the failure above — but
the section was written assuming the amplifiers already in hand could be
carried over to that rail, and they cannot, so the decision is reopened
there. What this bench was built to answer is *how much louder, in
fact*, and it can answer it only for a module rated for the rail.

---

## 1. First: the motors come off

The 12 V on this bench comes from the Dynamixel supply, which means a
connector that normally carries the servo chain is about to carry
something else. **Press `hardware > motors > unplug the motors` before
you touch anything.**

It is not a formality. Every servo runs in extended position mode, where
the count of whole turns lives in volatile memory, and the bar's travel
is 2.4 turns of its servo. A chain pulled at the far end wakes believing
it is somewhere else entirely, and its `dxl origin` is then a lie you get
back only by going to the rig with the bodies. The command walks
everything home, cuts torque, and leaves the server running so you can go
straight on to the two buttons on this page.

On a bench with no piece attached there is nothing to home and the
command says so. Press it anyway — the habit is what saves the
installation, and the button is in the same place on both machines.

---

## 2. Where the 12 V actually is

**The U2D2 itself has no power input.** It is a USB-to-TTL/RS-485
converter and it takes its own power from USB. The 12 V is on the
**U2D2 Power Hub Board**: in at its DC jack, out on every Dynamixel
connector.

| Connector | Pin 1 | Pin 2 | Pin 3 | Pin 4 |
|---|---|---|---|---|
| 3-pin TTL | GND | VDD | DATA | — |
| 4-pin RS-485 | GND | VDD | DATA+ | DATA− |

**Do not wire from that table.** It is the ROBOTIS convention and it is
here so you know what you are looking for, not so you can skip the meter.
Pin numbering on a JST housing is easy to read backwards, and pin 3 is a
data line that will not enjoy being treated as a rail.

Two things to measure before anything else:

- **What is the supply actually?** The SMPS shipped with Dynamixel kits
  is commonly 12 V, but 11.1 V and 14.8 V units exist for the XM/XH
  series. Meter the jack — you are about to write a number down, and
  "12 V" should be a measurement.

  ~~The amplifier module is specified 4.5–15 V, so any of the three is
  safe for *it*.~~ **This was false and it cost a module** — see section
  0. Nothing in this repository knows the GF1002's supply range. Whatever
  is on that jack, the only thing that makes it safe for an amplifier is
  a rating you have read off **that amplifier**, and the only place that
  belongs is `params > audio > amplifier max supply volts`.
- **Which pin is which**, on the housing you are actually holding.

---

## 3. The wiring

Three connections, and the order they are made in is part of the safety.

| From | To |
|---|---|
| Hub GND | amplifier GND **and** Mega GND — joined, and joined **first** |
| Hub VDD (+12 V) | amplifier VDD, through a fuse — see §4.5 |
| Mega timer pin | amplifier input, through the existing 22K/3K3 divider |

The tone pins are fixed by silicon and are the same five as everywhere
else in this repo: D11 (160 Hz), D5 (400 Hz), D6 (1 kHz), D46 (2.5 kHz),
D10 (6.25 kHz). Nothing about the microphones, the MSGEQ7 array, the
strobe or the reset changes — the hearing side stays exactly as
`hardware setup` describes it, on 5 V, and that is the point of the
comparison.

**Nothing on the hearing side goes anywhere near 12 V.** The MAX9814
microphone modules are 2.7–5.5 V parts and the MSGEQ7s are 5 V parts.
Twelve volts on either is instant and permanent.

---

## 4. The seven ways to destroy something

Roughly in order of how often they actually happen.

### 4.1 Twelve volts into a five-volt pin

Everything on the Mega, every MSGEQ7, and every microphone module is a
5 V part. One slipped probe or one JST plugged one row across puts 12 V
on an ADC input, and that pin — usually that chip — is gone.

**Route the supply lead down the other side of the bench from the
analyser board.** Physical distance is worth more here than care.

**And the amplifier is a 5 V part too until proven otherwise.** That is
the lesson of section 0: the one thing on this bench that was *supposed*
to take 12 V is the one thing that died of it. A module's rating is not
something another document can tell you.

### 4.2 Grounds not joined — join them first, part them last

The amplifier's *input* comes from the Mega's timer pin and is referenced
to the Mega's ground. Its *supply* is referenced to the hub's ground. If
those two grounds are not joined, the input sees an undefined common
mode and current finds its way out through the Mega pin's protection
diodes, which are not rated to be a power path.

So: **ground on first, ground off last**, every time. With both sides
powered and the grounds joined, a meter between the two ground points
should read a few millivolts. If it reads anything you would call a
voltage, stop and find out why before connecting a signal.

### 4.3 Reverse polarity

The GF1002-class modules generally have no reverse protection at all.
Meter the lead **at the amplifier end, with the amplifier unplugged**,
before it goes in. Red-wire-to-VDD is a convention, not a check; the
meter is the check.

### 4.4 The class-D output is differential — never ground either side

`ROUT+` and `ROUT−` are both driven. Neither is ground. Grounding either
one shorts half the bridge and kills the module, usually instantly and
usually silently.

That includes a **scope ground clip**, which is the way it normally
happens. If you must look at the output, use two probes and subtract, or
put the scope on the amplifier's input instead — which is where the
interesting question is anyway.

### 4.5 The supply can deliver amps, and will not politely trip

A Dynamixel SMPS is typically 5 A or more. A short across it does not
trip anything; it melts the thinnest wire in the path, and on this bench
that is whatever you just added.

**Put a fuse in the +12 V lead.** Size it for the bench rather than for
the installation: five class-D modules at test volume draw far less than
the installation's budget, and `next pcb` §5 budgets 0.25 A of *peak*
amplifier current per body at +12 V. A 1 A fuse is a sane bench value and
still turns a slipped probe into a blown fuse rather than a fire.

Better, if you have one: a **bench supply with a current limit**, set to
a few hundred milliamps. It turns every mistake in this list into a beep.

### 4.6 Change the supply with everything off

Power down, move the lead, power up. Hot-plugging a supply into a class-D
module's input capacitance draws a large inrush and can arc the
connector — and, on a good day, only browns out everything else sharing
the rail. There is field evidence for exactly that one commit back in
this repo: the 2026-08-28 brown-out, which was this same mistake one
level up.

### 4.7 Turn the volume down before the first 12 V run

The 22K/3K3 divider was sized to keep the filter output under the
amplifier's maximum input **with the module's pot at maximum** — at 5 V.
Raise the rail and the same input gives more output. Exceed it and the
amp clips, and a clipped output is a square wave again, throwing away
everything the filter board just did.

**Start with the pot low and bring it up.** The first sign of trouble is
the tone turning from a note into a buzz.

And the loudspeakers: they sit in an open frame, close to an acoustic
short circuit, and the two lowest tones are the ones at risk. More rail
means more excursion. Do not park 160 Hz at full volume at 12 V and go
and look at something else.

---

## 5. Five checks before you power up

0. **The module in your hand is rated for the rail**, read off the module
   or its listing — not off this document, and not off `next pcb`. It is
   recorded in `params > audio > amplifier module`, and the test refuses
   the pass if it is not. This check is numbered zero because it is the
   one that was skipped on 2026-09-01, and no other check on this list
   would have caught it.
1. Meter reads the supply you expect at the hub jack.
2. Meter reads that same voltage between the amplifier's VDD and GND
   terminals **with the amplifier unplugged** — right polarity, right pins.
3. Fuse (or current limit) is in the +12 V lead, not in the ground.
4. Grounds are joined: hub, amplifiers, Mega.
5. Nothing on the microphone or analyser side has been touched, and no
   12 V lead runs near it.

---

## 6. Running it

The test needs **two passes with a screwdriver between them**, and it
cannot make its comparison until it has both.

1. Pick Thomas's board under `com port` — the same lead and the same
   remembered choice as `test audio subsystem`, since it is the same board.
2. With the amplifiers on the supply you have now, press
   **`measure at 5 V`**. It silences the board, reads all five modules for
   three seconds as a floor, then holds each of the five tones for three
   seconds and reads again.
3. **Power down. Change the supply. Power up.** Turn the volume pot down
   first (§4.7).
4. Press **`measure at 12 V`**. Same sweep.
5. Read the comparison, one row per tone.

`forget both passes` throws them away. Use it whenever anything else on
the bench has moved between the two — a microphone nudged 10 cm between
passes produces a beautifully convincing result about a supply.

The `hold <n> Hz on` commands are the important ones. Hold a tone,
change the supply underneath it, and **listen** — that is the instrument
that actually settles this question, for the reason in the next section.
`silence` turns everything off and lets go of the board.

---

## 7. How to read what comes back, and why there are two numbers

**The MAX9814's automatic gain control is the whole difficulty.** It
exists to hold its output roughly constant against exactly the change
being measured: make the room twice as loud and it turns itself down.
A flat reading is therefore **not** evidence that nothing changed.

So each tone carries two numbers:

- **rise** — the tone's own band, over that band's level in silence.
  Direct, easy to read, and the reading the gain control flattens.
- **share** — that band as a fraction of all seven added together. This
  one largely survives the AGC, because of what the AGC does: it holds
  the *total* near constant, so a tone that is genuinely louder takes a
  larger fraction of that total while the room noise in the other six
  bands is turned down along with it.

A **share that climbs while the rise does not** is the signature of a
working amplifier behind a gain control doing its job. That is the result
to expect, and it is a pass.

Neither number is a sound pressure measurement and neither should be
written down as one. If you want the real answer, hold one tone and
change the supply under it with your ear a metre away.

Two rows that mean something other than what they say:

- **"not heard at either supply"** — almost always a channel nobody has
  wired yet. An unwired analyser input is a floating ADC pin, and a
  floating pin does not read silence; it reads whatever is nearby.
- **"QUIETER"** — check the wiring before believing it. A quieter tone at
  a higher rail is usually clipping (§4.7) or a supply that never
  actually changed.

Run against the stand-in it produces two passes that differ by nothing,
which looks exactly like a real bench where 12 V bought you nothing. That
is why the page says which board answered before it says any number.
