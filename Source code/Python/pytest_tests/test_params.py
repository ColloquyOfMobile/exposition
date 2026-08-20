import json

from colloquy.params import PARAMS_VERSION, Params, DEFAULTS, migrate


def test_load_falls_back_to_defaults_when_file_missing(tmp_path):
    params = Params.load(tmp_path / "does_not_exist.json")
    assert params["photosensor_threashold"] == DEFAULTS["photosensor_threashold"]
    # Degrees of the bar since v2, not the 2200 servo units it was.
    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 64.453


def test_load_reads_existing_file(tmp_path):
    path = tmp_path / "params.json"
    path.write_text('{"photosensor_threashold": 42}', encoding="utf-8")
    params = Params.load(path)
    assert params["photosensor_threashold"] == 42


def test_setitem_persists_to_disk(tmp_path):
    path = tmp_path / "params.json"
    params = Params(path, {"a": 1})
    params["a"] = 2
    assert path.exists()
    assert '"a": 2' in path.read_text(encoding="utf-8")


def test_nested_dict_write_persists_too(tmp_path):
    path = tmp_path / "params.json"
    params = Params(path, {"bar": {"dxl origin": 0}})

    params["bar"]["dxl origin"] = 123

    reloaded = Params.load(path)
    assert reloaded["bar"]["dxl origin"] == 123


def test_nested_writes_wrap_dicts_as_params(tmp_path):
    path = tmp_path / "params.json"
    params = Params(path, {"bar": {"dxl origin": 0}})
    assert isinstance(params["bar"], Params)


def test_delitem_persists_to_disk(tmp_path):
    path = tmp_path / "params.json"
    params = Params(path, {"a": 1, "b": 2})
    del params["a"]

    reloaded = Params.load(path)
    assert "a" not in reloaded
    assert reloaded["b"] == 2


def test_to_dict_round_trips_nested_structure(tmp_path):
    path = tmp_path / "params.json"
    params = Params(path, {"bar": {"dxl origin": 5, "interaction_origins": {"male1": {"female1": 0}}}})

    as_dict = params.to_dict()

    assert as_dict == {"bar": {"dxl origin": 5, "interaction_origins": {"male1": {"female1": 0}}}}
    assert not isinstance(as_dict["bar"], Params)


# --- migration -----------------------------------------------------------

# A params file as it was written before the angle layer: everything in
# servo units, no version key.
V1 = {
    "photosensor_threashold": 300,
    "near_origin_threashold": 400,
    "female1": {"dxl origin": 100},
    "bar": {
        "dxl origin": 0,
        "interaction_origins": {
            "male1": {"female1": 0, "female2": 2200, "female3": 4300},
            "male2": {"female1": 6200, "female2": 8400, "female3": 10400},
        },
    },
}


def test_migrate_turns_the_bars_meeting_points_into_degrees():
    migrated = migrate(json.loads(json.dumps(V1)))

    # Through the bar's 1:3 reduction: 2200 servo units is 64.453 degrees
    # of bar, and its full travel of 10400 is 304.688.
    assert migrated["bar"]["interaction_origins"] == {
        "male1": {"female1": 0.0, "female2": 64.453, "female3": 125.977},
        "male2": {"female1": 181.641, "female2": 246.094, "female3": 304.688},
    }


def test_migrate_splits_the_near_origin_threshold_per_kind():
    migrated = migrate(json.loads(json.dumps(V1)))

    # One number of servo units for every body, kept per kind so that one
    # of them can be narrowed alone. All three are geared 1:3, so 400
    # units is the same angle for all three - the male's 35.156 in a v2
    # file was the reduction being wrong, not a wider window.
    assert migrated["near origin threshold"] == {
        "female": 11.719,
        "male": 11.719,
        "bar": 11.719,
    }
    assert "near_origin_threashold" not in migrated


def test_migrate_leaves_a_bodys_own_origin_in_servo_units():
    # It is a raw servo reading, not an angle: converting it to degrees
    # and back would move the body it calibrates.
    migrated = migrate(json.loads(json.dumps(V1)))

    assert migrated["female1"]["dxl origin"] == 100


def test_migrate_stamps_the_version():
    migrated = migrate(json.loads(json.dumps(V1)))

    assert migrated["params version"] == PARAMS_VERSION


def test_migrate_is_idempotent():
    once = migrate(json.loads(json.dumps(V1)))
    twice = migrate(json.loads(json.dumps(once)))

    assert twice == once


