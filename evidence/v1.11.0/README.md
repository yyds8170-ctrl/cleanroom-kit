# v1.11.0 验证证据 · 脚手架与项目模板升级

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 本机新建 game 栈项目：`/tmp/ck-game`，经 `python3 -m http.server 8076` 提供服务。
- 调试端口：9367。

## 执行命令

```bash
# 1. 生成 game 栈模板
bin/crk init /tmp/ck-game --stack game --desc "v1.11 模板验证" --year 2026

# 2. 启动静态服务后截图
cd /tmp/ck-game && python3 -m http.server 8076 &
bin/crk shot --url http://127.0.0.1:8076/ --out evidence/v1.11.0/template.png --port 9367

# 3. 文件树留档
find /tmp/ck-game -type f | sort
```

## 验收判据与结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 模板可渲染非空白 | 画布与标题可见 | 标题 `ck-game`、画布占位文本 `ck-game` | 通过 |
| 骨架文件齐全 | evidence/tests/js/README/CI/LICENSE/NOTICE/VERSION | 12 个文件齐备（见 `tree.txt`） | 通过 |
| 占位符无残留 | `{{PROJECT}}` 等全部替换 | 全目录 `{{` 零命中 | 通过 |
| 许可证 / NOTICE 规范 | 署名洋洋、含 GitHub URL、年份可配 | LICENSE/NOTICE 无 `NOASSERTION` 占位，NOTICE 含项目 URL | 通过 |
| game 栈含画布与模块脚本 | `<canvas>` + `type="module"` | `index.html` 含二者，`js/main.js` 就位 | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `template.png` | game 模板页面截图（1280×900） |
| `tree.txt` | 生成项目文件树留档 |
| `probe-fail-sample.json` | 归档自 v1.9.0 的失败样例：断言不符判 FAIL（A5） |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W10）：模板骨架不全、占位符少、年份硬编码

- **发现**：旧模板只有 `index.html + css/style.css`，没有 `evidence/ tests/ js/` 与 CI；占位符仅两个；`license.py` 年份硬编码；NOTICE 缺 GitHub URL 行。
- **修复**：拆 web / game 两套模板，补 evidence/tests/js/README/CI 骨架；占位符扩为 `{{PROJECT}} {{DESCRIPTION}} {{YEAR}} {{AUTHOR}} {{GITHUB_USER}} {{GITHUB_REPO}}`；`build_license` / `build_notice` 年份可配（默认当前年），NOTICE 补项目 URL；CLI `init --stack/--author/--github-user/--github-repo/--year`，`license --year`。
- **复验**：web/game 两栈文件树断言通过；2027 年份覆盖测试通过；模板截图可渲染、占位符零残留。

### 闭环 2（复核 A1）：resize 未保宽高比

- **发现**：`compare --resize` 直接拉伸到目标尺寸，宽高比改变，与「等比缩放」措辞不符。
- **修复**：改为按 `min(目标宽/源宽, 目标高/源高)` 等比缩放，内容区居中、留边用源角背景填充；补等比回归断言。
- **复验**：2×2 源图缩到 4×3 画布内容区 3×3，比例保持 1:1。

### 闭环 3（复核 A2）：rgba 百分比 alpha 未换算

- **发现**：`rgba(...,50%)` 的百分比透明度未换算，alpha 解析失败。
- **修复**：颜色解析对以 `%` 结尾的 alpha 做 `/100` 换算；补百分比 alpha 回归断言。
- **复验**：`rgba(10,20,30,50%)` 与 `0.5` 等价。

### 闭环 4（复核 A3）：spacing 只采 marginTop

- **发现**：design 分桶间距只采集 `marginTop`，漏了 margin/padding 主要方向。
- **修复**：采样 `margin/marginTop/marginBottom/padding/paddingTop/paddingBottom`。
- **复验**：取证 JS 覆盖六个方向，既有取证回归不受影响。

### 闭环 5（复核 A4）：eval 返回值未入日志

- **发现**：`act` 的 `eval`/`eval_state` 返回值未写入逐步日志，无法回溯页面状态。
- **修复**：动作记录新增 `value` 字段保存 eval 返回值；补回归断言。
- **复验**：eval 步骤 `value` 与桩返回值一致。

### 闭环 6（复核 A5）：v1.9 失败样例未归档

- **发现**：v1.9.0「改坏断言值 → FAIL 退出码 1」验证报告只在临时目录，未入仓库证据。
- **修复**：把失败样例报告归档到本版本 `probe-fail-sample.json`，注明来源与判据。
- **复验**：样例断言 `pass=false`、`all_pass=false`。

### 闭环 7（复核 A7）：事件缓存只增不清

- **发现**：CDP 事件缓存只追加不清理，长会话内存持续增长。
- **修复**：缓存设 32 条上限，加载事件被消费后从缓存移除；补「导航后缓存为空」回归断言。
- **复验**：导航完成后 `_event_cache` 为空。

### 闭环 8（复核 A8）：许可证署名占位核实

- **发现 / 核实**：检查根 `LICENSE` / NOTICE 是否存在 `NOASSERTION` 类占位。
- **修复**：根 LICENSE 署名 `Copyright (c) 2026 洋洋`（GitHub: yyds8170-ctrl），NOTICE 项目 URL 就位；无 `NOASSERTION` 占位。
- **复验**：全仓库许可证/署名文本 grep 无占位符。

### 闭环 9（复核 A9）：act screenshot 未写进 schema 文档

- **发现**：`screenshot` 动作已实现但未写进动作 schema 说明。
- **修复**：`act.py` 模块文档补齐七个 op 及 `out` / `full_page` 参数说明。
- **复验**：文档与 `VALID_OPS` 一致。
