# 变更日志

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)，许可证 PolyForm Noncommercial 1.0.0。

## [1.12.0] - 2026-11-14

### 新增
- 新命令 `pipeline`：按 `--targets` 配置或 `--site` 批量执行截图 → 取证 →（可选）对照，汇总 `report.md` + `report.json`（背景一致 / 平均差 / 差异占比 / 判定 / 最重桶 / 总体 pass-fail），`--archive` 用标准库 `zipfile` 归档本轮证据。
- 新命令 `baseline save/diff`：基准截图与 compare 指标快照（纯 JSON + PNG，无数据库），回归比对标出指标超差与内容区间新增/消失项，漂移退出码 1。
- 5 项单元测试（目标配置解析、汇总聚合、快照保存读回、漂移判定、zip 归档列目录），核心测试增至 69 项。

### 修复
- 基线快照补存内容列/行区间字段，稳定样例不再误报内容变化。
- CI e2e 补 act / probe 步骤，交互动作与状态断言纳入自动化覆盖。

## [1.11.0] - 2026-11-14

### 新增
- `init --stack web|game`：新增 `templates/game/`（canvas + ES module 占位）；两栈均自带 `evidence/ tests/ js/ README.md`、CI 工作流与 `.gitignore` 骨架。
- 占位符扩充为 `{{PROJECT}} {{DESCRIPTION}} {{YEAR}} {{AUTHOR}} {{GITHUB_USER}} {{GITHUB_REPO}}`；`license --year` / `init --year` 年份可配（默认当前年），NOTICE 补 GitHub 项目 URL 行。
- 4 项单元测试（web 全骨架、game 画布与模块脚本、占位符无残留、许可证年份覆盖与 NOTICE URL），核心测试增至 64 项。

### 修复
- `compare --resize` 改为等比缩放对齐（保持宽高比、居中留边），不再拉伸变形。
- `rgba(...,50%)` 百分比 alpha 换算为 0~1。
- 取证 spacing 补采 margin / padding 主要方向，不再只取 `marginTop`。
- `act` 的 `eval` 返回值写入逐步日志 `value` 字段；补全 `screenshot` 动作 schema 文档。
- CDP 事件缓存设上限并在事件消费后清理，避免长会话内存增长。
- 归档 v1.9.0 失败样例断言报告；核实根 LICENSE / NOTICE 署名无 `NOASSERTION` 占位。

## [1.10.0] - 2026-11-14

### 新增
- 新增 `crkit/a11y.py`：WCAG 相对亮度 / 对比度公式（sRGB 分段线性化 + 0.2126/0.7152/0.0722 加权），`grade` 输出 `AAA / AA / A / fail / unverified`，复用 v1.7.0 颜色归一化。
- 新命令 `a11y`：支持 `--inspect` 报告或 `--url` 现场取证两种数据源，输出前景/背景对比度表（ratio / grade / requirement / pass）与 `passed / failed / unverified` 汇总，附带缺 alt、无名控件、缺 `lang` 清单；任一失败组合退出码 1。
- 5 项单元测试（亮度已知值、黑白 21:1、分级临界点、报告配对、不可解析标 unverified），核心测试增至 60 项。

### 修复
- 半透明颜色合成背景未知：配对层只取不透明颜色，alpha < 1 的组合标 `unverified`，不参与通过/失败计数。
- 元素级透明背景未回退 body 背景：前景/背景不可用时回退 body token 颜色后再配对分级。

## [1.9.0] - 2026-11-14

### 新增
- CDP 交互原语：`click`、`type_text`、`press_key`、`scroll_to`、`wait_for`、`eval_state`，找不到元素抛中文错误。
- 新命令 `act`：读取 JSON 动作序列（click/type/key/scroll/wait/eval/screenshot），逐步记录 `ok / elapsed_ms / error`，单步失败不中断后续。
- 新命令 `probe`：按断言 schema（文本 / 类名 / 属性 / 可见性 / 条件表达式）输出结构化 PASS/FAIL 报告，任一 FAIL 退出码 1；断言可带前置步骤，同一会话逐段核对多状态。
- 6 项单元测试（动作解析与未知 op、点击选择器、键盘事件构造、文本断言通过/失败、失败退出标识、act/probe 解析就位），核心测试增至 55 项。

### 修复
- 纯标准库闭环断在交互一环：补齐点击 / 键盘 / 输入 / 等待与断言取证，动态复刻可独立完成端到端验证。
- `Page.loadEventFired` 竞态错过：send 层缓存无 id 事件，等待加载先查缓存再监听。
- 键盘事件仅派发 window，页面监听挂在 document 时不生效：document 与 window 同时派发 keydown / keyup。

## [1.8.0] - 2026-11-14

### 新增
- 对照报告新增垂直内容范围 `content_rows_original / content_rows_rebuild`（与水平列算法对称）。
- 新增 8×6 网格分桶：每桶输出差异像素数与 `diff_ratio_pct`，定位差异集中区域。
- 新增整体判定 `verdict`：`match / minor / major`，依据差异占比与 `--max-diff` 阈值。
- `compare` 新增 `--resize`：把复刻图最近邻缩放对齐到原版尺寸，与 `--crop` 互斥（CLI 层校验）。
- 新增 `write_report_json` 与 `compare --json` 结构化报告落盘；文本报告末尾追加垂直范围、最重桶与判定结论。
- 背景采样边距做成函数参数（默认 5px）。
- 6 项单元测试（垂直范围、网格分桶、JSON 往返、resize 对齐、互斥校验、判定阈值），核心测试增至 49 项。

