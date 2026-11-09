"""cleanroom-kit 统一命令行入口（argparse，标准库）。"""
import argparse
import shutil
import sys

from . import browser as bmod
from .cdp import CDP, get_page_ws
from .compare import compare_images, format_report
from .license import write_license
from .scaffold import init_project


def cmd_init(a):
    target = a.dir or a.name
    p = init_project(target, a.name, a.desc or "", force=a.force)
    print(f"已创建项目：{p}")


def cmd_license(a):
    p = write_license(a.dir or ".", a.name, a.note or "")
    print(f"已生成 LICENSE：{p}")


def cmd_browser(a):
    r = bmod.launch(port=a.port, url=a.url, headless=not a.show)
    print(f"浏览器已启动：{r['browser']} 调试端口 {r['port']}")
    if a.show:
        r["process"].wait()


def cmd_shot(a):
    r = bmod.launch(port=a.port, headless=True)
    try:
        c = CDP(get_page_ws("127.0.0.1", a.port))
        c.set_device_metrics(a.width, a.height, mobile=a.mobile)
        c.navigate(a.url, wait=a.wait)
        data = c.screenshot()
        with open(a.out, "wb") as f:
            f.write(data)
        c.close()
        print(f"已保存截图（{a.width}x{a.height}）：{a.out}（{len(data)} 字节）")
    finally:
        r["process"].terminate()


def cmd_compare(a):
    r = compare_images(a.orig, a.rebuild)
    print(format_report(r))
    if r["diff_ratio_pct"] > a.max_diff:
        print(f"差异 {r['diff_ratio_pct']:.1f}% 超过阈值 {a.max_diff}%", file=sys.stderr)
        sys.exit(1)


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
    s.add_argument("--wait", type=float, default=1.5); s.set_defaults(func=cmd_shot)

    s = sub.add_parser("compare", help="像素对照")
    s.add_argument("--orig", required=True); s.add_argument("--rebuild", required=True)
    s.add_argument("--max-diff", type=float, default=10.0); s.set_defaults(func=cmd_compare)

    sub.add_parser("doctor", help="环境自检").set_defaults(func=cmd_doctor)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
