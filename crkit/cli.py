"""cleanroom-kit 统一命令行入口（argparse，标准库）。"""
import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

from . import browser as bmod
from . import cleanwords
from . import inspect as imod
from . import compare
from . import pngio
from . import act, probe, a11y, pipeline, baseline, verify
from .cdp import CDP, get_page_ws
from .compare import compare_images, format_report
from .license import write_license
from .scaffold import init_project
from .version import get_version


def cmd_init(a):
    if a.dir:
        target = Path(a.dir)
        name = a.name
    else:
        target = Path(a.name)
        name = target.name
    p = init_project(target, name, a.desc or "", stack=a.stack,
                     author=a.author, github_user=a.github_user,
                     github_repo=a.github_repo, year=a.year, force=a.force)
    print(f"已创建项目：{p}（栈：{a.stack}）")


def cmd_license(a):
    p = write_license(a.dir or ".", a.name, a.note or "", year=a.year)
    print(f"已生成 LICENSE：{p}")


def cmd_browser(a):
    r = bmod.launch(port=a.port, url=a.url, headless=not a.show)
    try:
        print(f"浏览器已启动：{r['browser']} 调试端口 {r['port']}")
        if a.show:
            r["process"].wait()
    finally:
        bmod.close_session(r)


def _parse_widths(text):
    if not text:
        return []
    out = []
    for x in text.split(","):
        x = x.strip()
        if not x:
            continue
        try:
            v = int(x)
        except ValueError:
            raise RuntimeError(f"--widths 宽度必须为整数，收到：{x}")
        if v <= 0:
            raise RuntimeError(f"--widths 宽度必须为正数，收到：{v}")
        out.append(v)
    return out


def _expand_outputs(out, widths):
    if not widths:
        return [out]
    p = Path(out)
    suffix = p.suffix or ".png"
    return [str(p.with_name(f"{p.stem}-{w}{suffix}")) for w in widths]


def cmd_shot(a):
    _validate_viewport(a.width, a.height)
    widths = _parse_widths(a.widths)
    targets = widths or [a.width]
    outs = _expand_outputs(a.out, widths)
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        for width, out in zip(targets, outs):
            c.set_device_metrics(width, a.height, mobile=a.mobile)
            c.navigate(a.url, wait=a.wait, timeout=a.timeout)
            data = c.screenshot(full_page=a.full_page, mobile=a.mobile,
                                viewport=(width, a.height))
            with open(out, "wb") as f:
                f.write(data)
            w_out, h_out, _, _ = pngio.read_png(out)
            print(f"已保存截图（{w_out}x{h_out}）：{out}（{len(data)} bytes）")
        c.close()
    finally:
        bmod.close_session(r)


def _validate_compare_options(a):
    if a.crop and a.resize:
        raise RuntimeError("--crop 与 --resize 互斥，请二选一")
    for label, path in (("原版图", a.orig), ("复刻图", a.rebuild)):
        if not Path(path).exists():
            raise RuntimeError(f"{label}不存在：{path}")


def _validate_viewport(width, height):
    if width <= 0 or height <= 0:
        raise RuntimeError(f"视口宽高必须为正数，收到：{width}×{height}")


def cmd_compare(a):
    _validate_compare_options(a)
    r = compare_images(a.orig, a.rebuild, threshold=a.threshold, crop=a.crop,
                       resize=a.resize, max_diff=a.max_diff)
    print(format_report(r))
    if a.diff_out:
        compare.write_diff_image(a.orig, a.rebuild, a.diff_out,
                                 threshold=a.threshold, crop=a.crop, resize=a.resize)
        print(f"差异热图已保存：{a.diff_out}")
    if a.json:
        compare.write_report_json(r, a.json)
        print(f"结构化报告已保存：{a.json}")
    if r["diff_ratio_pct"] > a.max_diff:
        print(f"差异 {r['diff_ratio_pct']:.1f}% 超过阈值 {a.max_diff}%", file=sys.stderr)
        sys.exit(1)


