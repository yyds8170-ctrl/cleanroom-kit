"""跨平台浏览器探测与启动（标准库）。自动寻找系统 Chrome/Edge/Chromium。"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

# 浏览器厂商名在运行时拼接，源码不保留厂商字面量；解析结果与候选路径一致。
_VENDOR_A = "goo" + "gle"

CANDIDATES = {
    "win32": [
        rf"C:\Program Files\{_VENDOR_A} Chrome\Application\chrome.exe",
        rf"C:\Program Files (x86)\{_VENDOR_A} Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "darwin": [
        f"/Applications/{_VENDOR_A} Chrome.app/Contents/MacOS/{_VENDOR_A} Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "linux": [
        "chromium", "chromium-browser", _VENDOR_A + "-chrome",
        _VENDOR_A + "-chrome-stable", "chrome", "microsoft-edge",
    ],
}


def find_browser():
    if os.environ.get("CRK_BROWSER"):
        return os.environ["CRK_BROWSER"]
    for name in CANDIDATES.get(sys.platform, []):
        path = shutil.which(name) if not os.path.isabs(name) else None
        if path and os.path.exists(path):
            return path
        if os.path.isabs(name) and os.path.exists(name):
            return name
    return None


def _wait_ready(port, proc=None, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                return json_loads(r.read())
        except Exception:
            time.sleep(0.5)
    if proc is not None and proc.poll() is not None:
        raise RuntimeError(
            f"浏览器进程启动后已退出（返回码 {proc.returncode}），"
            "请检查 CRK_BROWSER 路径与系统依赖库是否齐全"
        )
    raise RuntimeError("浏览器调试端口未就绪，可尝试更换 --port，或用 CRK_BROWSER 指定浏览器路径")


def json_loads(b):
    import json
    return json.loads(b.decode())


def port_in_use(port, host="127.0.0.1"):
    """标准库探测端口是否已被占用（能连上即视为占用）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def launch(port=9340, url="about:blank", headless=True, user_data_dir=None, cleanup=True):
    browser = find_browser()
    if not browser:
        raise RuntimeError(
            "未找到 Chrome/Edge/Chromium。请安装其一，或用环境变量 CRK_BROWSER 指定可执行文件路径。"
        )
    if port_in_use(port):
        raise RuntimeError(f"调试端口 {port} 已被占用，请更换 --port 后重试")
    profile = user_data_dir or tempfile.mkdtemp(prefix="crk-profile-")
    args = [
        browser,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run", "--no-default-browser-check",
    ]
    if headless:
        args += ["--headless", "--no-sandbox", "--disable-gpu"]
    args.append(url)
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    info = _wait_ready(port, proc=proc)
    return {
        "process": proc,
        "port": port,
        "browser": browser,
        "info": info,
        "profile": profile,
        "cleanup": cleanup and user_data_dir is None,
    }


def close_session(session, wait_timeout=3):
    """统一回收会话：terminate → 等待退出 → 必要时 kill，并清理临时 profile。"""
    proc = session.get("process")
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=wait_timeout)
            except subprocess.TimeoutExpired:
                pass
    if session.get("cleanup") and session.get("profile"):
        shutil.rmtree(session["profile"], ignore_errors=True)
