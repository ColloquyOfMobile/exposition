# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_shields.py

"""`shields` against the copper it keeps, the sketch it ports and the
arithmetic it quotes.

The document makes three kinds of promise, and each fails in its own
quiet way if it drifts:

- **the backplane is the v2 board**: the Mega's footprint carries the
  nets v2 gives it, and what moves into a shield (Thomas's filters, the
  MSGEQ7 network) keeps v2's values. Held to `circuit.json`, as
  `test_thomas_or_teensy.py` does.
- **the Teensy adapter is wired to what the silicon can do**: five voices
  on five timer units, the microphones on pins both converters reach,
  nothing on the LED. Held to `shields.py`'s copy of PJRC's tables.
- **every figure about a voice card is computed, not typed**: the card
  list, the windows, the comparison with Thomas's channel, the Teensy's
  frequencies. Held to `shields.py`, which recomputes them.

Like `test_harness.py`, these read checked-in files rather than doubles:
the parse finding them is the thing worth pinning.
"""
import json
import math
import re

import pytest

from colloquy.drivers import audio
from colloquy.drivers.arduino import firmware
from colloquy.hardware.electronics import Shields, shields
from colloquy.hardware.electronics.harness import KICAD

DOCUMENT = Shields.folder / Shields.file_name
CIRCUIT = KICAD / "electronic box v2" / "colloquy-control-v2" / "circuit.json"
SKETCH = firmware.SKETCH_PATH

# The three footprint pins the backplane adds.
ADDED_PINS = {"IORF", "SDA", "SCL"}


# --- reading the files ------------------------------------------------------


def _components():
    return json.loads(CIRCUIT.read_text(encoding="utf-8"))["components"]


def _component(ref):
    for component in _components():
        if component["ref"] == ref:
            return component
    raise AssertionError(f"{ref} is not in circuit.json")


def _pins(ref):
    return {pin: net for pin, net in _component(ref)["pins"].items() if net}


def _table(first_header_cell):
    """The markdown table whose header starts with this cell, as rows of
    cells with the backticks taken off."""
    lines = DOCUMENT.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells and cells[0] == first_header_cell:
            rows = []
            for row in lines[index + 2:]:
                if not row.startswith("|"):
                    break
                rows.append(_cells(row))
            return cells, rows
    raise AssertionError(f"no table headed {first_header_cell!r}")


def _cells(line):
    if not line.startswith("|"):
        return []
    return [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]


def _numbers(text):
    return [float(number) for number in re.findall(r"-?\d+(?:\.\d+)?", text)]


def _ohms(text):
    """`1K2` -> 1200, `82K5` -> 82500, `105K` -> 105000."""
    match = re.fullmatch(r"(\d+)K(\d*)", text.split()[0])
    assert match, text
    return float(f"{match.group(1)}.{match.group(2) or 0}") * 1000


def _farads(text):
    match = re.fullmatch(r"(\d+(?:\.\d+)?)nF", text.split()[0])
    assert match, text
    return float(match.group(1)) * 1e-9


def _footprint():
    """Every footprint pin the document gives a net, v2's and the added."""
    _, rows = _table("Mega pin")
    _, added = _table("Added pin")
    return {row[0]: row[1] for row in rows + added}


def _teensy_rows():
    _, rows = _table("Teensy pin")
    return [row for row in rows if row[0].isdigit()]


def test_the_files_are_where_this_thinks_they_are():
    """The one failure that would make every test here vacuous."""
    assert DOCUMENT.is_file()
    assert CIRCUIT.is_file()
    assert SKETCH.is_file()


# --- section 3e: the computing slot is v2's footprint ---------------------


def test_the_computing_slot_is_the_v2_boards_footprint_pin_for_pin():
    """So the Mega plugs in as it is and firmware 4 runs unmodified."""
    _, rows = _table("Mega pin")
    written = {row[0]: row[1] for row in rows}
    v2 = {
        pin: net for pin, net in _pins("A1").items()
        if not pin.startswith(("5V", "GND"))
    }

    assert written == v2


