#!/usr/bin/env python3
"""发布前一致性自检（纯标准库）。

串联以下门禁：
- VERSION 与包内 ``__version__`` 一致；
- CHANGELOG 顶部版本、README 版本徽章与 VERSION 一致；
- README 测试徽章数字与测试方法计数一致；
- 禁用词零命中；
- 当前版本证据目录齐备；
- git 工作区干净（未提交条目为零）。

全部通过才允许封版；任一 FAIL 以退出码 1 结束。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import importlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _read(root, rel):
    p = root / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _changelog_version(root):
    m = re.search(r"^##\s*\[([0-9]+\.[0-9]+\.[0-9]+)\]", _read(root, "CHANGELOG.md"), re.M)
    return m.group(1) if m else None


def _readme_badge(root, label):
    m = re.search(rf"badge/{label}-([0-9.]+)", _read(root, "README.md"))
    return m.group(1) if m else None


def _count_tests(root):
    return len(re.findall(r"^\s+def test_", _read(root, "tests/test_core.py"), re.M))


def run_checks(root=ROOT):
    """在指定仓库根目录跑全部自检，返回 ``{ok, checks}``。"""
    root = Path(root)
    sys.path.insert(0, str(root))
    import crkit
    importlib.reload(crkit)
    from crkit import cleanwords

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("VERSION 与 __version__ 一致", crkit.__version__ == version,
        f"VERSION={version} __version__={crkit.__version__}")
    add("CHANGELOG 顶部版本与 VERSION 一致", _changelog_version(root) == version,
        f"changelog={_changelog_version(root)}")
    add("README 版本徽章与 VERSION 一致", _readme_badge(root, "version") == version,
        f"badge={_readme_badge(root, 'version')}")

    ntests = _count_tests(root)
    badge = _readme_badge(root, "tests")
    add("README 测试数与测试方法计数一致", badge == str(ntests),
        f"badge={badge} count={ntests}")

    hits = cleanwords.scan_tree(root)
    add("禁用词零命中", not hits, f"hits={len(hits)}")

    evidence = root / "evidence" / f"v{version}" / "README.md"
    add("当前版本证据目录齐备", evidence.exists(),
        str(evidence.relative_to(root)) if evidence.exists() else "缺失")

    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                             capture_output=True, text=True, check=True)
        dirty = [line for line in out.stdout.splitlines() if line.strip()]
        add("git 工作区干净", not dirty, f"未提交条目 {len(dirty)}")
    except (OSError, subprocess.CalledProcessError) as exc:
        add("git 工作区干净", False, f"无法读取 git 状态：{exc}")

    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def main():
    result = run_checks(ROOT)
    for check in result["checks"]:
        mark = "PASS" if check["ok"] else "FAIL"
        print(f"[{mark}] {check['name']}：{check['detail']}")
    if not result["ok"]:
        print("发布自检未通过，请先修复上述 FAIL 项。", file=sys.stderr)
        sys.exit(1)
    print("发布自检全部通过。")


if __name__ == "__main__":
    main()
