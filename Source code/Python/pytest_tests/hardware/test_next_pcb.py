# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_next_pcb.py

"""The next PCB's netlist, held to what NEXT_PCB.md says it must be.

These are the mistakes that cost a board spin rather than an afternoon: a
Mega pin on two signals, a net with one end, a tone into the wrong
filter, an analyser output on the wrong ADC. Every one of them is
invisible on a schematic and obvious to a script.

The design is pure data - no hardware, no threads, no filesystem - so it
is exactly the kind of thing this suite is for.
"""
import pytest

from colloquy.drivers import audio
from colloquy.hardware.electronics import next_pcb
from colloquy.hardware.electronics.next_pcb import Design
from colloquy.hardware.electronics.next_pcb_report import (
    bom_markdown,
    mega_pins,
    netlist_markdown,
)


@pytest.fixture(scope="module")
def design():
    return Design()


# --- the board cannot disagree with the firmware -------------------------


def test_every_body_gets_its_tone_from_the_pin_the_firmware_drives(design):
    """The board reads `drivers/audio.py` rather than restating it, so this
    can only fail if something started restating it."""
    pins = mega_pins(design)
    for body, voice in audio.VOICES.items():
        assert pins[voice["pin"]] == [f"{body}/tone"], body


def test_every_filter_channel_is_cut_for_its_own_bodys_pitch(design):
    """The one fault the whole design cannot detect: a low-pass passes
    anything below its corner, so a tone in the wrong channel still comes
    out, still lands in its own band and still reports "heard"."""
    parts = {part.ref: part for part in design.parts}
    channels = next_pcb.channel_numbers()

    for body, voice in audio.VOICES.items():
        channel = channels[body]
        resistor, capacitor = next_pcb.FILTER_VALUES[voice["hz"]]
        assert parts[f"R{channel}01"].value == resistor, body
        assert parts[f"R{channel}02"].value == resistor, body
        assert parts[f"C{channel}01"].value == capacitor, body
        assert parts[f"C{channel}02"].value == capacitor, body


def test_the_tone_reaches_the_filter_before_it_reaches_the_harness(design):
    """Feeding a raw square wave at a body is exactly what the filter board
    exists to prevent, and the build-out resistor must not be a way round
    it."""
    for body in audio.VOICES:
        tone = design.net(f"{body}/tone").terminals
        line_out = design.net(f"{body}/line out").terminals
        # The tone pin meets one resistor and nothing else.
        assert len(tone) == 2, body
        # What leaves the board comes off the build-out resistor and the
        # connector, never off the Mega.
        assert not any(ref == "A1" for ref, _ in line_out), body


def test_module_n_is_body_n_all_the_way_to_the_adc(design):
    """One number identifies a body out of the timer, through the room and
    back into the ADC. If that ever stops being true it stops being worth
    anything."""
    pins = mega_pins(design)
    for body, voice in audio.VOICES.items():
        assert pins[f"A{voice['module']}"] == [f"{body}/analyser out"], body


def test_the_five_bodies_land_in_five_different_bands(design):
    """Thomas's pitches are chosen so the pitch itself says who is
    speaking. TJ's five all sat in one band and carried nothing."""
    bands = [audio.band_of_body(body) for body in audio.VOICES]
    assert len(set(bands)) == len(bands)


# --- the mistakes that cost a board spin ---------------------------------


def test_no_mega_pin_carries_two_signals(design):
    doubled = {pin: nets for pin, nets in mega_pins(design).items() if len(nets) > 1}
    assert doubled == {}


def test_no_net_has_only_one_end(design):
    """A net with one terminal is a component wired to nothing. It draws
    perfectly well and it is always a mistake."""
    lonely = [net.name for net in design.nets if len(net.terminals) < 2]
    assert lonely == []


def test_no_reference_is_used_twice(design):
    refs = [part.ref for part in design.parts]
    assert len(refs) == len(set(refs))


def test_nothing_is_hung_on_a_reserved_pin(design):
    """D0/D1 are the link to the driver, D13 is blinked by the bootloader
    at every reset, and D20/D21 are the SDA and SCL pads' own silicon."""
    used = mega_pins(design)
    for pin in next_pcb.RESERVED_PINS:
        assert pin not in used, f"{pin}: {next_pcb.RESERVED_PINS[pin]}"


def test_no_audio_is_on_the_bootloader_led_pin():
    """The board that exists put female3's amplifier on D13, so its amp
    clicks three times at every reset. Designed out here, not avoided."""
    assert "D13" not in {voice["pin"] for voice in audio.VOICES.values()}


def test_every_part_in_the_netlist_is_in_the_bill_of_materials(design):
    """A part with a net and no line in the BOM is a part nobody orders."""
    refs = {part.ref for part in design.parts}
    bom = bom_markdown(design)
    missing = [ref for ref in refs if ref not in bom]
    assert missing == []


# --- the connectors are the supplier's, not ours -------------------------


def test_the_connectors_keep_the_pinout_of_the_board_that_exists(design):
    """Fixed by the supplier. The only change against `as built` is the
    speaker pair becoming the line out and its return, so every other pin
    must still be what the old netlist said it was."""
    from_as_built = {
        ("J5", 15): "+5V",
        ("J5", 7): "+12V",
        ("J5", 14): "dxl_data",
        ("J5", 13): "female1/neopixel",
        ("J1", 15): "+5V",
        ("A-J3", 9): "+5V",
        ("A-J3", 10): "dxl_data",
        ("A-J3", 13): "male1/microphone",
        ("B-J4", 10): "male2/microphone",
    }
    for (ref, pin), net in from_as_built.items():
        assert next_pcb._CONNECTORS[ref][pin] == net, (ref, pin)


