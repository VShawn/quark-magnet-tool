import ctypes
import os
import time

import cv2
import numpy as np
from PIL import ImageGrab

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79

# 模板摄于150%缩放屏。弹窗几何(150%物理px)：宽1080；
# 标题模板距弹窗左上(44,22)；×中心实测(1042,48)，相对标题模板左上偏移(998,26)
POPUP_W = 1080
CLOSE_DX, CLOSE_DY = 998, 26

# 64位Python下必须声明句柄类API的类型，否则64位指针被截断为32位导致崩溃
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def scales_around(center, spread=0.20, step=0.05):
    n = int(round(spread / step))
    return sorted({round(center * (1 + i * step), 4) for i in range(-n, n + 1)})


def match_template(gray, tmpl, scales):
    """多尺度匹配，返回 (score, x, y, w, h, scale)；无有效尺度时返回 None"""
    best = None
    th, tw = tmpl.shape
    for sc in scales:
        nw, nh = max(2, int(round(tw * sc))), max(2, int(round(th * sc)))
        if nw >= gray.shape[1] or nh >= gray.shape[0]:
            continue
        t = cv2.resize(tmpl, (nw, nh), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        if best is None or score > best[0]:
            best = (score, loc[0], loc[1], nw, nh, sc)
    return best
