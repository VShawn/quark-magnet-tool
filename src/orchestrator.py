SUCCESS, FAIL = "成功", "失败"


class LinkResult:
    def __init__(self, index, link, status, detail=""):
        self.index = index
        self.link = link
        self.status = status
        self.detail = detail
