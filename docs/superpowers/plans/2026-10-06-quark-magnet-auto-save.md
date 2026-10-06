# 夸克磁力链批量自动保存工具 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单文件 exe：读取 txt 磁力链，逐条复制到剪贴板，自动识别夸克网盘弹窗并点击正确保存按钮，异常重试、断点续跑、汇总报告。

**Architecture:** 四模块（link_parser / screen_agent / orchestrator / reporter）+ main 装配。screen_agent 全屏截图（DPI 感知）+ OpenCV 多尺度模板匹配定位按钮 + ctypes 剪贴板/鼠标。orchestrator 为纯状态机，通过鸭子类型 FakeAgent 做单元测试。模板已从 1.jpg/2.jpg 核对裁剪完毕（templates/ 目录，随 exe 打包，外置 templates/ 优先）。

**Tech Stack:** Python 3.11 + opencv-python-headless + numpy + pillow；测试 pytest；打包 PyInstaller --onefile。

**规格文档:** `docs/superpowers/specs/2026-10-06-quark-magnet-auto-save-design.md`

---

## 关键背景（实现者必读）

1. **模板几何（已核对，150% 缩放物理像素）：** 弹窗截图宽 1080px；标题模板位于弹窗左上角偏移 (44, 22)；× 关闭钮中心 (1047, 48)（即相对标题模板左上偏移 (1003, 26)）；btn_save 在 1.jpg (685,770)-(1065,885)；btn_speed_save 在 2.jpg (687,763)-(1055,833)。这四个模板已生成在 `templates/`，勿重新裁剪。
2. **DPI 适配：** 程序启动即 `SetProcessDpiAwareness(2)`；截图为物理像素。模板摄于 150% 屏，目标屏理论缩放 = `system_scale()/1.5`，匹配时在 ±20%（步进5%）范围多尺度尝试。
3. **Esc 无法关闭夸克弹窗**——关闭只走点右上角 ×（模板匹配，失败则按标题锚点+固定偏移几何推算）。
4. **点击决策：** btn_save 与 btn_speed_save 两个模板都算分取 argmax，只有 ≥ 阈值者才点，防止把「高速下载」点错。
5. **dev 机器约定：** Windows、100% DPI、命令用 Git Bash 语法书写但 Python/打包命令为 Windows 路径形式。
6. **每步之后必须跑测试/命令并确认输出符合 Expected 再继续；不要跳过 commit 步骤。**

---

### Task 1: 环境与项目骨架

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pytest.ini`, `tests/__init__.py`(空)

- [ ] **Step 1: 创建 `.gitignore`**

```gitignore
.venv/
__pycache__/
build/
dist/
_verify/
_crop_probe/
异常截图/
done.txt
quark_auto_save.log
main.json
磁力链.txt
磁力链测试.txt
*.egg-info/
```

- [ ] **Step 2: 创建 `requirements.txt`**

```
opencv-python-headless
numpy
pillow
pytest
pyinstaller
```

- [ ] **Step 3: 创建 `pytest.ini`**

```ini
[pytest]
addopts = -m "not manual"
testpaths = tests
markers =
    manual: 需要真实键鼠/剪贴板环境，用 -m manual 显式运行
```

- [ ] **Step 4: 创建虚拟环境并安装依赖**

Run: `cd "I:\夸克磁力链工具" && mkdir -p tests && touch tests/__init__.py && uv venv .venv --python 3.11 && uv pip install --python .venv/Scripts/python.exe -r requirements.txt`
Expected: venv 创建成功，各包安装完成无 error。

- [ ] **Step 5: pytest 空跑**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: `no tests ran`（exit code 5 属正常）。

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt pytest.ini tests templates
git commit -m "chore: 项目骨架、依赖与已核对的匹配模板"
```

---

### Task 2: link_parser 磁力链解析

**Files:**
- Create: `src/link_parser.py`
- Test: `tests/test_link_parser.py`

- [ ] **Step 1: 写失败测试 `tests/test_link_parser.py`**

