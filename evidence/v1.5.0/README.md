# v1.5.0 验证证据 · 浏览器会话与导航可靠性

验证日期：2026-11-14。环境：Linux，Python 3.12.11，浏览器 `/usr/local/bin/chromium`。

## 验证目标

- 本地静态站点：`http://127.0.0.1:8071/`（`bin/crk init /tmp/ck-site` 生成的模板项目，`python3 -m http.server 8071` 提供 HTTP 服务）
- 截图视口：1280 × 900（CDP `Emulation.setDeviceMetricsOverride`）
- 调试端口：9361（正常截图）、9363（取证）、9368（占用复现）、9362（清理闭环）

## 执行命令

```bash
# 1. 正常截图（等待 load 事件，超时上限 10 秒）
bin/crk shot --url http://127.0.0.1:8071/ --out evidence/v1.5.0/shot.png \
    --width 1280 --height 900 --port 9361 --timeout 10

# 2. 端口占用复现：先在 9368 起一个监听 socket，再启动截图
bin/crk shot --url http://127.0.0.1:8071/ --out /tmp/busy.png \
    --port 9368 --timeout 5

# 3. 会话清理闭环（kit API：启动 → 关闭 → 记录 profile 与进程状态）
python3 -c "
import sys, json, os
sys.path.insert(0, '.')
from crkit import browser
s = browser.launch(port=9362, headless=True)
profile = s['profile']
browser.close_session(s)
json.dump({
  'profile_dir': profile,
  'profile_exists_after_close': os.path.exists(profile),
  'process_exited': s['process'].poll() is not None,
  'returncode': s['process'].returncode,
}, open('evidence/v1.5.0/session-cleanup.json', 'w'), ensure_ascii=False, indent=2)
"

# 4. 取证路径回归（同样走统一清理）
bin/crk inspect --url http://127.0.0.1:8071/ --out /tmp/inspect-v15.json \
    --width 1280 --height 900 --port 9363 --timeout 10
```

## 验收判据与结果

| 判据 | 阈值 / 期望 | 实测 | 结果 |
| --- | --- | --- | --- |
| 截图尺寸 | 1280 × 900 | 1280 × 900（RGB，14098 bytes） | 通过 |
| 截图非空白 | 含模板 `<h1>` 正文 | 标题与「从这里开始你的洁净室复刻。」段落可见 | 通过 |
| 占用端口报错 | 退出码 1，报错含端口号与换端口建议 | `错误：调试端口 9368 已被占用，请更换 --port 后重试` | 通过 |
| 临时 profile 回收 | 关闭后目录不存在 | `profile_exists_after_close: false` | 通过 |
| 进程退出 | 关闭后主进程已退出 | `process_exited: true`，`returncode: 0` | 通过 |
| 无 kit 残留进程 | 无 `crk-profile-*` 调试浏览器 | 复查无 kit-profile 进程 | 通过 |
| 取证回归 | 元素数 > 0，视口一致 | 3 个元素，视口 1280×900 | 通过 |

## 产物清单

| 文件 | 说明 |
| --- | --- |
| `shot.png` | 本地模板站点 1280×900 真实浏览器截图 |
| `busy-port-error.txt` | 端口占用时的 CLI 报错留档（退出码 1） |
| `session-cleanup.json` | 会话关闭后 profile 回收与进程退出状态记录 |
| `README.md` | 本验证说明 |

## 闭环记录

### 闭环 1（W2）：临时 profile 堆积、无端口预检、超时报错笼统

- **发现**：此前每次启动都 `mkdtemp` 创建 profile 但从不删除，反复运行在系统临时目录堆积；启动前不检查端口是否被占用；超时只抛「调试端口未就绪」，不区分进程已退出还是端口未释放。
- **修复**：`browser.port_in_use` 标准库预检，占用时中文报错并建议换 `--port`；新增 `close_session` 统一回收：`terminate` → 等待 3 秒 → 必要时 `kill`，再 `rmtree` 临时 profile；就绪判定区分「进程已退出（带返回码）」与「端口未就绪」。
- **复验**：`session-cleanup.json` 记录 profile 已回收、进程退出码 0；连续 shot/inspect 后无 kit 残留进程；占用端口复现报错清晰含端口号。

### 闭环 2（W4）：WebSocket 续帧未重组、二进制帧静默解码

- **发现**：`ws.recv_text` 按单帧返回，未处理 opcode 0x0 续帧，大响应被分片时会拼包失败；收到二进制帧（0x2）时被静默当文本解码，出现乱码。
- **修复**：续帧与前一文本帧拼接，FIN 置位后才返回完整文本；二进制帧抛出明确中文报错「当前 WebSocket 客户端仅支持文本帧」。
- **复验**：`test_continuation_frame_reassembled` 用两段续帧拼出完整文本；`test_binary_frame_raises_clear_error` 断言二进制帧抛中文报错。

### 闭环 3（W3 导航）：导航纯 sleep，不等真实加载事件

- **发现**：`cdp.navigate` 只 `time.sleep(wait)`，异步字体/图片/脚本未渲染完就继续，可能截到半成品页面。
- **修复**：导航先 `Page.enable`，在事件流中等待 `Page.loadEventFired`；新增 `wait_for_load(timeout)`，超时回退到 `wait` 秒兜底缓冲；`shot`/`inspect` 新增 `--timeout`（默认 15 秒）透传。
- **复验**：本地站点截图与取证均正常；`test_navigate_waits_for_load_event` 断言 `Page.enable` → `Page.navigate` 调用顺序且等待逻辑接入事件流。

### 闭环 4：CLI 运行期异常抛裸栈

- **发现**：端口占用、浏览器缺失等运行期错误直接抛出 Python 栈跟踪，终端阅读不友好。
- **修复**：`main` 统一捕获 `RuntimeError`，以「错误：…」中文信息输出到 stderr 并以退出码 1 结束。
- **复验**：占用端口复现只输出一行中文错误，退出码 1；正常命令路径不受影响。
