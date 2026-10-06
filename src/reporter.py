import logging
import os

from orchestrator import FAIL, SUCCESS


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
    ok = [r for r in results if r.status == SUCCESS]
    bad = [r for r in results if r.status == FAIL]
    lines = ["========== 汇总 ==========",
             f"成功 {len(ok)} 条，失败 {len(bad)} 条"]
    for r in bad:
        lines.append(f"  第{r.index}条 [{r.detail}] {r.link}")
    return "\n".join(lines)
