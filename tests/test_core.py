"""cleanroom-kit 核心测试（unittest，标准库，零依赖）。"""
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crkit import pngio, compare, license as lic, scaffold, ws, browser, inspect as insp  # noqa: E402
from crkit import version as vmod, cleanwords  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
ASSET = FIXTURES / "page-1280x900.png"
OTHER = FIXTURES / "other-480x760.png"


def _write_raw_png(path, w, h, color_type, channels, pixels):
    """构造 8 位、非隔行 PNG（用于测试 RGBA/灰度等非 RGB 格式）。"""
    def chunk(ct, data):
        block = ct + data
        return struct.pack(">I", len(data)) + block + struct.pack(
            ">I", zlib.crc32(block) & 0xFFFFFFFF)
    stride = w * channels
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw))))
        f.write(chunk(b"IEND", b""))


class TestPNG(unittest.TestCase):
    def test_decode_real_screenshot(self):
        w, h, c, px = pngio.read_png(ASSET)
        self.assertEqual((w, h, c), (1280, 900, 3))
        self.assertEqual(pngio.pixel_at(px, c, w, 0, 0), (238, 238, 238))

    def test_roundtrip_paeth(self):
        self.assertEqual(ws and pngio._paeth(10, 20, 5) in range(0, 256), True)

    def test_write_png_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            src = bytearray([255, 0, 0, 0, 255, 0, 0, 0, 255, 10, 20, 30])
            p = Path(d) / "rt.png"
            pngio.write_png(p, 2, 2, src)
            w, h, c, back = pngio.read_png(p)
            self.assertEqual((w, h, c), (2, 2, 3))
            self.assertEqual(bytes(back), bytes(src))

    def test_write_png_bad_length_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                pngio.write_png(Path(d) / "x.png", 2, 2, bytearray([1, 2, 3]))

    def test_rgb_normalizes_rgba_opaque(self):
        with tempfile.TemporaryDirectory() as d:
            # 2x1 不透明 RGBA
            pix = bytearray([10, 20, 30, 255, 40, 50, 60, 255])
            p = Path(d) / "rgba.png"
            _write_raw_png(p, 2, 1, 6, 4, pix)
            w, h, rgb = pngio.read_png_rgb(p)
            self.assertEqual((w, h), (2, 1))
            self.assertEqual(bytes(rgb), bytes([10, 20, 30, 40, 50, 60]))

    def test_rgb_normalizes_grayscale(self):
        with tempfile.TemporaryDirectory() as d:
            pix = bytearray([0, 128, 255])  # 3x1 灰度
            p = Path(d) / "gray.png"
            _write_raw_png(p, 3, 1, 0, 1, pix)
            w, h, rgb = pngio.read_png_rgb(p)
            self.assertEqual(bytes(rgb), bytes([0, 0, 0, 128, 128, 128, 255, 255, 255]))

    def test_rgba_semi_transparent_composited_white(self):
        with tempfile.TemporaryDirectory() as d:
            # 黑色、alpha=0（全透明）→ 合成白底应为 255
            pix = bytearray([0, 0, 0, 0])
            p = Path(d) / "a0.png"
            _write_raw_png(p, 1, 1, 6, 4, pix)
            _, _, rgb = pngio.read_png_rgb(p)
            self.assertEqual(bytes(rgb), bytes([255, 255, 255]))


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

    def test_crop_aligns_mismatched_sizes(self):
        with tempfile.TemporaryDirectory() as d:
            a = bytearray([10, 10, 10] * 6)   # 3x2
            b = bytearray([10, 10, 10] * 4)   # 2x2
            pa, pb = Path(d) / "a.png", Path(d) / "b.png"
            pngio.write_png(pa, 3, 2, a)
            pngio.write_png(pb, 2, 2, b)
            r = compare.compare_images(pa, pb, crop=True)
            self.assertEqual(r["size"], (2, 2))  # 裁剪到共同最小区域
            w, h, _ = compare.build_diff_image(pa, pb, crop=True)
            self.assertEqual((w, h), (2, 2))

    def test_threshold_changes_detection(self):
        with tempfile.TemporaryDirectory() as d:
            a = bytearray([10, 10, 10] * 2)
            b = bytearray([10, 10, 10, 25, 10, 10])  # 单像素总差 15
            pa, pb = Path(d) / "a.png", Path(d) / "b.png"
            pngio.write_png(pa, 2, 1, a)
            pngio.write_png(pb, 2, 1, b)
            strict = compare.compare_images(pa, pb, threshold=10)   # 15>10 算差异
            loose = compare.compare_images(pa, pb, threshold=30)    # 15<=30 不算
            self.assertGreater(strict["diff_ratio_pct"], 0.0)
            self.assertEqual(loose["diff_ratio_pct"], 0.0)

    def test_diff_image_identical_has_no_red(self):
        w, h, rgb = compare.build_diff_image(ASSET, ASSET)
        reds = sum(
            1 for i in range(w * h)
            if rgb[i * 3] == 255 and rgb[i * 3 + 1] == 0 and rgb[i * 3 + 2] == 0
        )
        self.assertEqual(reds, 0)

    def test_diff_image_marks_difference_red(self):
        with tempfile.TemporaryDirectory() as d:
            a = bytearray([10, 10, 10] * 4)
            b = bytearray([10, 10, 10] * 4)
            b[0:3] = bytearray([250, 250, 250])  # 第一个像素制造差异
            pa, pb = Path(d) / "a.png", Path(d) / "b.png"
            pngio.write_png(pa, 2, 2, a)
            pngio.write_png(pb, 2, 2, b)
            w, h, rgb = compare.build_diff_image(pa, pb)
            self.assertEqual(tuple(rgb[0:3]), (255, 0, 0))  # 差异像素标红
            out = Path(d) / "diff.png"
            compare.write_diff_image(pa, pb, out)
            self.assertTrue(out.exists())


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


class TestVersion(unittest.TestCase):
    def test_version_matches_VERSION(self):
        self.assertEqual(
            vmod.get_version(),
            vmod.VERSION_PATH.read_text(encoding="utf-8").strip(),
        )

    def test_init_dunder_derived(self):
        import crkit
        self.assertEqual(crkit.__version__, vmod.get_version())


class TestLint(unittest.TestCase):
    def test_no_banned_words_in_tree(self):
        self.assertEqual(cleanwords.scan_tree(ROOT), [])

    def test_detector_bidirectional(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "crkit"
            sample.mkdir()
            # 真实禁用词（厂商 / 机构名）必须被检出
            targets = [
                cleanwords.BANNED_WORDS[0],
                cleanwords.BANNED_WORDS[2],
                cleanwords.BANNED_WORDS[12],
            ]
            (sample / "banned.txt").write_text(
                "样例：" + "、".join(targets), encoding="utf-8"
            )
            hits = cleanwords.scan_tree(Path(d))
            found = {h["word"].lower() for h in hits}
            for t in targets:
                self.assertIn(t.lower(), found)
            # 普通中文单位用词不得被误报
            (sample / "normal.txt").write_text(
                "按字节读取；8 字节对齐；单位用 bytes 表述。", encoding="utf-8"
            )
            hits = cleanwords.scan_tree(Path(d))
            self.assertEqual(
                [h for h in hits if h["file"].endswith("normal.txt")], []
            )


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
