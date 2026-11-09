"""生成 PolyForm Noncommercial 1.0.0 LICENSE（内嵌标准条款 + 洋洋署名）。"""
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "polyform-noncommercial.txt"
LICENSOR = "洋洋"
GITHUB_USER = "yyds8170-ctrl"
YEAR = 2026


def build_license(repo_name, note=""):
    standard = _DATA.read_text(encoding="utf-8").rstrip()
    tail = f"""

---

## Licensor

The licensor of this software is {LICENSOR} (GitHub: {GITHUB_USER}).

Required Notice: Copyright (c) {YEAR} {LICENSOR} (https://github.com/{GITHUB_USER}/{repo_name})
"""
    if note:
        tail += f"\n{note.strip()}\n"
    return standard + tail


def write_license(target_dir, repo_name, note=""):
    path = Path(target_dir) / "LICENSE"
    path.write_text(build_license(repo_name, note), encoding="utf-8")
    return path


def build_notice(repo_name):
    return (
        f"Copyright (c) {YEAR} {LICENSOR}\n"
        f"Project: {repo_name}\n"
        f"Licensed under the PolyForm Noncommercial License 1.0.0 (noncommercial use only).\n"
        f"See LICENSE for the full terms.\n"
    )
