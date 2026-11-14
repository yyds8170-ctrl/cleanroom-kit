"""零依赖像素对照：基于 pngio，量化两张截图的差异（纯标准库）。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json

from .pngio import read_png_rgb, write_png


def _load_pair(orig_path, rebuild_path, crop=False, resize=False):
    """读取并归一化为 RGB。尺寸不一致时 crop 裁剪、resize 缩放对齐。"""
    w1, h1, a = read_png_rgb(orig_path)
    w2, h2, b = read_png_rgb(rebuild_path)
    if (w1, h1) != (w2, h2):
        if crop and resize:
            raise ValueError("--crop 与 --resize 互斥，请二选一")
        if crop:
            cw, ch = min(w1, w2), min(h1, h2)
            a = _crop_rgb(a, w1, h1, cw, ch)
            b = _crop_rgb(b, w2, h2, cw, ch)
            w1, h1 = cw, ch
        elif resize:
            b = _resize_rgb(b, w2, h2, w1, h1)
        else:
            raise ValueError(
                f"尺寸不一致：原版 {w1}x{h1}  vs 复刻 {w2}x{h2}，"
                "请统一视口，或加 --crop 裁剪 / --resize 缩放对齐"
            )
    return w1, h1, a, b


def _crop_rgb(px, w, h, cw, ch):
    out = bytearray(cw * ch * 3)
    for y in range(ch):
        src = y * w * 3
        out[y * cw * 3:y * cw * 3 + cw * 3] = px[src:src + cw * 3]
    return out


def _resize_rgb(px, w, h, tw, th):
    """等比缩放对齐到目标画布（保持宽高比，居中留边，最近邻，纯标准库）。"""
    fill = _corner_bg(w, h, px)
    scale = min(tw / w, th / h)
    nw = max(1, min(tw, round(w * scale)))
    nh = max(1, min(th, round(h * scale)))
    out = bytearray(tw * th * 3)
    for i in range(tw * th):
        out[i * 3:i * 3 + 3] = bytes(fill)
    ox = (tw - nw) // 2
    oy = (th - nh) // 2
    for y in range(nh):
        sy = min(h - 1, y * h // nh)
        for x in range(nw):
            sx = min(w - 1, x * w // nw)
            src = (sy * w + sx) * 3
            dst = ((oy + y) * tw + (ox + x)) * 3
            out[dst:dst + 3] = px[src:src + 3]
    return out


def _corner_bg(w, h, px, margin=5):
    raw = [(margin, margin), (w - margin, margin),
           (margin, h - margin), (w - margin, h - margin)]
    coords = sorted({
        (min(max(x, 0), w - 1), min(max(y, 0), h - 1)) for x, y in raw
    })
    pts = [px[(y * w + x) * 3:(y * w + x) * 3 + 3] for x, y in coords]
    return tuple(sorted(ch[i] for ch in pts)[len(pts) // 2] for i in range(3))


def _content_cols(px, w, h, bg, threshold):
    lo, hi = w, -1
    n = w * h
    for i in range(n):
        o = i * 3
        if abs(px[o] - bg[0]) + abs(px[o + 1] - bg[1]) + abs(px[o + 2] - bg[2]) > threshold:
            col = i % w
            lo, hi = min(lo, col), max(hi, col)
    return (lo, hi) if hi >= 0 else None


def _content_rows(px, w, h, bg, threshold):
    lo, hi = h, -1
    n = w * h
    for i in range(n):
        o = i * 3
        if abs(px[o] - bg[0]) + abs(px[o + 1] - bg[1]) + abs(px[o + 2] - bg[2]) > threshold:
            row = i // w
            lo, hi = min(lo, row), max(hi, row)
    return (lo, hi) if hi >= 0 else None


def _verdict(diff_ratio_pct, max_diff):
    if diff_ratio_pct <= max_diff * 0.5:
        return "match"
    if diff_ratio_pct <= max_diff:
        return "minor"
    return "major"


def compare_images(orig_path, rebuild_path, threshold=20, crop=False, resize=False,
                   max_diff=10.0, grid_cols=8, grid_rows=6, bg_margin=5):
    w1, h1, a, b = _load_pair(orig_path, rebuild_path, crop=crop, resize=resize)

    bg1 = _corner_bg(w1, h1, a, bg_margin)
    bg2 = _corner_bg(w1, h1, b, bg_margin)

    n = w1 * h1
    total_diff = 0
    diff_pixels = 0
    cell_total = [[0] * grid_cols for _ in range(grid_rows)]
    cell_diff = [[0] * grid_cols for _ in range(grid_rows)]
    for i in range(n):
        o = i * 3
        ar, ag, ab_ = a[o], a[o + 1], a[o + 2]
        d = abs(ar - b[o]) + abs(ag - b[o + 1]) + abs(ab_ - b[o + 2])
        total_diff += d
        col = i % w1
        row = i // w1
        gc = min(grid_cols - 1, col * grid_cols // w1)
        gr = min(grid_rows - 1, row * grid_rows // h1)
        cell_total[gr][gc] += 1
        if d > threshold:
            diff_pixels += 1
            cell_diff[gr][gc] += 1

    buckets = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            total = cell_total[r][c]
            diff = cell_diff[r][c]
            buckets.append({
                "row": r, "col": c,
                "diff_pixels": diff,
                "diff_ratio_pct": (diff / total * 100) if total else 0.0,
            })

    diff_ratio = diff_pixels / n * 100
    return {
        "size": (w1, h1),
        "bg_original": bg1,
        "bg_rebuild": bg2,
        "bg_match": bg1 == bg2,
        "mean_abs_diff": total_diff / n,
        "diff_ratio_pct": diff_ratio,
        "content_original": _content_cols(a, w1, h1, bg1, threshold),
        "content_rebuild": _content_cols(b, w1, h1, bg2, threshold),
        "content_rows_original": _content_rows(a, w1, h1, bg1, threshold),
        "content_rows_rebuild": _content_rows(b, w1, h1, bg2, threshold),
        "grid": {"cols": grid_cols, "rows": grid_rows, "buckets": buckets},
        "verdict": _verdict(diff_ratio, max_diff),
        "max_diff": max_diff,
    }


def build_diff_image(orig_path, rebuild_path, threshold=20, crop=False, resize=False):
    """返回 (width, height, rgb)。差异像素标红，一致区域灰化（保留原版上下文）。"""
    w1, h1, a, b = _load_pair(orig_path, rebuild_path, crop=crop, resize=resize)
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


def write_diff_image(orig_path, rebuild_path, out_path, threshold=20, crop=False, resize=False):
    w, h, rgb = build_diff_image(orig_path, rebuild_path, threshold, crop, resize)
    write_png(out_path, w, h, rgb)
    return out_path


def write_report_json(report, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return out_path


def _heaviest_bucket(report):
    buckets = report.get("grid", {}).get("buckets", [])
    if not buckets:
        return None
    return max(buckets, key=lambda b: b["diff_ratio_pct"])


def format_report(r):
    lines = [
        f"尺寸: {r['size'][0]}x{r['size'][1]}",
        f"背景色 原版{r['bg_original']} 复刻{r['bg_rebuild']} 一致={r['bg_match']}",
        f"平均像素差: {r['mean_abs_diff']:.2f}",
        f"差异像素占比: {r['diff_ratio_pct']:.1f}%",
        f"内容列 原版{r['content_original']} 复刻{r['content_rebuild']}",
        f"内容行 原版{r['content_rows_original']} 复刻{r['content_rows_rebuild']}",
    ]
    heavy = _heaviest_bucket(r)
    if heavy and heavy["diff_ratio_pct"] > 0:
        lines.append(
            f"差异最重桶: 第{heavy['row'] + 1}行 第{heavy['col'] + 1}列 "
            f"({heavy['diff_ratio_pct']:.1f}%)"
        )
    lines.append(f"判定: {r['verdict']}（阈值 {r['max_diff']}%）")
    return "\n".join(lines)
