# OpenCM and Pro Minis

**The third full solution, and the shortest to describe: it is `one board
per body` with two parts removed.** The U2D2 and the bridge collapse into
one OpenCM 9.04, because that board is a programmable controller with USB
on it that drives a Dynamixel bus natively — and the two things it
replaces are a dumb adapter and a relay.

Same fixed harness as the other two. Same four boards in `harness`, same
DSUBs, same pinouts.

---

## 0. TJ needed six of these. We need one.

His archive has an OpenCM sketch per body and one for the bar —
`deploy22_fem_OCM`, `deploy21_male_OCM`, `deploy37b_bar_OCM` and their
ancestors, all `Dynamixel2Arduino` on `Serial1` with the direction pin at
28, Protocol 2.0. Each drove only its own servos: a female's body and her
mirror, a male's body, the bar's two. The Pro Mini beside it asked for
states over a handful of GPIO lines — `VERTICAL`/`UP`/`DOWN` for the
mirror, a body-stop request — and the bar's controller read the two
males' drive states off its own pins to decide whether to wander.

**Six controllers because he had six separate buses.** This harness does
not: `dynamixel data` is *one* conductor that reaches every body
(`harness`), so all nine servos already sit on one bus with one master.
That is the whole reason this solution is small — the topology he had to
build around is already gone.

---

## 1. The one change that defines it

| | `one board per body` | this |
|---|---|---|
| servo bus master | **U2D2**, a USB-to-Dynamixel adapter | **OpenCM 9.04** |
| link to the driver | a **bridge** processor in the rack | the same OpenCM, over its own USB |
| bodies | five Pro Minis | five Pro Minis — unchanged |
| listening | Goertzel in software, no analyser chip | unchanged |
| filters, dividers, analysers | gone from the rack | unchanged |
| processors, total | 5 + bridge, **plus** the U2D2 | **6**, and no adapter |

**A U2D2 can only relay.** It is an FTDI part with a half-duplex driver
on it: everything it does is a byte the PC sent. An OpenCM is an STM32F1
at 72 MHz with the same bus driver, USB, three spare serial ports and
program memory — so the thing that was a cable becomes the thing that can
hold the piece up when the PC is not there.

---

## 2. What each processor does

**The OpenCM, in the rack.** Three jobs, and it is the only board with
more than one:

- **the servo bus** — nine Dynamixels on the one conductor the harness
  already carries, `Serial1` with the direction pin, Protocol 2.0, which
  is what `dynamixel_sdk` speaks today;
- **the body bus** — `Serial2` through an RS-485 transceiver, the same
  two conductors `one board per body` section 3 specifies, mastering the
  five Pro Minis;
- **the driver's link** — USB, one serial port, the JSON lines
  `drivers/arduino/` already sends. So the Python side keeps its shape
  and `drivers/u2d2/` goes.

**A Pro Mini, in each body.** Exactly as `one board per body` section 4:
its light sensors, its NeoPixel lines, its tone, its microphone, its
Goertzel bins. Nothing about that changes and this document does not
repeat it.

**A Mega: not needed.** Said plainly because the question was asked. The
listening is five Goertzel bins on the body's own processor at about 15%
of it, so there is nothing central left to hear with; the bridging is the
OpenCM's; and the rack has no sensor, no pixel and no tone of its own.
**What would make one needed** is one thing only: if a Pro Mini turns out
unable to sample while it writes NeoPixels — the interrupt blanking in
section 4 — and the listening has to move off the body. That is a
measurement (`tests > test goertzel ear` and a strip on the same board),
not a guess, and it is worth making before this is committed to.

---

## 3. What the rack becomes

Almost nothing, and less than either of the other two:

- the four DSUBs, in the panel, unchanged;
- power in, and the +5 V / +12 V distribution;
- the OpenCM on a mount, and one RS-485 transceiver;
- the DC jack, the screw bridge, the JST.

