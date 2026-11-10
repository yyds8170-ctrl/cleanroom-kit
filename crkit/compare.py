"""零依赖像素对照：基于 pngio，量化两张截图的差异。"""
from .pngio import read_png_rgb, write_png


def _load_pair(orig_path, rebuild_path, crop=False):
    """读取并归一化为 RGB。尺寸不一致时，crop=True 裁剪到共同最小区域。"""
    w1, h1, a = read_png_rgb(orig_path)
    w2, h2, b = read_png_rgb(rebuild_path)
    if (w1, h1) != (w2, h2):
        if not crop:
            raise ValueError(
                f"尺寸不一致：原版 {w1}x{h1}  vs 复刻 {w2}x{h2}，"
                "请统一视口，或加 --crop 裁剪到共同区域"
            )
        cw, ch = min(w1, w2), min(h1, h2)
        a = _crop_rgb(a, w1, h1, cw, ch)
        b = _crop_rgb(b, w2, h2, cw, ch)
        w1, h1 = cw, ch
    return w1, h1, a, b


def _crop_rgb(px, w, h, cw, ch):
    out = bytearray(cw * ch * 3)
    for y in range(ch):
        src = y * w * 3
        out[y * cw * 3:y * cw * 3 + cw * 3] = px[src:src + cw * 3]
    return out


def _corner_bg(w, h, px):
    raw = [(5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5)]
    coords = sorted({
        (min(max(x, 0), w - 1), min(max(y, 0), h - 1)) for x, y in raw
    })
    pts = [px[(y * w + x) * 3:(y * w + x) * 3 + 3] for x, y in coords]
    return tuple(sorted(ch[i] for ch in pts)[len(pts) // 2] for i in range(3))


def compare_images(orig_path, rebuild_path, threshold=20, crop=False):
    w1, h1, a, b = _load_pair(orig_path, rebuild_path, crop=crop)

    bg1 = _corner_bg(w1, h1, a)
    bg2 = _corner_bg(w1, h1, b)

    n = w1 * h1
    total_diff = 0
    diff_pixels = 0
    content_min, content_max = w1, -1
    for i in range(n):
        o = i * 3
        ar, ag, ab_ = a[o], a[o + 1], a[o + 2]
        d = abs(ar - b[o]) + abs(ag - b[o + 1]) + abs(ab_ - b[o + 2])
        total_diff += d
        if d > threshold:
            diff_pixels += 1
            col = i % w1
            if col < content_min:
                content_min = col
            if col > content_max:
                content_max = col

    def content_cols(px, bg):
        lo, hi = w1, -1
        for i in range(n):
            o = i * 3
            if abs(px[o] - bg[0]) + abs(px[o + 1] - bg[1]) + abs(px[o + 2] - bg[2]) > threshold:
                col = i % w1
                lo, hi = min(lo, col), max(hi, col)
        return (lo, hi) if hi >= 0 else None

    return {
        "size": (w1, h1),
        "bg_original": bg1,
        "bg_rebuild": bg2,
        "bg_match": bg1 == bg2,
        "mean_abs_diff": total_diff / n,
        "diff_ratio_pct": diff_pixels / n * 100,
        "content_original": content_cols(a, bg1),
        "content_rebuild": content_cols(b, bg2),
    }


def build_diff_image(orig_path, rebuild_path, threshold=20, crop=False):
    """返回 (width, height, rgb)。差异像素标红，一致区域灰化（保留原版上下文）。"""
    w1, h1, a, b = _load_pair(orig_path, rebuild_path, crop=crop)
    n = w1 * h1
    out = bytearray(n * 3)
    for i in range(n):
        o = i * 3
        d = abs(a[o] - b[o]) + abs(a[o + 1] - b[o + 1]) + abs(a[o + 2] - b[o + 2])
        if d > threshold:
            out[o], out[o + 1], out[o + 2] = 255, 0, 0
        else:
            gray = int(((a[o] + a[o + 1] + a[o + 2]) // 3) * 0.45)
            out[o], out[o + 1], out[o + 2] = gray, gray, gray
    return w1, h1, out


def write_diff_image(orig_path, rebuild_path, out_path, threshold=20, crop=False):
    w, h, rgb = build_diff_image(orig_path, rebuild_path, threshold, crop)
    write_png(out_path, w, h, rgb)
    return out_path


def format_report(r):
    lines = [
        f"尺寸: {r['size'][0]}x{r['size'][1]}",
        f"背景色 原版{r['bg_original']} 复刻{r['bg_rebuild']} 一致={r['bg_match']}",
        f"平均像素差: {r['mean_abs_diff']:.2f}",
        f"差异像素占比: {r['diff_ratio_pct']:.1f}%",
        f"内容列 原版{r['content_original']} 复刻{r['content_rebuild']}",
    ]
    return "\n".join(lines)