def cmd_inspect(a):
    _validate_viewport(a.width, a.height)
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        c.set_device_metrics(a.width, a.height, mobile=a.mobile)
        data = imod.inspect_page(c, a.url, wait=a.wait, timeout=a.timeout,
                                 full_page=a.full_page, max_text=a.max_text)
        imod.write_report(data, a.out)
        if a.text_out:
            imod.write_plaintext(data, a.text_out)
        c.close()
        print(
            f"已取证：{a.out}（{len(data.get('elements', []))} 个元素，"
            f"{len(data.get('palette', []))} 种颜色）"
        )
    finally:
        bmod.close_session(r)


def cmd_act(a):
    _validate_viewport(a.width, a.height)
    steps = act.load_steps(script_path=a.script, inline=a.steps)
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        c.set_device_metrics(a.width, a.height, mobile=a.mobile)
        c.navigate(a.url, wait=a.wait, timeout=a.timeout)
        report = act.run_steps(c, steps)
        c.close()
    finally:
        bmod.close_session(r)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"steps": report}, f, ensure_ascii=False, indent=2)
    failed = [x for x in report if not x["ok"]]
    print(f"动作完成：{len(report)} 步，失败 {len(failed)} 步")
    if failed:
        for x in failed:
            print(f"  失败：{x['op']} {x.get('target') or ''} - {x['error']}", file=sys.stderr)
        sys.exit(1)


def cmd_probe(a):
    _validate_viewport(a.width, a.height)
    assertions = probe.load_assertions(a.assertions)
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        c.set_device_metrics(a.width, a.height, mobile=a.mobile)
        c.navigate(a.url, wait=a.wait, timeout=a.timeout)
        if a.script:
            act.run_steps(c, act.load_steps(script_path=a.script))
        report = probe.run_assertions(c, assertions)
        c.close()
    finally:
        bmod.close_session(r)
    payload = {"results": report, "all_pass": probe.all_pass(report)}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    for item in report:
        mark = "PASS" if item["pass"] else "FAIL"
        print(f"[{mark}] {item['name']}（期望 {item['expected']}，实测 {item['actual']}）")
    if not probe.all_pass(report):
        print("存在未通过的断言", file=sys.stderr)
        sys.exit(1)


def cmd_a11y(a):
    if a.inspect:
        if not Path(a.inspect).exists():
            raise RuntimeError(f"取证报告不存在：{a.inspect}")
        report = json.loads(Path(a.inspect).read_text(encoding="utf-8"))
    elif a.url:
        r = bmod.launch(port=a.port, headless=True)
        try:
            c = CDP(get_page_ws("127.0.0.1", a.port))
            c.set_device_metrics(a.width, a.height, mobile=a.mobile)
            report = imod.inspect_page(c, a.url, wait=a.wait, timeout=a.timeout)
            c.close()
        finally:
            bmod.close_session(r)
    else:
        raise RuntimeError("a11y 需要 --inspect 报告路径或 --url 现场取证")

    result = a11y.analyze_inspect(report)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    for p in result["pairs"]:
        ratio = f"{p['ratio']:.2f}:1" if p["ratio"] is not None else "unverified"
        mark = "UNVERIFIED" if p["grade"] == "unverified" else ("PASS" if p["pass"] else "FAIL")
        print(f"[{mark}] {p['element']} 前景 {p['fg']} / 背景 {p['bg']} 对比度 {ratio}（{p['grade']}，{p['requirement']}）")
    s = result["summary"]
    print(f"汇总：共 {s['total']} 组，通过 {s['passed']}，失败 {s['failed']}，未核验 {s['unverified']}")
    if result["checklist"].get("lang") is None:
        print("提示：页面缺少 <html lang> 属性", file=sys.stderr)
    if s["failed"]:
        print(f"{s['failed']} 个颜色组合未达 AA", file=sys.stderr)
        sys.exit(1)


