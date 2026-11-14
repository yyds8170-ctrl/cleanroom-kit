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
from . import act, probe
from .cdp import CDP, get_page_ws
from .compare import compare_images, format_report
from .license import write_license
from .scaffold import init_project
from .version import get_version


def cmd_init(a):
    target = a.dir or a.name
    p = init_project(target, a.name, a.desc or "", force=a.force)
    print(f"已创建项目：{p}")


def cmd_license(a):
    p = write_license(a.dir or ".", a.name, a.note or "")
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


def cmd_doctor(a):
    import platform
    print("运行环境：", platform.platform())
    print("Python：", sys.version.split()[0])
    print("浏览器：", bmod.find_browser() or "未找到（请安装 Chrome/Edge/Chromium）")
    print("Node：", shutil.which("node") or "未安装（可选）")
    print("craft-anything：", shutil.which("craft-anything-cli") or "未安装（可选增强）")
    print("所有核心功能仅依赖 Python 标准库，无需 pip 安装。")


def build_parser():
    p = argparse.ArgumentParser(prog="crk", description="洁净室复刻工具包（零依赖、跨平台）")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="从模板创建新项目")
    s.add_argument("name"); s.add_argument("--dir"); s.add_argument("--desc")
    s.add_argument("--force", action="store_true"); s.set_defaults(func=cmd_init)

    s = sub.add_parser("license", help="生成 PolyForm 许可证")
    s.add_argument("name"); s.add_argument("--dir", default="."); s.add_argument("--note")
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

    s = sub.add_parser("version", help="输出版本与运行环境信息")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_version)

    sub.add_parser("lint", help="禁用词合规自检").set_defaults(func=cmd_lint)

    sub.add_parser("doctor", help="环境自检").set_defaults(func=cmd_doctor)
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
