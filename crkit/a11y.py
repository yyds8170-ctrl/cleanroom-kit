"""WCAG 相对亮度 / 对比度与 AA / AAA 分级（纯标准库）。

公式对齐 WCAG 2.x：sRGB 分段线性化后按 0.2126/0.7152/0.0722 加权求相对亮度，
对比度 `(L1+0.05)/(L2+0.05)`。颜色输入优先走 v1.7.0 `colors.py` 归一化，
无法解析的组合标注 `unverified`，不抛异常。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
from . import colors

_TEXT_MIN = 4.5   # 正文 AA
_LARGE_MIN = 3.0  # 大字号 / 非文本图形 AA
_TEXT_AAA = 7.0
_LARGE_AAA = 4.5


def parse_hex(value):
    """归一化后返回 `#rrggbb`；无法解析返回 None。"""
    token = colors.parse_color(value)
    return token.get("hex")


def _channel(hexv):
    r = int(hexv[1:3], 16) / 255
    g = int(hexv[3:5], 16) / 255
    b = int(hexv[5:7], 16) / 255

    def lin(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.2

    return lin(r), lin(g), lin(b)


def relative_luminance(hexstr):
    """相对亮度（0–1）；颜色不可解析返回 None。"""
    h = parse_hex(hexstr)
    if not h:
        return None
    r, g, b = _channel(h)
    return round(0.2126 * r + 0.7152 * g + 0.0722 * b, 6)


def contrast_ratio(fg, bg):
    """前景/背景对比度；任一不可解析返回 None。"""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    if l1 is None or l2 is None:
        return None
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _is_large(style):
    """粗体 ≥18px 或常规 ≥24px 视为大字号；缺样式按正文处理。"""
    if not isinstance(style, dict):
        return False
    size = style.get("fontSize") or ""
    weight = style.get("fontWeight") or ""
    try:
        px = float(str(size).rstrip("px"))
    except ValueError:
        px = 0.0
    bold = str(weight) in ("700", "800", "900", "bold")
    return px >= 24 or (bold and px >= 18)


def grade(ratio, large=False):
    """分级：`AAA / AA / A / fail / unverified`。"""
    if ratio is None:
        return "unverified"
    if large:
        if ratio >= _LARGE_AAA:
            return "AAA"
        if ratio >= _LARGE_MIN:
            return "AA"
        return "fail"
    if ratio >= _TEXT_AAA:
        return "AAA"
    if ratio >= _TEXT_MIN:
        return "AA"
    if ratio >= _LARGE_MIN:
        return "A"
    return "fail"


def requirement(large=False):
    return "大字号 AA≥3.0 / AAA≥4.5" if large else "正文 AA≥4.5 / AAA≥7.0"


def _color_display(token):
    """inspect 归一化颜色 token → 展示用前景/背景字符串。"""
    if isinstance(token, dict):
        return token.get("hex") or token.get("raw")
    return token


def _color_record(token):
    """统一成 `{hex, alpha, ...}` 记录，兼容 dict 与颜色字符串。"""
    if isinstance(token, dict):
        return token
    return colors.parse_color(token)


def _hex_of(token):
    """只取不透明颜色；半透明/透明色合成背景未知，标 unverified 更稳妥。"""
    rec = _color_record(token)
    if rec.get("alpha", 1.0) < 0.999:
        return None
    return rec.get("hex")


def _label(el):
    tag = el.get("tag") or "element"
    ident = el.get("id")
    label = f"{tag}#{ident}" if ident else tag
    text = (el.get("text") or "").strip()
    if text:
        label = f"{label}「{text[:24]}」"
    return label


def _opaque(token):
    """颜色 token 是否为可用于配对的不透明颜色（识别 rgba 0 透明度）。"""
    rec = _color_record(token)
    return rec.get("alpha", 1.0) >= 0.999 and bool(rec.get("hex"))


def pair_element(el, fallback_fg=None, fallback_bg=None):
    """把单个取证元素配成对比度行；返回 dict。元素级透明/未取到则回退 body。"""
    style = el.get("style") if isinstance(el, dict) else None
    fg = (style or {}).get("color")
    bg = (style or {}).get("backgroundColor")
    if not _opaque(fg):
        fg = fallback_fg
    if not _opaque(bg):
        bg = fallback_bg
    large = _is_large(style)
    fg_hex, bg_hex = _hex_of(fg), _hex_of(bg)
    ratio = contrast_ratio(fg_hex, bg_hex) if fg_hex and bg_hex else None
    g = grade(ratio, large=large)
    min_ratio = _LARGE_MIN if large else _TEXT_MIN
    passed = ratio is not None and ratio >= min_ratio
    return {
        "element": _label(el),
        "fg": _color_display(fg),
        "bg": _color_display(bg),
        "ratio": ratio,
        "grade": g,
        "large": large,
        "requirement": requirement(large),
        "pass": passed,
    }


def analyze_inspect(report):
    """从 inspect 报告配对前景/背景，汇总对比度表与无障碍清单。"""
    body = report.get("tokens", {}).get("body", {})
    fallback_fg = body.get("color")
    fallback_bg = body.get("backgroundColor")
    pairs = []
    seen = set()
    for el in report.get("elements", []):
        row = pair_element(el, fallback_fg=fallback_fg, fallback_bg=fallback_bg)
        key = (row["element"], row["fg"], row["bg"])
        if key in seen:
            continue
        seen.add(key)
        pairs.append(row)

    a11y = report.get("a11y", {}) or {}
    checklist = {
        "lang": a11y.get("lang"),
        "images_without_alt": a11y.get("images_without_alt", 0),
        "unnamed_controls": a11y.get("unnamed_controls", []),
        "landmarks": a11y.get("landmarks", []),
    }
    failed = [p for p in pairs if not p["pass"] and p["grade"] != "unverified"]
    unverified = [p for p in pairs if p["grade"] == "unverified"]
    summary = {
        "total": len(pairs),
        "passed": len(pairs) - len(failed) - len(unverified),
        "failed": len(failed),
        "unverified": len(unverified),
    }
    return {"pairs": pairs, "summary": summary, "checklist": checklist}
