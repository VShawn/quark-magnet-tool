import cv2
import numpy as np

from screen_agent import _box_is_blue, _iou, match_template, scales_around


def test_iou():
    assert _iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert _iou((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0
    assert abs(_iou((0, 0, 10, 10), (5, 0, 10, 10)) - 50.0 / 150.0) < 1e-6


def test_box_is_blue():
    dark = np.full((30, 60, 3), (63, 63, 58), np.uint8)
    blue = np.full((30, 60, 3), (255, 92, 43), np.uint8)
    assert not _box_is_blue(dark, 0, 0, 60, 30)
    assert _box_is_blue(blue, 0, 0, 60, 30)


def test_scales_around_range():
    s = scales_around(1.0, spread=0.2, step=0.05)
    assert len(s) == 9
    assert abs(s[0] - 0.8) < 1e-6 and abs(s[-1] - 1.2) < 1e-6


def test_match_finds_pasted_template():
    rng = np.random.default_rng(7)
    tmpl = (rng.random((80, 300)) * 255).astype(np.uint8)
    canvas = np.full((900, 1200), 200, np.uint8)
    sc = round(1 / 1.5, 4)
    t = cv2.resize(tmpl, (int(300 * sc), int(80 * sc)),
                   interpolation=cv2.INTER_AREA)
    canvas[300:300 + t.shape[0], 400:400 + t.shape[1]] = t
    best = match_template(canvas, tmpl, [sc])
    assert best is not None and best[0] > 0.95
    assert abs(best[1] - 400) <= 2 and abs(best[2] - 300) <= 2
    assert best[3] == t.shape[1] and best[4] == t.shape[0]


def test_match_returns_none_when_absent():
    rng = np.random.default_rng(1)
    tmpl = (rng.random((50, 120)) * 255).astype(np.uint8)
    canvas = (rng.random((600, 800)) * 255).astype(np.uint8)
    best = match_template(canvas, tmpl, [1.0])
    assert best is not None and best[0] < 0.5
