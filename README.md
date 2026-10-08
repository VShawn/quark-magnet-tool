# 夸克磁力链批量自动保存工具

把文本文件里的磁力链逐条自动转存到夸克网盘的 Windows 桌面工具：复制磁力链 → 等待夸克网盘客户端自动弹窗 → 自动点击正确的保存按钮 → 记录结果，全程无需人工干预。

## 功能特性

- **批量处理**：按行读取 txt（自动忽略空行和非磁力链行），提取磁力链逐条处理
- **两种弹窗都认**：未缓存弹窗点「保存至夸克网盘」，已缓存弹窗点「极速保存至夸克网盘」；
  按钮候选做颜色校验，绝不会误点蓝色的「高速下载」
- **异常容错**：保存失败/解析失败等异常弹窗自动截图存档（`异常截图\`）、点 × 关闭、重试 1 次后跳过，结束后输出成功/失败汇总
- **断点续跑**：已成功的链接记入 `done.txt`，中断后重新运行自动跳过
- **跨 DPI 运行**：多尺度模板匹配 + 每显示器 DPI 感知，150%/175% 缩放实测可用，其他分辨率同理
- **单文件交付**：PyInstaller 打包约 67MB 的独立 exe，拷到任何 Windows 10/11 电脑即用

## 快速开始

1. 从 [Releases](../../releases) 下载 `夸克磁力链工具.exe`
2. 与 `磁力链.txt` 放同一目录，双击运行（或把 txt 拖到 exe 图标上）
3. 运行期间**不要遮挡屏幕、不要动鼠标**；Ctrl+C 随时停止

前提：夸克网盘 PC 客户端已登录，且开启"检测剪贴板磁力链自动弹窗"。详细说明（配置项、文件清单、模板替换）见 [使用说明.md](使用说明.md)。

### 常用配置（`夸克磁力链工具.json`，首次运行自动生成）

| 键 | 含义 |
|---|---|
| `popup_timeout_sec` | 等弹窗超时秒数 |
| `save_timeout_sec` | 等保存完成超时秒数 |
| `retry_times` | 失败重试次数 |
| `interval_sec` | 每条之间间隔秒数 |
| `match_threshold` | 图像匹配阈值（识别不稳可降到 0.75） |

配置改坏不必慌：程序会自动把损坏文件备份为 `.bak` 并重建默认配置。

## 从源码构建

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
build.bat          # 产物: dist\夸克磁力链工具.exe
```

依赖锁定版本见 `requirements.lock.txt`；CI 使用该锁文件保证构建可复现。

## 测试

```bash
.venv/Scripts/python.exe -m pytest -v            # 37 个单元测试（另有 1 个真机点击测试需 -m manual 显式运行）
.venv/Scripts/python.exe tools/offline_verify.py # 匹配器回归基准：真实弹窗截图上的检测决策必须全 OK
```

模拟端到端（无需夸克客户端）：先启动 `tools/mock_dialog.py 1.jpg 2` 全屏模拟弹窗，再对测试 txt 运行 `src/main.py`，程序会走完整流程并点击模拟弹窗。

> `tools/offline_verify.py` 依赖仓库根目录的 `1.jpg` / `2.jpg` / `3.jpg` 三张真实弹窗截图作回归基准（已随仓库提供，文件列表与下载路径已打码），clone 后可直接运行。

## 项目结构

```
src/
  main.py           入口装配（拖拽txt/断点/汇总/Ctrl+C）
  link_parser.py    磁力链提取/去重/断点过滤
  config.py         同名 json 配置（损坏自愈）
  reporter.py       日志/done.txt/汇总报告
  orchestrator.py   主流程状态机（重试1次后跳过）
  screen_agent.py   DPI感知截图/多尺度模板匹配/剪贴板/鼠标
  templates.py      模板加载（外置templates\优先，内置兜底，error_*.png扩展）
templates/          匹配模板（摄自真实夸克弹窗）
tools/              offline_verify 离线回归 / mock_dialog 模拟弹窗
tests/              pytest 单元测试
```

## CI/CD

`.github/workflows/build.yml`：每次 push 自动在 windows-latest 上安装锁定依赖 → 跑全部测试 → 打包 exe 并上传 artifact；**push 到 master 且构建测试全部成功时**自动发布 GitHub Release，版本号 = 提交日期 + 短 SHA（如 `v20261008-a1b2c3d`），同日多次提交靠 SHA 后缀区分。

## 已知限制

- 运行期间弹窗区域必须可见（图像识别方案的固有约束）
- 多显示器场景以系统主屏 DPI 计算模板缩放
- 夸克客户端改版导致按钮找不到时：用新弹窗截图裁剪模板，命名 `title.png` / `btn_save.png` / `btn_speed_save.png` / `btn_close_x.png` 放到 exe 旁 `templates\` 目录即可，无需重新打包；错误弹窗截图命名为 `error_xxx.png` 放入同目录可被精准识别
