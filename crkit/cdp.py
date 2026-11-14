"""Chrome DevTools Protocol 高层封装（标准库 urllib + 内置 WebSocket）。"""
import json
import socket
import time
import urllib.request

from .ws import WebSocket


def list_targets(host="127.0.0.1", port=9222):
    with urllib.request.urlopen(f"http://{host}:{port}/json", timeout=5) as r:
        return json.loads(r.read().decode())


def get_page_ws(host, port):
    for t in list_targets(host, port):
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("未找到 page 类型的调试目标")


class CDP:
    def __init__(self, ws_url, ws=None):
        self.ws = ws or WebSocket(ws_url)
        self._id = 0

    def _next_id(self):
        self._id += 1
        return self._id

    def send(self, method, params=None):
        mid = self._next_id()
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv_text())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} 失败：{msg['error']}")
                return msg.get("result", {})

    def navigate(self, url, wait=1.0, timeout=15):
        self.send("Page.enable")
        self.send("Page.navigate", {"url": url})
        self.wait_for_load(timeout=timeout)
        if wait > 0:
            time.sleep(wait)

    def wait_for_load(self, timeout=15):
        """等待 Page.loadEventFired；超时返回 False，由调用方兜底等待。"""
        deadline = time.time() + timeout
        sock = getattr(self.ws, "sock", None)
        if sock is not None:
            sock.settimeout(max(0.5, timeout))
        try:
            while time.time() < deadline:
                msg = json.loads(self.ws.recv_text())
                if msg.get("method") == "Page.loadEventFired":
                    return True
        except (socket.timeout, OSError, ConnectionError):
            return False
        finally:
            if sock is not None:
                sock.settimeout(15)
        return False

    def set_device_metrics(self, width, height, device_scale=1, mobile=False):
        self.send("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height,
            "deviceScaleFactor": device_scale, "mobile": mobile,
        })

    def evaluate(self, expression):
        r = self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(f"JS 执行异常：{r['exceptionDetails']}")
        return r.get("result", {}).get("value")

    def page_dimensions(self):
        """探测整页滚动尺寸（scrollWidth / scrollHeight）。"""
        return self.evaluate(
            "({w: document.documentElement.scrollWidth, "
            "h: document.documentElement.scrollHeight})"
        ) or {"w": 0, "h": 0}

    def screenshot(self, full_page=False):
        params = {"format": "png"}
        if full_page:
            dims = self.page_dimensions()
            self.send("Emulation.setScrollbarsHidden", {"hidden": True})
            self.send("Emulation.setDeviceMetricsOverride", {
                "width": dims["w"], "height": dims["h"],
                "deviceScaleFactor": 1, "mobile": False,
            })
            params["captureBeyondViewport"] = True
        r = self.send("Page.captureScreenshot", params)
        import base64
        return base64.b64decode(r["data"])

    def close(self):
        self.ws.close()
