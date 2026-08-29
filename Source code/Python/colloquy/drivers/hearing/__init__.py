# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/hearing/__init__.py

"""What each body can hear - **emulated, because the microphones are not
in service.**

The sounding half of the channel is real: `drivers/sing/` writes a real
speaker through a real amplifier, and on the installation it makes a
noise in the room. The listening half is not. As of 2026-08-29 one
channel of the analyser array is wired, the bring-up test's own numbers
say female1's voice is heard by nobody, and no body has ever decoded a
pattern from a microphone. So a reinforcement loop written against the
microphones would be a loop that never closes.

**What this does instead.** It reads what the five `Sing` threads are
transmitting *right now* and hands each body what it would hear. Not a
model of a room - a statement of what is being sung, which is the one
part of the chain that is known to be true.

Two rules, and both are TJ's rather than convenience:

- **Nobody listens to their own voice.** Transmitting anything sets
  `sense_sound_active = false` in his firmware, and `act_transmit_*` sets
  it back afterwards (CODE_DOCUMENTATION 9.12). It is why a male never
  decodes his own `R` as an answer.
- **Everything else is in earshot.** Unlike the light channel there is no
  geometry here: the light side needs a female pointed at a male with the
  bar in the right place, and sound in a room that size reaches
  everybody. The pitch is what separates the voices, which is the whole
  reason each body has a different one landing in a different analyser
  band (`drivers/audio.py`).

**Where it stops being honest, said out loud on the page.** A real ear
would mishear, would be drowned by the room, and would sometimes hear
nothing at the far end of the bar. This one never does. So a
reinforcement that works here is not evidence that it works in the
gallery - it is evidence that the *behaviour* is right, which is what it
is for. `emulated` is a reading on this node, and it will read
`microphones` on the day the other half is trusted.
"""
from colloquy.base import Base
from colloquy.ui import leaves


class Hearing(Base):
    """The ears of the whole piece, in one place."""

    def __init__(self, owner, bodies):
        super().__init__(owner=owner)
        self._bodies = {body.name: body for body in bodies}

    @property
    def name(self):
        return "hearing"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def bodies(self):
        return list(self._bodies.values())

    @property
    def is_emulated(self):
        """True for as long as this is computed rather than heard.

        A property rather than a constant so that the day a microphone is
        trusted, there is one place to change and one reading on the page
        that changes with it.
        """
        return True

    # --- what a body hears ------------------------------------------------

    def voices(self):
        """Every body singing at this instant: name -> the ten bits.

        Only bodies whose burst is actually sounding - a `Sing` in its
        2.35 s of silence is not a voice, and that silence is part of the
        message.
        """
        singing = {}
        for name, body in self._bodies.items():
            sing = getattr(body, "sing", None)
            if sing is None or not sing.is_transmitting:
                continue
            if not sing.bits:
                continue
            singing[name] = tuple(sing.bits)
        return singing

    def heard_by(self, listener):
        """What `listener` can hear: (singer name, bits), or None.

        None while nobody is singing, and None while the listener is
        singing itself - see the module docstring on half duplex.
        """
        name = getattr(listener, "name", listener)
        own = self._bodies.get(name)
        if own is not None:
            sing = getattr(own, "sing", None)
            if sing is not None and sing.is_transmitting:
                return None

        for singer, bits in self.voices().items():
            if singer == name:
                continue
            return singer, bits
        return None

    def hears(self, listener, singer, pattern):
        """Is `listener` hearing exactly `pattern` from `singer` now?

        The question both halves of reinforcement actually ask: a female
        waits for one male's `R`, a male waits for one female singing his
        own call back. Anything else in the room is not an answer.
        """
        heard = self.heard_by(listener)
        if heard is None:
            return False
        who, bits = heard
        return who == singer and bits == tuple(pattern)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        # The one thing this node must never be ambiguous about, for the
        # same reason `drivers > arduino` says which board it is driving.
        leaf(
            "source",
            "emulated - what is being sung, not what any microphone heard"
            if self.is_emulated
            else "the microphones",
        )
        singing = self.voices()
        leaf(
            "voices now",
            ", ".join(
                f"{name} {''.join(str(bit) for bit in bits)}"
                for name, bits in singing.items()
            )
            or "nobody is singing",
        )
        for body in self._bodies.values():
            heard = self.heard_by(body)
            if heard is None:
                continue
            singer, bits = heard
            leaf(
                f"{body.name} hears",
                f"{singer} - {''.join(str(bit) for bit in bits)}",
            )
        return states
