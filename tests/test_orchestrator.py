import logging

from orchestrator import Orchestrator, SUCCESS, FAIL

CFG = {"popup_timeout_sec": 1, "save_timeout_sec": 1, "button_timeout_sec": 1,
       "retry_times": 1, "retry_backoff_sec": 0, "interval_sec": 0,
       "match_threshold": 0.8, "poll_interval_ms": 10}

POPUP = {"x": 0, "y": 0, "w": 100, "h": 100, "scale": 0.6667,
         "title_x": 5, "title_y": 5}


def btn(name="btn_save"):
    return {"name": name, "score": 0.95, "screen": (50, 50)}


def err(name="error_parse_fail"):
    return {"name": f"error:{name}", "score": 0.9, "screen": None}


class FakeAgent:
    def __init__(self):
        self.steps = []
        self.cur = None
        self.clicks, self.closes = [], []

    def step(self, clipboard=True, popup=None, button=None, closed=True):
        self.steps.append(dict(clipboard=clipboard, popup=popup,
                               button=button, closed=closed))

    def set_clipboard(self, text):
        self.cur = self.steps.pop(0)
        return self.cur["clipboard"]

    def wait_popup(self, timeout):
        return self.cur["popup"]

    def find_button(self, popup, timeout):
        return self.cur["button"]

    def click_at(self, x, y):
        self.clicks.append((x, y))

    def wait_popup_closed(self, popup, timeout):
        return self.cur["closed"]

    def close_popup(self, popup):
        self.closes.append(popup)

    def save_screenshot(self, tag):
        return f"shot_{tag}.png"


def run_one(agent, link="magnet:?xt=urn:btih:" + "a" * 40):
    log = logging.getLogger("t")
    log.addHandler(logging.NullHandler())
    return Orchestrator(agent, CFG, log).run([link])


def test_success_path_a():
    a = FakeAgent()
    a.step(popup=POPUP, button=btn("btn_save"))
    rs = run_one(a)
    assert rs[0].status == SUCCESS and a.clicks == [(50, 50)]


def test_success_path_b_speed():
    a = FakeAgent()
    a.step(popup=POPUP, button=btn("btn_speed_save"))
    rs = run_one(a)
    assert rs[0].status == SUCCESS


def test_popup_timeout_retry_then_success():
    a = FakeAgent()
    a.step(popup=None)
    a.step(popup=POPUP, button=btn())
    rs = run_one(a)
    assert rs[0].status == SUCCESS and not a.steps


def test_unknown_dialog_retries_then_fails():
    a = FakeAgent()
    a.step(popup=POPUP, button=None)
    a.step(popup=POPUP, button=None)
    rs = run_one(a)
    assert rs[0].status == FAIL and "按钮未找到" in rs[0].detail
    assert len(a.closes) == 2


def test_error_dialog_fails():
    a = FakeAgent()
    a.step(popup=POPUP, button=err())
    a.step(popup=POPUP, button=err())
    rs = run_one(a)
    assert rs[0].status == FAIL and "error:" in rs[0].detail


def test_save_not_closed_fails():
    a = FakeAgent()
    a.step(popup=POPUP, button=btn(), closed=False)
    a.step(popup=POPUP, button=btn(), closed=False)
    rs = run_one(a)
    assert rs[0].status == FAIL and "未关闭" in rs[0].detail


def test_clipboard_fail_skips_to_fail():
    a = FakeAgent()
    a.step(clipboard=False)
    a.step(clipboard=False)
    rs = run_one(a)
    assert rs[0].status == FAIL and "剪贴板" in rs[0].detail


def test_multiple_links_results_in_order():
    a = FakeAgent()
    a.step(popup=POPUP, button=btn())
    a.step(popup=POPUP, button=None)
    a.step(popup=POPUP, button=None)
    log = logging.getLogger("t")
    log.addHandler(logging.NullHandler())
    links = ["magnet:?xt=urn:btih:" + "a" * 40,
             "magnet:?xt=urn:btih:" + "b" * 40]
    rs = Orchestrator(a, CFG, log).run(links)
    assert [r.status for r in rs] == [SUCCESS, FAIL]
    assert [r.index for r in rs] == [1, 2]
