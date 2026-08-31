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

from colloquy.drivers import U2D2Error

import pytest

from colloquy import HOMING_TIMEOUT, Colloquy


def make_colloquy(arrived=True, port_name="COM4", motors_unplugged=False):
    """A double recording the order of the power-down steps.

    `port_name` is the U2D2's, and it is the double's way of saying
    whether this run ever opened the servo bus: `main.py` sets it in
    `open_the_hardware()`, which is skipped entirely when the main PCB is
    noted as unmounted. Pass "" for that case.
    """
    done = []

    drivers = SimpleNamespace(
        bodies=SimpleNamespace(
            turn_all_bodies_origin=lambda: done.append("bodies home")
        ),
        bar=SimpleNamespace(turn_to_origin=lambda: done.append("bar home")),
        neopixels=[SimpleNamespace(off=lambda: done.append("lights off"))],
        audio=SimpleNamespace(silence=lambda: done.append("speakers silent")),
        u2d2=SimpleNamespace(port_name=port_name, ever_opened=bool(port_name)),
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
        # What `servos_can_be_commanded` asks after `servos_were_opened`:
        # whether this run already walked the chain home and cut torque on
        # the way to it being unplugged. See hardware/motors/.
        _hardware=SimpleNamespace(
            motors=SimpleNamespace(were_unplugged_this_run=motors_unplugged)
        ),
        shutdown=lambda: done.append("threads down"),
        join_all=lambda: done.append("joined"),
        log=lambda *a, **k: done.append("logged"),
    )
    fake.shutdown_neopixels = lambda: Colloquy.shutdown_neopixels(fake)
    fake.silence_speakers = lambda: Colloquy.silence_speakers(fake)
    fake.servos_were_opened = Colloquy.servos_were_opened.fget(fake)
    fake.servos_can_be_commanded = Colloquy.servos_can_be_commanded.fget(fake)
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
    drivers = SimpleNamespace(
        disable_torque=lambda: done.append("torque off"),
        audio=SimpleNamespace(silence=lambda: done.append("speakers silent")),
        u2d2=SimpleNamespace(port_name="COM4", ever_opened=True),
    )
    fake = SimpleNamespace(
        _drivers=drivers,
        shutdown=lambda: done.append("threads down"),
    )
    fake.servos_were_opened = True
    fake.servos_can_be_commanded = True
    fake.disable_torque = lambda: Colloquy.disable_torque(fake)
    fake.silence_speakers = lambda: Colloquy.silence_speakers(fake)

    Colloquy.emergency_stop(fake)

    assert done == ["torque off", "speakers silent", "threads down"]
    assert not hasattr(drivers, "bodies")
    assert not hasattr(drivers, "bar")


def test_an_emergency_stop_cuts_torque_before_signalling_threads():
    # Torque off is the actual physical halt; the rest is bookkeeping.
    fake = emergency_double()

    Colloquy.emergency_stop(fake)

    assert fake.done.index("torque off") < fake.done.index("threads down")


# --- the sound half ------------------------------------------------------


def test_power_down_silences_every_speaker_before_the_power_can_go():
    """A body left humming is not something anybody notices from the door,
    which is exactly why it is not left to the lights' loop."""
    fake = make_colloquy()

    Colloquy.power_down(fake)

    assert fake.done.index("speakers silent") < fake.done.index("torque off")


def emergency_double(port_name="COM4", disable_torque=None):
    """The smallest double `emergency_stop` can be called against."""
    done = []
    fake = SimpleNamespace(
        _drivers=SimpleNamespace(
            disable_torque=disable_torque or (lambda: done.append("torque off")),
            audio=SimpleNamespace(silence=lambda: done.append("speakers silent")),
            u2d2=SimpleNamespace(port_name=port_name, ever_opened=bool(port_name)),
        ),
        shutdown=lambda: done.append("threads down"),
        log=lambda *a, **k: done.append("logged"),
    )
    fake.done = done
    fake._hardware = SimpleNamespace(
        motors=SimpleNamespace(were_unplugged_this_run=False)
    )
    fake.servos_were_opened = Colloquy.servos_were_opened.fget(fake)
    fake.servos_can_be_commanded = Colloquy.servos_can_be_commanded.fget(fake)
    fake.disable_torque = lambda: Colloquy.disable_torque(fake)
    fake.silence_speakers = lambda: Colloquy.silence_speakers(fake)
    return fake


def test_an_emergency_stop_silences_too():
    """It refuses to *move* anything, not to stop anything. A tone is not
    motion, and leaving five of them sounding after a red button has been
    pressed would be its own kind of alarming."""
    fake = emergency_double()

    Colloquy.emergency_stop(fake)

    assert "speakers silent" in fake.done


def test_a_dead_link_while_silencing_still_lets_the_threads_be_stopped():
    """The reason silence_speakers swallows its exception.

    Torque is cut first and the threads are signalled last, so anything
    that raises in between leaves every thread running - which is the one
    outcome an emergency stop must not have. A dead Arduino link is
    exactly when that would happen, and a dead link is also a link that is
    not making any sound.
    """
    def explode():
        raise OSError("the port is not open")

    fake = emergency_double()
    fake._drivers.audio.silence = explode

    Colloquy.emergency_stop(fake)

    assert fake.done == ["torque off", "logged", "threads down"]


# --- and the crash this whole section was rewritten after -----------------


