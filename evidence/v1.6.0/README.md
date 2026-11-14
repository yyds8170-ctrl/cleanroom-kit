# v1.6.0 验证证据 · 全页截图与多视口批量取证

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 本地静态站点：`http://127.0.0.1:8072/`（`real-rebuild/site/` 复刻样本，`python3 -m http.server 8072` 提供 HTTP 服务）
- 视口：桌面 1280×900、移动 390×900（CDP `Emulation.setDeviceMetricsOverride`）
- 调试端口：9362（批量截图）、9363（1280 取证）、9367（390 取证）

## 执行命令

```bash
# 1. 全页双宽度批量出图
bin/crk shot --url http://127.0.0.1:8072/ --out evidence/v1.6.0/site \
    --full-page --widths 1280,390 --port 9362 --timeout 10

# 2. 桌面视口全页取证（按路线图 --width 1280）
bin/crk inspect --url http://127.0.0.1:8072/ --out evidence/v1.6.0/inspect.json \
    --full-page --width 1280 --port 9363 --timeout 10

# 3. 移动视口全页取证（补充样本：覆盖首屏以下元素坐标）
bin/crk inspect --url http://127.0.0.1:8072/ --out evidence/v1.6.0/inspect-390.json \
    --full-page --width 390 --port 9367 --timeout 10
```

## 验收判据与结果

| 判据 | 阈值 / 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 1280 截图宽度 | 与参数 1280 一致 | 1280 宽 | 通过 |
| 1280 截图高度 | ≥ 视口 900，非空白 | 1280×900（114320 bytes）；宽屏下页面本就正好 900 高，含 IANA 标题、三张卡片与完整 footer | 通过 |
| 390 截图宽度 | 与参数 390 一致 | 390 宽 | 通过 |
| 390 长图高度 | ≥ 视口 900，非空白 | 390×1470（112037 bytes），三张卡片纵向堆叠，完整覆盖 footer 至 Privacy Policy / Terms of Service | 通过 |
| 滚动条挤压 | 内容列未被滚动条挤窄 | 全页前 `Emulation.setScrollbarsHidden`，长图内容列对齐基线参考图，无水平偏移 | 通过 |
| 1280 取证 | `full_page` 标记就位 | 54 个元素，`full_page: true`，视口 1280×900，最大 `box.y` 807（宽屏无首屏以下元素） | 通过 |
| 390 取证 | 存在 `box.y` 大于首屏高度 900 的元素 | 54 个元素，29 个 `box.y > 900`，最大 `box.y` 1433，与长图 1470 高度吻合 | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `site-1280.png` | 桌面 1280 宽全页截图（宽屏视口内完整页面） |
| `site-390.png` | 移动 390 宽全页长图（390×1470） |
| `inspect.json` | 1280 视口全页取证报告（元素坐标 / 设计 token / 调色板） |
| `inspect-390.json` | 390 视口全页取证报告（首屏以下元素坐标样本） |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W3）：截图仅截视口，长页面漏掉首屏以下内容

- **发现**：`cdp.screenshot()` 原先只调用 `Page.captureScreenshot` 截当前视口；长页面复刻取证会漏掉首屏以下部分，kit 能力落后于自身验证脚本早已使用的跨视口截图做法。
- **修复**：补齐全页参数 `captureBeyondViewport: true`；新增 `page_dimensions` 探测 `scrollWidth / scrollHeight`；全页前隐藏滚动条、按整页尺寸同步设备度量；取证 JS 在元素纵坐标上叠加 `window.scrollY`；`shot` 新增 `--full-page` 与 `--widths` 多宽度批量出图，输出名 `<主名>-<宽度>.png`。
- **复验**：390 视口长图 1470 高，完整覆盖 footer；对照 `real-rebuild/evidence/orig.png`，内容列未被滚动条挤压；390 取证 29 个元素坐标落在首屏以下，与长图高度吻合。

### 闭环 2：全页截图单测桩消息缺 `id` 被请求匹配忽略

- **发现**：第一轮跑全页截图单测时，模拟 WebSocket 回放的响应消息未带 `id` 字段，`send` 按 `id` 匹配响应时逐条忽略，最终队列空报 `IndexError`。
- **修复**：测试桩响应补齐与请求序号对应的 `id`；产品代码匹配逻辑不变。
- **复验**：`test_fullpage_screenshot_passes_capture_beyond_viewport` 通过，断言全页截图参数含 `captureBeyondViewport: true`。

### 闭环 3：非法 `--widths` 参数未校验

- **发现**：主动构造边界输入时，`--widths abc`、`--widths -100` 会让 `int()` 抛裸栈，错误不可读。
- **修复**：`_parse_widths` 校验每项为正整数，非法值抛中文报错；既有批量输出测试内补两条非法输入回归断言。
- **复验**：两类非法输入均抛 `RuntimeError` 中文提示，正常逗号分隔宽度解析不受影响。
