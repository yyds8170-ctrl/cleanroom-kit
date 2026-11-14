# v1.13.0 验证证据 · 格式可移植性加固与发布收尾

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- `https://example.com`（在线页面，1280×900 视口）。
- 解码/自检能力以本地构造样例与全量单测覆盖；真实浏览器截图见 `final.png`。

## 执行命令

```bash
# 1. 机器可读环境自检
bin/crk doctor --json > evidence/v1.13.0/doctor.json

# 2. 真实页面截图（CDP 设备模拟，自动启停浏览器）
bin/crk shot --url https://example.com --out evidence/v1.13.0/final.png --port 9368

# 3. 发布前一致性自检（版本/徽章/测试数/禁用词/证据目录/git 干净）
python3 scripts/pre_release_check.py
```

## 验收判据与结果

| 判据 | 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| `doctor.json` 可解析且字段齐全 | version/python/platform/browser 等字段 | 字段齐全，version=1.13.0，浏览器路径就位，端口空闲 | 通过 |
| 截图正常非空白 | 1280×900，像素非全空 | 1280×900，3 通道，非空白 | 通过 |
| 全量单测 | 77 项全绿 | `Ran 77 tests … OK` | 通过 |
| 发布自检 | 版本/徽章/测试数/禁用词/证据目录一致 | 干净树上全绿（见 `pre-release.txt`） | 通过 |
| 禁用词 | 零命中 | `bin/crk lint` PASS | 通过 |
| 主页渲染 | 四枚徽章 / banner / 描述正常 | 浏览器打开仓库主页，徽章 1.13.0、77 passing，banner 1280×260 正常渲染，描述与主题就位 | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `doctor.json` | 机器可读环境自检报告 |
| `final.png` | example.com 1280×900 截图 |
| `repo-home.png` | 仓库主页浏览器核对截图（徽章 / banner / 描述渲染） |
| `pre-release.txt` | 发布前自检输出留档 |

## 对比度口径说明（复核 B5）

内置 `a11y` 采用标准 WCAG 2.x 公式：sRGB 分段线性化后按 0.2126/0.7152/0.0722 加权求相对亮度，对比度 `(L1+0.05)/(L2+0.05)`，与外部对照脚本公式一致。早期证据中链接对比度的小幅出入（16.53:1 与 18.32:1）来自**前景取色口径**：内置取证读取元素 computed style 继承色，外部脚本使用固定配色表；并非公式偏差。当前 example.com 锚点由脚本注入，computed style 前景为黑色，故按黑色配对计算。

## 闭环记录

### 闭环 1（W12）：PNG 解码边界、启动器回退、doctor 无可读输出

- **发现**：旧解码器不支持 Adam7 隔行与 tRNS 透明块，CRC 不校验；非 8 位深/不支持类型/坏文件头报错笼统；Windows 启动器只找 `python` 无回退；`doctor` 只能看终端文本，CI 无法解析。
- **修复**：补 Adam7 七次扫描解包、tRNS（索引/灰度/RGB）并入白底合成、逐 chunk CRC32 校验（不一致告警并标 `crc_mismatch`）；报错列出实际位深/类型与支持范围；两个启动器按 `python3`/`python` 顺序探测，找不到给中文提示；`doctor --json` 输出版本/Python/平台/浏览器/可选 Node 与 craft-anything CLI/端口自检。
- **复验**：隔行与透明样例单测通过；CRC 损坏样例标注 `crc_mismatch`；坏头/不支持类型给出中文报错；`doctor.json` 可被 JSON 解析。

### 闭环 2（W13）：发布前一致性靠人工核对

- **发现**：版本号、README 徽章、测试数、禁用词、证据目录全靠人工对照，容易漂移。
- **修复**：新增 `scripts/pre_release_check.py`，串联 VERSION 与 `__version__`、CHANGELOG/README 版本与测试数对齐、禁用词零命中、证据目录齐备、git 工作区干净检查，并接入 CI unit job。
- **复验**：规范样例树全绿；注入版本不一致时自检正确报错并以退出码 1 结束。

### 闭环 3（复核 B1–B8）：流水线口径、归档、基线容差与模板开箱

- **B1**：流水线汇总补断言摘要字段；无对照目标明确标「仅取证」模式与说明，不参与对照门禁。
- **B2**：`--archive` 把参考图与基线快照一并打包，zip 内含参考图与快照断言。
- **B3**：基线 `mean_abs_diff` 增加可配置绝对容差（默认 3.0），轻微抖动不误报，超差仍报漂移。
- **B4**：`a11y` 补 `--json` 别名（同 `--out`），README 统一为结构化 JSON 报告路径。
- **B5**：核对对比度公式与外部脚本一致；数值出入源于取色口径，已在本 README 注明。
- **B6**：取证 spacing 补采 `marginLeft/marginRight/gap`。
- **B7**：web/game 模板各补占位测试，init 后 CI 单测开箱可跑绿。
- **B8**：全仓核查 `NOASSERTION`，根 LICENSE/NOTICE 署名 `Copyright (c) 2026 洋洋`，无版权占位；许可证标识为 `PolyForm Noncommercial License 1.0.0`。
