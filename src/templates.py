import glob
import os
import sys

import cv2
import numpy as np

TEMPLATE_NAMES = ["title", "btn_save", "btn_speed_save", "btn_close_x"]


def _imread_gray(path):
    # cv2.imread 不支持非 ASCII 路径，统一走 bytes 解码
    with open(path, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)


def _imwrite_png(path, bgr):
    ok, buf = cv2.imencode(".png", bgr)
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def resource_root():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_templates(external_dir):
    out = {}
    internal_dir = os.path.join(resource_root(), "templates")
    missing = []
    for name in TEMPLATE_NAMES:
        img = None
        for d in (external_dir, internal_dir):
            p = os.path.join(d, name + ".png")
            if os.path.exists(p):
                img = _imread_gray(p)
                break
        if img is None:
            missing.append(name)
        else:
            out[name] = img
    if missing:
        raise FileNotFoundError(
            f"缺少模板 {missing}；查找过 {external_dir} 与 {internal_dir}")
    for p in sorted(glob.glob(os.path.join(external_dir, "error_*.png"))):
        out[os.path.splitext(os.path.basename(p))[0]] = _imread_gray(p)
    return out
