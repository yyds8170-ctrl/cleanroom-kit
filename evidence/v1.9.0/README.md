# v1.9.0 验证证据 · 交互行为取证与断言（面向动态复刻）

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 本地动态样本：`http://127.0.0.1:8074/`（`测试/rebuild-snake/` 贪吃蛇，ES module，HTTP 提供服务）。
- 覆盖核心交互路径：开始 → 空格暂停 → 空格恢复，与本机既有 `e2e_test.mjs` 同一路径。
- 调试端口：9364（act）、9365（probe）、9366（失败样例）。

## 执行命令

```bash
# 1. 动作序列：截图初始态 → 点击开始 → 空格暂停 → 截图暂停态 → 空格恢复
bin/crk act --url http://127.0.0.1:8074/ \
    --script evidence/v1.9.0/snake-actions.json \
    --out evidence/v1.9.0/act-log.json --port 9364 --timeout 10

# 2. 三态断言（每条断言带前置步骤，同一会话逐段执行）
bin/crk probe --url http://127.0.0.1:8074/ \
    --assertions evidence/v1.9.0/snake-probe.json \
    --out evidence/v1.9.0/probe-report.json --port 9365 --timeout 10

# 3. 失败样例（改坏断言值，应判 FAIL 并非零退出）
bin/crk probe --url http://127.0.0.1:8074/ --assertions /tmp/bad-probe.json \
    --out /tmp/bad-report.json --port 9366 --timeout 10
```

## 验收判据与结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 动作序列无报错 | 全部步骤 `ok: true` | 9 步全部成功，失败 0 步 | 通过 |
| 开始后遮罩隐藏 | `#overlay` 含 `hidden` | PASS（实测 `overlay hidden`） | 通过 |
| 暂停后标题 | `#overlay-title` 文本「已暂停」 | PASS（实测 `已暂停`） | 通过 |
| 恢复后遮罩隐藏 | `#overlay` 含 `hidden` | PASS（实测 `overlay hidden`） | 通过 |
| 失败样例 | 断言不符判 FAIL，退出码 1 | 1 条 FAIL，退出码 1 | 通过 |
| 过程截图 | 开始前 / 暂停后可归档 | `before.png`（准备开始）、`after-start.png`、`paused.png`（已暂停） | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `before.png` | 初始态截图（准备开始 / 开始游戏） |
| `after-start.png` | 点击开始后的截图 |
| `paused.png` | 空格暂停后的截图（已暂停 / 按空格继续） |
| `act-log.json` | 动作序列逐步日志（op / ok / elapsed_ms / error） |
| `probe-report.json` | 三态断言报告（逐条 PASS/FAIL + 实测值） |
| `snake-actions.json` | act 动作序列脚本 |
| `snake-probe.json` | probe 断言脚本（含每条前置步骤） |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W8）：纯标准库闭环断在「交互」一环

- **发现**：CDP 层只有导航 / 截图 / 取值，没有点击、键盘、输入与断言；贪吃蛇这类交互复刻的端到端验证只能依赖外部脚本，kit 无法独立完成行为闭环。
- **修复**：`cdp.py` 补 `click / type_text / press_key / scroll_to / wait_for / eval_state` 原语；新增 `act` 命令读取 JSON 动作序列逐步执行并记录日志；新增 `probe` 命令按断言 schema 输出结构化 PASS/FAIL 报告，任一 FAIL 退出码 1；断言支持文本 / 类名 / 属性 / 可见性 / 条件表达式五类核对。
- **复验**：本地 snake 站点跑通开始 / 暂停 / 恢复全链路，动作 0 失败，三断言全 PASS；改坏断言值的失败样例正确判 FAIL 并非零退出。

### 闭环 2（复核：load 事件竞态）

- **发现**：`wait_for_load` 若 `Page.loadEventFired` 在开始监听前到达会被错过，空等至超时。
- **修复**：`send` 层缓存无 id 的事件入队，`wait_for_load` 先查缓存再监听，避免竞态丢事件。
- **复验**：导航等待逻辑回归通过；既有导航事件顺序单测不受影响。

### 闭环 3：键盘事件派发目标不匹配页面监听

- **发现**：首轮实现把键盘事件派发到 `window`，而 snake 监听挂在 `document` 上，暂停/恢复不生效。
- **修复**：`press_key` 在 `document` 与 `window` 上同时派发 keydown / keyup。
- **复验**：空格暂停出现「已暂停」遮罩，再按空格恢复隐藏；probe 暂停态断言 PASS。
