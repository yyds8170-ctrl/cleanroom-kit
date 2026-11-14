"""项目脚手架：从 web / game 模板生成新项目并替换占位符。

占位符：`{{PROJECT}} {{DESCRIPTION}} {{YEAR}} {{AUTHOR}}
{{GITHUB_USER}} {{GITHUB_REPO}}`。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
from pathlib import Path

from .license import write_license, build_notice, LICENSOR, GITHUB_USER, _year

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates"
STACKS = ("web", "game")


def init_project(target_dir, name, description="", stack="web", author=LICENSOR,
                 github_user=GITHUB_USER, github_repo=None, year=None, force=False):
    target = Path(target_dir)
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"目标目录非空：{target}（用 force=True 覆盖）")
    if stack not in STACKS:
        raise RuntimeError(f"未知模板栈：{stack}（可选：{', '.join(STACKS)}）")
    target.mkdir(parents=True, exist_ok=True)

    repo = github_repo or name
    replacements = {
        "{{PROJECT}}": name,
        "{{DESCRIPTION}}": description or name,
        "{{YEAR}}": str(_year(year)),
        "{{AUTHOR}}": author,
        "{{GITHUB_USER}}": github_user,
        "{{GITHUB_REPO}}": repo,
    }

    tpl = TEMPLATE_DIR / stack
    for src in tpl.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(tpl)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        for k, v in replacements.items():
            text = text.replace(k, v)
        dst.write_text(text, encoding="utf-8")

    write_license(target, repo, year=year)
    (target / "NOTICE").write_text(
        build_notice(repo, year=year, github_user=github_user), encoding="utf-8"
    )
    (target / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (target / ".gitignore").write_text(
        "*.log\n.DS_Store\nnode_modules/\n__pycache__/\n", encoding="utf-8"
    )
    return target
