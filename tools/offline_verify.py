import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from config import DEFAULTS  # noqa: E402
from screen_agent import ScreenAgent, match_template, scales_around  # noqa: E402
from templates import load_templates, _imread_gray  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "_verify")
os.makedirs(OUT, exist_ok=True)

tpls = load_templates(os.path.join(ROOT, "templates"))
scales = scales_around(1 / 1.5)  # 100%屏的生产缩放档
runtime_scales = scales_around(0.6667, spread=0.10)  # find_button运行时档(±10%)

for img_name in ("1.jpg", "2.jpg"):
    img = _imread_gray(os.path.join(ROOT, img_name))
    # 原图是150%物理像素，模板与原图同尺度；先缩到2/3模拟100%屏再匹配
    img = cv2.resize(img, (img.shape[1] * 2 // 3, img.shape[0] * 2 // 3),
                     interpolation=cv2.INTER_AREA)
    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    print(f"== {img_name} ==")
    btn_scores = {}
    for name in ("title", "btn_save", "btn_speed_save", "btn_close_x"):
        m = match_template(img, tpls[name], scales)
        if m is None:
            print(f"  {name:15s} 无结果")
            continue
        score, x, y, w, h, sc = m
        print(f"  {name:15s} [全档±20%] score={score:.3f} scale={sc:.3f} "
              f"box=({x},{y}) {w}x{h}")
        color = (0, 200, 0) if score >= 0.8 else (0, 0, 255)
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
        if name in ("btn_save", "btn_speed_save"):
            rm = match_template(img, tpls[name], runtime_scales)
            if rm:
                btn_scores[name] = rm[0]
                rscore, rx, ry, rw, rh, rsc = rm
                print(f"  {name:15s} [运行时档] score={rscore:.3f} "
                      f"scale={rsc:.3f} box=({rx},{ry}) {rw}x{rh}")
    if len(btn_scores) == 2:
        win = max(btn_scores, key=btn_scores.get)
        margin = btn_scores[win] - min(btn_scores.values())
        verdict = "OK" if margin >= 0.03 else "分差<0.03 拒点"
        print(f"  [运行时档argmax] {win} 分差={margin:.3f} -> {verdict}")
    out = os.path.join(OUT, f"verify_{img_name}".replace(".jpg", ".png"))
    ok, buf = cv2.imencode(".png", vis)
    with open(out, "wb") as f:
        f.write(buf.tobytes())
    print(f"  标注图: {out}")


# ---- 第二部分：用真实 wait_popup/find_button 代码对真实截图做决策验证 ----
class _StaticAgent(ScreenAgent):
    """抓屏替换为静态图片；fake_scale 模拟来源机器的 DPI"""

    def __init__(self, gray, bgr, fake_scale):
        super().__init__(dict(DEFAULTS, poll_interval_ms=10), tpls)
        self._g, self._c, self._fs = gray, bgr, fake_scale

    def system_scale(self):
        return self._fs

    def _grab(self):
        self._last_bgr = self._c
        return self._g


def _imread_color(path):
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


print()
print("==== find_button decision (real code path) ====")
CASES = [
    ("1.jpg", 2 / 3, 1.0),   # 150%截图缩到2/3，模拟100%屏
    ("2.jpg", 2 / 3, 1.0),
    ("3.jpg", 1.0, 1.75),    # 175%屏原生截图
]
EXPECT = {"1.jpg": "btn_save", "2.jpg": "btn_speed_save", "3.jpg": "btn_speed_save"}
failures = 0
for img_name, resize, fake_scale in CASES:
    bgr = _imread_color(os.path.join(ROOT, img_name))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if abs(resize - 1.0) > 1e-6:
        bgr = cv2.resize(bgr, (int(bgr.shape[1] * resize), int(bgr.shape[0] * resize)),
                         interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    agent = _StaticAgent(gray, bgr, fake_scale)
    popup = agent.wait_popup(3)
    if popup is None:
        print(f"[FAIL] {img_name}: popup not found (fake_scale={fake_scale})")
        failures += 1
        continue
    btn = agent.find_button(popup, 3)
    got = btn["name"] if btn else "None"
    status = "OK" if got == EXPECT[img_name] else "FAIL"
    if status == "FAIL":
        failures += 1
    detail = f"score={btn['score']}" if btn else "no decision"
    print(f"[{status}] {img_name}: expect={EXPECT[img_name]} got={got} ({detail})")

print()
print("decision check:", "ALL OK" if failures == 0 else f"{failures} FAILED")
sys.exit(1 if failures else 0)
