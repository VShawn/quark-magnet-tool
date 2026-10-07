import time

SUCCESS, FAIL = "成功", "失败"


class LinkResult:
    def __init__(self, index, link, status, detail=""):
        self.index = index
        self.link = link
        self.status = status
        self.detail = detail


class Orchestrator:
    def __init__(self, agent, cfg, log):
        self.agent = agent
        self.cfg = cfg
        self.log = log
        self.results = []

    def run(self, links, on_result=None):
        for i, link in enumerate(links, 1):
            self.log.info("[%d/%d] %s", i, len(links), link)
            r = self.process(i, link)
            self.results.append(r)
            if on_result:
                on_result(r)
            time.sleep(self.cfg["interval_sec"])
        return self.results

    def process(self, index, link, attempt=0):
        if attempt > 0:
            # 夸克只响应剪贴板“内容变化”：重试同一链接前先写占位内容，确保再次触发弹窗
            self.agent.set_clipboard("quark-retry-reset")
            time.sleep(0.5)
        if not self.agent.set_clipboard(link):
            return self._retry_or_fail(index, link, attempt, "剪贴板写入失败")
        popup = self.agent.wait_popup(self.cfg["popup_timeout_sec"])
        if popup is None:
            return self._retry_or_fail(index, link, attempt, "弹窗超时未出现")
        found = self.agent.find_button(popup, self.cfg["button_timeout_sec"])
        if found is None:
            p = self.agent.save_screenshot("第%d条_未知弹窗" % index)
            self.log.warning("[%d] 按钮未找到，截图: %s", index, p)
            self.agent.close_popup(popup)
            return self._retry_or_fail(index, link, attempt, "按钮未找到(未知弹窗)")
        if found["name"].startswith("error:"):
            p = self.agent.save_screenshot("第%d条_%s" % (index, found["name"]))
            self.log.warning("[%d] 错误弹窗 %s，截图: %s", index, found["name"], p)
            self.agent.close_popup(popup)
            return self._retry_or_fail(index, link, attempt, found["name"])
        self.agent.click_at(*found["screen"])
        if not self.agent.wait_popup_closed(popup, self.cfg["save_timeout_sec"]):
            p = self.agent.save_screenshot("第%d条_保存后未关闭" % index)
            self.log.warning("[%d] 点击后弹窗未关闭，截图: %s", index, p)
            self.agent.close_popup(popup)
            return self._retry_or_fail(index, link, attempt, "保存后弹窗未关闭")
        self.log.info("[%d] 成功 (%s)", index, found["name"])
        return LinkResult(index, link, SUCCESS)

    def _retry_or_fail(self, index, link, attempt, reason):
        if attempt < self.cfg["retry_times"]:
            self.log.warning("[%d] %s，重试(%d/%d)",
                             index, reason, attempt + 1, self.cfg["retry_times"])
            time.sleep(self.cfg["retry_backoff_sec"])
            return self.process(index, link, attempt + 1)
        self.log.error("[%d] 失败: %s", index, reason)
        return LinkResult(index, link, FAIL, reason)
