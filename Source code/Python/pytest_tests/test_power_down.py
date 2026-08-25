"""Stopping the installation without losing where anything is.

Every servo runs in extended position mode, where the count of whole
turns lives in volatile memory. The bar's travel is 293 degrees of bar,
which is 2.4 turns of its servo, so a bar powered down at the far end
comes back believing it is somewhere else and its calibration is a lie.
Homing before the power can go is what prevents that, and the order
matters: torque cut before the move would leave everything where it
stood.

The other half is the exception. An **emergency stop must never home** -
commanding more movement is the opposite of what it is for - and that
distinction is the whole reason these two are tested side by side.

Called unbound against doubles (see conftest): the real Colloquy reaches
for params on disk and a servo bus.
"""
from types import SimpleNamespace

from colloquy import HOMING_TIMEOUT, Colloquy


def make_colloquy(arrived=True):
    """A double recording the order of the power-down steps."""
    done = []

    drivers = SimpleNamespace(
        bodies=SimpleNamespace(
            turn_all_bodies_origin=lambda: done.append("bodies home")
        ),
        bar=SimpleNamespace(turn_to_origin=lambda: done.append("bar home")),
        neopixels=[SimpleNamespace(off=lambda: done.append("lights off"))],
        disable_torque=lambda: done.append("torque off"),
    )

    waits = []

    def wait(timeout=30, dxls=None, should_stop=None):
        waits.append(timeout)
        done.append("waited")
        return arrived

    drivers.wait_until_everything_is_still = wait

    fake = SimpleNamespace(
        _drivers=drivers,
        shutdown=lambda: done.append("threads down"),
        join_all=lambda: done.append("joined"),
        log=lambda *a, **k: done.append("logged"),
    )
    fake.shutdown_neopixels = lambda: Colloquy.shutdown_neopixels(fake)
    fake.move_to_origin = lambda: Colloquy.move_to_origin(fake)
    fake.disable_torque = lambda: Colloquy.disable_torque(fake)
    fake.done = done
    fake.waits = waits
    return fake


# --- the orderly stop ----------------------------------------------------


def test_power_down_homes_everything_before_cutting_torque():
    """The order is the point. Torque cut first would leave every body
    wherever it happened to be, which is exactly what this exists to
    avoid."""
    fake = make_colloquy()

    assert Colloquy.power_down(fake) is True

    assert fake.done.index("bodies home") < fake.done.index("torque off")
    assert fake.done.index("bar home") < fake.done.index("torque off")
    assert fake.done.index("waited") < fake.done.index("torque off")


def test_power_down_stops_the_threads_before_moving_anything():
    # Nothing else should be commanding a body while it is being sent home.
    fake = make_colloquy()

    Colloquy.power_down(fake)

    assert fake.done.index("threads down") < fake.done.index("bodies home")
    assert fake.done.index("joined") < fake.done.index("bodies home")


def test_the_bar_is_sent_home_as_well_as_the_bodies():
    # The bar is the one that actually needs it - it spans 2.4 servo turns
    # where a body sways less than half of one - but both go.
    fake = make_colloquy()

    Colloquy.power_down(fake)

    assert "bar home" in fake.done
    assert "bodies home" in fake.done


def test_homing_waits_long_enough_for_a_full_bar_crossing():
    """A full crossing is about 32s at the profile velocity every servo is
    initialised with (20 -> 4.58 rev/min at the servo, a third of that at
    the bar). The wait used to be the 30s default, so the one case where
    homing matters most was also the one most likely to time out."""
    fake = make_colloquy()

    Colloquy.move_to_origin(fake)

    assert fake.waits == [HOMING_TIMEOUT]
    assert HOMING_TIMEOUT > 32.0


def test_a_homing_that_did_not_finish_is_reported_not_swallowed():
    """It still cuts torque - somebody is about to pull the cables either
    way - but the caller is told, because a bar that did not get home has
    lost its turn count and nobody can see that by looking at it."""
    fake = make_colloquy(arrived=False)

    assert Colloquy.power_down(fake) is False
    assert "torque off" in fake.done
    assert "logged" in fake.done


def test_a_completed_homing_says_nothing_extra():
    fake = make_colloquy(arrived=True)

    Colloquy.power_down(fake)

    assert "logged" not in fake.done


# --- and the one that must not home --------------------------------------


def test_an_emergency_stop_never_commands_a_move():
    """Commanding more movement is the opposite of an emergency stop. The
    double has no turn_to_origin at all, so reaching for one raises rather
    than passing quietly."""
    done = []
    drivers = SimpleNamespace(disable_torque=lambda: done.append("torque off"))
    fake = SimpleNamespace(
        _drivers=drivers,
        shutdown=lambda: done.append("threads down"),
    )

    Colloquy.emergency_stop(fake)

    assert done == ["torque off", "threads down"]
    assert not hasattr(drivers, "bodies")
    assert not hasattr(drivers, "bar")


def test_an_emergency_stop_cuts_torque_before_signalling_threads():
    # Torque off is the actual physical halt; the rest is bookkeeping.
    done = []
    fake = SimpleNamespace(
        _drivers=SimpleNamespace(disable_torque=lambda: done.append("torque off")),
        shutdown=lambda: done.append("threads down"),
    )

    Colloquy.emergency_stop(fake)

    assert done.index("torque off") < done.index("threads down")
