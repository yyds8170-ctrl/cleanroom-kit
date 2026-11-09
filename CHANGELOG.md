# 变更日志

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)，许可证 PolyForm Noncommercial 1.0.0。

## [1.0.0] - 2026-11-09

### 新增
- 零依赖、跨平台洁净室复刻工具包，仅用 Python 标准库。
- 纯标准库 PNG 解码（`pngio.py`，zlib）与像素对照（`compare.py`）：背景色、平均像素差、差异占比、内容列。
- 纯标准库 WebSocket（`ws.py`）与 CDP 客户端（`cdp.py`）：导航、设备模拟、精确视口截图、JS 执行。
- 跨平台浏览器探测与启动（`browser.py`），支持 Chrome/Edge/Chromium。
- 项目脚手架（`scaffold.py` + `templates/web`），内嵌 PolyForm 条款与许可证生成。
- 统一 CLI（`crk`/`crk.cmd`，无需安装）与 9 项核心测试。

### 修复
- 测试资产打包进 `tests/fixtures/`，测试完全自包含，不再依赖仓库外文件。
- 修正 CI 中 `init` 命令参数写法（位置参数与 `--dir` 区分）。