def test_the_added_footprint_pins_are_free_on_v2_and_in_firmware_4():
    """IOREF and the R3 header's I2C pair. If v2 or firmware 4 used any of
    them - or D20/D21, which they are on a Mega - the Mega would no longer
    see the v2 board."""
    _, added = _table("Added pin")
    assert {row[0] for row in added} == ADDED_PINS

    used_on_v2 = set(_pins("A1"))
    assert not (ADDED_PINS | {"D20", "D21"}) & used_on_v2

    sketch = SKETCH.read_text(encoding="utf-8")
    defined = set(re.findall(r"^#define \w+ (\d+)\b", sketch, re.MULTILINE))
    assert not {"20", "21"} & defined
    assert "Wire" not in sketch


# --- section 3g: the voice slots -------------------------------------------


def test_slot_n_is_body_n_and_carries_v2s_nets():
    """Pin 1 is the body's tone net, which is on the Mega pin
    `drivers/audio.py` names; pin 3 is the net v2's own build-out takes
    to the line out; the straps count the slots up from 0x50."""
    _, rows = _table("Voice slot")
    footprint = _footprint()

    assert [row[1] for row in rows] == list(audio.BODIES)
    for number, (slot, body, tone, filter_out, straps, address) in enumerate(rows):
        assert slot == f"JV{number + 1}"
        assert tone == f"{body}/tone"
        assert footprint[audio.VOICES[body]["pin"]] == tone
        assert filter_out == f"{body}/filter out"

        build_out = [
            component for component in _components()
            if set(component["pins"].values()) == {filter_out, f"{body}/line out"}
        ]
        assert [component["value"] for component in build_out] == ["100R"]

        bits = "".join("1" if strap == "IOREF" else "0" for strap in straps.split())
        assert int(bits, 2) == number
        assert int(address, 16) == 0x50 + number


# --- section 5b: the Teensy adapter ----------------------------------------


def test_no_teensy_pin_is_used_twice_and_the_led_is_left_alone():
    pins = [int(row[0]) for row in _teensy_rows()]

    assert len(pins) == len(set(pins))
    assert shields.TEENSY41_LED not in pins


def test_the_adapter_carries_every_footprint_net_once_and_on_its_own_pin():
    """The adapter stands in for a Mega, so every net the footprint
    carries has to arrive on the Mega pin the backplane expects it on."""
    # IOREF is the Teensy's 3.3 V, a supply rather than a pin.
    footprint = {pin: net for pin, net in _footprint().items() if pin != "IORF"}
    rows = _teensy_rows()

    assert {row[1]: row[2] for row in rows} == footprint
    assert len(rows) == len(footprint)


def test_five_voices_sit_on_five_timer_units():
    """`analogWriteFrequency()` sets a whole FlexPWM submodule or
    QuadTimer channel; two voices on one unit would play one pitch."""
    voices = [row for row in _teensy_rows() if row[2].endswith("/tone")]
    units = [shields.TEENSY41_TIMER[int(row[0])] for row in voices]

    assert len(voices) == 5
    assert len(set(units)) == 5
    for row, unit in zip(voices, units):
        assert row[3] == f"translator; {unit}"


def test_the_microphones_are_on_pins_both_converters_reach_in_body_order():
    microphones = [row for row in _teensy_rows() if row[2].endswith("/analyser out")]
    pins = [int(row[0]) for row in microphones]

    assert pins == [14, 15, 16, 17, 18]
    assert [row[2].split("/")[0] for row in microphones] == list(audio.BODIES)
    for pin in pins:
        assert shields.TEENSY41_ANALOG[pin] == {"ADC1", "ADC2"}


def _a_number(pin):
    return pin - 14 if pin < 28 else pin - 24


def test_every_analogue_input_is_on_an_analogue_pin_named_right():
    for row in _teensy_rows():
        pin = int(row[0])
        if "photosensor" in row[2] or row[2].endswith("/analyser out"):
            assert pin in shields.TEENSY41_ANALOG, row
            assert row[3].endswith(f"A{_a_number(pin)}"), row


def test_the_photosensors_are_divided_and_the_microphones_are_not():
    """A photosensor module can put 5 V on its line; the analyser
    shields' outputs are bounded by IOREF and go direct."""
    for row in _teensy_rows():
        if "photosensor" in row[2]:
            assert row[3].startswith("divider"), row
        if row[2].endswith("/analyser out"):
            assert row[3].startswith("direct"), row


def test_what_leaves_the_backplane_is_translated_and_what_stays_is_not():
    """NeoPixels, tones, aux and shutdown go to bodies and cards at 5 V;
    the analyser's controls and the I2C pair stay at IOREF."""
    translated = [row for row in _teensy_rows() if row[3].startswith("translator")]
    for row in _teensy_rows():
        net = row[2]
        leaves = net.endswith(("/tone", "/driven", "aux driven")) or net == "amp shutdown"
        assert row[3].startswith("translator") == leaves, row

    # Four SN74LV4T125s, four channels each.
    assert len(translated) <= 4 * 4


