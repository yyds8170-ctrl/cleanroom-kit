"""单命令完整闭环验证：截图 → 取证 → 对照 → 无障碍 → 断言 → 基线回归。

在同一会话内串起既有能力，输出分步状态与总 pass/fail 汇总报告（JSON + Markdown）。
纯标准库；对照/断言/基线为可选步骤，缺输入时标记 skipped 不计失败。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json
from pathlib import Path

from . import compare, inspect as imod, a11y, probe, baseline


def aggregate(steps):
    """汇总分步状态，给出总体 pass/fail。"""
    failed = [s for s in steps if not s["pass"]]
    return {
        "overall": "fail" if failed else "pass",
        "summary": {
            "total": len(steps),
            "passed": len(steps) - len(failed),
            "failed": len(failed),
        },
        "steps": steps,
    }


def run_verify(cdp, url, out_dir, ref=None, assertions=None, baseline_name=None,
               max_diff=10.0, width=1280, height=900, mobile=False, wait=1.5,
               timeout=15.0, evidence_root="evidence"):
    """在已连接的 CDP 会话上跑完整闭环，返回汇总报告 dict。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    steps = []

    cdp.set_device_metrics(width, height, mobile=mobile)
    cdp.navigate(url, wait=wait, timeout=timeout)

    # 1. 截图
    data = cdp.screenshot(mobile=mobile, viewport=(width, height))
    shot = out / "shot.png"
    shot.write_bytes(data)
    steps.append({"step": "shot", "pass": True, "artifact": "shot.png",
                   "detail": f"{width}x{height}"})

    # 2. DOM 取证
    report = imod.inspect_page(cdp, url, wait=wait, timeout=timeout)
    imod.write_report(report, out / "inspect.json")
    steps.append({"step": "inspect", "pass": bool(report.get("elements")),
                   "artifact": "inspect.json",
                   "detail": f"元素 {len(report.get('elements', []))}"})

    # 3. 无障碍对比度
    a11y_res = a11y.analyze_inspect(report)
    (out / "a11y.json").write_text(
        json.dumps(a11y_res, ensure_ascii=False, indent=2), encoding="utf-8")
    a11y_pass = a11y_res["summary"]["failed"] == 0
    steps.append({"step": "a11y", "pass": a11y_pass, "artifact": "a11y.json",
                   "detail": f"失败 {a11y_res['summary']['failed']}，"
                             f"未核验 {a11y_res['summary']['unverified']}"})

    # 4. 像素对照（可选）
    cmp_report = None
    if ref:
        cmp_report = compare.compare_images(str(ref), str(shot), resize=True,
                                            max_diff=max_diff)
        compare.write_report_json(cmp_report, out / "compare.json")
        steps.append({"step": "compare",
                       "pass": cmp_report["diff_ratio_pct"] <= max_diff,
                       "artifact": "compare.json",
                       "detail": f"{cmp_report['diff_ratio_pct']}% {cmp_report['verdict']}"})
    else:
        steps.append({"step": "compare", "pass": True, "skipped": True,
                       "detail": "无参考图，跳过对照"})

    # 5. 状态断言（可选）
    if assertions:
        probe_report = probe.run_assertions(cdp, assertions)
        (out / "probe.json").write_text(
            json.dumps({"results": probe_report, "all_pass": probe.all_pass(probe_report)},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        steps.append({"step": "probe", "pass": probe.all_pass(probe_report),
                       "artifact": "probe.json", "detail": f"断言 {len(probe_report)} 条"})
    else:
        steps.append({"step": "probe", "pass": True, "skipped": True,
                       "detail": "未提供断言，跳过"})

    # 6. 基线回归（可选，依赖对照指标）
    if baseline_name and cmp_report:
        current = {k: cmp_report.get(k) for k in baseline.METRIC_KEYS + baseline.CONTENT_KEYS}
        base_res = baseline.diff_snapshot(baseline_name, current, root=evidence_root)
        (out / "baseline.json").write_text(
            json.dumps(base_res, ensure_ascii=False, indent=2), encoding="utf-8")
        steps.append({"step": "baseline", "pass": not base_res["regressed"],
                       "artifact": "baseline.json",
                       "detail": "回归" if base_res["regressed"] else "稳定"})
    else:
        steps.append({"step": "baseline", "pass": True, "skipped": True,
                       "detail": "未指定基线，跳过"})

    result = aggregate(steps)
    result["url"] = url
    return result


def write_report_json(report, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_report_md(report, path):
    lines = ["# 闭环验证报告", ""]
    s = report["summary"]
    lines.append(f"总体判定：**{report['overall']}**（共 {s['total']} 步，"
                 f"通过 {s['passed']}，失败 {s['failed']}）")
    lines.append("")
    lines.append(f"目标：{report.get('url', '—')}")
    lines.append("")
    lines.append("| 步骤 | 状态 | 产物 | 说明 |")
    lines.append("| --- | --- | --- | --- |")
    for st in report["steps"]:
        mark = "跳过" if st.get("skipped") else ("通过" if st["pass"] else "失败")
        lines.append(f"| {st['step']} | {mark} | {st.get('artifact', '—')} | {st['detail']} |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
