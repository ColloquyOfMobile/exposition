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

# The footprint pins the backplane adds: the microphones, direct.
ADDED_PINS = {"D26", "D27", "D28", "D29", "D30"}

# The footprint pins the Teensy adapter leaves unconnected: the analyser's,
# since with the Teensy the analyser slot is empty.
NOT_ON_THE_ADAPTER = {"A0", "A1", "A2", "A3", "A4", "D3", "D4"}


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


def _flat():
    """The document's prose with every run of whitespace made one space,
    so a phrase can be found across a line break."""
    return re.sub(r"\s+", " ", DOCUMENT.read_text(encoding="utf-8"))


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


# --- section 2b: the computing slot is v2's footprint ---------------------


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
    """The five direct microphones. If v2 or firmware 4 used any of these
    pins, the Mega would no longer see the v2 board."""
    _, added = _table("Added pin")
    assert {row[0] for row in added} == ADDED_PINS
    assert not ADDED_PINS & set(_pins("A1"))

    sketch = SKETCH.read_text(encoding="utf-8")
    defined = {
        f"D{number}"
        for number in re.findall(r"^#define \w+ (\d+)\b", sketch, re.MULTILINE)
    }
    assert not ADDED_PINS & defined


def test_each_microphone_reaches_its_added_pin_in_body_order():
    """D26 is female1's, D30 male2's: body order, which is module order."""
    _, added = _table("Added pin")

    assert [row[1] for row in added] == [f"{body}/mic direct" for body in audio.BODIES]
    for row, body in zip(added, audio.BODIES):
        assert f"from {body}/microphone" in row[2]


# --- section 2d: the voice slots -------------------------------------------


def test_slot_n_is_body_n_and_carries_v2s_nets():
    """Pin 1 is the body's tone net, which is on the Mega pin
    `drivers/audio.py` names; pin 3 is the net v2's own build-out takes
    to the line out; and the silkscreen beside the slot names both pins
    the tone can come from, since with no shield identification the
    silkscreen is the only label a slot has."""
    _, rows = _table("Voice slot")
    footprint = _footprint()
    teensy = {row[2]: row[0] for row in _teensy_rows()}

    assert [row[1] for row in rows] == list(audio.BODIES)
    for number, (slot, body, tone, filter_out, silkscreen) in enumerate(rows):
        assert slot == f"JV{number + 1}"
        assert tone == f"{body}/tone"
        assert footprint[audio.VOICES[body]["pin"]] == tone
        assert filter_out == f"{body}/filter out"

        build_out = [
            component for component in _components()
            if set(component["pins"].values()) == {filter_out, f"{body}/line out"}
        ]
        assert [component["value"] for component in build_out] == ["100R"]

        mega = audio.VOICES[body]["pin"]
        assert silkscreen == (
            f"{slot} · {body.upper()} · MEGA {mega} · TEENSY {teensy[tone]}"
        )


# --- section 3b: the Teensy adapter ----------------------------------------


def test_no_teensy_pin_is_used_twice_and_the_led_is_left_alone():
    pins = [int(row[0]) for row in _teensy_rows()]

    assert len(pins) == len(set(pins))
    assert shields.TEENSY41_LED not in pins


def test_the_adapter_carries_every_footprint_net_but_the_analysers_once():
    """The adapter stands in for a Mega, so every net the footprint
    carries has to arrive on the Mega pin the backplane expects it on -
    except the analyser's, which a Teensy never reads."""
    footprint = {
        pin: net for pin, net in _footprint().items() if pin not in NOT_ON_THE_ADAPTER
    }
    rows = _teensy_rows()

    assert {row[1]: row[2] for row in rows} == footprint
    assert len(rows) == len(footprint)
    assert not NOT_ON_THE_ADAPTER & {row[1] for row in rows}


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
    microphones = [row for row in _teensy_rows() if row[2].endswith("/mic direct")]
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
        if "photosensor" in row[2] or row[2].endswith("/mic direct"):
            assert pin in shields.TEENSY41_ANALOG, row
            assert row[3].endswith(f"A{_a_number(pin)}"), row


