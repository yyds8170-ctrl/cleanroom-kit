# v2.0.0 验证证据 · 里程碑收敛

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`，视口 1280×900。

## 验证目标（第二轮 · 真实浏览器完整闭环）

| 目标 | 地址 | 参考图 | 断言 | 基线 | 总体 |
| --- | --- | --- | --- | --- | --- |
| rebuild-example（本地 HTTP） | `http://127.0.0.1:18191/` | `rebuild-v2-1280.png` | 2 条 | `v1.12-example` | **pass 6/6** |
| rebuild-snake（本地 HTTP，C5 交互） | `http://127.0.0.1:18192/` | — | 3 条（点击开始 / 空格暂停 / 空格恢复） | — | **pass 6/6** |
| real-rebuild/site（本地 HTTP） | `http://127.0.0.1:18193/` | `real-rebuild/evidence/orig.png` | — | — | fail 5/6（a11y 样例债务，见下） |
| example.com（外部只读页） | `https://example.com` | — | — | — | **pass 6/6**（7 组透明背景标 unverified） |

各目标分步产物见同名子目录：`shot.png`、`inspect.json`、`a11y.json`、`compare.json`（可选）、`probe.json`（可选）、`baseline.json`（可选）、`report.json`、`report.md`。

## 执行命令

```bash
# 环境自检（机器可读）
bin/crk doctor --json > evidence/v2.0.0/doctor.json

# 单命令完整闭环（示例：rebuild-example）
bin/crk verify --url http://127.0.0.1:18191/ --out evidence/v2.0.0/example \
  --ref ../测试/rebuild-example/evidence/rebuild-v2-1280.png \
  --assertions evidence/v2.0.0/example/assertions.json \
  --baseline v1.12-example --max-diff 25

# 一键自证
bin/crk selftest

# 发布前一致性自检
python3 scripts/pre_release_check.py
```

## 第一轮本地门禁结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 全量单测 | 全绿 | `Ran 89 tests … OK` | 通过 |
| 禁用词 lint | 零命中 | `bin/crk lint` PASS | 通过 |
| 发布自检 | 版本/徽章/测试数/证据目录一致 | 干净树上全绿（封版时留档 `pre-release.txt`） | 通过 |
| 环境自检 | 字段齐全 | `doctor.json` version=2.0.0，浏览器就位，端口空闲 | 通过 |

## 第二轮 · 主动构造边界 / 异常输入

记录见 `boundary/boundary.txt`。

| 输入 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 坏 JSON 断言文件 | 中文报错，退出码 1，不抛裸栈 | `错误：断言 JSON 解析失败：…`，exit=1 | 通过 |
| 缺失断言 / 动作脚本 | 中文报错，退出码 1 | `错误：断言文件不存在：…` | 通过 |
| 缺失参考图 / 取证报告 | 中文报错，退出码 1 | `错误：原版图不存在：…` | 通过 |
| 非法视口宽高（0 / 负值） | 中文报错，退出码 1 | `错误：视口宽高必须为正数，收到：0×900` | 通过 |
| 调试端口被占用 | 中文报错，退出码 1 | `错误：调试端口 18215 已被占用…` | 通过 |
| 空断言数组 | 视为全部通过，不崩溃 | `results: []，all_pass: true` | 通过 |

## C1–C5 终审遗留处置

| 编号 | 问题 | 处置 | 证据 / 回归 |
| --- | --- | --- | --- |
| C1 | 根 `NOTICE` 缺 Project URL 行 | 用 `license.build_notice("cleanroom-kit")` 重生成，含 `Project URL: https://github.com/yyds8170-ctrl/cleanroom-kit` | 根 `NOTICE` |
| C2 | 基线 verdict/bg_match 全等比较 | 改为仅判降级：分级变差、背景由一致变不一致、平均差回升超容差才记漂移；改善不误报；`--lenient-verdict` 下 match/minor 互不算降级 | 单测：严格/宽松口径、major→match 改善、bg_match False→True 改善 |
| C3 | 模板占位测试恒真断言 | 改为核心骨架文件存在 + 文本文件占位符零残留；web/game init 后测试均可跑绿 | 单测 `TestTemplateSkeleton` 双栈加载执行通过 |
| C4 | 许可证 `NOASSERTION` 占位 | 全仓终查：`LICENSE`/`NOTICE`/`CITATION.cff` 无版权占位，SPDX 标识 `PolyForm-Noncommercial-1.0.0`；命中字样仅存在于历史证据/CHANGELOG 描述核查过程的叙述文字，保留不改 | `bin/crk lint` + 全仓 grep |
| C5 | v1.13 缺 snake 交互截图 | 对 `测试/rebuild-snake/` 跑 act/probe 闭环，截图与 3 条断言报告归档 `snake/` | `snake/shot.png`、`snake/probe.json`、`snake/report.md` |

