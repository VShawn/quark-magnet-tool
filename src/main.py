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
