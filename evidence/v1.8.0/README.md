# v1.8.0 验证证据 · 对照增强：结构化报告与区块级差异

验证日期：2026-11-14。环境：Linux，Python 3.12.11。

## 验证目标

- 真实对照样本（只读）：`../real-rebuild/evidence/orig.png` vs `../real-rebuild/evidence/rebuild.png`，均为 1280×900。
- 不启动浏览器，直接用 kit 像素对照复算。

## 执行命令

```bash
bin/crk compare \
    --orig ../real-rebuild/evidence/orig.png \
    --rebuild ../real-rebuild/evidence/rebuild.png \
    --diff-out evidence/v1.8.0/diff.png \
    --json evidence/v1.8.0/report.json --crop
```

## 验收判据与结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 垂直内容范围 | 报告含 `content_rows_original / content_rows_rebuild` | 原版 `[53, 899]`，复刻 `[48, 843]` | 通过 |
| 网格分桶 | 8×6 桶，每桶 `diff_pixels / diff_ratio_pct` | 48 个桶齐全 | 通过 |
| 结构化判定 | 含 `verdict`（match/minor/major） | `major`（阈值 10.0%） | 通过 |
| JSON 报告落盘 | `report.json` 可被程序读回 | 字段齐全，往返读取正常 | 通过 |
| 最重桶定位 | 与热图红色聚集区位置一致 | 最重桶第 6 行第 2 列（48.5%）；热图底部页脚整行为红色聚集区，位置吻合 | 通过 |
| 差异量级 | 与基线 14–21% 量级相互印证 | 差异像素占比 16.8%，平均像素差 28.48 | 通过 |

> 说明：差异 16.8% 超过 `--max-diff` 默认 10% 门禁，compare 以退出码 1 结束，属门禁行为而非崩溃；终端文本留档于 `compare-text.txt`。

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `diff.png` | 差异热图（差异像素标红，一致区域灰化） |
| `report.json` | 结构化对照报告（指标 / 垂直范围 / 网格桶 / 判定） |
| `compare-text.txt` | 终端文本报告留档 |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W7）：对照只有水平列与终端文本，差异无法定位、无法被程序消费

- **发现**：此前只算水平内容列，没有垂直范围；报告只能看终端文本；尺寸不一致只能裁剪；差异定位只有整图占比，指不出「哪一块」错了。
- **修复**：补垂直内容范围（与水平列算法对称）；新增 8×6 网格分桶，每桶输出差异像素数与占比；新增 `verdict` 三档判定；`compare` 新增 `--resize` 缩放对齐（与 `--crop` 互斥，CLI 层校验）与 `--json` 结构化报告落盘；背景采样边距做成可配参数。
- **复验**：真实 orig/rebuild 复算，垂直范围、48 桶、判定齐全；最重桶与热图红区位置吻合；JSON 可被后续流水线直接读取。

### 闭环 2（复核：lint 扫描范围不全）

- **发现**：禁用词扫描只覆盖 `crkit/bin/templates/tests`，未纳入 `evidence/`、`data/` 与根 `NOTICE/VERSION`。
- **修复**：扫描目录补 `evidence`、`data`，根文本文件补 `NOTICE`、`VERSION`；补一条扫描范围断言。
- **复验**：`bin/crk lint` 在扩大范围后零命中；测试断言证据 JSON、data 条款、NOTICE、VERSION 均在扫描集内。

### 闭环 3（复核：CI 缺 lint 门禁）

- **发现**：三个 CI job 都未跑禁用词自检，合规问题只能靠本地发现。
- **修复**：unit job 新增 `bin/crk lint` 步骤作为门禁。
- **复验**：推送后 CI unit job 包含合规自检步骤并通过。

### 闭环 4（复核：全页截图丢失移动模拟）

- **发现**：`screenshot(full_page=True)` 重设设备度量时硬编码 `mobile: False`，`--mobile --full-page` 会丢掉移动视口模拟。
- **修复**：全页分支透传调用方 `mobile`，仅把宽高替换为整页尺寸。
- **复验**：截图签名支持 `mobile` 与 `viewport` 回退；既有全页单测与 e2e 移动截图路径不受影响。

### 闭环 5（复核：根 LICENSE 缺失）

- **发现**：仓库根无 `LICENSE` 实体，徽章与 NOTICE 却指向它，平台识别不到许可证。
- **修复**：用 `license.py` 生成根 `LICENSE` 入库（PolyForm Noncommercial 1.0.0 全文，署名洋洋，`Copyright (c) 2026 洋洋`）。
- **复验**：根目录存在 LICENSE，含版权署名；README 徽章与 NOTICE 指向保持一致。

### 闭环 6（复核：0×0 静默兜底）

- **发现**：`page_dimensions` 探测异常时兜底 `{w:0,h:0}`，会静默产出 0 尺寸图。
- **修复**：兜底回退到当前视口宽高；整页宽高仍为 0 时抛中文错误，不再出 0 尺寸图。
- **复验**：探测失败路径带视口回退；0 尺寸场景抛明确中文报错。

### 闭环 7（复核：ASCII 禁用词子串误报）

- **发现**：ASCII 词用纯子串匹配，普通英文词含同名子串时会被误报。
- **修复**：ASCII 词加 `\b` 词边界，中文词保持全词包含；补双向回归：真实禁用词仍可检出，加后缀的普通英文词（含同名子串）不误报。
- **复验**：49 项单测全绿，lint 零命中。