def test_the_i2c_pair_is_on_wire2():
    by_net = {row[2]: int(row[0]) for row in _teensy_rows()}

    assert by_net["shield/scl"] == shields.TEENSY41_WIRE2_SCL
    assert by_net["shield/sda"] == shields.TEENSY41_WIRE2_SDA


# --- sections 6a and 7b: what leaves v2 keeps v2's values ------------------


def test_the_thomas_cards_are_v2s_filters():
    _, rows = _table("Thomas card")
    assert [row[1] for row in rows] == list(audio.BODIES)

    for row in rows:
        body, plays, resistors, capacitors, refs = row[1], row[2], row[3], row[4], row[5]
        r1, r2, c1, c2 = re.findall(r"[RC]\d+", refs)
        assert _component(r1)["value"] == resistors
        assert _component(r2)["value"] == resistors
        assert _component(c1)["value"] == capacitors
        assert _component(c2)["value"] == capacitors
        assert f"{body}/tone" in _component(r1)["pins"].values()

        assert _numbers(plays) == [shields.MEGA_PITCHES[body]]
        assert shields.THOMAS_CHANNELS[body] == pytest.approx(
            (_ohms(resistors), _farads(capacitors))
        )


def _role(component, body):
    """A part's place in one body's channel, with the body taken out of
    its net names, so female1's oscillator resistor and male2's compare.
    The kind of part is in it too: the series resistor and the bypass
    jumper join the same two nets."""
    kind = re.match(r"[A-Z]+", component["ref"]).group(0)
    return (kind,) + tuple(sorted(
        (net or "").replace(f"{body}/", "<body>/")
        for net in component["pins"].values()
    ))


def test_the_msgeq7_shield_is_v2s_network_in_every_channel():
    _, rows = _table("MSGEQ7 part")
    for row in rows:
        value, ref = row[1], row[3]
        if not re.fullmatch(r"[RCJ]S?\d+", ref):
            continue
        female1 = _component(ref)
        assert female1["value"] == value, ref

        role = _role(female1, "female1")
        for body in audio.BODIES:
            twins = [
                component for component in _components()
                if _role(component, body) == role
            ]
            assert [twin["value"] for twin in twins] == [value], (ref, body)


# --- section 7c: the voice cards, recomputed --------------------------------


def test_the_card_list_is_the_computed_one():
    _, rows = _table("Card")
    assert len(rows) == len(shields.CARD_CORNERS)

    for row, corner in zip(rows, shields.CARD_CORNERS):
        assert _numbers(row[0]) == [round(corner)]
        assert _numbers(row[1]) == [round(corner)]
        sweet = [round(shields.SWEET[0] * corner), round(shields.SWEET[1] * corner)]
        allowed = [round(shields.ALLOWED[0] * corner), round(shields.ALLOWED[1] * corner)]
        assert _numbers(row[2].replace("–", " ")) == sweet
        assert _numbers(row[3].replace("–", " ")) == allowed
        assert (_ohms(row[4]), _ohms(row[5])) == pytest.approx(
            shields.card_resistors(corner)
        )


def test_the_sweet_windows_leave_no_gap():
    for lower, upper in zip(shields.CARD_CORNERS, shields.CARD_CORNERS[1:]):
        assert shields.SWEET[0] * upper <= shields.SWEET[1] * lower


def _worst_over(window):
    worst = shields.Harmonics(0.0, -math.inf, -math.inf)
    for corner in shields.CARD_CORNERS:
        resistors = shields.card_resistors(corner)
        for step in range(201):
            ratio = window[0] + (window[1] - window[0]) * step / 200
            found = shields.square_through(
                lambda hz: shields.card_response(hz, corner, resistors), ratio * corner
            )
            worst = shields.Harmonics(
                min(worst.fundamental, found.fundamental),
                max(worst.third, found.third),
                max(worst.fifth, found.fifth),
            )
    return worst


