from colloquy.params import Params, DEFAULTS


def test_load_falls_back_to_defaults_when_file_missing(tmp_path):
    params = Params.load(tmp_path / "does_not_exist.json")
    assert params["photosensor_threashold"] == DEFAULTS["photosensor_threashold"]
    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 2200


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
