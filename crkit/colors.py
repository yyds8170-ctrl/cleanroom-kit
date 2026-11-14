"""颜色归一化：把计算样式里的颜色字符串统一成结构化 token（纯标准库）。

支持 `#rgb / #rrggbb / #rrggbbaa / rgb() / rgba() / oklch()`；
oklch 按可见近似映射到 sRGB 并标注 `space: "oklch-approx"`；
无法解析的原值保留并标注 `space: "raw"`，不抛异常。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import math
import re

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\s*$")
_RGB_RE = re.compile(r"rgba?\(([^)]+)\)\s*$")
_OKLCH_RE = re.compile(r"oklch\(([^)]+)\)\s*$")


def _clamp_byte(v):
    return min(max(int(round(v)), 0), 255)


def _parse_channel(text):
    text = text.strip()
    if text.endswith("%"):
        return float(text[:-1]) / 100 * 255
    return float(text)


def _oklch_to_srgb(L, C, h):
    """oklch → oklab → 线性 sRGB → sRGB 伽马近似，返回 0-255 三元组。"""
    h_rad = math.radians(h)
    a = C * math.cos(h_rad)
    b = C * math.sin(h_rad)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    b = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3

    def gamma(x):
        x = min(max(x, 0.0), 1.0)
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055

    return (
        _clamp_byte(gamma(r) * 255),
        _clamp_byte(gamma(g) * 255),
        _clamp_byte(gamma(b) * 255),
    )


def parse_color(value):
    """归一化单个颜色字符串。

    返回 `{hex: "#rrggbb" | None, alpha: float, space: str, ...}`；
    raw 分支额外保留 `raw` 原值。
    """
    if not isinstance(value, str) or not value.strip():
        return {"hex": None, "alpha": 1.0, "space": "raw", "raw": value}
    s = value.strip()

    m = _HEX_RE.match(s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        alpha = int(h[6:8], 16) / 255 if len(h) >= 8 else 1.0
        return {"hex": f"#{r:02x}{g:02x}{b:02x}",
                "alpha": round(alpha, 3), "space": "hex"}

    m = _RGB_RE.match(s)
    if m:
        try:
            parts = [t for part in m.group(1).replace("/", ",").split(",")
                     for t in part.split() if t]
            r, g, b = (_parse_channel(parts[0]), _parse_channel(parts[1]),
                       _parse_channel(parts[2]))
            alpha = float(parts[3]) if len(parts) > 3 else 1.0
        except (ValueError, IndexError):
            return {"hex": None, "alpha": 1.0, "space": "raw", "raw": s}
        return {"hex": f"#{_clamp_byte(r):02x}{_clamp_byte(g):02x}{_clamp_byte(b):02x}",
                "alpha": round(min(max(alpha, 0.0), 1.0), 3), "space": "rgb"}

    m = _OKLCH_RE.match(s)
    if m:
        try:
            parts = [p.strip() for p in m.group(1).split()]
            L = float(parts[0].rstrip("%"))
            C = float(parts[1])
            H = float(parts[2])
            if L > 1:
                L /= 100.0
            r, g, b = _oklch_to_srgb(L, C, H)
        except (ValueError, IndexError):
            return {"hex": None, "alpha": 1.0, "space": "raw", "raw": s}
        return {"hex": f"#{r:02x}{g:02x}{b:02x}", "alpha": 1.0,
                "space": "oklch-approx"}

    return {"hex": None, "alpha": 1.0, "space": "raw", "raw": s}


def normalize_palette(colors):
    """色板去重归一化，按 hex + alpha 去重，保留原始顺序。"""
    out, seen = [], set()
    for c in colors or []:
        item = parse_color(c)
        key = (item["hex"], item["alpha"], item["space"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
