# v1.7.0 验证证据 · 取证增强：设计 token 归一化与结构大纲

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 联网目标：`https://example.com`（结构简单、稳定）
- 本地复刻样本：`http://127.0.0.1:8073/`（`测试/rebuild-example/`，`python3 -m http.server 8073` 提供 HTTP 服务）
- 视口：1280×900；调试端口：9361（example.com）、9363（rebuild-example）

## 执行命令

```bash
# 1. 联网站点取证
bin/crk inspect --url https://example.com --out evidence/v1.7.0/example-inspect.json \
    --width 1280 --port 9361 --timeout 10

# 2. 本地复刻样本取证 + 纯文本大纲导出
bin/crk inspect --url http://127.0.0.1:8073/ \
    --out evidence/v1.7.0/rebuild-inspect.json \
    --text-out evidence/v1.7.0/rebuild-text.txt \
    --width 1280 --port 9363 --timeout 10
```

## 验收判据与结果

| 判据 | 期望 | example.com 实测 | rebuild-example 实测 | 结果 |
| --- | --- | --- | --- | --- |
| 报告新增段 | 含 `links / headings / a11y / design / text` | 五段齐全 | 五段齐全 | 通过 |
| 链接采集 | `{text, href, target}` | 1 条链接 | 1 条链接 | 通过 |
| 标题大纲 | `{level, text, box}` | 精简页无标题（页面本身无 h1–h6） | 1 条 h1「Example Domain」 | 通过 |
| 无障碍清单 | `lang / images_without_alt / landmarks / unnamed_controls` | `lang: en`，无未命名控件 | `lang: en`，landmark `main` | 通过 |
| 设计分桶 | 字号 / 字重 / 字体 / 最大宽度 / 圆角 / 阴影 / 间距 | 七桶齐全 | 七桶齐全 | 通过 |
| 颜色归一化 | 色板为含 `hex/alpha/space` 的对象，无裸 `rgba()/oklch()` 未标注项 | 3 色均归一化（`#000000 / #eeeeee / #0000ee`） | 4 色均归一化 | 通过 |
| 纯文本导出 | txt 非空，含标题大纲与可见正文 | — | `rebuild-text.txt` 含 h1 大纲与双语正文 | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `example-inspect.json` | example.com 结构化取证报告 |
| `rebuild-inspect.json` | rebuild-example 结构化取证报告 |
| `rebuild-text.txt` | 标题大纲 + 可见纯文本导出 |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W6）：色板保留裸颜色字符串，取证维度不全

- **发现**：此前色板直接保留 `oklch(...) / rgba(...) / rgb(...)` 原始字符串，编码代理无法直接当 CSS hex token 使用；报告缺链接、图片、标题大纲、无障碍与圆角/阴影/间距分桶。
- **修复**：抽出 `crkit/colors.py` 颜色归一化模块（hex/rgb/rgba/oklch，oklch 标 `oklch-approx`，不可解析标 `raw` 保留原值）；扩充取证 JS 采集 `links / images / headings / a11y / design / text`；元素文字色与背景色同步归一化；`inspect` 新增 `--text-out`、`--max-text`。
- **复验**：两份报告五段齐全；色板全部为结构化对象；纯文本 txt 非空；旧字段 `url / viewport / tokens / elements / palette` 保持不变。

### 闭环 2：rgb/rgba 仅支持逗号分隔，空格分隔写法落入 raw

- **发现**：第二轮主动构造边界输入时，`rgb(255 0 0)`、`rgba(10 20 30 / 0.5)` 这类空格分隔 / 斜杠 alpha 写法被误判为 raw。
- **修复**：解析器先把 `/` 归一并按逗号、空白双重分词，兼容现代空格分隔颜色函数。
- **复验**：两类写法均归一化到正确 hex；`not-a-color`、`var(--x)` 等不可解析值仍走 raw 分支不抛异常；43 项单测全绿。
