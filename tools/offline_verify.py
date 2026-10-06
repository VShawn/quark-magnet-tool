import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2  # noqa: E402

from screen_agent import match_template, scales_around  # noqa: E402
from templates import load_templates, _imread_gray  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "_verify")
os.makedirs(OUT, exist_ok=True)

tpls = load_templates(os.path.join(ROOT, "templates"))
scales = scales_around(1 / 1.5)  # 100%屏的生产缩放档

for img_name in ("1.jpg", "2.jpg"):
    img = _imread_gray(os.path.join(ROOT, img_name))
    # 原图是150%物理像素，模板与原图同尺度；先缩到2/3模拟100%屏再匹配
    img = cv2.resize(img, (img.shape[1] * 2 // 3, img.shape[0] * 2 // 3),
                     interpolation=cv2.INTER_AREA)
    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    print(f"== {img_name} ==")
    for name in ("title", "btn_save", "btn_speed_save", "btn_close_x"):
        m = match_template(img, tpls[name], scales)
        if m is None:
            print(f"  {name:15s} 无结果")
            continue
        score, x, y, w, h, sc = m
        print(f"  {name:15s} score={score:.3f} scale={sc:.3f} box=({x},{y}) {w}x{h}")
        color = (0, 200, 0) if score >= 0.8 else (0, 0, 255)
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
    out = os.path.join(OUT, f"verify_{img_name}".replace(".jpg", ".png"))
    ok, buf = cv2.imencode(".png", vis)
    with open(out, "wb") as f:
        f.write(buf.tobytes())
    print(f"  标注图: {out}")