def test_the_photosensors_are_divided_and_the_microphones_are_not():
    """A photosensor module can put 5 V on its line; a MAX9814 cannot pass
    2.45 V, so the microphones go direct, with only the reservoir at the
    pin (the 4.7 K is on the backplane)."""
    for row in _teensy_rows():
        if "photosensor" in row[2]:
            assert row[3].startswith("divider"), row
        if row[2].endswith("/mic direct"):
            assert row[3].startswith("direct, 1 nF"), row


def test_what_leaves_the_backplane_is_translated_and_what_stays_is_not():
    """NeoPixels, tones, aux and shutdown go to bodies and cards at 5 V;
    nothing else on the adapter is translated."""
    translated = [row for row in _teensy_rows() if row[3].startswith("translator")]
    for row in _teensy_rows():
        net = row[2]
        leaves = net.endswith(("/tone", "/driven", "aux driven")) or net == "amp shutdown"
        assert row[3].startswith("translator") == leaves, row

    # Four SN74LV4T125s, four channels each.
    assert len(translated) <= 4 * 4


def test_the_photosensors_keep_their_mega_a_numbers():
    """A5-A15 mean the same on both processors; A0-A4 are the bands on a
    Mega and the microphones themselves on the Teensy."""
    photosensors = [row for row in _teensy_rows() if "photosensor" in row[2]]

    assert len(photosensors) == 11
    for row in photosensors:
        assert row[1] == f"A{_a_number(int(row[0]))}", row


# --- section 4: the microphones, and every voltage against its reference ----


def test_the_microphone_table_is_the_datasheets_and_the_measured_part():
    datasheet = {row[0]: _numbers(row[1]) for row in _microphone_rows()}

    assert datasheet["output bias"][0] == shields.MAX9814_BIAS
    assert datasheet["swing, most it will give"][0] == shields.MAX9814_MOST_VPP
    assert datasheet["highest output"] == [shields.MAX9814_HIGHEST]


def _microphone_rows():
    lines = DOCUMENT.read_text(encoding="utf-8").splitlines()
    start = lines.index("| | Datasheet | Measured here, on the body's 5 V |")
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append(_cells(line))
    return rows


def test_nothing_reaches_a_teensy_pin_above_its_reference():
    """Section 4c, recomputed: the microphones as they come, the
    photosensors divided, each against the Teensy's fixed 3.3 V."""
    _, rows = _table("Signal")
    teensy = [row for row in rows if row[1].startswith("Teensy")]
    assert len(teensy) == 2

    microphone, photosensor = teensy
    low, high = shields.microphone_window()
    assert _numbers(microphone[3]) == pytest.approx(
        [round(low, 2), round(high, 2), shields.MAX9814_HIGHEST]
    )
    assert shields.MAX9814_HIGHEST < shields.TEENSY41_REFERENCE
    assert _numbers(microphone[4]) == [
        round(100 * shields.span_used(low, high, shields.TEENSY41_REFERENCE))
    ]

    top = shields.PHOTOSENSOR_HIGHEST * shields.PHOTOSENSOR_DIVIDER
    assert _numbers(photosensor[3]) == pytest.approx([0, round(top, 2)])
    assert top < shields.TEENSY41_REFERENCE
    assert _numbers(photosensor[4]) == [
        round(100 * shields.span_used(0, top, shields.TEENSY41_REFERENCE))
    ]
    for row in teensy:
        assert row[2] == f"{shields.TEENSY41_REFERENCE} V"


def test_the_microphone_figures_quoted_in_the_prose_are_the_computed_ones():
    text = DOCUMENT.read_text(encoding="utf-8")
    low, high = shields.microphone_window()
    counts = shields.span_used(low, high, shields.TEENSY41_REFERENCE) * shields.TEENSY41_COUNTS

    assert f"about {round(counts, -1):.0f} of its 4096 counts" in text
    assert f"a {shields.microphone_corner() / 1000:.0f} kHz first-order" in text
    spare = shields.TEENSY41_REFERENCE - shields.MAX9814_HIGHEST
    assert f"with {spare:.2f} V to spare" in text


# --- section 5a: Thomas's five are v2's filters ----------------------------


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


# --- section 5b: a card for any pitch, recomputed --------------------------


