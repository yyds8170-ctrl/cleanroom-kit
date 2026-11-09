"""零依赖像素对照：基于 pngio，量化两张截图的差异。"""
from .pngio import read_png


def _corner_bg(w, h, c, px):
    pts = [
        (px[(y * w + x) * c:(y * w + x) * c + 3])
        for x, y in [(5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5)]
    ]
    return tuple(sorted(ch[i] for ch in pts)[len(pts) // 2] for i in range(3))


def compare_images(orig_path, rebuild_path, threshold=20):
    w1, h1, c1, a = read_png(orig_path)
    w2, h2, c2, b = read_png(rebuild_path)
    if (w1, h1) != (w2, h2):
        raise ValueError(f"尺寸不一致：原版 {w1}x{h1} vs 复刻 {w2}x{h2}，请先统一视口")

    bg1 = _corner_bg(w1, h1, c1, a)
    bg2 = _corner_bg(w2, h2, c2, b)

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

    # 内容列（基于与各自背景的差异）
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


def format_report(r):
    lines = [
        f"尺寸: {r['size'][0]}x{r['size'][1]}",
        f"背景色 原版{r['bg_original']} 复刻{r['bg_rebuild']} 一致={r['bg_match']}",
        f"平均像素差: {r['mean_abs_diff']:.2f}",
        f"差异像素占比: {r['diff_ratio_pct']:.1f}%",
        f"内容列 原版{r['content_original']} 复刻{r['content_rebuild']}",
    ]
    return "\n".join(lines)