def test_the_speaker_pair_became_the_line_out_and_its_return():
    """`speaker +/out` carried an amplified output the whole length of a
    DSUB; it carries a filtered sine now. The pins do not move."""
    for ref, pin, body in (("J5", 12, "female1"), ("J1", 12, "female2"),
                           ("A-J3", 12, "female3"), ("B-J4", 9, "male1"),
                           ("B-J4", 6, "male2")):
        assert next_pcb._CONNECTORS[ref][pin] == f"{body}/line out"
    for ref, pin, body in (("J5", 4, "female1"), ("J1", 4, "female2"),
                           ("A-J3", 5, "female3"), ("B-J4", 2, "male1"),
                           ("B-J4", 14, "male2")):
        assert next_pcb._CONNECTORS[ref][pin] == f"{body}/audio return"


def test_no_speaker_output_leaves_the_board(design):
    """The amplifier is at the body now. A `speaker` net on this board
    would mean one had been left behind."""
    assert not [net.name for net in design.nets if "speaker" in net.name]


def test_the_connector_with_no_power_says_so_on_the_silkscreen(design):
    """`B-J4` carries no supply at all and is the only connector male2
    has. It is the one fact about it nobody expects."""
    parts = {part.ref: part for part in design.parts}
    for ref in next_pcb.UNPOWERED_CONNECTORS:
        assert "NO POWER" in parts[ref].description
        assert "+5V" not in next_pcb._CONNECTORS[ref].values()
        assert "+12V" not in next_pcb._CONNECTORS[ref].values()


def test_every_body_that_can_be_powered_from_its_own_connector_is(design):
    """Three connectors, four bodies - female3 and male1 share A-J3. The
    fifth is male2, and NEXT_PCB.md section 5 decides the rail without
    waiting for it."""
    powered = [
        ref for ref, pins in next_pcb._CONNECTORS.items()
        if "+5V" in pins.values()
    ]
    assert sorted(powered) == ["A-J3", "J1", "J5"]


def test_both_rails_reach_every_connector_that_has_either(design):
    """The rail decision (+12 V, section 5) is only free to be made if
    every body that can be fed at all can be fed either way. A connector
    with +5 V and no +12 V would have decided it by default."""
    for ref, pins in next_pcb._CONNECTORS.items():
        values = set(pins.values())
        assert ("+5V" in values) == ("+12V" in values), ref


def test_male2s_connector_cannot_carry_an_amplifier_supply(design):
    """The finding section 5 rests on, and the reason male2 stopped being
    an open item that blocks the build.

    An amplifier needs a supply *and* a return. `B-J4` has one spare
    conductor and GND only on its shell, so even spending that spare on
    the supply leaves the return on a cable screen - which is the last
    copper class-D switching current should go home through - and leaves
    male2 no spare for the shutdown line section 4 reserves. So male2's
    amplifier is fed locally whatever rail this board offers, and its
    supply decides male2's module setting rather than this board's
    copper.
    """
    pins = next_pcb._CONNECTORS["B-J4"]

    spares = [net for net in pins.values() if "spare" in net]
    assert len(spares) == 1, spares

    # Pin 0 is the shell. Nothing else on it is a ground conductor.
    grounds = [pin for pin, net in pins.items() if net == "GND"]
    assert grounds == [0], grounds


# --- the mute line is reserved, not wired --------------------------------


def test_the_shutdown_net_defaults_to_amplifiers_enabled(design):
    """Firmware 4 leaves D2 an input. The default of a pin nobody drives
    must be five bodies that can speak, not five silent ones and a morning
    spent looking for why."""
    terminals = dict(design.net("amp shutdown").terminals)
    assert terminals["A1"] == next_pcb.SHUTDOWN_PIN
    pull_up = design.net("+5V").terminals
    assert ("RS1", "2") in pull_up


def test_the_shutdown_net_reaches_no_connector(design):
    """It cannot reach five bodies over this harness, and a
    `silence_speakers()` that half-works is worse than one that plainly
    does not exist."""
    on_connectors = [
        ref for ref, _ in design.net("amp shutdown").terminals
        if ref in next_pcb._CONNECTORS
    ]
    assert on_connectors == []


# --- what the generator refuses to guess ---------------------------------


def test_the_values_nobody_here_knows_are_kept_apart(design):
    """The MSGEQ7's support network and the light-sensor dividers are not
    in this repository. A plausible-looking number passing for a known one
    is how a board comes back wrong."""
    confirm = [part for part in design.parts if part.confirm]
    assert confirm, "the confirm section has silently emptied"

    bom = bom_markdown(design)
    decided, _, unconfirmed = bom.partition("Not decided here")
    for part in confirm:
        assert part.ref in unconfirmed, part.ref
        assert part.ref not in decided, part.ref


def test_every_light_sensor_divider_is_flagged(design):
    """`as built` says the KiCad files do not record what is fitted across
    J11/J12, and to look before pulling one out."""
    dividers = [part for part in design.parts if part.ref.startswith("RP")]
    assert len(dividers) == len(next_pcb.PHOTOSENSOR_PINS)
    assert all(part.confirm for part in dividers)


def test_the_analyser_terminals_are_named_not_numbered(design):
    """Its footprint has not been chosen. Inventing pin numbers for it
    would be inventing the part."""
    for ref, pin in design.net("analyser/strobe").terminals:
        if ref.startswith("U"):
            assert pin == "STROBE"


# --- the documents ------------------------------------------------------


def test_the_generated_files_announce_themselves(design):
    """One that does not gets edited by hand exactly once."""
    for text in (netlist_markdown(design), bom_markdown(design)):
        assert "Generated. Do not edit." in text


def test_the_netlist_names_every_net(design):
    text = netlist_markdown(design)
    for net in design.nets:
        assert f"`{net.name}`" in text, net.name