def cmd_pipeline(a):
    if a.targets:
        targets = pipeline.load_targets(a.targets)
    elif a.site:
        targets = [{"name": Path(a.site).name or "site", "url": a.site,
                    "widths": _parse_widths(a.widths) or [a.width]}]
    else:
        raise RuntimeError("pipeline 需要 --targets 配置或 --site 单站地址")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    reports = []
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        for t in targets:
            name, url = t["name"], t["url"]
            widths = t.get("widths") or _parse_widths(a.widths) or [a.width]
            tdir = out / name
            tdir.mkdir(parents=True, exist_ok=True)
            shots = []
            for w in widths:
                c.set_device_metrics(w, a.height, mobile=a.mobile)
                c.navigate(url, wait=a.wait, timeout=a.timeout)
                data = c.screenshot(mobile=a.mobile, viewport=(w, a.height))
                sp = tdir / f"shot-{w}.png"
                sp.write_bytes(data)
                shots.append(str(sp))
            c.set_device_metrics(widths[0], a.height, mobile=a.mobile)
            c.navigate(url, wait=a.wait, timeout=a.timeout)
            insp = imod.inspect_page(c, wait=a.wait, timeout=a.timeout)
            imod.write_report(insp, tdir / "inspect.json")

            assertions = []
            if t.get("assertions"):
                items = probe.load_assertions(Path(t["assertions"]))
                probe_report = probe.run_assertions(c, items)
                (tdir / "probe.json").write_text(
                    json.dumps({"results": probe_report,
                                "all_pass": probe.all_pass(probe_report)},
                               ensure_ascii=False, indent=2), encoding="utf-8")
                assertions = [{"name": x["name"], "pass": x["pass"]} for x in probe_report]

            cmp_report = None
            ref = Path(a.rebuild_dir) / f"{name}.png" if a.rebuild_dir else None
            if ref and ref.exists():
                cmp_report = compare.compare_images(str(ref), shots[0], resize=True,
                                                    max_diff=a.max_diff)
                compare.write_report_json(cmp_report, tdir / "compare.json")
            compare_ok = cmp_report is None or cmp_report["diff_ratio_pct"] <= a.max_diff
            reports.append({
                "name": name, "url": url, "widths": widths, "shots": shots,
                "inspect": str(tdir / "inspect.json"),
                "mode": "compare" if cmp_report else "forensics-only",
                "note": "" if cmp_report else "仅取证，未做像素对照，不参与对照门禁",
                "assertions": assertions,
                "compare": pipeline.compare_subset(cmp_report),
                "pass": compare_ok and all(x["pass"] for x in assertions),
            })
        c.close()
    finally:
        bmod.close_session(r)

    agg = pipeline.aggregate(reports)
    pipeline.write_report_json(agg, out / "report.json")
    pipeline.write_report_md(agg, out / "report.md")
    if a.archive:
        extras = [p for p in (a.rebuild_dir, str(out.parent.parent / "baselines")) if p]
        pipeline.archive_zip(out, a.archive, extra_dirs=extras)
        print(f"证据已归档：{a.archive}")
    print(f"流水线完成：{agg['summary']['total']} 目标，总体 {agg['overall']}")
    if agg["overall"] != "pass":
        sys.exit(1)


def cmd_baseline(a):
    if a.baseline_action == "save":
        metrics = json.loads(Path(a.metrics).read_text(encoding="utf-8")) if a.metrics else {}
        d = baseline.save_snapshot(a.name, metrics, png_path=a.orig, root=a.evidence_root)
        print(f"基线已保存：{d}")
    else:
        current = json.loads(Path(a.current).read_text(encoding="utf-8")) if a.current else {}
        res = baseline.diff_snapshot(a.name, current, max_ratio_drift=a.max_diff,
                                     mean_diff_tol=a.mean_diff_tol,
                                     verdict_strict=not a.lenient_verdict,
                                     root=a.evidence_root)
        for d in res["drift"]:
            print(f"漂移：{d['metric']} 基线 {d['baseline']} → 当前 {d['current']}（{d['detail']}）")
        for ch in res["content_changes"]:
            print(f"内容变化：{ch['field']} 基线 {ch['baseline']} → 当前 {ch['current']}")
        print(f"回归判定：{'regressed' if res['regressed'] else 'stable'}")
        if res["regressed"]:
            sys.exit(1)


