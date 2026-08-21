"""Unit tests for colloquy.drivers.mirror.Mirror.

Mirror is a plain Base - no thread, no loop - so it can be built against
a hand-made female that exposes what its __init__ touches: `.owner.owner
.u2d2.dxls[name]` for its servo and `.params` for its calibration. It
holds a real DXLOrigin and a real Angle, which is the point: what is
being pinned is that a mirror turns one for one with its servo (unlike
the female it belongs to, at 1:3) and reads its origin from its own
params entry.

Nothing drives a mirror yet - see the class docstring and
CODE_DOCUMENTATION section 9 - so these are about it being findable,
calibratable, and safe to leave alone on servos that may not be wired.
"""
from types import SimpleNamespace

import pytest

from colloquy.drivers.angle.conversion import REDUCTIONS
from colloquy.drivers.mirror import Mirror


def make_mirror(stub_factory, id_number=1, origin=0, position=0):
    """A mirror over a fake servo that records every transaction: `traffic`
    ends up holding a ("read", value) or ("write", value) per exchange."""
    traffic = []

    def read(request=None):
        traffic.append(("read", position))
        return position

    def write(value):
        traffic.append(("write", value))

    dxl = SimpleNamespace(
        name=f"dxl_{id_number * 2}",
        position=SimpleNamespace(read=read),
        goal_position=SimpleNamespace(read=read, write=write),
        is_moving=False,
    )
    params = {f"mirror{id_number}": {"dxl origin": origin}}
    drivers = stub_factory(u2d2=SimpleNamespace(dxls={f"mirror{id_number}": dxl}))
    female = stub_factory(
        name=f"female{id_number}",
        owner=drivers,
        params=params,
        colloquy=stub_factory(params=params),
    )
    return Mirror(owner=female, id_number=id_number), traffic, params


def test_name_carries_the_number_so_params_can_be_found(stub_factory):
    mirror, _traffic, _params = make_mirror(stub_factory, id_number=2)

    # DXLOrigin looks its value up as params[owner.name]["dxl origin"],
    # so the name is what ties this node to its calibration.
    assert mirror.name == "mirror2"


def test_it_takes_the_servo_of_its_own_number(stub_factory):
    mirror, _traffic, _params = make_mirror(stub_factory, id_number=3)

    assert mirror.dxl is mirror.owner.owner.u2d2.dxls["mirror3"]


def test_a_mirror_turns_one_for_one_with_its_servo(stub_factory):
    # Unlike the female it belongs to, which is geared 1:3.
    mirror, traffic, _params = make_mirror(stub_factory, origin=1000)

    mirror.turn_to(20)

    assert mirror.angle.reduction == REDUCTIONS["mirror"] == 1
    assert traffic == [("write", 1228)]


def test_the_angle_is_measured_from_its_own_origin(stub_factory):
    mirror, _traffic, _params = make_mirror(stub_factory, origin=1000, position=1228)

    # Within half a servo unit, which is as close as 20 degrees can be
    # expressed on a direct-drive body (0.044 degrees).
    assert mirror.angle.get() == pytest.approx(20, abs=0.05)


def test_turn_to_origin_writes_the_origin(stub_factory):
    mirror, traffic, _params = make_mirror(stub_factory, origin=734)

    mirror.turn_to_origin()

    assert traffic == [("write", 734)]


def test_calibrating_stores_where_the_servo_is_now(stub_factory):
    mirror, _traffic, params = make_mirror(stub_factory, origin=0, position=1234)

    mirror.set_current_position_as_dxl_origin()

    assert params["mirror1"]["dxl origin"] == 1234


def test_it_offers_angle_origin_and_the_raw_servo_on_the_page(stub_factory):
    mirror, _traffic, _params = make_mirror(stub_factory)

    assert set(mirror.snapshot_children) == {"angle", "dxl origin", mirror.dxl.name}


def test_a_mirror_costs_no_bus_traffic_until_somebody_asks(stub_factory):
    # The three servos may not be wired yet. Building a mirror and showing
    # it in its female's tree must not touch the bus at all - no torque,
    # no reads, nothing to time out on. Only opening its angle node, or
    # commanding it, talks to the servo.
    mirror, traffic, _params = make_mirror(stub_factory)

    mirror.snapshot_as_child(path=("drivers", "female1", "mirror1"))

    assert traffic == []
