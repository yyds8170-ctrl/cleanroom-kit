"""批量流水线：截图 → 取证 → 对照 → 汇总报告（纯标准库编排）。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json
import zipfile
from pathlib import Path

from . import compare


def load_targets(path):
    """读取多目标配置 `[{name, url, widths?}]`，校验 name/url。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("targets 配置必须是数组")
    for i, t in enumerate(data):
        if not isinstance(t, dict) or not t.get("name") or not t.get("url"):
            raise RuntimeError(f"第 {i + 1} 个目标缺 name/url：{t}")
    return data


def aggregate(target_reports):
    """汇总逐项指标与断言摘要，给出总体 pass/fail。"""
    failed = [t for t in target_reports if not t.get("pass")]
    assertions = [a for t in target_reports for a in (t.get("assertions") or [])]
    a_passed = sum(1 for a in assertions if a.get("pass"))
    return {
        "targets": target_reports,
        "overall": "fail" if failed else "pass",
        "summary": {
            "total": len(target_reports),
            "passed": len(target_reports) - len(failed),
            "failed": len(failed),
        },
        "assertions": {
            "total": len(assertions),
            "passed": a_passed,
            "failed": len(assertions) - a_passed,
        },
    }


def write_report_json(report, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def write_report_md(report, path):
    lines = ["# 流水线汇总报告", ""]
    s = report["summary"]
    lines.append(f"总体判定：**{report['overall']}**（共 {s['total']}，通过 {s['passed']}，失败 {s['failed']}）")
    a = report.get("assertions") or {"total": 0, "passed": 0, "failed": 0}
    lines.append(f"断言摘要：共 {a['total']}，通过 {a['passed']}，失败 {a['failed']}")
    lines.append("")
    lines.append("| 目标 | 模式 | 尺寸 | 背景一致 | 平均差 | 差异占比 | 判定 | 最重桶 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in report["targets"]:
        c = t.get("compare") or {}
        heavy = c.get("heaviest_bucket")
        heavy_txt = f"第{heavy['row'] + 1}行第{heavy['col'] + 1}列 {heavy['diff_ratio_pct']:.1f}%" if heavy else "—"
        size = f"{c['size'][0]}x{c['size'][1]}" if c.get("size") else "—"
        mode = t.get("mode", "forensics-only")
        mode_txt = "对照" if mode == "compare" else "仅取证"
        lines.append(
            f"| {t['name']} | {mode_txt} | {size} | {c.get('bg_match', '—')} | "
            f"{c.get('mean_abs_diff', '—')} | {c.get('diff_ratio_pct', '—')}% | "
            f"{c.get('verdict', '无对照')} | {heavy_txt} |"
        )
    lines.append("")
    lines.append("> 仅取证目标不做像素对照门禁，其通过仅表示截图与取证完成。")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def archive_zip(out_dir, zip_path, extra_dirs=()):
    """把本轮证据目录及额外目录（参考图、基线快照等）打包为 zip。"""
    out_dir = Path(out_dir)
    Path(zip_path).parent.mkdir(parents=True, exist_ok=True)
    roots = [out_dir] + [Path(p) for p in extra_dirs if Path(p).exists()]
    base = out_dir.parent
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root in roots:
            for f in sorted(root.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(base))
    return zip_path


def compare_subset(report):
    """从 compare 报告抽取汇总所需指标。"""
    if not report:
        return None
    heavy = None
    buckets = report.get("grid", {}).get("buckets", [])
    if buckets:
        heavy = max(buckets, key=lambda b: b["diff_ratio_pct"])
    return {
        "size": report.get("size"),
        "bg_match": report.get("bg_match"),
        "mean_abs_diff": round(report.get("mean_abs_diff", 0.0), 2),
        "diff_ratio_pct": round(report.get("diff_ratio_pct", 0.0), 1),
        "verdict": report.get("verdict"),
        "heaviest_bucket": heavy,
    }
