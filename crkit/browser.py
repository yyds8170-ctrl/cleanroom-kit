"""跨平台浏览器探测与启动（标准库）。自动寻找系统 Chrome/Edge/Chromium。"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

CANDIDATES = {
    "win32": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "linux": [
        "chromium", "chromium-browser", "google-chrome",
        "google-chrome-stable", "chrome", "microsoft-edge",
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


def _wait_ready(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                return json_loads(r.read())
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("浏览器调试端口未就绪")


def json_loads(b):
    import json
    return json.loads(b.decode())


def launch(port=9340, url="about:blank", headless=True, user_data_dir=None):
    browser = find_browser()
    if not browser:
        raise RuntimeError(
            "未找到 Chrome/Edge/Chromium。请安装其一，或用环境变量 CRK_BROWSER 指定可执行文件路径。"
        )
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
    info = _wait_ready(port)
    return {"process": proc, "port": port, "browser": browser, "info": info}
