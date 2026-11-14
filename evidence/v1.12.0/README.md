# v1.12.0 验证证据 · 批量闭环与回归基线

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 站点 A：`http://127.0.0.1:8077/`（`测试/rebuild-example/`）。
- 站点 B：`http://127.0.0.1:8078/`（`real-rebuild/site/`）。
- 对照参考图：`ref/site.png`（取自 `real-rebuild/evidence/orig.png`）。
- 调试端口：9368。

## 执行命令

```bash
# 1. 批量流水线：截图 → 取证 → 对照 → 汇总 → 归档
bin/crk pipeline --targets evidence/v1.12.0/targets.json \
    --out evidence/v1.12.0/run \
    --rebuild-dir evidence/v1.12.0/ref \
    --archive evidence/v1.12.0/evidence.zip --port 9368

# 2. 保存基线快照（指标 + 基准截图）
bin/crk baseline save --name v1.12-example \
    --orig evidence/v1.12.0/ref/site.png \
    --metrics evidence/v1.12.0/run/site/compare.json

# 3. 稳定样例回归比对（应 stable，退出码 0）
bin/crk baseline diff --name v1.12-example \
    --current evidence/v1.12.0/run/site/compare.json

# 4. 漂移样例回归比对（指标劣化，应 regressed，退出码 1）
bin/crk baseline diff --name v1.12-example --current /tmp/worse.json
```

## 验收判据与结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 两目标指标齐全 | 截图 / inspect / 对照报告落盘 | example 截图+取证；site 截图+取证+compare.json | 通过 |
| 汇总报告 | report.md + report.json，总体判定 | 2 目标，通过 1、失败 1，总体 fail | 通过 |
| 对照指标对齐单步 compare | site 差异占比 / 判定 / 最重桶 | 16.8%、major、最重桶第 6 行第 2 列 48.5%，与 v1.8.0 一致 | 通过 |
| 基线保存 / 读回 | 指标字段一致，参考截图就位 | `snapshot.json` + `reference.png`，字段读回一致 | 通过 |
| 稳定样例 | 不判漂移 | `stable`，退出码 0 | 通过 |
| 漂移样例 | 标出超差项，退出码 1 | 差异占比 / 平均差 / 背景一致三项漂移，`regressed`，退出码 1 | 通过 |
| 证据归档 | zip 可列出全部产物 | `evidence.zip` 含 run 下截图 / inspect / compare / 报告 | 通过 |

> 站点 B 差异 16.8% 超 10% 门禁，流水线总体 `fail` 属预期门禁行为，不是崩溃。

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `targets.json` | 多目标配置（name / url / widths） |
| `run/report.md` | 流水线汇总 Markdown 报告 |
| `run/report.json` | 流水线汇总结构化报告 |
| `run/example/` | 站点 A 截图与取证 |
| `run/site/` | 站点 B 截图、取证、对照报告 |
| `ref/site.png` | 对照参考图（基准截图） |
| `evidence.zip` | 本轮证据归档 |
| `../baselines/v1.12-example/` | 基线快照（`snapshot.json` + `reference.png`） |

## 闭环记录

### 闭环 1（W11）：无批量编排、无基线快照、无归档

- **发现**：现有命令都是单步手动执行，没有一条命令串起取证→对照→汇总；多轮迭代缺少基准快照，无法量化变好还是变坏；证据分散，没有归档手段。
- **修复**：新增 `pipeline`（多目标截图→取证→对照→汇总 `report.md/json`，`--archive` zip 归档）与 `baseline save/diff`（纯 JSON + PNG 快照，指标回升超阈值与内容区间变化记漂移）；汇总复用 v1.8.0 compare 指标。
- **复验**：两站点批量跑通；汇总指标与单步 compare 对齐；基线稳定/漂移两条路径均可复跑；zip 可解压复原产物。

### 闭环 2：基线快照漏存内容区间字段

- **发现**：首轮快照只存四项对照指标，内容列/行区间未入库，稳定样例也被误报「内容变化：基线 None → 当前 …」。
- **修复**：快照补存 `content_original/content_rebuild/content_rows_*` 四项；回归比对基于快照字段逐项比较；补读回断言。
- **复验**：同一指标稳定样例不再报内容变化；漂移样例正确标出超差指标。

### 闭环 3（复核 A6）：CI e2e 未覆盖 act/probe

- **发现**：CI 端到端只跑 shot/compare/inspect，交互动作与状态断言没有自动化覆盖。
- **修复**：e2e 新增 act（eval 取证并校验步骤成功）与 probe（h1 可见性断言）两步，复用既有浏览器会话环境变量。
- **复验**：本地镜像执行 act eval 返回页面标题、probe 断言 PASS；随本版 CI 一并验证。