**Gone from it**, against `next pcb`: five filters, five dividers, five
MSGEQ7s and their support networks, the commoned strobe and reset, every
analogue net — *and* the Mega, *and* the U2D2's mount and its second USB
lead. Two USB cables out of the rack become one.

---

## 4. What it wins, beyond a smaller board

- **One USB lead, one thing to open.** Today `open_the_hardware()` has
  three independent halves because a dead Arduino must not cost the
  servos. Here there is one link, and what is behind it is a controller
  that can report on both buses rather than a pair of adapters that
  cannot report on anything.
- **An emergency stop that does not need the PC.** Torque comes off
  because Python reached the U2D2, and this repository has a traceback
  where that path was itself the thing that failed
  (`emergency_stop` raising out of `U2D2.open`). A controller can hold a
  deadman and cut torque on its own. That is the strongest argument here
  and it is a safety one.
- **The bar's own rule was already his.** `Bar.loop()` decides to wander
  by watching the males' search flags; his bar controller did the same by
  reading their drive-state pins. Moving that decision back down is a
  port rather than an invention.
- **The piece can be alive with the computer off**, which it was in 2021.
  Not a requirement, and not free — but nothing in this arrangement
  forbids it, where the other two designs make the PC the only thing that
  can decide anything.

## 5. What it costs

- **New firmware on a board nobody here has written for.** The OpenCM
  side is real work: the driver's protocol, two buses, and the
  scheduling between them. Both other solutions reuse a sketch that
  exists.
- **A single-source part**, and one whose maker has moved on to newer
  controllers. The U2D2 is single-source too, so this is a change of
  supplier rather than a new exposure — but it is worth knowing before
  buying one of anything.
- **3.3 V.** The OpenCM is a 3.3 V board where the Mega is 5 V. Its
  Dynamixel port handles the servo bus itself, and an RS-485 transceiver
  handles the body bus, so nothing here needs a level shifter — but that
  is a thing to check per pin rather than assume.
- **Everything `one board per body` costs**, unchanged: five firmwares,
  five flashings onto boards with no USB, five places to look.

---

## 6. Against the other two

| | `next pcb` | `one board per body` | this |
|---|---|---|---|
| processors | 1 | 5 + bridge | **6** |
| adapters | U2D2 | U2D2 | **none** |
| USB leads out of the rack | 2 | 2 | **1** |
| analogue on the harness | yes | no | no |
| where the bit clock lives | unsolved | in the body | in the body |
| stop without the PC | no | no | **yes** |
| firmware to write | none new | one sketch + a bus | one sketch + a bus + **the controller** |
| how finished | netlist generated | specified | specified |

**The recommendation is unchanged, and this does not displace it.** Build
`next pcb` for the exhibition: it is done, it is one board, and the piece
has a date. What this adds to the choice is that **if the harness
measurement in `next pcb` section 3 fails**, the answer is a distributed
design — and *then* the question is only whether the rack keeps a bridge
and an adapter, or one controller instead. On that narrower question this
one wins on parts, on leads, and on the stop.

So read section 1 as the real content: **it is not a third architecture,
it is `one board per body` with the rack tidied.** Everything about the
bodies, the bus, the filters and the pitches is that document's, and
nothing here changes it.

---

## 7. What is open

- **The measurement that decides whether a Mega is wanted** (section 2):
  can a Pro Mini sample while it writes a NeoPixel strip?
- **Whether the OpenCM masters the body bus or merely relays it.** If it
  schedules the five nodes itself, the driver sees one tidy device; if it
  relays, the driver sees five and the controller is a hub. The first is
  more work and more use.
- **How much autonomy to move down.** The bar's wander rule is the
  obvious first one, since it was his. Anything more is a decision about
  what the driver is *for*, and that is not an electronics question.
- **The mirrors.** Their range is known (`params.py`) and their origins
  are not; that is true of all three solutions and is not this one's to
  answer.
