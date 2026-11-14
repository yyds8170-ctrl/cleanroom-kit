"""版本号单一来源：仓库根目录 VERSION 文件。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
from pathlib import Path

VERSION_PATH = Path(__file__).resolve().parent.parent / "VERSION"


def get_version():
    """读取根目录 VERSION 文件，去除首尾空白后返回版本号字符串。"""
    return VERSION_PATH.read_text(encoding="utf-8").strip()