def test_the_window_figures_are_the_cards_as_built():
    """Over every card, E96 resistors and E12 capacitors, the document's
    worst cases are what the arithmetic gives, to the tenth it quotes."""
    _, rows = _table("Window")
    windows = {"sweet": shields.SWEET, "allowed": shields.ALLOWED}
    for row in rows:
        window = windows[row[0]]
        assert _numbers(row[1].replace("–", " ")) == pytest.approx(list(window))
        worst = _worst_over(window)
        assert _numbers(row[2]) == [round(-worst.fundamental, 1)]
        assert _numbers(row[3]) == [round(-worst.third, 1)]
        assert _numbers(row[4]) == [round(-worst.fifth, 1)]


def test_the_comparison_with_thomas_is_recomputed():
    _, rows = _table("Pitch")
    assert [row[1] for row in rows] == list(audio.BODIES)

    for row in rows:
        body = row[1]
        hz = shields.MEGA_PITCHES[body]
        assert _numbers(row[0]) == [hz]

        ohms, farads = shields.THOMAS_CHANNELS[body]
        thomas = shields.square_through(
            lambda f: shields.thomas_response(f, ohms, farads), hz
        )
        # Unloaded, for a 5.0 V square: its fundamental is (4/pi) x 5 Vpp.
        thomas_line = 4 / math.pi * shields.LOGIC_HIGH * 10 ** (thomas.fundamental / 20)
        assert _numbers(row[2]) == [round(thomas.fundamental, 1)]
        assert _numbers(row[3]) == [round(thomas.third, 1)]
        assert _numbers(row[4]) == [round(thomas_line, 2)]

        corner = shields.card_for(hz)
        assert _numbers(row[5]) == [round(corner)]
        resistors = shields.card_resistors(corner)
        card = shields.square_through(
            lambda f: shields.card_response(f, corner, resistors), hz
        )
        assert _numbers(row[6]) == [round(card.fundamental, 1)]
        assert _numbers(row[7]) == [round(card.third, 1)]
        assert _numbers(row[8]) == [round(shields.line_level_vpp(card.fundamental), 2)]


def test_the_stage_qs_and_the_line_level_are_the_ones_quoted():
    text = DOCUMENT.read_text(encoding="utf-8")
    for capacitors in shields.STAGE_CAPACITORS:
        assert f"**Q {shields.stage_q(capacitors):.3f}**" in text
    assert f"**{shields.line_level_vpp():.2f} Vpp**" in text


# --- section 9a: what the Teensy plays --------------------------------------


def test_the_teensy_frequencies_are_what_its_core_produces():
    _, rows = _table("Asked")
    voice_pins = [int(row[0]) for row in _teensy_rows() if row[2].endswith("/tone")]
    for row in rows:
        asked = _numbers(row[0])[0]
        for pin in voice_pins:
            plays = shields.teensy_pwm_frequency(asked, pin)
            assert _numbers(row[1]) == [round(plays, 2)], (asked, pin)


def test_every_pitch_this_piece_uses_comes_out_within_an_eighth_of_a_hertz():
    pitches = list(shields.MEGA_PITCHES.values()) + [160, 400, 1000, 2500, 6250]
    for hz in pitches:
        assert abs(shields.teensy_pwm_frequency(hz, 2) - hz) < 0.12


def test_the_lowest_pitch_is_the_largest_divider_at_the_largest_prescaler():
    lowest = shields.TEENSY41_F_BUS / 128 / 65535

    assert round(lowest, 1) == 17.9
    assert "**17.9 Hz**" in DOCUMENT.read_text(encoding="utf-8")


# --- section 9c: the port ---------------------------------------------------


def test_the_port_table_names_every_class_and_function_in_the_sketch():
    """"Can the rest of the Mega code be ported" is only answered if every
    part of it is in the table."""
    _, rows = _table("Sketch part")
    named = " ".join(row[0] for row in rows)
    sketch = SKETCH.read_text(encoding="utf-8")

    classes = re.findall(r"^class (\w+)", sketch, re.MULTILINE)
    functions = re.findall(r"^(?:String|void) (\w+)\(", sketch, re.MULTILINE)
    assert classes and functions
    for name in classes + functions:
        assert re.search(rf"\b{name}\b", named), name


def test_no_probe_rate_reboots_a_teensy_into_its_bootloader():
    """A host setting 134 baud reboots a Teensy into its bootloader
    (`cores/teensy4/usb.c`). `_diagnose_silence()` reopens at every probe
    rate, so one at 134 would turn a quiet board into a missing one."""
    assert 134 not in firmware.PROBE_BAUDRATES
