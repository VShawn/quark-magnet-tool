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
