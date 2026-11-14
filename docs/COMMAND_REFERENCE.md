# 命令参考（COMMAND REFERENCE）

> 本文件是 cleanroom-kit 全部 CLI 命令的统一速查；README 的「命令清单」为摘要，参数细节以本文为准。
> 启动器：`bin/crk`（macOS / Linux）、`bin/crk.cmd`（Windows）；也可 `python3 -m crk <command>`。
> 通用视口参数：`--width`（默认 1280）、`--height`（默认 900）、`--port`（CDP 调试端口）、`--mobile`（移动视口模拟）、`--wait`（加载等待秒，默认 1.5）、`--timeout`（导航上限秒，默认 15.0）。

## 环境与自证

| 命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `doctor` | 环境自检：Python / 平台 / 浏览器 / Node / 可选 craft-anything CLI / 端口占用 / 版本 | `--json` `--port` |
| `selftest` | clone 即自证：环境自检 + 全量单测 + 发布一致性自检，任一失败非零退出 | `--port` |
| `version` | 输出版本与运行环境信息 | `--json` |
| `lint` | 禁用词合规自检，命中即非零退出 | — |

## 项目脚手架

| 命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `init` | 从模板创建项目（web / game 栈，自动带 LICENSE/NOTICE/VERSION/CI） | `name` `--dir` `--desc` `--stack` `--author` `--github-user` `--github-repo` `--year` `--force` |
| `license` | 生成 PolyForm Noncommercial 1.0.0 许可证 | `name` `--dir` `--note` `--year` |

## 取证与对照

| 命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `shot` | 设备模拟截图（全页长图 / 多宽度批量） | `--url` `--out` `--width` `--height` `--mobile` `--wait` `--timeout` `--full-page` `--widths` |
| `inspect` | DOM 取证：设计 token、元素坐标、调色板、结构大纲、无障碍线索 | `--url` `--out` `--width` `--height` `--mobile` `--wait` `--timeout` `--full-page` `--text-out` `--max-text` |
| `act` | 按 JSON 动作序列执行交互（点击/输入/键盘/滚动/等待/截图），逐步记录返回值 | `--url` `--out` `--script` `--steps` 通用视口参数 |
| `probe` | 页面状态断言，输出结构化 PASS/FAIL 报告 | `--url` `--out` `--assertions` `--script` 通用视口参数 |
| `a11y` | WCAG 对比度与无障碍清单检查（AA/AAA 分级）；数据源为 `--inspect` 报告或现场 `--url` | `--inspect` `--url` `--out`/`--json` 通用视口参数 |
| `compare` | 像素对照：背景色、平均像素差、差异占比、内容列、差异热图、JSON 报告 | `--orig` `--rebuild` `--max-diff` `--threshold` `--crop` `--resize` `--diff-out` `--json` |

## 批量、闭环与基线

| 命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `pipeline` | 批量流水线：截图→取证→对照→汇总 report.md/json，可归档 zip（含参考图与基线快照） | `--targets` `--site` `--out` `--rebuild-dir` `--archive` `--widths` `--width` `--height` `--port` `--mobile` `--wait` `--timeout` `--max-diff` |
| `verify` | 单命令完整闭环：截图→取证→无障碍→对照→断言→基线回归，汇总 report.md/json 与总 pass/fail | `--url` `--out` `--ref` `--assertions` `--baseline` `--max-diff` `--evidence-root` 通用视口参数 |
| `baseline save` | 保存基准快照（对照指标 + 内容列/行区间） | `--name` `--orig` `--metrics` `--evidence-root` |
| `baseline diff` | 与基线回归比对；差异占比 / 平均差带容差，verdict 默认严格全等，`--lenient-verdict` 下 match/minor 互不算降级 | `--name` `--current` `--max-diff` `--mean-diff-tol` `--lenient-verdict` `--evidence-root` |

## 调试

| 命令 | 作用 | 关键参数 |
| --- | --- | --- |
| `browser` | 启动调试浏览器（保持会话供手工检查） | `--port` `--url` `--show` |

## 退出码约定

- `0`：全部通过；
- `1`：存在未通过步骤、断言失败、差异超阈值、回归漂移，或合规自检命中禁用词。

## 结构化产物

- `verify` / `pipeline`：`report.json` + `report.md`，分步状态 + 总体判定；
- `compare`：对照 JSON（`diff_ratio_pct`、`mean_abs_diff`、`bg_match`、`verdict`、内容列/行）；
- `inspect`：取证 JSON（tokens、elements、palette、a11y、plaintext 大纲可选）；
- `probe`：断言报告（逐条 expected/actual/reason + `all_pass`）；
- `baseline`：快照 JSON 与漂移清单 JSON。
