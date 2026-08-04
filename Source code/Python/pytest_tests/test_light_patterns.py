"""colloquy.Colloquy.light_patterns is a pure, hardcoded dict - the morse-
code-like blink sequences male1/male2 use to encode identity + requested
drive state (O/P/both/neither). See CLAUDE.md's "Male blink pattern /
female pattern reading" section. Male.get_blink_pattern() (write side) and
ReadPattern._try_match() (read side, tested in
pytest_tests/female/test_read_pattern.py) both key off this same shape.
"""
from types import SimpleNamespace

from colloquy import Colloquy


def _light_patterns():
    # light_patterns is a plain @property with no dependency on self beyond
    # being called on an instance - a bare SimpleNamespace stand-in works.
    return Colloquy.light_patterns.fget(SimpleNamespace())


def test_light_patterns_has_both_males():
    patterns = _light_patterns()
    assert set(patterns.keys()) == {"male1", "male2"}


def test_each_male_has_four_drive_states():
    patterns = _light_patterns()
    for male, by_drive in patterns.items():
        assert set(by_drive.keys()) == {tuple(), ("O",), ("P",), ("O", "P")}


def test_each_sequence_is_a_10_bit_pattern():
    patterns = _light_patterns()
    for male, by_drive in patterns.items():
        for drive, sequence in by_drive.items():
            assert len(sequence) == 10
            assert all(bit in (0, 1) for bit in sequence)


def test_male1_and_male2_sequences_are_all_distinct():
    # The whole point of the encoding is that a female can tell males and
    # drive-states apart - duplicate sequences would make that impossible.
    patterns = _light_patterns()
    all_sequences = [
        sequence
        for by_drive in patterns.values()
        for sequence in by_drive.values()
    ]
    assert len(all_sequences) == len(set(all_sequences))
