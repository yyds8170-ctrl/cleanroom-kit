# v1.10.0 验证证据 · 内置 WCAG 无障碍与对比度检查

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 本地复刻站点：`http://127.0.0.1:8075/`（`测试/rebuild-example/`，HTTP 提供服务）。
- 交叉对照：该站点既有 `tests/contrast.mjs`（Node 脚本）的全 AA 结论。
- 调试端口：9366。

## 执行命令

```bash
# 1. DOM 取证（复用 v1.7.0 颜色归一化与 a11y 清单）
bin/crk inspect --url http://127.0.0.1:8075/ \
    --out evidence/v1.10.0/inspect.json --port 9366

# 2. WCAG 对比度与无障碍清单检查
bin/crk a11y --inspect evidence/v1.10.0/inspect.json \
    --out evidence/v1.10.0/a11y.json

# 3. 外部既有脚本交叉对照
node ../测试/rebuild-example/tests/contrast.mjs
```

## 验收判据与结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 正文 / 链接组合 ≥ AA | 全部通过 | 5 组全部 PASS，均达 AAA | 通过 |
| 与 `contrast.mjs` 方向一致 | 正文 / 注释比值吻合 | 正文 18.32:1、注释 9.75:1 与 mjs 一致；mjs 全部 AA | 通过 |
| 无障碍清单 | 缺 alt / 无名控件为空或与实际相符 | `lang=en`，缺 alt 0，无名控件 0，地标 `main` | 通过 |
| 不可解析颜色 | 标 `unverified`，不误判失败 | 单测锁定，空报告不抛错 | 通过 |

对比度汇总：共 5 组，通过 5，失败 0，未核验 0。

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `inspect.json` | 现场 DOM 取证报告（元素样式 / 调色板 / a11y 清单） |
| `a11y.json` | 对比度配对表 + 汇总计数 + 无障碍清单 |
| `contrast-table.txt` | kit 终端对比度表留档 |
| `contrast-mjs.txt` | 外部 `contrast.mjs` 交叉对照输出留档 |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W9）：对比度能力只存在于外部脚本

- **发现**：WCAG 对比度仅存在于复刻项目外部的 `tests/contrast.mjs`（Node 脚本），kit 本体没有无障碍能力，Python 零依赖闭环无法在交付前自检配色可读性。
- **修复**：下沉 WCAG 相对亮度 / 对比度公式到 `crkit/a11y.py`，新增 `a11y` 命令，复用 v1.7.0 颜色归一化与既有 a11y 采集字段，输出前景/背景对比度表与 AA/AAA 分级、汇总计数。
- **复验**：rebuild-example 五组配色全部 ≥ AA（AAA），正文 / 注释比值与 `contrast.mjs` 一致；临界点单测锁定公式；不可解析颜色标 unverified。

### 闭环 2：半透明颜色被当成不透明纯色配对

- **发现**：首轮把 `rgba(0,0,0,0)` 透明背景解析成纯黑配对，对比度 1.0 误判，而其合成背景实际未知。
- **修复**：配对层只取 alpha ≥ 0.999 的不透明颜色；半透明组合标 `unverified`，不参与通过/失败计数。
- **复验**：透明背景样例回归测试标 unverified；不透明配色正常计算。

### 闭环 3：元素级透明背景未回退 body 背景

- **发现**：元素计算样式背景为透明（alpha 0）时，首轮仍拿元素层透明色配对，导致正文全部 unverified，未回退到 body 背景色。
- **修复**：元素前景/背景不可用时回退 body token 颜色；回退后再做配对与分级。
- **复验**：五组配色正确回退到 `rgb(238,238,238)`，对比度 18.32 / 9.75 与 mjs 吻合。