def cmd_verify(a):
    _validate_viewport(a.width, a.height)
    if a.ref and not Path(a.ref).exists():
        raise RuntimeError(f"参考图不存在：{a.ref}")
    assertions = probe.load_assertions(a.assertions) if a.assertions else None
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        report = verify.run_verify(
            c, a.url, a.out, ref=a.ref, assertions=assertions,
            baseline_name=a.baseline, max_diff=a.max_diff, width=a.width,
            height=a.height, mobile=a.mobile, wait=a.wait, timeout=a.timeout,
            evidence_root=a.evidence_root)
        c.close()
    finally:
        bmod.close_session(r)
    out = Path(a.out)
    verify.write_report_json(report, out / "report.json")
    verify.write_report_md(report, out / "report.md")
    s = report["summary"]
    print(f"闭环验证：总体 {report['overall']}（{s['passed']}/{s['total']} 步通过）")
    for st in report["steps"]:
        mark = "跳过" if st.get("skipped") else ("PASS" if st["pass"] else "FAIL")
        print(f"  [{mark}] {st['step']}：{st['detail']}")
    if report["overall"] != "pass":
        sys.exit(1)


def cmd_selftest(a):
    import unittest
    import importlib.util
    root = Path(__file__).resolve().parent.parent
    info = _doctor_info(a.port)
    print(f"版本：{info['version']}　Python：{info['python']}　平台：{info['platform']}")
    print(f"浏览器：{info['browser'] or '未找到（可选，截图/取证类命令需要）'}")

    loader = unittest.TestLoader()
    suite = loader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    spec = importlib.util.spec_from_file_location(
        "pre_release_check", root / "scripts" / "pre_release_check.py")
    prc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prc)
    check = prc.run_checks(root)
    for item in check["checks"]:
        if item["name"] == "git 工作区干净":
            continue  # 封版门禁，selftest 阶段仅提示
        mark = "PASS" if item["ok"] else "FAIL"
        print(f"[{mark}] {item['name']}：{item['detail']}")

    consistency_ok = all(c["ok"] for c in check["checks"] if c["name"] != "git 工作区干净")
    ok = result.wasSuccessful() and consistency_ok
    print("自证通过。" if ok else "自证未通过，请查看上方失败项。")
    if not ok:
        sys.exit(1)


