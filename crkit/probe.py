"""页面状态断言取证：把交互后的页面状态断言成结构化 JSON。

断言 schema：
`[{name, selector?, expect: {text?|class?|attribute?|visible?|state_js?}, value?}]`

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json
from pathlib import Path

from . import act


def _element_snapshot(cdp, selector):
    expr = (
        "(()=>{const el=document.querySelector(" + json.dumps(selector) + ");"
        "if(!el)return null;const r=el.getBoundingClientRect();"
        "return{text:(el.textContent||'').trim(),className:el.className||'',"
        "attrs:Object.fromEntries([...el.attributes].map(a=>[a.name,a.value])),"
        "visible:r.width>0&&r.height>0};})()"
    )
    return cdp.evaluate(expr)


def run_assertions(cdp, assertions):
    """逐条断言，返回 `{name, pass, expected, actual, reason}` 清单。"""
    report = []
    for item in assertions:
        name = item.get("name", "")
        expect = item.get("expect", {})
        selector = item.get("selector")
        if item.get("steps"):
            act.run_steps(cdp, item["steps"])
        actual = None
        ok = True
        reason = None
        if "state_js" in expect:
            actual = cdp.eval_state(expect["state_js"])
            ok = bool(actual)
        else:
            el = _element_snapshot(cdp, selector) if selector else None
            if el is None:
                ok = False
                reason = "元素未找到"
            elif "text" in expect:
                actual = el["text"]
                ok = el["text"] == expect["text"]
            elif "class" in expect:
                actual = el["className"]
                ok = expect["class"] in el["className"]
            elif "attribute" in expect:
                attr = expect["attribute"]
                actual = el["attrs"].get(attr.get("name"))
                ok = actual == attr.get("value")
            elif "visible" in expect:
                actual = el["visible"]
                ok = bool(el["visible"]) == bool(expect["visible"])
        report.append({"name": name, "pass": ok, "expected": expect,
                       "actual": actual, "reason": reason})
    return report


def all_pass(report):
    return all(item["pass"] for item in report)


def load_assertions(path):
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"断言文件不存在：{path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"断言 JSON 解析失败：{exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError("断言序列必须是数组")
    return data