### 修复
- 对照只算水平内容列、报告仅终端文本、尺寸不一致只能裁剪、差异无区块定位：补垂直范围、网格分桶、JSON 报告、resize 策略与判定结论。
- 禁用词扫描范围不全：纳入 `evidence/`、`data/` 与根 `NOTICE/VERSION`。
- CI 缺合规门禁：unit job 新增 `bin/crk lint` 步骤。
- 全页截图重设度量硬编码 `mobile: False`，`--mobile --full-page` 丢失移动模拟：全页分支透传 `mobile`。
- 仓库根缺 `LICENSE` 实体：生成 PolyForm 全文 LICENSE 入库并保持徽章/NOTICE 一致。
- 页高探测异常兜底 `0×0` 静默出图：改为视口回退，仍为 0 时抛中文错误。
- ASCII 禁用词子串误报：ASCII 词加词边界，中文词保持全词包含。

## [1.7.0] - 2026-11-14

### 新增
- 新增 `crkit/colors.py` 颜色归一化：解析 `#rgb / #rrggbb / #rrggbbaa / rgb() / rgba() / oklch()`，统一输出 `{hex, alpha, space}`；oklch 标 `oklch-approx`，不可解析保留原值标 `raw`。
- 取证报告扩充 `links / images / headings / a11y / design / text` 段：链接文本与目标、图片 alt 与自然尺寸、标题大纲、无障碍清单（语言/缺 alt 图片/地标/未命名控件）、字号字重字体圆角阴影间距分桶、可见纯文本。
- `inspect` 新增 `--text-out`（纯文本大纲另存 `.txt`）与 `--max-text`（纯文本字符上限，默认 4000）。
- 7 项单元测试（颜色 hex/rgb/rgba、oklch 标注、raw 兜底、新段透传、色板归一化、JS 采集关键选择器、纯文本导出），核心测试增至 43 项。

### 修复
- 色板直接保留裸 `rgb()/rgba()/oklch()` 字符串：统一归一化为结构化 hex token，元素文字色与背景色同步处理。
- `rgb()/rgba()` 仅兼容逗号分隔：补空格分隔与斜杠 alpha 写法解析。

## [1.6.0] - 2026-11-14

### 新增
- `cdp.page_dimensions` 探测整页 `scrollWidth / scrollHeight`；`screenshot(full_page=True)` 隐藏滚动条、按整页尺寸同步设备度量并传 `captureBeyondViewport: true`。
- `shot` 新增 `--full-page` 全页长图开关与 `--widths` 逗号分隔多宽度批量出图，输出名 `<主名>-<宽度>.png`，stdout 回写实际 PNG 尺寸。
- `inspect` 新增 `--full-page` 透传；取证 JS 元素 `box.y` 叠加 `window.scrollY`，报告记录 `full_page` 标记。
- 5 项单元测试（全页参数、多宽度输出名、scrollY 坐标、长图往返尺寸、CLI 新参数解析），核心测试增至 36 项。

### 修复
- 截图只截当前视口，长页面漏掉首屏以下内容：补齐全页跨视口截图与全页坐标换算。
- 全页截图前滚动条挤压内容列：截图前隐藏滚动条。
- 非法 `--widths` 宽度（非整数 / 非正数）抛裸栈：改为中文报错并在 CLI 层统一退出码 1。

## [1.5.0] - 2026-11-14

### 新增
- `browser.port_in_use` 端口预检：启动前探测调试端口，占用时中文报错并建议更换 `--port`。
- `browser.close_session` 统一会话回收：`terminate` → 等待 3 秒 → 必要时 `kill`，再清理临时 profile；`shot`/`inspect`/`browser` 命令的 finally 全部走该路径。
- `cdp.wait_for_load`：导航在事件流中等待 `Page.loadEventFired`，超时回退兜底等待；`shot`/`inspect` 新增 `--timeout`（默认 15 秒）透传导航等待上限。
- WebSocket 续帧重组（opcode 0x0 与前一文本帧拼接）；二进制帧（0x2）抛出明确中文报错，不再静默当文本解码。
- 5 项单元测试（端口占用探测、占用端口报错、导航事件顺序、续帧重组、二进制帧报错），核心测试增至 31 项。

### 修复
- 临时 profile 目录启动后从不回收、反复运行堆积：统一在会话关闭时清理（显式指定 `user_data_dir` 时不删除）。
- 浏览器就绪超时不区分「进程已退出」与「端口未就绪」：补进程返回码判定，报错给出更换端口 / 指定浏览器路径的可操作建议。
- 大响应分片时续帧拼包失败、二进制帧被静默当文本解码：分别修复为拼接重组与明确中文报错。
- CLI 运行期异常由裸栈跟踪改为统一中文错误信息，并以退出码 1 结束。

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
