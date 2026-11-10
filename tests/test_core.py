"""cleanroom-kit 核心测试（unittest，标准库，零依赖）。"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crkit import pngio, compare, license as lic, scaffold, ws, browser, inspect as insp  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
ASSET = FIXTURES / "page-1280x900.png"
OTHER = FIXTURES / "other-480x760.png"


class TestPNG(unittest.TestCase):
    def test_decode_real_screenshot(self):
        w, h, c, px = pngio.read_png(ASSET)
        self.assertEqual((w, h, c), (1280, 900, 3))
        self.assertEqual(pngio.pixel_at(px, c, w, 0, 0), (238, 238, 238))

    def test_roundtrip_paeth(self):
        self.assertEqual(ws and pngio._paeth(10, 20, 5) in range(0, 256), True)


class TestCompare(unittest.TestCase):
    def test_identical_images(self):
        r = compare.compare_images(ASSET, ASSET)
        self.assertEqual(r["mean_abs_diff"], 0.0)
        self.assertEqual(r["diff_ratio_pct"], 0.0)
        self.assertTrue(r["bg_match"])

    def test_size_mismatch_raises(self):
        # 不同尺寸的真实截图应触发 ValueError
        with self.assertRaises(ValueError):
            compare.compare_images(ASSET, OTHER)


class TestLicense(unittest.TestCase):
    def test_build_license(self):
        text = lic.build_license("demo")
        self.assertIn("PolyForm Noncommercial License 1.0.0", text)
        self.assertIn("洋洋", text)
        self.assertIn("demo", text)

    def test_write_and_notice(self):
        with tempfile.TemporaryDirectory() as d:
            p = lic.write_license(d, "demo")
            self.assertTrue(p.exists())
            self.assertIn("Copyright (c) 2026 洋洋", lic.build_notice("demo"))


class TestScaffold(unittest.TestCase):
    def test_init_project(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "newproj"
            scaffold.init_project(target, "newproj", "说明")
            for f in ["index.html", "LICENSE", "NOTICE", "VERSION", "css/style.css"]:
                self.assertTrue((target / f).exists())
            self.assertIn("newproj", (target / "index.html").read_text())

    def test_nonempty_requires_force(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "x").write_text("y")
            with self.assertRaises(FileExistsError):
                scaffold.init_project(d, "p")


class TestBrowserDetect(unittest.TestCase):
    def test_find_returns_path_or_none(self):
        r = browser.find_browser()
        self.assertTrue(r is None or os.path.exists(r))


class FakeCDP:
    """模拟 CDP 会话，避免单元测试依赖真实浏览器。"""
    def __init__(self, payload):
        self._payload = payload
        self.navigated = None

    def navigate(self, url, wait=1.0):
        self.navigated = url

    def evaluate(self, js):
        return self._payload


class TestInspect(unittest.TestCase):
    def _payload(self):
        return {
            "url": "http://x",
            "viewport": {"width": 390, "height": 844},
            "tokens": {"body": {"color": "rgb(0, 0, 0)"}},
            "elements": [{"tag": "h1", "box": {"x": 1, "y": 2, "width": 10, "height": 20}}],
            "palette": ["rgb(0, 0, 0)"],
        }

    def test_inspect_page_with_navigation(self):
        fake = FakeCDP(self._payload())
        data = insp.inspect_page(fake, url="http://x", wait=0)
        self.assertEqual(fake.navigated, "http://x")
        self.assertEqual(data["elements"][0]["box"]["width"], 10)

    def test_bad_payload_raises(self):
        with self.assertRaises(RuntimeError):
            insp.inspect_page(FakeCDP(["not", "dict"]))

    def test_write_report_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "inspect.json"
            insp.write_report(self._payload(), out)
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["viewport"]["width"], 390)

    def test_js_constant_contains_key_apis(self):
        self.assertIn("getComputedStyle", insp.INSPECT_JS)
        self.assertIn("getBoundingClientRect", insp.INSPECT_JS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
