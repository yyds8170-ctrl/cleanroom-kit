"""骨架就位校验：init 生成后核心文件存在、占位符零残留。

项目落地后替换为真实页面/对照断言；运行：python3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".html", ".css", ".js", ".md", ".json", ".yml", ".yaml"}
PLACEHOLDER = "{" + "{"  # 占位符起始标记，避免在本文件留下字面占位符


class TestSkeleton(unittest.TestCase):
    def test_core_files_exist(self):
        for rel in ("index.html", "README.md", "css/style.css"):
            self.assertTrue((ROOT / rel).exists(), f"缺少骨架文件：{rel}")

    def test_no_placeholders_left(self):
        leftovers = []
        for p in ROOT.rglob("*"):
            if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
                if PLACEHOLDER in p.read_text(encoding="utf-8"):
                    leftovers.append(str(p.relative_to(ROOT)))
        self.assertEqual(leftovers, [], f"存在未替换占位符：{leftovers}")


if __name__ == "__main__":
    unittest.main()
