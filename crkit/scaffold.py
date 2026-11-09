"""项目脚手架：从模板生成新项目并替换占位符。"""
import shutil
from pathlib import Path

from .license import write_license, build_notice

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "web"


def init_project(target_dir, name, description="", force=False):
    target = Path(target_dir)
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"目标目录非空：{target}（用 force=True 覆盖）")
    target.mkdir(parents=True, exist_ok=True)

    replacements = {"{{PROJECT}}": name, "{{DESCRIPTION}}": description or name}

    for src in TEMPLATE_DIR.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE_DIR)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        for k, v in replacements.items():
            text = text.replace(k, v)
        dst.write_text(text, encoding="utf-8")

    write_license(target, name)
    (target / "NOTICE").write_text(build_notice(name), encoding="utf-8")
    (target / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (target / ".gitignore").write_text(
        "*.log\n.DS_Store\nnode_modules/\n__pycache__/\n", encoding="utf-8"
    )
    return target
