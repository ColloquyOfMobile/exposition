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

    # One number of servo units for every body meant a much wider window
    # for a male than for a female; the migration keeps both exactly as
    # they were rather than picking one.
    assert migrated["near origin threshold"] == {
        "female": 11.719,
        "male": 35.156,
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

    assert not (tmp_path / "params.json.v2.bak").exists()