```python
from link_parser import extract_links, hash_of, filter_done, read_text

A40, B32 = "a" * 40, "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def test_extract_ignores_blank_and_noise():
    text = f"第一行\n\n{A40}不是磁力链\nmagnet:?xt=urn:btih:{A40}\n垃圾\n"
    links = extract_links(text)
    assert links == [f"magnet:?xt=urn:btih:{A40}"]


def test_extract_with_tr_params_and_surrounding_text():
    line = f"标题 magnet:?xt=urn:btih:{B32}&tr=udp%3A%2F%2Fxx 后缀"
    links = extract_links(line)
    assert len(links) == 1 and links[0].startswith(f"magnet:?xt=urn:btih:{B32}")


def test_dedup_case_insensitive_keeps_first():
    text = f"magnet:?xt=urn:btih:{'A'*40}\nmagnet:?xt=urn:btih:{'a'*40}"
    assert len(extract_links(text)) == 1


def test_invalid_ignored():
    assert extract_links("magnet:?xt=urn:sha1:abc\nhttp://x.com\nbtih:123") == []


def test_hash_of_lowercase():
    assert hash_of(f"magnet:?xt=urn:btih:{'A'*40}") == "a" * 40


def test_filter_done():
    links = [f"magnet:?xt=urn:btih:{A40}", f"magnet:?xt=urn:btih:{B32.lower()}"]
    rest = filter_done(links, {A40})
    assert rest == [f"magnet:?xt=urn:btih:{B32.lower()}"]


def test_read_text_gbk(tmp_path):
    p = tmp_path / "t.txt"
    p.write_bytes(f"magnet:?xt=urn:btih:{A40}".encode("gbk"))
    assert len(extract_links(read_text(str(p)))) == 1


def test_read_text_utf8_bom(tmp_path):
    p = tmp_path / "t.txt"
    p.write_bytes(f"\ufeffmagnet:?xt=urn:btih:{A40}".encode("utf-8"))
    assert len(extract_links(read_text(str(p)))) == 1
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_link_parser.py -v`
Expected: FAIL（ModuleNotFoundError: link_parser）

- [ ] **Step 3: 实现 `src/link_parser.py`**

```python
import re

_MAGNET_RE = re.compile(r"magnet:\?xt=urn:btih:[0-9A-Za-z]{32,40}[^\s]*", re.IGNORECASE)


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_links(text):
    out, seen = [], set()
    for m in _MAGNET_RE.finditer(text):
        link = m.group(0)
        h = hash_of(link)
        if h not in seen:
            seen.add(h)
            out.append(link)
    return out


def hash_of(link):
    m = re.search(r"urn:btih:([0-9A-Za-z]{32,40})", link, re.IGNORECASE)
    return m.group(1).lower() if m else ""


def filter_done(links, done_hashes):
    return [l for l in links if hash_of(l) not in done_hashes]
```

- [ ] **Step 4: 运行测试通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_link_parser.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/link_parser.py tests/test_link_parser.py
git commit -m "feat: 磁力链提取/去重/断点过滤"
```

---

### Task 3: config 配置加载

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败测试 `tests/test_config.py`**

```python
import json
from config import DEFAULTS, load_config, default_config_path


def test_create_default_when_missing(tmp_path):
    p = str(tmp_path / "x.json")
    cfg = load_config(p)
    assert json.load(open(p, encoding="utf-8")) == DEFAULTS
    assert cfg["popup_timeout_sec"] == 20 and cfg["retry_times"] == 1


