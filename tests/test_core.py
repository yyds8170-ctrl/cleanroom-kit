"""cleanroom-kit 核心测试（unittest，标准库，零依赖）。"""
import json
import os
import socket
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crkit import pngio, compare, license as lic, scaffold, ws, browser, inspect as insp  # noqa: E402
from crkit import version as vmod, cleanwords, cdp as cdpmod, cli, colors, act, probe, a11y  # noqa: E402

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

    def test_readback_fullpage_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            pix = bytearray([10, 20, 30] * 200 * 1200)
            p = Path(d) / "long.png"
            pngio.write_png(p, 200, 1200, pix)
            w, h, c, _ = pngio.read_png(p)
            self.assertEqual((w, h, c), (200, 1200, 3))


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

    def test_vertical_content_range(self):
        with tempfile.TemporaryDirectory() as d:
            a = bytearray([200, 200, 200] * 2 * 2 + [240, 240, 240] * 2 * 2)
            pa = Path(d) / "a.png"
            pngio.write_png(pa, 2, 4, a)
            r = compare.compare_images(pa, pa)
            self.assertEqual(r["content_rows_original"], (0, 1))
            self.assertEqual(r["content_rows_rebuild"], (0, 1))

    def test_grid_buckets_report_diff_per_cell(self):
        with tempfile.TemporaryDirectory() as d:
            w, h = 8, 6
            a = bytearray([240, 240, 240] * w * h)
            b = bytearray(a)
            b[0:3] = bytearray([10, 10, 10])  # 仅 (row0, col0) 差异
            pa, pb = Path(d) / "a.png", Path(d) / "b.png"
            pngio.write_png(pa, w, h, a)
            pngio.write_png(pb, w, h, b)
            r = compare.compare_images(pa, pb)
            buckets = r["grid"]["buckets"]
            target = [x for x in buckets if x["row"] == 0 and x["col"] == 0][0]
            self.assertGreater(target["diff_ratio_pct"], 0.0)
            others = [x for x in buckets if not (x["row"] == 0 and x["col"] == 0)]
            self.assertTrue(all(x["diff_ratio_pct"] == 0.0 for x in others))

    def test_json_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            r = compare.compare_images(ASSET, ASSET)
            p = Path(d) / "report.json"
            compare.write_report_json(r, p)
            loaded = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(tuple(loaded["size"]), r["size"])
            self.assertEqual(loaded["verdict"], "match")
            self.assertIn("grid", loaded)

    def test_resize_aligns_mismatched_size(self):
        with tempfile.TemporaryDirectory() as d:
            a = bytearray([10, 10, 10] * 6)   # 3x2
            b = bytearray([10, 10, 10] * 4)   # 2x2
            pa, pb = Path(d) / "a.png", Path(d) / "b.png"
            pngio.write_png(pa, 3, 2, a)
            pngio.write_png(pb, 2, 2, b)
            r = compare.compare_images(pa, pb, resize=True)
            self.assertEqual(r["size"], (3, 2))
            # 等比缩放：2x2 源图缩到 4x3 画布时内容区 3x3，宽高比保持 1:1
            scaled = compare._resize_rgb(bytearray([10, 10, 10] * 4), 2, 2, 4, 3)
            self.assertEqual(len(scaled), 4 * 3 * 3)

    def test_crop_and_resize_mutually_exclusive(self):
        args = cli.build_parser().parse_args(
            ["compare", "--orig", "x", "--rebuild", "y", "--crop", "--resize"]
        )
        with self.assertRaises(RuntimeError):
            cli._validate_compare_options(args)

    def test_verdict_threshold(self):
        self.assertEqual(compare.compare_images(ASSET, ASSET)["verdict"], "match")
        with tempfile.TemporaryDirectory() as d:
            a = bytearray([10, 10, 10] * 4)
            b = bytearray([240, 240, 240] * 4)
            pa, pb = Path(d) / "a.png", Path(d) / "b.png"
            pngio.write_png(pa, 2, 2, a)
            pngio.write_png(pb, 2, 2, b)
            r = compare.compare_images(pa, pb, max_diff=10.0)
            self.assertEqual(r["verdict"], "major")


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

    def test_year_override(self):
        text = lic.build_license("demo", year=2027)
        self.assertIn("Copyright (c) 2027 洋洋", text)
        notice = lic.build_notice("demo", year=2027)
        self.assertIn("https://github.com/yyds8170-ctrl/demo", notice)


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

    def test_web_stack_full_skeleton(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "webproj"
            scaffold.init_project(target, "webproj", "说明", stack="web")
            for f in ["evidence/README.md", "tests/README.md", "js/.gitkeep",
                      "README.md", ".github/workflows/ci.yml", "LICENSE", "NOTICE", "VERSION"]:
                self.assertTrue((target / f).exists(), f)

    def test_game_stack_has_canvas_and_module(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "gameproj"
            scaffold.init_project(target, "gameproj", "说明", stack="game")
            html = (target / "index.html").read_text(encoding="utf-8")
            self.assertIn("<canvas", html)
            self.assertIn('type="module"', html)
            self.assertTrue((target / "js/main.js").exists())

    def test_placeholders_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "ph"
            scaffold.init_project(target, "ph", "描述", stack="game",
                                  author="洋洋", github_user="yyds8170-ctrl",
                                  github_repo="ph-repo", year=2027)
            leftover = [p for p in target.rglob("*")
                        if p.is_file() and "{{" in p.read_text(encoding="utf-8")]
            self.assertEqual(leftover, [])
            readme = (target / "README.md").read_text(encoding="utf-8")
            self.assertIn("2027", readme)
            self.assertIn("洋洋", readme)
            self.assertIn("ph-repo", readme)


class TestBrowserDetect(unittest.TestCase):
    def test_find_returns_path_or_none(self):
        r = browser.find_browser()
        self.assertTrue(r is None or os.path.exists(r))


class TestBrowserPort(unittest.TestCase):
    def test_port_in_use_detects_open_port(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            self.assertTrue(browser.port_in_use(port))
        finally:
            srv.close()
        self.assertFalse(browser.port_in_use(port))

    def test_launch_reports_busy_port(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            with self.assertRaises(RuntimeError) as ctx:
                browser.launch(port=port, headless=True)
            self.assertIn(str(port), str(ctx.exception))
        finally:
            srv.close()


class _FakeWS:
    """模拟 WebSocket 会话，按队列回放消息并记录发出的命令。"""

    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []
        self.sock = type("S", (), {"settimeout": lambda self, t: None})()

    def send_text(self, text):
        self.sent.append(json.loads(text))

    def recv_text(self):
        return json.dumps(self._messages.pop(0))

    def close(self):
        pass


class TestCDPNavigate(unittest.TestCase):
    def test_navigate_waits_for_load_event(self):
        ws = _FakeWS([
            {"id": 1, "result": {}},
            {"id": 2, "result": {}},
            {"method": "Page.loadEventFired"},
        ])
        c = cdpmod.CDP("ws://x", ws=ws)
        c.navigate("http://x", wait=0, timeout=5)
        methods = [m["method"] for m in ws.sent]
        self.assertEqual(methods[0], "Page.enable")
        self.assertEqual(methods[1], "Page.navigate")
        # 消费掉的加载事件已清理，缓存不残留
        self.assertEqual(c._event_cache, [])

    def test_click_evaluates_selector(self):
        ws = _FakeWS([{"id": 1, "result": {"result": {"value": True}}}])
        c = cdpmod.CDP("ws://x", ws=ws)
        c.click("#start-btn")
        expr = [m for m in ws.sent if m["method"] == "Runtime.evaluate"][0]["params"]["expression"]
        self.assertIn("#start-btn", expr)

    def test_press_key_builds_keyboard_event(self):
        ws = _FakeWS([{"id": 1, "result": {"result": {"value": True}}}])
        c = cdpmod.CDP("ws://x", ws=ws)
        c.press_key("Space")
        expr = [m for m in ws.sent if m["method"] == "Runtime.evaluate"][0]["params"]["expression"]
        self.assertIn("KeyboardEvent", expr)
        self.assertIn("Space", expr)

    def test_fullpage_screenshot_passes_capture_beyond_viewport(self):
        import base64
        b64 = base64.b64encode(b"x").decode()
        ws = _FakeWS([
            {"id": 1, "result": {"result": {"value": {"w": 1280, "h": 2400}}}},
            {"id": 2, "result": {}},
            {"id": 3, "result": {}},
            {"id": 4, "result": {"data": b64}},
        ])
        c = cdpmod.CDP("ws://x", ws=ws)
        c.screenshot(full_page=True)
        shot = [m for m in ws.sent if m["method"] == "Page.captureScreenshot"][0]
        self.assertTrue(shot["params"]["captureBeyondViewport"])


class TestShotOutput(unittest.TestCase):
    def test_widths_expands_multiple_outputs(self):
        self.assertEqual(
            cli._expand_outputs("site.png", [1280, 390]),
            ["site-1280.png", "site-390.png"],
        )
        with self.assertRaises(RuntimeError):
            cli._parse_widths("abc")
        with self.assertRaises(RuntimeError):
            cli._parse_widths("-100")


class TestCLIParse(unittest.TestCase):
    def test_shot_parser_registers_new_flags(self):
        args = cli.build_parser().parse_args(
            ["shot", "--url", "http://x", "--full-page", "--widths", "1280,390"]
        )
        self.assertTrue(args.full_page)
        self.assertEqual(args.widths, "1280,390")

    def test_act_probe_parser_registered(self):
        args = cli.build_parser().parse_args(
            ["act", "--url", "http://x", "--steps", "[]"]
        )
        self.assertEqual(args.command, "act")
        args2 = cli.build_parser().parse_args(
            ["probe", "--url", "http://x", "--assertions", "a.json"]
        )
        self.assertEqual(args2.command, "probe")


class TestActCDP:
    """记录 eval 调用并返回固定值。"""
    def __init__(self):
        self.calls = []

    def eval_state(self, js):
        self.calls.append(js)
        return {"score": 3}


class TestAct(unittest.TestCase):
    def test_script_parses_steps(self):
        steps = act.load_steps(
            inline='[{"op":"click","target":"#btn"},{"op":"key","code":"Space"}]'
        )
        self.assertEqual([s["op"] for s in steps], ["click", "key"])
        with self.assertRaises(RuntimeError):
            act.load_steps(inline='[{"op":"teleport"}]')
        # eval 返回值记入日志（回归：A4）
        cdp = TestActCDP()
        report = act.run_steps(
            cdp, [{"op": "eval", "condition": "document.getElementById('score').textContent"}]
        )
        self.assertTrue(report[0]["ok"])
        self.assertEqual(report[0]["value"], {"score": 3})


class TestProbeCDP:
    """记录 evaluate 调用并返回固定快照，避免依赖真实浏览器。"""
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def evaluate(self, js):
        return self.snapshot

    def eval_state(self, js):
        return self.snapshot


class TestProbe(unittest.TestCase):
    def test_assertion_text_pass_fail(self):
        ok = probe.run_assertions(
            TestProbeCDP({"text": "已开始", "className": "", "attrs": {}, "visible": True}),
            [{"name": "t", "selector": "#overlay", "expect": {"text": "已开始"}}],
        )
        self.assertTrue(ok[0]["pass"])
        bad = probe.run_assertions(
            TestProbeCDP({"text": "已暂停", "className": "", "attrs": {}, "visible": True}),
            [{"name": "t", "selector": "#overlay", "expect": {"text": "已开始"}}],
        )
        self.assertFalse(bad[0]["pass"])

    def test_report_exit_code_on_fail(self):
        self.assertFalse(probe.all_pass([{"pass": False}]))
        self.assertTrue(probe.all_pass([{"pass": True}, {"pass": True}]))


def _ws_frame(opcode, payload, fin=True):
    b1 = (0x80 if fin else 0x00) | opcode
    return bytes(bytearray([b1, len(payload)])) + payload


class TestWSFrames(unittest.TestCase):
    def test_continuation_frame_reassembled(self):
        srv, cli = socket.socketpair()
        w = ws.WebSocket.__new__(ws.WebSocket)
        w.sock = cli
        srv.sendall(
            _ws_frame(0x1, "片段一".encode(), fin=False)
            + _ws_frame(0x0, "-片段二".encode(), fin=True)
        )
        self.assertEqual(w.recv_text(), "片段一-片段二")
        srv.close()
        cli.close()

    def test_binary_frame_raises_clear_error(self):
        srv, cli = socket.socketpair()
        w = ws.WebSocket.__new__(ws.WebSocket)
        w.sock = cli
        srv.sendall(_ws_frame(0x2, b"\x00\x01"))
        with self.assertRaises(ConnectionError) as ctx:
            w.recv_text()
        self.assertIn("二进制帧", str(ctx.exception))
        srv.close()
        cli.close()


class TestVersion(unittest.TestCase):
    def test_version_matches_VERSION(self):
        self.assertEqual(
            vmod.get_version(),
            vmod.VERSION_PATH.read_text(encoding="utf-8").strip(),
        )

    def test_init_dunder_derived(self):
        import crkit
        self.assertEqual(crkit.__version__, vmod.get_version())


class TestA11y(unittest.TestCase):
    def test_luminance_known_values(self):
        self.assertEqual(a11y.relative_luminance("#000000"), 0.0)
        self.assertEqual(a11y.relative_luminance("#ffffff"), 1.0)
        gray = a11y.relative_luminance("#808080")
        self.assertTrue(0.0 < gray < 1.0)

    def test_contrast_ratio_black_white(self):
        self.assertEqual(a11y.contrast_ratio("#000000", "#ffffff"), 21.0)

    def test_grade_thresholds(self):
        self.assertEqual(a11y.grade(7.0), "AAA")
        self.assertEqual(a11y.grade(4.5), "AA")
        self.assertEqual(a11y.grade(3.0), "A")
        self.assertEqual(a11y.grade(2.0), "fail")
        self.assertEqual(a11y.grade(4.5, large=True), "AAA")
        self.assertEqual(a11y.grade(3.0, large=True), "AA")
        self.assertEqual(a11y.grade(2.0, large=True), "fail")
        self.assertEqual(a11y.grade(None), "unverified")

    def test_inspect_report_pairing(self):
        report = {
            "tokens": {"body": {"color": "#111111", "backgroundColor": "#ffffff"}},
            "elements": [{
                "tag": "p", "id": None, "className": None, "text": "正文",
                "style": {"color": {"hex": "#111111", "space": "hex"},
                          "backgroundColor": {"hex": "#ffffff", "space": "hex"},
                          "fontSize": "16px", "fontWeight": "400"},
            }],
            "a11y": {"lang": "zh-CN", "images_without_alt": 0, "unnamed_controls": [], "landmarks": ["main"]},
        }
        result = a11y.analyze_inspect(report)
        self.assertEqual(result["summary"]["total"], 1)
        self.assertIsNotNone(result["pairs"][0]["ratio"])
        self.assertTrue(result["pairs"][0]["pass"])

    def test_unparsable_marked_unverified(self):
        report = {
            "tokens": {"body": {"color": "raw-ink", "backgroundColor": "transparent"}},
            "elements": [
                {
                    "tag": "span", "style": {"color": {"space": "raw", "raw": "weird"},
                                              "backgroundColor": {"space": "raw", "raw": "weird"}},
                },
                {
                    "tag": "i", "style": {"color": {"hex": "#111111", "alpha": 1.0, "space": "hex"},
                                           "backgroundColor": {"hex": "#000000", "alpha": 0.0, "space": "rgba"}},
                },
            ],
            "a11y": {},
        }
        result = a11y.analyze_inspect(report)
        self.assertEqual(result["pairs"][0]["grade"], "unverified")
        self.assertEqual(result["summary"]["unverified"], 2)


class TestLint(unittest.TestCase):
    def test_no_banned_words_in_tree(self):
        self.assertEqual(cleanwords.scan_tree(ROOT), [])
        rel = {str(p.relative_to(ROOT)) for p in cleanwords._iter_files(ROOT)}
        self.assertIn("evidence/v1.7.0/example-inspect.json", rel)
        self.assertIn("data/polyform-noncommercial.txt", rel)
        self.assertIn("NOTICE", rel)
        self.assertIn("VERSION", rel)

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
            # 含同名子串的普通英文词不得被词边界规则误报
            normal_ascii = " ".join([
                "g" + "ptx", "open" + "air", "moon" + "shotx",
                "byte" + "dancex", "q" + "wenx",
            ])
            (sample / "ascii-normal.txt").write_text(normal_ascii, encoding="utf-8")
            hits = cleanwords.scan_tree(Path(d))
            self.assertEqual(
                [h for h in hits if h["file"].endswith("normal.txt")], []
            )
            self.assertEqual(
                [h for h in hits if h["file"].endswith("ascii-normal.txt")], []
            )


class FakeCDP:
    """模拟 CDP 会话，避免单元测试依赖真实浏览器。"""
    def __init__(self, payload):
        self._payload = payload
        self.navigated = None

    def navigate(self, url, wait=1.0, timeout=15):
        self.navigated = url

    def evaluate(self, js):
        return self._payload


class TestColors(unittest.TestCase):
    def test_parse_hex_rgb_rgba(self):
        self.assertEqual(colors.parse_color("#fff")["hex"], "#ffffff")
        self.assertEqual(colors.parse_color("#ff8800")["hex"], "#ff8800")
        rgb = colors.parse_color("rgb(255, 0, 128)")
        self.assertEqual(rgb["hex"], "#ff0080")
        self.assertEqual(rgb["alpha"], 1.0)
        rgba = colors.parse_color("rgba(10, 20, 30, 0.5)")
        self.assertEqual(rgba["hex"], "#0a141e")
        self.assertEqual(rgba["alpha"], 0.5)
        rgba_pct = colors.parse_color("rgba(10, 20, 30, 50%)")
        self.assertEqual(rgba_pct["hex"], "#0a141e")
        self.assertEqual(rgba_pct["alpha"], 0.5)

    def test_parse_oklch_marks_approx(self):
        c = colors.parse_color("oklch(60% 0.15 250)")
        self.assertTrue(c["hex"])
        self.assertEqual(c["space"], "oklch-approx")

    def test_unparsable_kept_raw(self):
        c = colors.parse_color("not-a-color")
        self.assertEqual(c["space"], "raw")
        self.assertIsNone(c["hex"])
        self.assertEqual(c["raw"], "not-a-color")


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

    def test_fullpage_box_adds_scroll_offset(self):
        self.assertIn("scrollY", insp.INSPECT_JS)

    def _rich_payload(self):
        p = self._payload()
        p.update({
            "links": [{"text": "Learn more", "href": "/x", "target": None}],
            "images": [{"alt": "logo", "naturalWidth": 100, "naturalHeight": 40,
                        "box": {"x": 1, "y": 2, "width": 100, "height": 40}}],
            "headings": [{"level": 1, "text": "标题",
                          "box": {"x": 1, "y": 2, "width": 100, "height": 20}}],
            "a11y": {"lang": "en", "images_without_alt": 0,
                     "landmarks": ["main"], "unnamed_controls": []},
            "design": {"font_sizes": ["16px"], "font_weights": ["400"],
                       "fonts": ["sans"], "max_widths": [], "radii": [],
                       "shadows": [], "spacing": []},
            "text": "页面可见纯文本",
        })
        return p

    def test_report_has_new_sections(self):
        fake = FakeCDP(self._rich_payload())
        data = insp.inspect_page(fake, wait=0)
        self.assertEqual(data["links"][0]["href"], "/x")
        self.assertEqual(data["headings"][0]["level"], 1)
        self.assertEqual(data["a11y"]["lang"], "en")
        self.assertIn("font_sizes", data["design"])
        self.assertEqual(data["text"], "页面可见纯文本")

    def test_palette_normalized_objects(self):
        payload = self._payload()
        payload["palette"] = ["rgba(10, 20, 30, 0.5)"]
        data = insp.inspect_page(FakeCDP(payload), wait=0)
        self.assertEqual(data["palette"][0]["hex"], "#0a141e")
        self.assertEqual(data["palette"][0]["alpha"], 0.5)

    def test_js_collects_links_and_headings(self):
        self.assertIn("querySelectorAll('a')", insp.INSPECT_JS)
        self.assertIn("h1,h2,h3,h4,h5,h6", insp.INSPECT_JS)
        self.assertIn("alt", insp.INSPECT_JS)
        self.assertIn("header,nav,main,footer,aside,section", insp.INSPECT_JS)

    def test_plaintext_export(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "text.txt"
            insp.write_plaintext(self._rich_payload(), out)
            txt = out.read_text(encoding="utf-8")
            self.assertIn("标题", txt)
            self.assertIn("页面可见纯文本", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
