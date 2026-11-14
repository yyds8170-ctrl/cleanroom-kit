"""交互动作序列执行（纯标准库，CDP 驱动）。

动作项 schema：
`{op: "click"|"type"|"key"|"scroll"|"wait"|"eval"|"screenshot",
 target?, text?, code?, x?, y?, condition?, timeout?, out?, full_page?}`

- `click`：`target` 选择器，点击匹配元素。
- `type`：`target` 选择器 + `text`，聚焦并填入文本，派发 input。
- `key`：`code` 键盘码（如 `Space`），派发 keydown/keyup。
- `scroll`：`x` / `y` 滚动坐标。
- `wait`：`condition` 条件表达式 + 可选 `timeout`（秒）。
- `eval`：`condition` 表达式，返回值记入日志 `value`。
- `screenshot`：`out` 截图路径，可选 `full_page` 布尔。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json
import time
from pathlib import Path

VALID_OPS = {"click", "type", "key", "scroll", "wait", "eval", "screenshot"}


def load_steps(script_path=None, inline=None):
    """读取并校验动作序列，返回有序步骤列表；非法动作抛中文错误。"""
    if script_path:
        sp = Path(script_path)
        if not sp.exists():
            raise RuntimeError(f"动作序列文件不存在：{script_path}")
        raw = sp.read_text(encoding="utf-8")
    elif inline:
        raw = inline
    else:
        raise RuntimeError("act 需要 --script 或 --steps 提供动作序列")
    try:
        steps = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"动作序列 JSON 解析失败：{e}")
    if not isinstance(steps, list):
        raise RuntimeError("动作序列必须是数组")
    for i, step in enumerate(steps):
        op = step.get("op") if isinstance(step, dict) else None
        if op not in VALID_OPS:
            raise RuntimeError(f"第 {i + 1} 步动作非法或未知：{op}")
    return steps


def run_steps(cdp, steps):
    """按顺序执行动作，逐步记录 `ok / elapsed_ms / error`，单步失败不中断后续。"""
    report = []
    for step in steps:
        op = step["op"]
        t0 = time.time()
        err = None
        value = None
        try:
            if op == "click":
                cdp.click(step["target"])
            elif op == "type":
                cdp.type_text(step["target"], step.get("text", ""))
            elif op == "key":
                cdp.press_key(step["code"])
            elif op == "scroll":
                cdp.scroll_to(step.get("x", 0), step.get("y", 0))
            elif op == "wait":
                cdp.wait_for(step["condition"], timeout=step.get("timeout", 15))
            elif op == "eval":
                value = cdp.eval_state(step.get("condition", ""))
            elif op == "screenshot":
                data = cdp.screenshot(full_page=step.get("full_page", False))
                Path(step["out"]).write_bytes(data)
        except Exception as e:  # 记录失败步骤，继续后续动作
            err = str(e)
        report.append({
            "op": op,
            "target": step.get("target"),
            "ok": err is None,
            "elapsed_ms": round((time.time() - t0) * 1000, 1),
            "error": err,
            "value": value,
        })
    return report