def test_migrate_fills_in_keys_the_file_predates():
    # A file written before a key existed used to be missing it forever -
    # load() reads the file *or* the defaults, never both - and the first
    # read raised KeyError somewhere far away.
    migrated = migrate({"params version": PARAMS_VERSION, "female1": {}})

    assert migrated["female1"]["dxl origin"] == 0
    assert migrated["arduino"]["baudrate"] == DEFAULTS["arduino"]["baudrate"]
    assert migrated["male2"] == DEFAULTS["male2"]


def test_migrate_does_not_overwrite_what_the_file_already_says():
    migrated = migrate({"params version": PARAMS_VERSION, "female1": {"dxl origin": 77}})

    assert migrated["female1"]["dxl origin"] == 77


# A params file as it stood while a male was believed to turn one for one
# with his servo: degrees already, but his are three times the angle he
# actually swept.
V2 = {
    "params version": 2,
    "male1": {"dxl origin": 0, "motion range": 175.781},
    "male2": {"dxl origin": 250, "motion range": 90.0},
    "female1": {"dxl origin": 100, "motion range": 58.594},
    "near origin threshold": {"female": 11.719, "male": 35.156, "bar": 11.719},
    "bar": {
        "dxl origin": 0,
        "motion range": 292.969,
        "interaction_origins": {"male1": {"female2": 64.453}},
    },
}


def test_migrate_divides_a_v2_males_angles_by_the_reduction_he_was_missing():
    migrated = migrate(json.loads(json.dumps(V2)))

    # The point is that he moves as he did: 175.781 degrees reached the
    # servo as 2000 units while the reduction was written as 1:1, and
    # 58.594 reaches it as 2000 now that it is 1:3. Same sway, corrected
    # description. A hand-set 90 comes down with it.
    assert migrated["male1"]["motion range"] == 58.594
    assert migrated["male2"]["motion range"] == 30.0
    assert migrated["near origin threshold"]["male"] == 11.719


def test_migrate_to_v3_leaves_every_other_body_alone():
    migrated = migrate(json.loads(json.dumps(V2)))

    # Only the male's reduction was wrong. A female, the bar, the two
    # thresholds beside his and the bar's meeting points are all angles
    # that were already right.
    assert migrated["female1"]["motion range"] == 58.594
    assert migrated["bar"]["motion range"] == 292.969
    assert migrated["near origin threshold"]["female"] == 11.719
    assert migrated["near origin threshold"]["bar"] == 11.719
    assert migrated["bar"]["interaction_origins"]["male1"]["female2"] == 64.453


def test_migrate_to_v3_leaves_a_males_own_origin_in_servo_units():
    # Raw servo units, like every other "dxl origin": it is where his
    # servo reads when he points forward, and no reduction touches it.
    migrated = migrate(json.loads(json.dumps(V2)))

    assert migrated["male2"]["dxl origin"] == 250


def test_migrate_of_a_v1_file_corrects_the_male_on_the_way_through():
    # v1 knew nothing about degrees at all, so it passes through both
    # steps: the threshold's 400 servo units become 35.156 degrees at the
    # reduction v2 believed in, then a third of that.
    migrated = migrate(json.loads(json.dumps(V1)))

    assert migrated["near origin threshold"]["male"] == 11.719
    assert migrated["male1"]["motion range"] == 58.594


def test_migrate_from_v2_is_idempotent():
    once = migrate(json.loads(json.dumps(V2)))
    twice = migrate(json.loads(json.dumps(once)))

    assert twice == once


def test_load_backs_up_a_v2_file_before_correcting_the_male(tmp_path):
    path = tmp_path / "params.json"
    path.write_text(json.dumps(V2), encoding="utf-8")

    params = Params.load(path)

    backup = tmp_path / "params.json.v2.bak"
    assert json.loads(backup.read_text()) == V2
    assert params["male1"]["motion range"] == 58.594


def test_load_backs_up_the_file_before_converting_it(tmp_path):
    # This is the calibration of a physical installation: re-deriving it
    # means going back to the rig with the bodies.
    path = tmp_path / "params.json"
    path.write_text(json.dumps(V1), encoding="utf-8")

    params = Params.load(path)

    backup = tmp_path / "params.json.v1.bak"
    assert json.loads(backup.read_text()) == V1
    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 64.453
    # And the converted file is what is now on disk.
    assert json.loads(path.read_text())["params version"] == PARAMS_VERSION


def test_load_of_an_up_to_date_file_writes_no_backup(tmp_path):
    path = tmp_path / "params.json"
    path.write_text(json.dumps(migrate(json.loads(json.dumps(V1)))), encoding="utf-8")

    Params.load(path)

    assert not list(tmp_path.glob("params.json.v*.bak"))
