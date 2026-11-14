"""禁用词合规自检：扫描仓库文本文件，命中即报文件与行号（纯标准库）。

词表在运行时由片段拼接，避免词表本身在源码中留下字面命中。
许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import re
from pathlib import Path

# 片段拼接出的禁用词表（厂商 / 模型 / 平台名称），源码中不出现完整字面量。
_FRAGMENTS = [
    ["豆", "包"],
    ["dou", "bao"],
    ["g", "pt"],
    ["cla", "ude"],
    ["gem", "ini"],
    ["q", "wen"],
    ["deep", "seek"],
    ["ki", "mi"],
    ["moon", "shot"],
    ["open", "ai"],
    ["anthro", "pic"],
    ["goo", "gle"],
    ["字节", "跳动"],
    ["byte", "dance"],
]
BANNED_WORDS = ["".join(parts) for parts in _FRAGMENTS]

SCAN_DIRS = ["crkit", "bin", "templates", "tests", "evidence", "data"]
ROOT_FILES = ["NOTICE", "VERSION"]
TEXT_SUFFIXES = {
    ".py", ".sh", ".cmd", ".html", ".css", ".js", ".mjs",
    ".md", ".yml", ".yaml", ".txt", ".json", ".gitignore",
}


def _word_pattern(word):
    """ASCII 词按词边界匹配，避免普通英文词含同名子串被误报；中文词保持全词包含。"""
    if word.isascii():
        return re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    return re.compile(re.escape(word), re.IGNORECASE)


def _iter_files(root):
    root = Path(root)
    for dirname in SCAN_DIRS:
        base = root / dirname
        if base.is_dir():
            for p in base.rglob("*"):
                if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
                    yield p
    for name in ROOT_FILES:
        p = root / name
        if p.is_file():
            yield p
    for pattern in ("*.md", "*.yml", "*.yaml"):
        for p in root.glob(pattern):
            if p.is_file():
                yield p


def scan_tree(root):
    """扫描 root 下的文本文件，返回命中清单（dict 列表，空列表表示通过）。"""
    root = Path(root)
    word_patterns = [_word_pattern(w) for w in BANNED_WORDS]
    hits = []
    for path in _iter_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(lines, 1):
            for pat in word_patterns:
                m = pat.search(line)
                if m:
                    hits.append({
                        "file": str(path.relative_to(root)),
                        "line": lineno,
                        "word": m.group(0),
                        "text": line.strip(),
                    })
    return hits
