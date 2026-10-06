import cv2
import numpy as np
import pytest

import templates as T
from templates import TEMPLATE_NAMES, load_templates, _imread_gray


def _write_png(path, w=40, h=12):
    img = (np.random.default_rng(0).random((h, w)) * 255).astype(np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    path.write_bytes(buf.tobytes())


def test_imread_gray_unicode(tmp_path):
    p = tmp_path / "中文.png"
    _write_png(p)
    assert _imread_gray(str(p)).shape == (12, 40)


def test_load_internal_fallback(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    t = load_templates(str(ext))
    assert set(TEMPLATE_NAMES) <= set(t)


def test_external_overrides_internal(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    _write_png(ext / "title.png", 77, 9)
    t = load_templates(str(ext))
    assert t["title"].shape == (9, 77)


def test_error_templates_picked_up(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    _write_png(ext / "error_parse_fail.png")
    t = load_templates(str(ext))
    assert "error_parse_fail" in t


def test_missing_internal_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "resource_root", lambda: str(tmp_path / "nothing"))
    with pytest.raises(FileNotFoundError):
        load_templates(str(tmp_path / "ext2"))
