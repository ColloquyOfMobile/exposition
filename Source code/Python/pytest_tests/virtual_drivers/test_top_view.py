"""The simulated room from above (colloquy.virtual_drivers.top_view and
browser.TopViewNode): where the drawing puts things, how a moving part
is tweened, and that a render never raises."""
import xml.etree.ElementTree as ET

from colloquy.params import DEFAULTS
from colloquy.virtual_drivers import top_view
from colloquy.virtual_drivers.browser import TopViewNode
from colloquy.virtual_drivers.virtual_dxl import VirtualDXL


def _body(angle=0.0, **extra):
    return {"angle": angle, "goal": angle, "next": angle, "pixels": {}, **extra}


def _scene(**overrides):
    scene = {
        "params": DEFAULTS,
        "bar": {"angle": 0.0, "goal": 0.0, "next": 0.0},
        "females": {f: _body() for f in top_view.FEMALES},
        "males": {m: _body() for m in top_view.MALES},
    }
    scene.update(overrides)
    return scene


def test_females_sit_where_the_bar_brings_male1():
    females, males = top_view.layout(DEFAULTS)
    origins = DEFAULTS["bar"]["interaction_origins"]

    assert females == origins["male1"]
    assert males["male1"] == 0


def test_male2_sits_at_the_other_end_of_the_bar():
    _, males = top_view.layout(DEFAULTS)

    # The mean of his meeting points minus hers: about half a turn back.
    assert -185 < males["male2"] < -175


def test_a_broken_layout_param_falls_back_instead_of_raising():
    females, _ = top_view.layout({"bar": {"interaction_origins": "nonsense"}})

    assert set(females) == set(top_view.FEMALES)


def test_travel_stops_at_the_goal_and_is_capped_by_speed():
    assert top_view.travel(0, 5, speed=10, seconds=1) == 5
    assert top_view.travel(0, 50, speed=10, seconds=1) == 10
    assert top_view.travel(0, -50, speed=10, seconds=1) == -10
    assert top_view.travel(3, 50, speed=0, seconds=1) == 3


def test_white_adds_to_every_channel_and_dark_is_none():
    assert top_view.pixel_colour({"r": 10, "g": 0, "b": 0, "w": 250}) == "#fffafa"
    assert top_view.pixel_colour({"r": 0, "g": 0, "b": 0, "w": 0}) is None
    assert top_view.pixel_colour("garbage") is None


def test_the_drawing_is_well_formed_svg():
    ET.fromstring(top_view.draw(_scene()))


def test_a_still_scene_has_no_tween_and_draws_the_same_twice():
    # What lets the live stream skip resending an idle room.
    assert "animateTransform" not in top_view.draw(_scene())
    assert top_view.draw(_scene()) == top_view.draw(_scene())


def test_a_moving_bar_is_tweened_to_where_it_will_be():
    scene = _scene(bar={"angle": 10.0, "goal": 100.0, "next": 19.2})

    svg = top_view.draw(scene)

    assert 'from="10 215 220" to="19.2 215 220"' in svg


def test_a_lit_ring_casts_a_beam_and_a_dark_one_does_not():
    dark = top_view.draw(_scene())
    lit = top_view.draw(
        _scene(males={"male1": _body(pixels={"ring": {"r": 0, "g": 0, "b": 0, "w": 255}}),
                      "male2": _body()})
    )

    assert 'fill-opacity="0.45"' not in dark
    assert 'fill-opacity="0.45"' in lit


def _dxl(position=0, goal=0, torque=1, velocity=20):
    dxl = VirtualDXL.__new__(VirtualDXL)
    dxl._dict = {
        "position": position,
        "goal position": goal,
        "torque enabled": torque,
        "profile velocity": velocity,
    }
    return dxl


def _states():
    states = {}
    for f in top_view.FEMALES:
        states[f] = {p: dict(r=0, g=0, b=0, w=0) for p in top_view.FEMALE_PIXELS}
        states[f].update({"light sensor": 0, "speaker": False})
    for m in top_view.MALES:
        states[m] = {p: dict(r=0, g=0, b=0, w=0) for p in top_view.MALE_PIXELS}
        states[m].update({"light sensor": {k: 0 for k in "abcd"}, "speaker": False})
    return states


def _node(stub_factory, dxls=None, params=DEFAULTS):
    dxls = dxls or [_dxl() for _ in range(10)]
    return TopViewNode(owner=stub_factory(params=params, dxls=dxls, states=_states()))


def test_the_scene_reads_angles_in_degrees_of_the_body(stub_factory):
    dxls = [_dxl() for _ in range(10)]
    # 3072 servo units is three quarters of a servo turn: at 1:3, a
    # quarter turn of the bar.
    dxls[9] = _dxl(position=3072, goal=3072)

    scene = _node(stub_factory, dxls).scene()

    assert scene["bar"]["angle"] == 90
    assert scene["bar"]["next"] == 90


def test_the_node_draws_the_room_as_an_image(stub_factory):
    states = _node(stub_factory)._snapshot_if_opened(())

    assert "<svg" in states["room"]["image"]


def test_a_param_of_the_wrong_shape_is_said_not_raised(stub_factory):
    states = _node(stub_factory, params={"bar": None})._snapshot_if_opened(())

    assert "cannot be drawn" in states["room"]["value"]


def test_a_moving_servo_is_given_where_it_will_be_next(stub_factory):
    part = _node(stub_factory)._part("bar", "bar", _dxl(0, 30000))

    # Velocity 20 is ~313 units/s, ~9.2 degrees of the bar per second.
    assert 9 < part["next"] < 9.4
    assert part["goal"] > part["next"]


def test_torque_off_means_it_will_not_move(stub_factory):
    part = _node(stub_factory)._part("bar", "bar", _dxl(0, 30000, torque=0))

    assert part["next"] == 0
