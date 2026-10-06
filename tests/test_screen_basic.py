import pytest

from screen_agent import (ScreenAgent, enable_dpi_awareness, user32,
                          SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN,
                          SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN)

CFG = {"screenshot_dir": "_test_shots", "poll_interval_ms": 50}


@pytest.fixture(scope="module", autouse=True)
def _dpi():
    enable_dpi_awareness()


def make_agent():
    return ScreenAgent(CFG, {})


def test_grab_covers_virtual_screen():
    a = make_agent()
    g = a._grab()
    assert g.shape[0] == user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    assert g.shape[1] == user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)


def test_clipboard_roundtrip():
    a = make_agent()
    text = "magnet:?xt=urn:btih:" + "f" * 40
    assert a.set_clipboard(text) is True
    assert a.get_clipboard_text() == text


@pytest.mark.manual
def test_click_moves_and_clicks():
    import tkinter as tk

    hit = []
    root = tk.Tk()
    root.geometry("300x200+100+100")
    tk.Label(root, text="3秒后将自动点击本窗口").pack(expand=True)

    def on_click(e):
        hit.append((e.x, e.y))
        root.destroy()

    root.bind("<Button-1>", on_click)

    def do_click():
        a = make_agent()
        x = root.winfo_rootx() + 150
        y = root.winfo_rooty() + 100
        a.click_at(x, y)

    root.after(3000, do_click)
    root.after(8000, root.destroy)
    root.mainloop()
    assert hit, "未收到点击事件"