def cmd_version(a):
    info = {
        "version": get_version(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "license": "PolyForm Noncommercial License 1.0.0",
    }
    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(f"版本：{info['version']}")
        print(f"Python：{info['python']}")
        print(f"平台：{info['platform']}")
        print(f"许可证：{info['license']}")


def cmd_lint(a):
    root = Path(__file__).resolve().parent.parent
    hits = cleanwords.scan_tree(root)
    if hits:
        print(f"禁用词命中 {len(hits)} 处：", file=sys.stderr)
        for h in hits:
            print(f"{h['file']}:{h['line']}: [{h['word']}] {h['text']}", file=sys.stderr)
        sys.exit(1)
    print("PASS：未发现禁用词。")


def _doctor_info(port=9340):
    import socket
    port_free = True
    try:
        sock = socket.socket()
        sock.bind(("127.0.0.1", port))
        sock.close()
    except OSError:
        port_free = False
    return {
        "version": get_version(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "browser": bmod.find_browser(),
        "node": shutil.which("node"),
        "craft_cli": shutil.which("craft-anything-cli"),
        "port": port,
        "port_free": port_free,
        "license": "PolyForm Noncommercial License 1.0.0",
    }


def cmd_doctor(a):
    info = _doctor_info(a.port)
    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return
    print(f"版本：{info['version']}")
    print(f"Python：{info['python']}")
    print(f"平台：{info['platform']}")
    print(f"浏览器：{info['browser'] or '未找到（请安装 Chrome/Edge/Chromium）'}")
    print(f"Node：{info['node'] or '未安装（可选）'}")
    print(f"craft-anything：{info['craft_cli'] or '未安装（可选增强）'}")
    print(f"端口 {info['port']}：{'空闲' if info['port_free'] else '被占用'}")
    print("所有核心功能仅依赖 Python 标准库，无需 pip 安装。")


def build_parser():
    p = argparse.ArgumentParser(prog="crk", description="洁净室复刻工具包（零依赖、跨平台）")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="从模板创建新项目")
    s.add_argument("name"); s.add_argument("--dir"); s.add_argument("--desc")
    s.add_argument("--stack", choices=["web", "game"], default="web")
    s.add_argument("--author", default="洋洋")
    s.add_argument("--github-user", default="yyds8170-ctrl")
    s.add_argument("--github-repo", help="仓库名（默认与项目名一致）")
    s.add_argument("--year", type=int, help="许可证年份（默认当前年）")
    s.add_argument("--force", action="store_true"); s.set_defaults(func=cmd_init)

    s = sub.add_parser("license", help="生成 PolyForm 许可证")
    s.add_argument("name"); s.add_argument("--dir", default="."); s.add_argument("--note")
    s.add_argument("--year", type=int, help="许可证年份（默认当前年）")
    s.set_defaults(func=cmd_license)

    s = sub.add_parser("browser", help="启动调试浏览器")
    s.add_argument("--port", type=int, default=9340); s.add_argument("--url", default="about:blank")
    s.add_argument("--show", action="store_true"); s.set_defaults(func=cmd_browser)

    s = sub.add_parser("shot", help="设备模拟截图")
    s.add_argument("--url", required=True); s.add_argument("--out", default="shot.png")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9341); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.add_argument("--full-page", action="store_true", help="截取整页长图（跨视口）")
    s.add_argument("--widths", help="逗号分隔多宽度批量出图，如 1280,390")
    s.set_defaults(func=cmd_shot)

    s = sub.add_parser("compare", help="像素对照")
    s.add_argument("--orig", required=True); s.add_argument("--rebuild", required=True)
    s.add_argument("--max-diff", type=float, default=10.0)
    s.add_argument("--threshold", type=int, default=20,
                   help="单像素 RGB 差值判定阈值（默认 20）")
    s.add_argument("--crop", action="store_true",
                   help="尺寸不一致时裁剪到共同最小区域")
    s.add_argument("--resize", action="store_true",
                   help="尺寸不一致时把复刻图缩放对齐到原版尺寸（与 --crop 互斥）")
    s.add_argument("--diff-out", help="差异热图输出路径（差异像素标红）")
    s.add_argument("--json", help="结构化对照报告落盘路径（JSON）")
    s.set_defaults(func=cmd_compare)

    s = sub.add_parser("inspect", help="DOM 取证（设计 token/元素坐标/调色板）")
    s.add_argument("--url", required=True); s.add_argument("--out", default="inspect.json")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9342); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.add_argument("--full-page", action="store_true", help="全页坐标（box.y 叠加滚动偏移）")
    s.add_argument("--text-out", help="纯文本大纲另存路径（.txt）")
    s.add_argument("--max-text", type=int, default=4000, help="纯文本字符上限（默认 4000）")
    s.set_defaults(func=cmd_inspect)

    s = sub.add_parser("act", help="按 JSON 动作序列执行交互（点击/输入/键盘/滚动/等待）")
    s.add_argument("--url", required=True); s.add_argument("--out", help="动作日志 JSON 路径")
    s.add_argument("--script", help="动作序列 JSON 文件路径")
    s.add_argument("--steps", help="内联动作序列 JSON")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9343); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.set_defaults(func=cmd_act)

    s = sub.add_parser("probe", help="页面状态断言，输出结构化断言报告")
    s.add_argument("--url", required=True); s.add_argument("--out", default="probe-report.json")
    s.add_argument("--assertions", required=True, help="断言序列 JSON 文件路径")
    s.add_argument("--script", help="断言前执行的动作序列 JSON（可选，同一会话）")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9344); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.set_defaults(func=cmd_probe)

    s = sub.add_parser("a11y", help="WCAG 对比度与无障碍清单检查")
    s.add_argument("--inspect", help="inspect 报告 JSON 路径")
    s.add_argument("--url", help="现场取证的页面地址（与 --inspect 二选一）")
    s.add_argument("--out", dest="out", help="结构化对比度报告落盘路径（JSON）")
    s.add_argument("--json", dest="out", help="同 --out，结构化 JSON 报告路径")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9366); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.set_defaults(func=cmd_a11y)

    s = sub.add_parser("pipeline", help="批量流水线：截图→取证→对照→汇总报告")
    s.add_argument("--targets", help="多目标配置 JSON（[{name,url,widths}]）")
    s.add_argument("--site", help="单站地址（与 --targets 二选一）")
    s.add_argument("--out", default="evidence/run", help="本轮证据输出目录")
    s.add_argument("--rebuild-dir", help="对照参考图目录（<目标名>.png）")
    s.add_argument("--archive", help="证据归档 zip 路径")
    s.add_argument("--widths", help="逗号分隔多宽度批量出图")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9368); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.add_argument("--max-diff", type=float, default=10.0)
    s.set_defaults(func=cmd_pipeline)

    s = sub.add_parser("baseline", help="基准快照保存与回归比对")
    s.add_argument("baseline_action", choices=["save", "diff"])
    s.add_argument("--name", required=True, help="基线名")
    s.add_argument("--orig", help="基准截图路径（save）")
    s.add_argument("--metrics", help="compare 指标快照 JSON（save）")
    s.add_argument("--current", help="当前指标 JSON（diff）")
    s.add_argument("--max-diff", type=float, default=5.0, help="差异占比回升漂移阈值（百分点）")
    s.add_argument("--mean-diff-tol", type=float, default=3.0, help="平均差绝对容差")
    s.add_argument("--lenient-verdict", action="store_true",
                   help="verdict 宽松口径：match/minor 互不算降级")
    s.add_argument("--evidence-root", default="evidence", help="证据根目录")
    s.set_defaults(func=cmd_baseline)

    s = sub.add_parser("verify", help="单命令完整闭环：截图→取证→对照→无障碍→断言→基线")
    s.add_argument("--url", required=True)
    s.add_argument("--out", default="evidence/verify", help="闭环证据输出目录")
    s.add_argument("--ref", help="对照参考图 PNG（可选，提供后执行像素对照）")
    s.add_argument("--assertions", help="断言序列 JSON（可选，提供后执行 probe）")
    s.add_argument("--baseline", help="基线名（可选，对照后做回归比对）")
    s.add_argument("--max-diff", type=float, default=10.0)
    s.add_argument("--evidence-root", default="evidence", help="证据根目录")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=900)
    s.add_argument("--port", type=int, default=9367); s.add_argument("--mobile", action="store_true")
    s.add_argument("--wait", type=float, default=1.5)
    s.add_argument("--timeout", type=float, default=15.0, help="导航加载等待上限（秒）")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("selftest", help="clone 即自证：环境自检 + 单测 + 发布一致性自检")
    s.add_argument("--port", type=int, default=9340, help="自检端口")
    s.set_defaults(func=cmd_selftest)

    s = sub.add_parser("version", help="输出版本与运行环境信息")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_version)

    sub.add_parser("lint", help="禁用词合规自检").set_defaults(func=cmd_lint)

    s = sub.add_parser("doctor", help="环境自检")
    s.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    s.add_argument("--port", type=int, default=9340, help="自检端口")
    s.set_defaults(func=cmd_doctor)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
