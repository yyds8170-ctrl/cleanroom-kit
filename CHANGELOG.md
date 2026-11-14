# 变更日志

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)，许可证 PolyForm Noncommercial 1.0.0。

## [1.4.0] - 2026-11-14

### 新增
- `crkit/version.py`：版本号单一来源（根目录 `VERSION` 文件），导出 `get_version()` 与 `VERSION_PATH`；`crkit/__init__.py::__version__` 改为派生值，不再硬编码。
- `version` 命令：输出版本号、Python 版本、平台、许可证名称；`--json` 时输出 `version / python / platform / license` 结构化字典。
- `crkit/cleanwords.py` 与 `lint` 命令：扫描源码、启动器、模板、测试与根目录 Markdown/YAML 中的禁用词，输出 PASS/FAIL 与命中文件:行号，命中即非零退出。
- 新建 `evidence/` 证据目录约定与 `evidence/v1.4.0/` 首批真实浏览器样本（example.com 截图、版本 JSON、lint 留档）。
- 4 项单元测试（版本号与 VERSION 一致、`__version__` 派生一致、整树零命中、注入样例可检出），核心测试增至 26 项。

### 修复
- 消除 `crkit/__init__.py` 版本号硬编码漂移（原硬编码 1.0.0 与 `VERSION` 1.3.0 不一致）：改为从 `VERSION` 单一来源派生，并新增一致性测试防止再次漂移。
- `lint` 首轮自检命中浏览器探测模块的常量标识符自身（含被禁厂商子串）：改中性命名，厂商路径在运行时由片段拼接，探测行为不变。
- 修复一行内出现多个禁用词时扫描器遇首个命中即中断、漏报其余的问题：改为逐模式全量记录命中，并补双向回归测试。
- 禁用词表收窄为完整全词匹配（机构名以完整词形判定），普通中文单位用词不再被误报；CLI 提示语对应位置改用 `bytes`。
- 修复 CI 端到端 `inspect` 步骤未继承浏览器路径环境变量（仅在 `shot` 步骤注入），二次启动浏览器回退到 PATH 无效候选、调试端口未就绪；`inspect` 步骤补齐同名环境变量。
- 浏览器启动就绪判定区分「进程已退出（带返回码）」与「端口未就绪」，报错给出更换端口 / 指定浏览器路径的可操作建议。

## [1.3.0] - 2026-11-10

### 新增
- `pngio.read_png_rgb` 统一归一化：灰度/RGBA/灰度+alpha 自动转 RGB，RGBA 按 alpha 合成到白底，兼容各类截图格式。
- `compare --threshold`：单像素差异判定阈值可配置（默认 20）。
- `compare --crop`：两张图尺寸不一致时裁剪到共同最小区域，而非直接报错。
- 5 项单元测试（RGBA/灰度/透明合成、裁剪对齐、阈值），核心测试增至 22 项。

### 修复
- 修正 alpha 合成公式（此前不透明像素会被错误地洗白）。
- 修复小尺寸图片在背景采样时的越界问题，采样点自动 clamp 到有效范围。

## [1.2.0] - 2026-11-10

### 新增
- 纯标准库 PNG 编码（`pngio.write_png`，zlib/struct），与解码器支持完整往返。
- `compare --diff-out` 可视化差异热图：差异像素标红、一致区域灰化，直观定位需要修正的位置。
- 4 项单元测试（PNG 往返/异常、差异热图），核心测试增至 17 项。

## [1.1.0] - 2026-11-10

### 新增
- `inspect` 取证命令（`crkit/inspect.py`）：通过 CDP 提取页面设计 token（计算样式、字体、字号、颜色、行高）、关键元素的精确 bounding box 与去重调色板，输出结构化 JSON。
- inspect 单元测试 4 项（模拟 CDP 会话，不依赖真实浏览器），核心测试增至 13 项。
- CI 端到端加入 inspect 取证验证。

### 变更
- 补全「取证 → 实现 → 对照 → 验证」闭环中的 DOM 取证环节，与文档承诺一致。

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
