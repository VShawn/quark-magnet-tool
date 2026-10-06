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


def _write_default(path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)


def load_config(path):
    if not os.path.exists(path):
        _write_default(path)
        return dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("config json top level must be an object")
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        # 用户手改配置损坏时自愈：损坏文件留作 .bak，重新生成默认配置
        try:
            os.replace(path, path + ".bak")
        except OSError:
            pass
        _write_default(path)
        return dict(DEFAULTS)
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    return cfg
