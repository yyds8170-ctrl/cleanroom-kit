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
        self._event_cache = []

    def _next_id(self):
        self._id += 1
        return self._id

    def _cache_event(self, msg):
        self._event_cache.append(msg)
        if len(self._event_cache) > 32:  # 上限防止长会话缓存无限增长
            self._event_cache.pop(0)

    def send(self, method, params=None):
        mid = self._next_id()
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv_text())
            if "id" not in msg:
                self._cache_event(msg)
                continue
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
        """等待 Page.loadEventFired；先查事件缓存避免竞态错过，超时返回 False。"""
        for i, msg in enumerate(self._event_cache):
            if msg.get("method") == "Page.loadEventFired":
                self._event_cache.pop(i)
                return True
        deadline = time.time() + timeout
        sock = getattr(self.ws, "sock", None)
        if sock is not None:
            sock.settimeout(max(0.5, timeout))
        try:
            while time.time() < deadline:
                msg = json.loads(self.ws.recv_text())
                if "id" not in msg:
                    self._cache_event(msg)
                if msg.get("method") == "Page.loadEventFired":
                    for i, cached in enumerate(self._event_cache):
                        if cached is msg:
                            self._event_cache.pop(i)
                            break
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

    def page_dimensions(self, fallback=None):
        """探测整页滚动尺寸；探测异常或为 0 时回退到给定视口尺寸。"""
        dims = self.evaluate(
            "({w: document.documentElement.scrollWidth, "
            "h: document.documentElement.scrollHeight})"
        )
        if not isinstance(dims, dict) or not dims.get("w") or not dims.get("h"):
            if fallback:
                return {"w": fallback[0], "h": fallback[1]}
            return {"w": 0, "h": 0}
        return dims

    def screenshot(self, full_page=False, mobile=False, viewport=None):
        params = {"format": "png"}
        if full_page:
            dims = self.page_dimensions(fallback=viewport)
            if not dims["w"] or not dims["h"]:
                raise RuntimeError("整页尺寸探测失败：宽高为 0，请检查页面是否正常加载")
            self.send("Emulation.setScrollbarsHidden", {"hidden": True})
            self.send("Emulation.setDeviceMetricsOverride", {
                "width": dims["w"], "height": dims["h"],
                "deviceScaleFactor": 1, "mobile": mobile,
            })
            params["captureBeyondViewport"] = True
        r = self.send("Page.captureScreenshot", params)
        import base64
        return base64.b64decode(r["data"])

    def click(self, selector):
        """点击匹配选择器的元素；找不到抛中文错误。"""
        expr = (
            f"(()=>{{const el=document.querySelector({json.dumps(selector)});"
            f"if(!el)return false;el.click();return true;}})()"
        )
        if not self.evaluate(expr):
            raise RuntimeError(f"未找到可点击元素：{selector}")

    def type_text(self, selector, text):
        """聚焦元素并填入文本，派发 input 事件。"""
        expr = (
            f"(()=>{{const el=document.querySelector({json.dumps(selector)});"
            f"if(!el)return false;el.focus();el.value={json.dumps(text)};"
            f"el.dispatchEvent(new Event('input',{{bubbles:true}}));return true;}})()"
        )
        if not self.evaluate(expr):
            raise RuntimeError(f"未找到可输入元素：{selector}")

    def press_key(self, code):
        """在 document 与 window 上派发 keydown / keyup KeyboardEvent。"""
        key = json.dumps(code)
        expr = (
            f"(()=>{{const evD=new KeyboardEvent('keydown',{{code:{key},bubbles:true}});"
            f"const evU=new KeyboardEvent('keyup',{{code:{key},bubbles:true}});"
            f"document.dispatchEvent(evD);window.dispatchEvent(evD);"
            f"document.dispatchEvent(evU);window.dispatchEvent(evU);return true;}})()"
        )
        self.evaluate(expr)

    def scroll_to(self, x, y):
        self.evaluate(f"(()=>{{window.scrollTo({int(x)},{int(y)});return true;}})()")

    def wait_for(self, condition_js, timeout=15):
        """轮询条件表达式直到为真；超时抛中文错误。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.evaluate(condition_js):
                return True
            time.sleep(0.2)
        raise RuntimeError(f"等待条件超时（{timeout}s）：{condition_js[:60]}")

    def eval_state(self, expression):
        """返回任意可序列化页面状态，异常由 evaluate 统一带回。"""
        return self.evaluate(expression)

    def close(self):
        self.ws.close()