def test_an_emergency_stop_signals_the_threads_even_if_torque_cannot_be_cut():
    """The one that arrived as a real traceback.

    `Server2.wsgi` treats any unhandled crash as an emergency stop,
    precisely so that no hardware thread is left running with no UI to
    stop it. So an emergency stop that *itself* raises before reaching
    `shutdown()` fails at the one job it was called to do - and that is
    what happened: `U2D2.open` raised a bare AssertionError on an
    installation whose main PCB was noted as unmounted, straight out of
    `disable_torque`, and every thread kept going.
    """
    done = []

    def explode():
        raise RuntimeError("the servo bus is not there")

    fake = emergency_double(disable_torque=explode)
    fake.done = done = fake.done

    with pytest.raises(RuntimeError):
        Colloquy.emergency_stop(fake)

    # It still raises - the caller re-raises to kill the HTTP loop - but
    # not before the threads have been told to stop.
    assert "threads down" in done


def test_power_down_does_not_reach_for_a_bus_that_was_never_opened():
    """The other half of the same crash. `/shutdown` on a process started
    with the main PCB noted as unmounted used to die in `U2D2.open`,
    leaving the server up and the page gone."""
    fake = make_colloquy(port_name="")

    assert Colloquy.power_down(fake) is True

    assert "bodies home" not in fake.done
    assert "bar home" not in fake.done
    assert "torque off" not in fake.done


def test_nothing_to_home_is_not_reported_as_a_failure_to_home():
    """The answer means "did everything get home". Returning False for a
    bus that was never opened would print the warning about a bar that
    has lost its turn count - about a bar that was never powered."""
    fake = make_colloquy(port_name="")

    assert Colloquy.move_to_origin(fake) is True
    assert "logged" in fake.done  # it says why, rather than going quiet


def test_the_servo_check_asks_the_port_name_not_whether_it_is_open():
    """`U2D2.__enter__`/`__exit__` open and close the port around a
    transaction that finds it closed, so `is_open` flickers during normal
    running. A shutdown that consulted it could decide, on a perfectly
    healthy installation, that there were no servos to bring home."""
    flickering = SimpleNamespace(
        _drivers=SimpleNamespace(
            u2d2=SimpleNamespace(port_name="COM4", is_open=False, ever_opened=True)
        )
    )

    assert Colloquy.servos_were_opened.fget(flickering) is True


def test_a_bus_that_was_named_but_never_opened_has_nothing_to_home():
    """`main.py` sets the port name *before* opening the port, so a bus
    whose open() raised has a name and no link. That state only started
    reaching a shutdown once startup began surviving it (colloquy/startup/)
    - before, the process died and the question never came up."""
    named_but_dead = SimpleNamespace(
        _drivers=SimpleNamespace(
            u2d2=SimpleNamespace(port_name="COM4", ever_opened=False)
        )
    )

    assert Colloquy.servos_were_opened.fget(named_but_dead) is False


def test_a_servo_that_dies_during_homing_still_gets_its_torque_cut():
    """power_down() calls disable_torque *after* move_to_origin, so an
    exception escaping the homing would leave every body powered and
    standing where it stopped - which is the one outcome the whole
    sequence exists to prevent."""
    fake = make_colloquy()

    def refuse():
        raise U2D2Error("female2 is not answering")

    fake._drivers.bodies.turn_all_bodies_origin = refuse

    assert Colloquy.power_down(fake) is False
    assert "torque off" in fake.done


def test_a_light_that_will_not_go_out_does_not_stop_the_shutdown():
    """It raised inside `power_down` before a single body had been sent
    home, and inside `emergency_stop` before a single thread had been
    signalled."""
    done = []

    def explode():
        raise OSError("the Arduino is not answering")

    fake = SimpleNamespace(
        _drivers=SimpleNamespace(neopixels=[SimpleNamespace(off=explode)]),
        log=lambda *a, **k: done.append("logged"),
    )

    Colloquy.shutdown_neopixels(fake)

    assert done == ["logged"]


# --- after the motors have been unplugged --------------------------------
#
# `hardware/motors/unplug the motors` walks everything home, cuts torque
# and leaves the server running, so a /shutdown later in the same session
# meets a bus whose servos are on a bench. See colloquy/hardware/motors/.


def test_a_shutdown_after_an_unplug_does_not_command_the_absent_servos():
    """The ninety seconds is the point. HOMING_TIMEOUT is sized for the
    worst real case - the bar at the far end of a 293 degree travel - and
    spending it writing goal positions to servos in a box is the one
    outcome nobody would read as anything but a hang."""
    fake = make_colloquy(motors_unplugged=True)

    Colloquy.power_down(fake)

    assert "bodies home" not in fake.done
    assert "bar home" not in fake.done
    assert "waited" not in fake.done


def test_a_shutdown_after_an_unplug_does_not_warn_about_the_turn_count():
    """It returns True, and the difference is the whole meaning of the
    answer: the chain was walked home *before* it came off, so the
    calibration is intact. Returning False would print the warning about
    a bar that has lost its turn count about a bar that has not."""
    fake = make_colloquy(motors_unplugged=True)

    assert Colloquy.move_to_origin(fake) is True


def test_an_unplug_does_not_cost_the_lights_or_the_speakers():
    """Only the servo half of the sequence knows about the chain. A body
    left humming is still worth silencing, and the Arduino is on its own
    lead and entirely unaffected."""
    fake = make_colloquy(motors_unplugged=True)

    Colloquy.power_down(fake)

    assert "lights off" in fake.done
    assert "speakers silent" in fake.done


def test_the_bus_being_open_is_still_not_enough_on_its_own():
    """servos_were_opened and servos_can_be_commanded are two different
    facts, which is why they are two properties. The first stays True
    here - the bus really was opened this run - and only the second goes
    False."""
    fake = make_colloquy(motors_unplugged=True)

    assert fake.servos_were_opened is True
    assert fake.servos_can_be_commanded is False
