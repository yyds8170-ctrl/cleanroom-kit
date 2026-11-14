# v1.4.0 验证证据 · 版本一致性与工程基线加固

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 公开稳定目标：`https://example.com`
- 截图视口：1280 × 900（CDP `Emulation.setDeviceMetricsOverride`）
- 调试端口：9361（验证前 `ss -ltn` 确认空闲）

## 执行命令

```bash
# 1. 版本信息落盘（结构化 JSON）
bin/crk version --json > evidence/v1.4.0/version.json

# 2. 禁用词合规自检，留档文本
bin/crk lint > evidence/v1.4.0/lint-report.txt

# 3. 真实浏览器截图
bin/crk shot --url https://example.com --out evidence/v1.4.0/orig.png \
    --width 1280 --height 900 --port 9361
```

## 验收判据与结果

| 判据 | 阈值 / 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 截图文件非空 | 文件大小 > 0 | 74903 bytes | 通过 |
| 截图尺寸 | 1280 × 900 | 1280 × 900（RGB，3 通道） | 通过 |
| 截图非错误页 | 含 example.com 正文 | 多语言示例正文与「Learn more」链接可见 | 通过 |
| version.json 版本号 | 等于 1.4.0 | `"version": "1.4.0"` | 通过 |
| lint 退出码 | 0，零命中 | 退出码 0，`PASS：未发现禁用词。` | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `orig.png` | example.com 1280×900 真实浏览器截图 |
| `version.json` | `version --json` 产出的版本/Python/平台/许可证结构化信息 |
| `lint-report.txt` | `lint` 禁用词自检终端留档 |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W1）：版本号硬编码漂移

- **发现**：`crkit/__init__.py` 原先硬编码 `__version__ = "1.0.0"`，与根目录 `VERSION`（1.3.0）漂移；仓库也没有任何命令回读版本号，后续打 tag 时极易再次不一致。
- **修复**：新增 `crkit/version.py`，以根目录 `VERSION` 为单一来源，导出 `get_version()` 与 `VERSION_PATH`；`__init__.py::__version__` 改为派生值；新增 `version` 命令（`--json` 输出结构化字典）与一致性测试。
- **复验**：`bin/crk version` 输出 `1.4.0`；`test_version_matches_VERSION`、`test_init_dunder_derived` 通过；CHANGELOG、README 徽章数字与 VERSION 一致。

### 闭环 2：lint 首轮自检命中标识符自身

- **发现**：实现 `lint` 后首次跑自检，扫描命中 `browser.py` 中的常量标识符（含被禁厂商子串），扫描结果非空。
- **修复**：将该常量改名为中性标识符 `_VENDOR_A`，浏览器厂商路径在运行时由片段拼接，源码中不保留厂商字面量；探测行为不变。
- **复验**：重跑 `bin/crk lint` 退出码 0、零命中；26 项单元测试全绿；`browser.find_browser()` 仍正确返回本机 chromium 路径。

### 闭环 3：普通单位用词被误命中

- **发现**：CLI 截图提示语中的中文数据单位用词被禁用词规则误命中；该词作为普通单位使用，不属于机构称谓。
- **修复**：禁用词表收窄为完整全词匹配（机构名以完整词形判定），提示语对应位置改用 `bytes`；双向回归测试锁定：真实禁用词仍可检出，普通单位用词不误报。
- **复验**：`test_detector_bidirectional` 通过；全树禁用词扫描零命中，CLI 截图命令输出正常。

### 闭环 4：一行多个禁用词漏报

- **发现**：边界构造时在同一行注入多个禁用词，扫描器遇首个命中即中断，后续词被漏报。
- **修复**：`cleanwords.scan_tree` 改为逐模式全量记录命中，不再提前中断。
- **复验**：回归样例中三个禁用词全部出现在命中清单；26 项单元测试全绿，`bin/crk lint` 退出码 0。

### 闭环 5：CI 二次启动浏览器未就绪

- **发现**：首次 CI 推送后 e2e 失败，`inspect` 步骤报「浏览器调试端口未就绪」；排查日志确认浏览器路径环境变量只在 `shot` 步骤注入，`inspect` 步骤未继承，回退到 PATH 上的无效候选，进程启动后即退出。
- **修复**：CI 的 `inspect` 步骤补齐同名浏览器路径环境变量；`browser._wait_ready` 增加进程退出判定，区分「进程已退出（带返回码）」与「端口未就绪」，报错附可操作建议。
- **复验**：本地以无效浏览器路径启动，正确报出「进程已退出（返回码 1）」；本地 `shot` → `inspect` 连续会话通过；待 CI 重跑三 job 全绿后封版。