## 闭环记录

### 闭环 1：分散命令无法一条命令自证

- **发现**：取证、对照、无障碍、断言、基线分属多个命令，验证一轮要手工串联并分别判断通过与否。
- **修复**：新增 `crkit/verify.py` 与 `verify` 命令，同一会话内串起截图→取证→无障碍→（可选）对照→（可选）断言→（可选）基线，分步状态 + 总体 pass/fail 汇总 `report.json`/`report.md`；缺输入步骤标 skipped 不计失败。
- **复验**：四个真实目标闭环跑通，example 与 snake 全 pass；聚合通过/失败/跳过与报告落盘有单测锁定。

### 闭环 2：fresh clone 后缺少统一自证入口

- **发现**：环境检查、单测、发布一致性分散在 `doctor`、`unittest`、`pre_release_check.py`，新克隆项目要分别手动跑。
- **修复**：新增 `selftest` 命令，串联环境自检、全量单测、发布一致性自检（git 干净项作为封版门禁在 selftest 中仅提示），任一失败退出码 1。
- **复验**：命令可正常解析执行；一致性检查复用 `pre_release_check.run_checks`。

### 闭环 3：命令文档分散在 README 与源码注释

- **修复**：新增 `docs/COMMAND_REFERENCE.md`，汇总全部命令、参数、退出码与结构化产物；README 命令清单改为摘要并链接该文档。

### 闭环 4：基线把改善误判为漂移（第二轮主动构造发现）

- **发现**：基线 `mean_abs_diff` 用绝对差判定，28.48→0.0 的改善也被报漂移；`verdict`/`bg_match` 只要与基线不同就报，major→match 的改善被误判。
- **修复**：三项指标改为方向敏感——仅回升/变差超容差记漂移；`verdict` 按严重度排序，仅当前更差时记漂移；`bg_match` 仅 True→False 记漂移。
- **复验**：稳定样例不误报，超差/降级样例仍报漂移（单测锁定正反例）。

### 闭环 5：透明 rgba 背景被当成黑色配对（第二轮主动构造发现）

- **发现**：字符串形式 `rgba(0, 0, 0, 0)` 未被识别为透明，按黑色取色，导致外部页 7 组正文误报对比度 1.0:1 失败。
- **修复**：a11y 取色统一走 `colors.parse_color` 读取 alpha，透明/半透明标 `unverified` 而非按黑色判失败。
- **复验**：外部 example.com 7 组正文转为 unverified、0 失败；新增透明 rgba 回归测试。

### 闭环 6：边界输入抛裸栈（第二轮主动构造发现）

- **发现**：坏 JSON、缺失文件、非法视口、占用端口直接抛 traceback。
- **修复**：断言/动作 JSON 解析与文件存在性、参考图/报告存在性、视口正数、端口占用均给中文报错并以退出码 1 结束；补对应单测。

## 已知边界（如实留档）

- `real-rebuild/site` 链接蓝 `#2e7dca` 对白底 3.89:1，达大字号 AA（3.0）但未达正文 AA（4.5）；页脚 `#9999a0` 对 `#ebeff1` 2.28:1，属该复刻样例自带的无障碍债务，非工具误报。对照像素差异 16.76%（minor），与历史量级一致。
- 透明背景元素因合成背景未知，对比度标 `unverified`，不参与 AA/AA 门禁。
