# cleanroom-kit · 洁净室复刻工具包

[![ci](https://img.shields.io/github/actions/workflow/status/yyds8170-ctrl/cleanroom-kit/ci.yml?branch=main)](https://github.com/yyds8170-ctrl/cleanroom-kit/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-1.12.0-blue.svg)](#快速开始)
[![tests](https://img.shields.io/badge/tests-69%20passing-brightgreen.svg)](#测试)

一套**零依赖、跨平台、即开即用**的洁净室（clean-room）复刻工具包。它只观察目标网站或应用的**外部可见行为**，不读取其源码，帮助你独立完成「**取证 → 实现 → 对照 → 验证**」的完整闭环。

> **维护者 / Maintainer：洋洋（[yyds8170-ctrl](https://github.com/yyds8170-ctrl)）**
>
> 本工具包为独立实现，不包含任何第三方源码或二进制，与相关第三方**无隶属、无背书、无赞助关系**。仅可对你拥有或已获授权的目标使用。详见 [NOTICE](NOTICE)。

## 目录

- [特性亮点](#特性亮点)
- [零依赖与跨平台](#零依赖与跨平台)
- [快速开始](#快速开始)
- [命令清单](#命令清单)
- [标准工作流](#标准工作流)
- [目录结构](#目录结构-1)
- [示例项目](#示例项目)
- [与 craft-anything 的关系](#与-craft-anything-的关系)
- [测试](#测试)
- [许可证](#许可证)

## 特性亮点

- **零安装**：仅依赖 Python 3.8+ 标准库，无需 `pip`、Docker 或任何外部二进制。
- **DOM 取证**：一键提取设计 token、计算样式、元素精确坐标与调色板，输出结构化 JSON。
- **设备模拟**：基于标准 CDP 精确控制视口尺寸，移动端/桌面端一致。
- **量化对照**：背景色、平均像素差、差异占比、内容列位置，并可生成**差异热图**直观定位。
- **跨平台**：自动探测系统 Chrome / Edge / Chromium，三大操作系统行为一致。

## 零依赖与跨平台

- 核心仅使用 **Python 3.8+ 标准库**，无需 `pip install`、无需 Docker/Electron。
- 浏览器自动化通过标准 **Chrome DevTools Protocol** 驱动系统已装的 Chrome / Edge / Chromium，Windows、macOS、Linux 行为一致。
- 浏览器路径自动探测，也可用环境变量 `CRK_BROWSER` 显式指定。
- clone 后直接运行，无需安装：`bin/crk`（macOS/Linux）或 `bin/crk.cmd`（Windows）。

## 快速开始

```bash
# 1. 环境自检：确认 Python、浏览器与可选运行时
bin/crk doctor

# 2. 从模板创建一个新项目（自动带 LICENSE/NOTICE/VERSION）
bin/crk init my-app --desc "我的复刻项目"

# 3. 对目标页面做精确视口截图（设备模拟，自动启停浏览器）
bin/crk shot --url https://example.com --out evidence/orig.png --width 1280 --height 900

# 4. DOM 取证：提取设计 token、元素坐标与调色板（输出 JSON）
bin/crk inspect --url https://example.com --out evidence/inspect.json --width 1280 --height 900

# 5. 实现后做像素级对照，并生成差异热图（差异像素标红）
bin/crk compare --orig evidence/orig.png --rebuild evidence/rebuild.png --diff-out evidence/diff.png
```

## 命令清单

| 命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `doctor` | 环境自检 | — |
| `version` | 输出版本与运行环境信息 | `--json` |
| `lint` | 禁用词合规自检，命中即非零退出 | — |
| `init` | 从模板创建项目（web / game 栈） | `name` `--dir` `--desc` `--stack` `--author` `--github-user` `--github-repo` `--year` `--force` |
| `shot` | 设备模拟截图（支持全页长图 / 多宽度批量） | `--url` `--out` `--width` `--height` `--mobile` `--wait` `--timeout` `--full-page` `--widths` |
| `inspect` | DOM 取证（设计 token / 元素坐标 / 调色板 / 大纲 / 无障碍） | `--url` `--out` `--width` `--height` `--mobile` `--wait` `--timeout` `--full-page` `--text-out` `--max-text` |
| `act` | 按 JSON 动作序列执行交互（点击/输入/键盘/滚动/等待/截图） | `--url` `--out` `--script` `--steps` `--width` `--height` `--mobile` `--wait` `--timeout` |
| `probe` | 页面状态断言，输出结构化 PASS/FAIL 报告 | `--url` `--out` `--assertions` `--script` `--width` `--height` `--mobile` `--wait` `--timeout` |
| `a11y` | WCAG 对比度与无障碍清单检查（AA/AAA 分级） | `--inspect` `--url` `--out` `--width` `--height` `--mobile` `--wait` `--timeout` |
| `compare` | 像素对照（区块级差异 + JSON 报告 + 差异热图） | `--orig` `--rebuild` `--max-diff` `--threshold` `--crop` `--resize` `--diff-out` `--json` |
| `pipeline` | 批量流水线：截图→取证→对照→汇总报告，可归档 zip | `--targets` `--site` `--out` `--rebuild-dir` `--archive` `--widths` `--max-diff` |
| `baseline` | 基准快照保存与回归比对 | `save`/`diff` `--name` `--orig` `--metrics` `--current` `--max-diff` |
| `license` | 生成 PolyForm 许可证 | `name` `--dir` `--note` `--year` |
| `browser` | 启动调试浏览器 | `--port` `--url` `--show` |

也可用模块方式运行：`python3 -m crkit <command>`。

## 标准工作流

1. **取证**：用 `shot` 在统一视口下截图，用 `inspect` 提取设计 token、元素坐标与调色板（只读取外部可见信息，不读取源码）。
2. **实现**：用 `init` 起项目，编码代理仅依据取证证据从零写出可运行代码。
3. **对照**：用 `compare` 量化背景色、平均像素差、差异占比与内容列位置。
4. **验证**：迭代修正直到差异收敛，所有检查均可重复运行。

## 目录结构

```text
cleanroom-kit/
├── bin/crk, bin/crk.cmd     # 跨平台启动器（无需安装）
├── crkit/                   # 纯标准库包
│   ├── cli.py               # 命令路由
│   ├── version.py           # VERSION 单一来源读取
│   ├── cleanwords.py        # 禁用词合规自检
│   ├── pngio.py             # PNG 解码与编码（zlib，替代图像库）
│   ├── ws.py / cdp.py       # WebSocket + CDP 客户端
│   ├── browser.py           # 浏览器探测与启动
│   ├── inspect.py           # DOM 取证（设计 token/元素坐标/调色板）
│   ├── compare.py           # 像素对照与差异热图
│   ├── scaffold.py          # 脚手架
│   └── license.py           # 许可证生成
├── templates/web/           # web 栈项目模板
├── templates/game/         # game 栈项目模板（canvas + ES module）
├── data/                    # 内嵌 PolyForm 标准条款
├── evidence/                # 各版本真实浏览器验证产物
└── tests/test_core.py       # 核心测试（69 项）
```

## 示例项目

工具包附带两个完整的参考示例，展示从取证到达标的全过程：

- [craft-example-rebuild](https://github.com/yyds8170-ctrl/craft-example-rebuild)：静态网站复刻（HTML/CSS，含响应式与无障碍）。
- [craft-snake-rebuild](https://github.com/yyds8170-ctrl/craft-snake-rebuild)：带交互逻辑的贪吃蛇（难度、音效、完美通关）。

## 与 craft-anything 的关系

本工具包可独立使用。若系统已安装 craft-anything（`craft-anything-cli` 在 PATH 中），可将其作为**可选增强**，提供更丰富的反汇编/取证能力；未安装时，内置的 CDP 取证与对照能力不受影响。

## 测试

```bash
python3 -m unittest tests.test_core -v   # 69 项，覆盖 PNG/颜色归一化/对照/网格分桶/取证/交互动作/断言/WCAG 对比度/脚手架双栈/批量流水线/基线回归/许可证年份/版本一致性/合规自检/会话可靠性/WS 帧/全页截图
```

## 许可证

本项目基于 [PolyForm Noncommercial License 1.0.0](LICENSE) 发布，仅限非商业用途。Copyright (c) 2026 洋洋。
