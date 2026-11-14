"""生成 PolyForm Noncommercial 1.0.0 LICENSE（内嵌标准条款 + 洋洋署名）。

年份可配，默认当前年；NOTICE 附带 GitHub 项目 URL。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import datetime
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "polyform-noncommercial.txt"
LICENSOR = "洋洋"
GITHUB_USER = "yyds8170-ctrl"


def _year(year):
    return year or datetime.date.today().year


def build_license(repo_name, note="", year=None):
    standard = _DATA.read_text(encoding="utf-8").rstrip()
    y = _year(year)
    tail = f"""

---

## Licensor

The licensor of this software is {LICENSOR} (GitHub: {GITHUB_USER}).

Required Notice: Copyright (c) {y} {LICENSOR} (https://github.com/{GITHUB_USER}/{repo_name})
"""
    if note:
        tail += f"\n{note.strip()}\n"
    return standard + tail


def write_license(target_dir, repo_name, note="", year=None):
    path = Path(target_dir) / "LICENSE"
    path.write_text(build_license(repo_name, note, year=year), encoding="utf-8")
    return path


def build_notice(repo_name, year=None, github_user=GITHUB_USER):
    y = _year(year)
    return (
        f"Copyright (c) {y} {LICENSOR}\n"
        f"Project: {repo_name}\n"
        f"Project URL: https://github.com/{github_user}/{repo_name}\n"
        f"Maintainer: {LICENSOR} (https://github.com/{github_user})\n"
        f"\n"
        f"This product is independently implemented and contains no third-party source code\n"
        f"or binaries. It is not affiliated with, endorsed by, or sponsored by any third party.\n"
        f"\n"
        f"Licensed under the PolyForm Noncommercial License 1.0.0 (noncommercial use only).\n"
        f"See LICENSE for the full terms.\n"
    )
