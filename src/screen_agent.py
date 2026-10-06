import ctypes
import ctypes.wintypes
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
kernel32.GlobalFree.restype = ctypes.c_void_p
kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.wintypes.BOOL
user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]


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


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        user32.SetProcessDPIAware()


class ScreenAgent:
    def __init__(self, cfg, templates):
        self.cfg = cfg
        self.templates = templates
        self._origin = (user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
                        user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        self._size = (user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
                      user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        self._last_bgr = None

    def system_scale(self):
        try:
            dpi = user32.GetDpiForSystem()
        except Exception:
            dpi = 96
        return dpi / 96.0

    def _grab(self):
        x, y = self._origin
        w, h = self._size
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        self._last_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return self._last_bgr

    def to_screen(self, gx, gy):
        return self._origin[0] + gx, self._origin[1] + gy

    # ---- 剪贴板 ----
    def set_clipboard(self, text, retries=3):
        for _ in range(retries):
            ok = False
            if user32.OpenClipboard(None):
                try:
                    user32.EmptyClipboard()
                    buf = ctypes.create_unicode_buffer(text)
                    h = kernel32.GlobalAlloc(0x0002, ctypes.sizeof(buf))
                    p = kernel32.GlobalLock(h)
                    ctypes.memmove(p, buf, ctypes.sizeof(buf))
                    kernel32.GlobalUnlock(h)
                    # 成功后系统接管h；失败则仍归我们所有，须GlobalFree防泄漏
                    if user32.SetClipboardData(13, h):  # CF_UNICODETEXT
                        ok = True
                    else:
                        kernel32.GlobalFree(h)
                finally:
                    user32.CloseClipboard()
            if ok and self.get_clipboard_text() == text:
                return True
            time.sleep(0.3)
        return False

    def get_clipboard_text(self):
        text = None
        if user32.OpenClipboard(None):
            try:
                h = user32.GetClipboardData(13)  # CF_UNICODETEXT
                if h:
                    p = kernel32.GlobalLock(h)
                    if p:
                        text = ctypes.wstring_at(p)
                        kernel32.GlobalUnlock(h)
            finally:
                user32.CloseClipboard()
        return text

    # ---- 鼠标 ----
    def click_at(self, x, y):
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.1)
        for flag in (0x0002, 0x0004):  # LEFTDOWN, LEFTUP
            inp = _INPUT(type=0)
            inp.mi = _MOUSEINPUT(0, 0, 0, flag, 0, 0)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
            time.sleep(0.05)
