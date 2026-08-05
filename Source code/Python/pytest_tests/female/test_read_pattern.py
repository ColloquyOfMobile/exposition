"""Unit tests for ReadPattern._try_match(), the pure-logic core of
colloquy.hardware.female.search.read_pattern.ReadPattern.

Background (see CLAUDE.md's "Male blink pattern / female pattern reading"
section): each male continuously blinks his ring in a repeating 10-step,
0.5s-per-step on/off sequence encoding his identity (male1/male2) and his
requested drive state (neither, "O", "P", or both). ReadPattern samples a
female's light sensor as a boolean over time into `self.sample_buffer` (a
deque of (timestamp, 0_or_1) tuples) and `_try_match()` tries to decode
which male + drive state she's facing by:
  1. trying several start-time offsets within one step (`offset_substeps`),
     because the sampling loop can't sustain `sample_rate` exactly and the
     resulting drift means the "true" bit boundaries aren't known a priori;
  2. for each offset, binning samples into `steps` (10) bins by majority
     vote to build a 10-bit "candidate";
  3. comparing the candidate against every (male, drive) entry in
     `self.colloquy.light_patterns`, and every circular rotation of each
     reference sequence (since a female can start sampling at any phase of
     the male's repeating blink), tolerating up to `max_mismatches` (1)
     bit differences;
  4. returning the first (male, drive) match found, or None.

ReadPattern.__init__ is inert (plain instance attributes, a
threading.Lock, an empty deque - no filesystem/serial/thread access), and
`self.colloquy` is a property that walks `self.owner.colloquy` (defined on
BaseThread), so constructing the real ReadPattern against a stub owner
whose `.colloquy` attribute exposes the real `light_patterns` dict is
sufficient to exercise `_try_match()` with zero hardware.

Test sample buffers are built by `_bits_to_sample_buffer()` below: for
each intended bit, it emits several samples spread across the *middle* of
that bit's 0.5s window (leaving an `edge_margin` gap at each edge), so
majority-vote binning reconstructs the intended bit even after the small
sub-step shift `_try_match()`'s own offset-search introduces internally.
The exact timings/parameters used here (6 samples/step, 0.05s edge
margin) were cross-checked by hand-tracing `_try_match()`'s bisect/binning
logic (see the method's docstring/body) against a full offline replica of
the algorithm before being written into these tests, including confirming
that the "no match" fixture below genuinely produces no match at *any* of
the 10 offsets `_try_match()` tries internally (a naive/sparser fixture
can produce spurious matches at large offsets, where bins straddle two
adjacent real steps) - see the mismatch sanity-check assertion in
test_no_match_returns_none_for_unrelated_pattern.
"""
from collections import deque
from types import SimpleNamespace


from colloquy import Colloquy
from colloquy.hardware.female.search.read_pattern import ReadPattern


def _light_patterns():
    # light_patterns is a plain @property with no dependency on self beyond
    # being called on an instance - a bare SimpleNamespace stand-in works
    # (same approach as pytest_tests/test_light_patterns.py).
    return Colloquy.light_patterns.fget(SimpleNamespace())


def make_read_pattern(stub_factory):
    colloquy_double = SimpleNamespace(light_patterns=_light_patterns())
    owner = stub_factory(colloquy=colloquy_double, owners=[])
    return ReadPattern(owner=owner)


def _bits_to_sample_buffer(
    bits, step_duration=0.5, samples_per_step=6, edge_margin=0.05, epsilon=0.001
):
    """Build a (timestamp, bit) sample_buffer reproducing `bits` (a 10-bit
    sequence) under ReadPattern._try_match()'s majority-vote binning.

    Samples for step i are spread evenly across the middle of that step's
    window ([edge_margin, step_duration - edge_margin) relative to the
    step's start), so they land cleanly inside a single bin even after
    the small negative shift `_try_match()`'s offset_index=0 pass applies
    (t0 = t_end - needed_duration, and t_end is set just under
    steps * step_duration below, not exactly on it).
    """
    steps = len(bits)
    samples = []
    span = step_duration - 2 * edge_margin
    for i, bit in enumerate(bits):
        for j in range(samples_per_step):
            frac = edge_margin + span * j / (samples_per_step - 1)
            samples.append((i * step_duration + frac, bit))
    # A trailing sample fixes t_end (the last buffer timestamp, which
    # _try_match() anchors its offset search on) just under one full
    # pattern length, without adding a vote to any bin (it lands exactly
    # on bin 9's exclusive upper edge).
    samples.append((steps * step_duration - epsilon, bits[-1]))
    return deque(samples)


def test_empty_buffer_returns_none(stub_factory):
    read_pattern = make_read_pattern(stub_factory)
    read_pattern.sample_buffer = deque()

    assert read_pattern._try_match() is None


def test_clean_match_returns_correct_male_and_drive(stub_factory):
    read_pattern = make_read_pattern(stub_factory)
    patterns = _light_patterns()
    bits = list(patterns["male1"][("O",)])

    read_pattern.sample_buffer = _bits_to_sample_buffer(bits)

    assert read_pattern._try_match() == ("male1", ("O",))


def test_rotated_match_returns_correct_male_and_drive(stub_factory):
    # A female can start sampling at any point in a male's repeating
    # blink cycle - _try_match() must recognize a circularly rotated
    # reference sequence just as well as an unrotated one.
    read_pattern = make_read_pattern(stub_factory)
    patterns = _light_patterns()
    ref = list(patterns["male2"][("P",)])
    rot = 3
    rotated = ref[rot:] + ref[:rot]

    read_pattern.sample_buffer = _bits_to_sample_buffer(rotated)

    assert read_pattern._try_match() == ("male2", ("P",))


def test_near_match_within_tolerance_still_matches(stub_factory):
    read_pattern = make_read_pattern(stub_factory)
    patterns = _light_patterns()
    ref = list(patterns["male1"][tuple()])
    noisy = ref.copy()
    noisy[2] = 1 - noisy[2]
    assert sum(a != b for a, b in zip(noisy, ref)) == read_pattern.max_mismatches

    read_pattern.sample_buffer = _bits_to_sample_buffer(noisy)

    assert read_pattern._try_match() == ("male1", tuple())


def _min_mismatches_to_any_pattern(candidate, patterns, steps):
    """Smallest Hamming distance from `candidate` to any (male, drive)
    reference sequence, over every circular rotation of that reference -
    mirrors the comparison _try_match() itself performs, used here only to
    sanity-check that a "no match" test fixture is genuinely unrelated to
    every real pattern."""
    best = None
    for by_drive in patterns.values():
        for ref in by_drive.values():
            ref_list = list(ref)
            for rot in range(steps):
                rotated = ref_list[-rot:] + ref_list[:-rot] if rot else ref_list
                mismatches = sum(1 for a, b in zip(candidate, rotated) if a != b)
                if best is None or mismatches < best:
                    best = mismatches
    return best


def test_no_match_returns_none_for_unrelated_pattern(stub_factory):
    read_pattern = make_read_pattern(stub_factory)
    patterns = _light_patterns()
    candidate = [0, 1, 1, 0, 1, 0, 0, 1, 1, 0]

    # Sanity-check the fixture itself is genuinely unrelated: no real
    # pattern, in any rotation, is within tolerance of this candidate.
    min_mismatches = _min_mismatches_to_any_pattern(
        candidate, patterns, read_pattern.steps
    )
    assert min_mismatches > read_pattern.max_mismatches

    read_pattern.sample_buffer = _bits_to_sample_buffer(candidate)

    assert read_pattern._try_match() is None
