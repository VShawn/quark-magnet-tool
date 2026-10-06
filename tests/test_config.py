import json
from config import DEFAULTS, load_config, default_config_path


def test_create_default_when_missing(tmp_path):
    p = str(tmp_path / "x.json")
    cfg = load_config(p)
    assert json.load(open(p, encoding="utf-8")) == DEFAULTS
    assert cfg["popup_timeout_sec"] == 20 and cfg["retry_times"] == 1


def test_merge_existing_and_drop_unknown(tmp_path):
    p = str(tmp_path / "x.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"popup_timeout_sec": 5, "bogus": 1}, f)
    cfg = load_config(p)
    assert cfg["popup_timeout_sec"] == 5 and "bogus" not in cfg


def test_default_config_path_ends_with_json():
    assert default_config_path().endswith(".json")


def test_corrupt_json_regenerates_with_backup(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{broken", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg["popup_timeout_sec"] == 20
    assert (tmp_path / "x.json.bak").read_text(encoding="utf-8") == "{broken"
    assert json.load(open(p, encoding="utf-8")) == DEFAULTS


def test_non_dict_json_regenerates(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("[]", encoding="utf-8")
    assert load_config(str(p)) == DEFAULTS