def test_the_card_table_is_the_computed_one():
    """Pitch, window, R, C and line level for every row, as `shields.py`
    values them: E24 resistors and E6 film capacitors, through-hole."""
    _, rows = _table("Card pitch")
    assert len(rows) == len(shields.CARD_PITCHES)

    for row, pitch in zip(rows, shields.CARD_PITCHES):
        ohms, farads = shields.card_values(pitch)
        window = shields.card_window(pitch)
        level = shields.square_through(
            lambda hz: shields.thomas_response(hz, ohms, farads), pitch
        ).fundamental

        assert _numbers(row[0]) == [round(pitch)]
        assert _numbers(row[1].replace("–", " ")) == [round(window.low), round(window.high)]
        assert _ohms(row[2]) == ohms
        assert _farads(row[3]) == pytest.approx(farads)
        assert _numbers(row[4]) == [round(shields.line_level_vpp(level), 2)]
        assert shields.RESISTOR_RANGE[0] <= ohms <= shields.RESISTOR_RANGE[1]
        assert farads in shields.FILM_CAPACITORS


def test_the_windows_join_with_no_gap():
    for lower, upper in zip(shields.CARD_PITCHES, shields.CARD_PITCHES[1:]):
        assert shields.card_window(upper).low <= shields.card_window(lower).high * (1 + 1e-9)


def test_the_window_figures_are_the_cards_as_built():
    """The worst level swing and the worst third harmonic over every
    card's window, to the tenth the document quotes - and at least as
    clean as Thomas's own channels."""
    windows = [shields.card_window(pitch) for pitch in shields.CARD_PITCHES]
    swing = max(window.level_swing for window in windows)
    third = max(window.third for window in windows)
    text = _flat()

    assert f"within {swing:.1f} dB" in text
    assert f"at least {-third:.1f} dB down" in text
    thomas = [
        shields.square_through(
            lambda hz: shields.thomas_response(hz, ohms, farads), shields.MEGA_PITCHES[body]
        ).third
        for body, (ohms, farads) in shields.THOMAS_CHANNELS.items()
    ]
    assert third <= max(thomas) + 0.1


def test_the_rule_is_thomas_s_own_ratio():
    """R x C puts the tone three times above the corner, which is where
    Thomas's five sit; the document quotes the constant and his range."""
    text = _flat()
    ratios = [
        shields.MEGA_PITCHES[body] / (shields.X_3DB / (2 * math.pi * ohms * farads))
        for body, (ohms, farads) in shields.THOMAS_CHANNELS.items()
    ]

    assert f"**R × C = {shields.rc_for(1.0):.3f} / f**" in text
    assert f"({min(ratios):.1f} to {max(ratios):.1f} on his five)" in text
    assert min(ratios) <= shields.TONE_OVER_CORNER <= max(ratios)


def test_every_card_puts_out_thomas_s_level():
    levels = [
        shields.line_level_vpp(
            shields.square_through(
                lambda hz: shields.thomas_response(hz, ohms, farads), shields.MEGA_PITCHES[body]
            ).fundamental
        )
        for body, (ohms, farads) in shields.THOMAS_CHANNELS.items()
    ]
    text = _flat()
    assert f"({min(levels):.2f} to {max(levels):.2f} Vpp on his five)" in text

    for pitch in shields.CARD_PITCHES:
        ohms, farads = shields.card_values(pitch)
        level = shields.line_level_vpp(
            shields.square_through(
                lambda hz: shields.thomas_response(hz, ohms, farads), pitch
            ).fundamental
        )
        assert min(levels) <= level <= max(levels), pitch


# --- section 7a: what the Teensy plays --------------------------------------


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


# --- section 7c: the port ---------------------------------------------------


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


# --- section 6: LEDs and test pins -----------------------------------------

# What each LED's net sits at, and the forward drop the currents assume.
RAILS = {"+5V": 5.0, "+12V": 12.0, "MEGA_5V": 5.0}
TONE_HIGH = 5.0
LED_DROP = 2.0


def test_eight_leds_each_at_the_current_its_resistor_gives():
    _, rows = _table("LED")
    leds = 0
    for row in rows:
        net, resistor, current = row[2], row[4], row[5]
        volts = RAILS.get(net, TONE_HIGH)
        ohms = _numbers(resistor)[0] * 1000
        assert _numbers(current)[0] == round((volts - LED_DROP) / ohms * 1000, 1), row
        leds += 5 if "TONE 5" in row[0] else 1

    assert leds == 8


def test_every_test_pin_row_has_its_own_ground():
    _, rows = _table("Board")
    for row in rows:
        assert "GND" in row[2], row
