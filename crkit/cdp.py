"""Chrome DevTools Protocol 高层封装（标准库 urllib + 内置 WebSocket）。"""
import json
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
    def __init__(self, ws_url):
        self.ws = WebSocket(ws_url)
        self._id = 0

    def send(self, method, params=None):
        self._id += 1
        mid = self._id
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv_text())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} 失败：{msg['error']}")
                return msg.get("result", {})

    def navigate(self, url, wait=1.0):
        self.send("Page.enable")
        self.send("Page.navigate", {"url": url})
        time.sleep(wait)

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

    def screenshot(self):
        r = self.send("Page.captureScreenshot", {"format": "png"})
        import base64
        return base64.b64decode(r["data"])

    def close(self):
        self.ws.close()