def test_merge_existing_and_drop_unknown(tmp_path):
    p = str(tmp_path / "x.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"popup_timeout_sec": 5, "bogus": 1}, f)
    cfg = load_config(p)
    assert cfg["popup_timeout_sec"] == 5 and "bogus" not in cfg


def test_default_config_path_ends_with_json():
    assert default_config_path().endswith(".json")
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: FAIL（ModuleNotFoundError: config）

- [ ] **Step 3: 实现 `src/config.py`**

```python
import json
import os
import sys

DEFAULTS = {
    "txt_path": "磁力链.txt",
    "done_file": "done.txt",
    "log_file": "quark_auto_save.log",
    "screenshot_dir": "异常截图",
    "popup_timeout_sec": 20,
    "save_timeout_sec": 30,
    "button_timeout_sec": 5,
    "retry_times": 1,
    "retry_backoff_sec": 2.0,
    "interval_sec": 2.0,
    "match_threshold": 0.8,
    "poll_interval_ms": 400,
}


def default_config_path():
    if getattr(sys, "frozen", False):
        exe = sys.executable
    else:
        exe = os.path.abspath(sys.argv[0])
    return os.path.splitext(exe)[0] + ".json"


def exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
        return dict(DEFAULTS)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    return cfg
```

- [ ] **Step 4: 运行测试通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: 同名json配置加载与默认生成"
```

---

### Task 4: reporter 日志/断点记录/汇总

**Files:**
- Create: `src/reporter.py`
- Test: `tests/test_reporter.py`

- [ ] **Step 1: 写失败测试 `tests/test_reporter.py`**

```python
from reporter import setup_logging, load_done, append_done, format_summary
from orchestrator import LinkResult, SUCCESS, FAIL


def test_done_roundtrip(tmp_path):
    p = str(tmp_path / "d.txt")
    assert load_done(p) == set()
    append_done(p, "ABC")
    append_done(p, "abc")
    assert load_done(p) == {"abc"}


def test_format_summary_lists_failures():
    rs = [LinkResult(1, "l1", SUCCESS),
          LinkResult(2, "l2", FAIL, "弹窗超时未出现")]
    s = format_summary(rs)
    assert "成功 1 条" in s and "失败 1 条" in s and "弹窗超时" in s


def test_setup_logging_writes_file(tmp_path):
    logger = setup_logging(str(tmp_path / "a.log"))
    logger.info("hello")
    assert "hello" in (tmp_path / "a.log").read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reporter.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 `src/reporter.py`**

```python
import logging
import os


def setup_logging(log_file):
    logger = logging.getLogger("quark")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def load_done(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


def append_done(path, infohash):
    with open(path, "a", encoding="utf-8") as f:
        f.write(infohash.lower() + "\n")


def format_summary(results):
    ok = [r for r in results if r.status == "成功"]
    bad = [r for r in results if r.status == "失败"]
    lines = ["========== 汇总 ==========",
             f"成功 {len(ok)} 条，失败 {len(bad)} 条"]
    for r in bad:
        lines.append(f"  第{r.index}条 [{r.detail}] {r.link}")
    return "\n".join(lines)
```

- [ ] **Step 4: 运行测试通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reporter.py -v`
Expected: 3 passed（依赖 orchestrator，故先建 `src/orchestrator.py` 最小桩：`LinkResult`/`SUCCESS`/`FAIL` 定义，Task 9 再补全）

创建最小桩 `src/orchestrator.py`：

```python
SUCCESS, FAIL = "成功", "失败"


class LinkResult:
    def __init__(self, index, link, status, detail=""):
        self.index = index
        self.link = link
        self.status = status
        self.detail = detail
```

- [ ] **Step 5: 重跑测试并 Commit**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reporter.py -v` → 3 passed

```bash
git add src/reporter.py src/orchestrator.py tests/test_reporter.py
git commit -m "feat: 日志/断点记录/汇总报告"
```

---

### Task 5: templates 模板加载器

**Files:**
- Create: `src/templates.py`
- Test: `tests/test_templates.py`

- [ ] **Step 1: 写失败测试 `tests/test_templates.py`**

```python
import cv2
import numpy as np
import pytest

import templates as T
from templates import TEMPLATE_NAMES, load_templates, _imread_gray


def _write_png(path, w=40, h=12):
    img = (np.random.default_rng(0).random((h, w)) * 255).astype(np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    path.write_bytes(buf.tobytes())


def test_imread_gray_unicode(tmp_path):
    p = tmp_path / "中文.png"
    _write_png(p)
    assert _imread_gray(str(p)).shape == (12, 40)


def test_load_internal_fallback(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    t = load_templates(str(ext))
    assert set(TEMPLATE_NAMES) <= set(t)


def test_external_overrides_internal(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    _write_png(ext / "title.png", 77, 9)
    t = load_templates(str(ext))
    assert t["title"].shape == (9, 77)


def test_error_templates_picked_up(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    _write_png(ext / "error_parse_fail.png")
    t = load_templates(str(ext))
    assert "error_parse_fail" in t


def test_missing_internal_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "resource_root", lambda: str(tmp_path / "nothing"))
    with pytest.raises(FileNotFoundError):
        load_templates(str(tmp_path / "ext2"))
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_templates.py -v`
Expected: FAIL（ModuleNotFoundError: templates）

- [ ] **Step 3: 实现 `src/templates.py`**

```python
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
```

- [ ] **Step 4: 运行测试通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_templates.py -v`
Expected: 5 passed（internal fallback 用项目根 templates/ 下真实文件）

- [ ] **Step 5: Commit**

```bash
git add src/templates.py tests/test_templates.py
git commit -m "feat: 模板加载（外置优先+内置兜底+error_*扩展）"
```

---

### Task 6: 多尺度匹配核心（纯函数）

**Files:**
- Create: `src/screen_agent.py`（本任务只含纯函数部分）
- Test: `tests/test_match.py`

- [ ] **Step 1: 写失败测试 `tests/test_match.py`**

```python
import cv2
import numpy as np

from screen_agent import match_template, scales_around


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
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_match.py -v`
Expected: FAIL（ModuleNotFoundError: screen_agent）

- [ ] **Step 3: 实现（`src/screen_agent.py` 第一部分，后续任务继续追加）**

```python
import ctypes
import os
import time

import cv2
import numpy as np
from PIL import ImageGrab

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 模板摄于150%缩放屏。弹窗几何(150%物理px)：宽1080；
# 标题模板距弹窗左上(44,22)；×中心相对标题模板左上偏移(1003,26)
POPUP_W = 1080
CLOSE_DX, CLOSE_DY = 1003, 26


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
```

- [ ] **Step 4: 运行测试通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_match.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/screen_agent.py tests/test_match.py
git commit -m "feat: 多尺度模板匹配核心"
```

---

### Task 7: ScreenAgent 基础能力（DPI/截图/剪贴板/鼠标）

**Files:**
- Modify: `src/screen_agent.py`（追加）
- Test: `tests/test_screen_basic.py`

- [ ] **Step 1: 写测试 `tests/test_screen_basic.py`**

```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_screen_basic.py -v`
Expected: FAIL（ScreenAgent 未定义）

- [ ] **Step 3: 在 `src/screen_agent.py` 追加实现**

```python
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
            if user32.OpenClipboard(0):
                try:
                    user32.EmptyClipboard()
                    buf = ctypes.create_unicode_buffer(text)
                    h = kernel32.GlobalAlloc(0x0002, ctypes.sizeof(buf))
                    p = kernel32.GlobalLock(h)
                    ctypes.memmove(p, buf, ctypes.sizeof(buf))
                    kernel32.GlobalUnlock(h)
                    user32.SetClipboardData(13, h)  # CF_UNICODETEXT
                    ok = True
                finally:
                    user32.CloseClipboard()
            if ok and self.get_clipboard_text() == text:
                return True
            time.sleep(0.3)
        return False

    def get_clipboard_text(self):
        text = None
        if user32.OpenClipboard(0):
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
```

- [ ] **Step 4: 运行自动化测试通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_screen_basic.py -v`
Expected: 2 passed, 1 deselected（manual）

- [ ] **Step 5: 手动跑点击测试（会移动真实鼠标）**

Run: `.venv/Scripts/python.exe -m pytest tests/test_screen_basic.py::test_click_moves_and_clicks -m manual -v`
Expected: 1 passed（窗口弹出 3 秒后被自动点击并关闭）

- [ ] **Step 6: Commit**

```bash
git add src/screen_agent.py tests/test_screen_basic.py
git commit -m "feat: DPI感知截图/剪贴板/鼠标点击"
```

---

### Task 8: ScreenAgent 弹窗流程 + 离线验证

**Files:**
- Modify: `src/screen_agent.py`（追加流程方法）
- Create: `tools/offline_verify.py`

- [ ] **Step 1: 在 `src/screen_agent.py` 追加弹窗流程方法**

```python
    # ---- 以下方法属于 ScreenAgent 类 ----
    def _popup_box(self, tx, ty, sc, gray):
        x = max(0, tx - int(55 * sc))
        y = max(0, ty - int(25 * sc))
        w = min(gray.shape[1] - x, int((POPUP_W + 40) * sc))
        h = min(gray.shape[0] - y, int(1060 * sc))
        return {"x": x, "y": y, "w": w, "h": h, "scale": sc,
                "title_x": tx, "title_y": ty}

    @staticmethod
    def _roi(gray, box):
        return gray[box["y"]:box["y"] + box["h"], box["x"]:box["x"] + box["w"]]

    def wait_popup(self, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            gray = self._grab()
            m = match_template(gray, self.templates["title"],
                               scales_around(self.system_scale() / 1.5))
            if m and m[0] >= self.cfg["match_threshold"]:
                score, tx, ty, _w, _h, sc = m
                return self._popup_box(tx, ty, sc, gray)
            time.sleep(self.cfg["poll_interval_ms"] / 1000.0)
        return None

    def find_button(self, popup, timeout):
        deadline = time.time() + timeout
        scales = scales_around(popup["scale"], spread=0.10)
        while time.time() < deadline:
            gray = self._grab()
            roi = self._roi(gray, popup)
            best_name, best_m = None, None
            for name in ("btn_save", "btn_speed_save"):
                m = match_template(roi, self.templates[name], scales)
                if m and (best_m is None or m[0] > best_m[0]):
                    best_name, best_m = name, m
            if best_m and best_m[0] >= self.cfg["match_threshold"]:
                score, x, y, w, h, sc = best_m
                gx, gy = popup["x"] + x + w // 2, popup["y"] + y + h // 2
                return {"name": best_name, "score": round(score, 3),
                        "screen": self.to_screen(gx, gy)}
            for name, tmpl in self.templates.items():
                if name.startswith("error_"):
                    m = match_template(roi, tmpl, scales)
                    if m and m[0] >= self.cfg["match_threshold"]:
                        return {"name": f"error:{name}", "score": round(m[0], 3),
                                "screen": None}
            time.sleep(self.cfg["poll_interval_ms"] / 1000.0)
        return None

    def wait_popup_closed(self, popup, timeout):
        deadline = time.time() + timeout
        gone, need = 0, 2
        while time.time() < deadline:
            gray = self._grab()
            m = match_template(gray, self.templates["title"],
                               scales_around(popup["scale"], spread=0.10))
            if m and m[0] >= self.cfg["match_threshold"]:
                gone = 0
            else:
                gone += 1
                if gone >= need:
                    return True
            time.sleep(self.cfg["poll_interval_ms"] / 1000.0)
        return False

    def close_popup(self, popup):
        gray = self._grab()
        m = match_template(self._roi(gray, popup), self.templates["btn_close_x"],
                           scales_around(popup["scale"], spread=0.10))
        if m and m[0] >= self.cfg["match_threshold"] - 0.05:
            _s, x, y, w, h, _sc = m
            gx, gy = popup["x"] + x + w // 2, popup["y"] + y + h // 2
        else:  # 几何推算：×中心相对标题模板左上固定偏移
            gx = popup["title_x"] + int(CLOSE_DX * popup["scale"])
            gy = popup["title_y"] + int(CLOSE_DY * popup["scale"])
        sx, sy = self.to_screen(gx, gy)
        self.click_at(sx, sy)
        time.sleep(1.0)

    def save_screenshot(self, tag):
        os.makedirs(self.cfg["screenshot_dir"], exist_ok=True)
        path = os.path.join(self.cfg["screenshot_dir"],
                            time.strftime("%Y%m%d_%H%M%S") + f"_{tag}.png")
        if self._last_bgr is None:
            self._grab()
        ok, buf = cv2.imencode(".png", self._last_bgr)
        with open(path, "wb") as f:
            f.write(buf.tobytes())
        return path
```

- [ ] **Step 2: 跑既有测试确认无回归**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: 全部 passed（新增方法不影响既有用例）

- [ ] **Step 3: 创建 `tools/offline_verify.py`（对 1.jpg/2.jpg 跑生产匹配代码）**

```python
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
scales = scales_around(1 / 1.5)  # 本机100%屏，模板来自150%

for img_name in ("1.jpg", "2.jpg"):
    img = _imread_gray(os.path.join(ROOT, img_name))
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
```

- [ ] **Step 4: 运行离线验证**

Run: `.venv/Scripts/python.exe tools/offline_verify.py`
Expected 控制台输出：
- 1.jpg：`title` score≥0.95；`btn_save` score≥0.9；`btn_speed_save` score明显更低（<0.8）；`btn_close_x` score≥0.75
- 2.jpg：`title` score≥0.95；`btn_speed_save` score≥0.9；`btn_save` score更低；`btn_close_x` score≥0.75
- **关键判据：每张图中 argmax 按钮与该图应点的按钮一致**（1.jpg→btn_save，2.jpg→btn_speed_save）

- [ ] **Step 5: 目视核对标注图**

Read `_verify/verify_1.jpg.png` 与 `_verify/verify_2.jpg.png`（绿框=分数≥0.8）。
确认：绿框分别套在标题、正确按钮、×上；无红框套在正确目标上。
若按钮框偏移到错误按钮：调整 `templates/*.png` 裁剪（只保留主文字行区域，去掉副标题），重跑本步。

- [ ] **Step 6: Commit**

```bash
git add src/screen_agent.py tools/offline_verify.py
git commit -m "feat: 弹窗检测/按钮定位/关闭/截图与离线验证工具"
```

---

### Task 9: orchestrator 状态机

**Files:**
- Modify: `src/orchestrator.py`（在 Task 4 桩基础上补全）
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: 写失败测试 `tests/test_orchestrator.py`**

```python
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
    rs = run_one(a)
    assert [r.status for r in rs] == [SUCCESS, FAIL]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_orchestrator.py -v`
Expected: 多数 FAIL（Orchestrator 无 run/process）

- [ ] **Step 3: 补全 `src/orchestrator.py`（保留 Task 4 的 LinkResult/SUCCESS/FAIL）**

```python
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
```

- [ ] **Step 4: 全量测试通过**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: 全部 passed（含 Task 4 reporter 测试，仍引用 LinkResult）

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: 主流程状态机（重试1次后跳过）"
```

---

### Task 10: main 入口装配

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: 实现 `src/main.py`**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, default_config_path, exe_dir
from link_parser import extract_links, filter_done, hash_of, read_text
from orchestrator import SUCCESS, Orchestrator
from reporter import append_done, format_summary, load_done, setup_logging
from screen_agent import ScreenAgent, enable_dpi_awareness
from templates import load_templates


def main():
    enable_dpi_awareness()
    cfg = load_config(default_config_path())
    log = setup_logging(cfg["log_file"])

    txt = sys.argv[1] if len(sys.argv) > 1 else cfg["txt_path"]
    if not os.path.exists(txt):
        print(f"未找到磁力链文件: {txt}")
        print("用法：将 磁力链.txt 与本程序放同一目录后双击运行；"
              "或将 txt 文件直接拖到程序图标上。")
        input("按回车退出...")
        sys.exit(1)

    links = extract_links(read_text(txt))
    if not links:
        print(f"{txt} 中没有有效的磁力链")
        input("按回车退出...")
        sys.exit(1)

    done = load_done(cfg["done_file"])
    todo = filter_done(links, done)
    log.info("共 %d 条磁力链，已完成跳过 %d 条，本次待处理 %d 条",
             len(links), len(links) - len(todo), len(todo))
    if not todo:
        print("所有磁力链均已处理完成（记录见 %s）" % cfg["done_file"])
        input("按回车退出...")
        return

    templates = load_templates(os.path.join(exe_dir(), "templates"))
    agent = ScreenAgent(cfg, templates)
    orch = Orchestrator(agent, cfg, log)

    def on_result(r):
        if r.status == SUCCESS:
            append_done(cfg["done_file"], hash_of(r.link))

    log.info("开始处理：请勿遮挡屏幕、勿移动鼠标；Ctrl+C 可停止。")
    try:
        results = orch.run(todo, on_result)
    except KeyboardInterrupt:
        results = orch.results
        print("\n已手动中断，以下是已完成部分的汇总。")
    print(format_summary(results))
    input("按回车退出...")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 冒烟——无txt时的提示路径**

Run: `cd "I:\夸克磁力链工具" && echo "" | .venv/Scripts/python.exe src/main.py 不存在的文件.txt`
Expected: 打印"未找到磁力链文件"、"用法…"，然后退出；同时生成 `main.json`（默认配置）。检查 `cat main.json` 内容与 DEFAULTS 一致。

- [ ] **Step 3: 冒烟——空链接文件**

Run: `printf "abc\n123\n" > _empty.txt && echo "" | .venv/Scripts/python.exe src/main.py _empty.txt`
Expected: 打印"没有有效的磁力链"并退出。完成后 `rm _empty.txt`。

- [ ] **Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: 入口装配（拖拽/断点/汇总/Ctrl+C）"
```

---

### Task 11: 模拟弹窗端到端测试

**Files:**
- Create: `tools/mock_dialog.py`, `磁力链测试.txt`（本地，已被 gitignore）

- [ ] **Step 1: 创建 `tools/mock_dialog.py`（按 150%→100% 缩放显示弹窗图）**

```python
import sys
import tkinter as tk
from PIL import Image, ImageTk

path = sys.argv[1]
delay = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2 / 3  # 150%图→100%屏

root = tk.Tk()
root.attributes("-fullscreen", True)
root.attributes("-topmost", True)
root.configure(bg="white")


def show():
    img = Image.open(path)
    if abs(scale - 1.0) > 1e-6:
        img = img.resize((int(img.width * scale), int(img.height * scale)),
                         Image.LANCZOS)
    ph = ImageTk.PhotoImage(img)
    cv = tk.Canvas(root, width=root.winfo_screenwidth(),
                   height=root.winfo_screenheight(), bg="white",
                   highlightthickness=0)
    cv.pack()
    x = (root.winfo_screenwidth() - img.width) // 2
    y = (root.winfo_screenheight() - img.height) // 2
    cv.create_image(x, y, image=ph, anchor="nw")
    root._img = ph  # 防 GC
    cv.bind("<Button-1>", on_click)


def on_click(e):
    print(f"MOCK_CLICK x={e.x} y={e.y}", flush=True)
    root.destroy()


root.after(int(delay * 1000), show)
root.mainloop()
```

- [ ] **Step 2: 准备测试 txt（本地文件，不入库）**

Run: `printf 'magnet:?xt=urn:btih:%s\n' "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" > 磁力链测试.txt`
（第二条测试用 40 个 b；第三条用 40 个 c）

- [ ] **Step 3: 端到端——模拟弹窗1（未缓存场景）**

前提：**关闭夸克网盘客户端**。
终端A：`.venv/Scripts/python.exe tools/mock_dialog.py 1.jpg 2`
终端B：`echo "" | .venv/Scripts/python.exe src/main.py 磁力链测试.txt`
Expected：
- B 端日志显示弹窗检测→`成功 (btn_save)`→汇总"成功 1 条"
- A 端打印 `MOCK_CLICK x=... y=...` 后窗口关闭，且点击坐标落在缩放后的深色按钮区域内（约 x∈[455,712], y∈[510,593]，1080 图缩放 2/3 后按钮区 (683,766)-(1067,889)×2/3）
- 生成 `done.txt` 含一行 40 个 a

- [ ] **Step 4: 端到端——模拟弹窗2（已缓存场景）**

换 40 个 b 的链接追加进 磁力链测试.txt，重跑 Step 3 两终端命令（mock 用 `2.jpg`）。
Expected: `成功 (btn_speed_save)`；done.txt 追加一行 40 个 b。

- [ ] **Step 5: 断点续跑验证**

再次运行 B 端命令（不重启 mock 也可：直接运行，等待超时前 Ctrl+C）。
Expected: 日志显示"已完成跳过 2 条"，无待处理则提示"所有磁力链均已处理完成"。

- [ ] **Step 6: 清理并 Commit**

Run: `rm done.txt 磁力链测试.txt quark_auto_save.log main.json; rm -rf 异常截图`

```bash
git add tools/mock_dialog.py
git commit -m "test: 模拟弹窗端到端验证工具"
```

---

### Task 12: PyInstaller 打包与 exe 验证

**Files:**
- Create: `build.bat`, `使用说明.md`

- [ ] **Step 1: 创建 `build.bat`**

```bat
@echo off
cd /d "%~dp0"
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --console ^
  --name 夸克磁力链工具 ^
  --paths src ^
  --add-data "templates;templates" ^
  src\main.py
echo.
echo 产物: dist\夸克磁力链工具.exe
pause
```

- [ ] **Step 2: 打包**

Run: `cd "I:\夸克磁力链工具" && cmd //c build.bat < NUL`
Expected: `Building EXE ... completed successfully.`，生成 `dist/夸克磁力链工具.exe`。

- [ ] **Step 3: exe 冒烟——独立目录运行**

把 exe 复制到临时目录（如 `%TEMP%\quarktest`），放入一条 40 个 d 的 `磁力链测试.txt`，双击或命令行运行。
Expected: 生成同名 `夸克磁力链工具.json`（默认配置）；读取到 1 条链接后开始等待弹窗（日志出现"开始处理"）；Ctrl+C 或关窗可中断并打印空汇总。
确认后删除临时目录。

- [ ] **Step 4: exe 端到端——模拟弹窗**

同 Task 11 步骤，但终端B运行 `dist\夸克磁力链工具.exe 磁力链测试.txt`（mock 终端A不变）。
Expected: `成功 (btn_save)`；done.txt 写入。再跑一次 2.jpg 场景 Expected `成功 (btn_speed_save)`。

- [ ] **Step 5: 创建 `使用说明.md`**

```markdown
# 夸克磁力链批量自动保存工具

## 准备
1. 夸克网盘 PC 客户端已登录，且开启了"检测剪贴板磁力链自动弹窗"。
2. 把 `夸克磁力链工具.exe` 和 `磁力链.txt` 放在同一目录。

## 使用
- 双击 `夸克磁力链工具.exe`；或把 txt 直接拖到 exe 图标上。
- 程序逐条复制磁力链 → 等夸克弹窗 → 自动点保存按钮。
- 运行期间**不要遮挡屏幕、不要动鼠标**；按 Ctrl+C 可随时停止。

## 文件说明
- `夸克磁力链工具.json`：配置（首次运行自动生成，超时/重试/阈值可改）。
- `done.txt`：已成功保存的链接记录；重新运行自动跳过它们（删掉即全量重跑）。
- `quark_auto_save.log`：运行日志。
- `异常截图/`：出现异常时的自动截图，供排查。

## 弹窗兼容
若夸克更新导致界面变化、程序找不到按钮：把新弹窗截图发给开发者重新裁剪模板，
或将新模板 png 命名为 `title.png` / `btn_save.png` / `btn_speed_save.png` /
`btn_close_x.png` 放到 exe 旁的 `templates\` 目录即可（无需重新打包）。
错误弹窗截图可命名为 `error_xxx.png` 放入 `templates\`，程序识别到会直接按失败处理。

## 已知限制
- 运行期间需要屏幕可见（图像识别方案固有约束）。
- 多显示器场景以系统主屏 DPI 计算缩放。
```

- [ ] **Step 6: 全量回归 + Commit**

Run: `.venv/Scripts/python.exe -m pytest -v` → 全部 passed

```bash
git add build.bat 使用说明.md
git commit -m "build: PyInstaller单文件打包与使用说明"
```

---

## 验收清单（对照需求）

- [ ] txt 按行读取，空行/非磁力链行被忽略（Task 2 测试）
- [ ] 两种弹窗分别点「保存至夸克网盘」/「极速保存至夸克网盘」（Task 8 离线 + Task 11/12 端到端）
- [ ] 4K+150% 模板在 1920+100% 机器可用（多尺度匹配，Task 11 mock 按 2/3 缩放模拟）
- [ ] 同名 json 配置（Task 3、Task 12 冒烟）
- [ ] 独立 exe（Task 12）
- [ ] 保存失败/解析失败容错：重试1次→跳过→汇总（Task 9 测试 + error_* 模板机制）
- [ ] 断点续跑 done.txt（Task 11 Step 5）
- [ ] git 记录完整（每个 Task 至少一个 commit）
