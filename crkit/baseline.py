"""基准快照与回归比对（纯 JSON + PNG，不引入数据库）。

快照存放于 `evidence/baselines/<name>/`：
- `snapshot.json`：compare 指标快照；
- `reference.png`：基准截图（可选）。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import json
import shutil
from pathlib import Path

METRIC_KEYS = ("diff_ratio_pct", "mean_abs_diff", "bg_match", "verdict")
CONTENT_KEYS = ("content_original", "content_rebuild",
                "content_rows_original", "content_rows_rebuild")


def _dir(name, root):
    return Path(root) / "baselines" / name


def save_snapshot(name, metrics, png_path=None, root="evidence"):
    """保存基准指标快照；`metrics` 为 compare 报告子集。"""
    d = _dir(name, root)
    d.mkdir(parents=True, exist_ok=True)
    snapshot = {k: metrics.get(k) for k in METRIC_KEYS + CONTENT_KEYS}
    snapshot["name"] = name
    (d / "snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if png_path:
        shutil.copyfile(png_path, d / "reference.png")
    return d


def load_snapshot(name, root="evidence"):
    d = _dir(name, root)
    f = d / "snapshot.json"
    if not f.exists():
        raise RuntimeError(f"基线不存在：{name}（{f}）")
    return json.loads(f.read_text(encoding="utf-8"))


def diff_snapshot(name, current, max_ratio_drift=5.0, mean_diff_tol=3.0, root="evidence"):
    """当前指标与基线回归比对，返回漂移项清单。

    - `diff_ratio_pct` 回升超过 `max_ratio_drift` 个百分点记漂移；
    - `mean_abs_diff` 绝对差超过 `mean_diff_tol` 记漂移，轻微抖动在容差内不报；
    - `bg_match` / `verdict` 与基线不一致记漂移（布尔与分级不容差）；
    - 内容列/行区间新增或消失记入 `content_changes`。
    """
    base = load_snapshot(name, root=root)
    drift = []
    for key in METRIC_KEYS:
        old, new = base.get(key), current.get(key)
        if key == "diff_ratio_pct":
            if new is not None and old is not None and (new - old) > max_ratio_drift:
                drift.append({"metric": key, "baseline": old, "current": new,
                              "detail": f"差异占比回升 {new - old:.1f} 个百分点"})
        elif key == "mean_abs_diff":
            if new is not None and old is not None and abs(new - old) > mean_diff_tol:
                drift.append({"metric": key, "baseline": old, "current": new,
                              "detail": f"平均差偏离 {abs(new - old):.1f}（容差 {mean_diff_tol}）"})
        elif old != new:
            drift.append({"metric": key, "baseline": old, "current": new,
                          "detail": "指标与基线不一致"})
    content_changes = []
    for side in CONTENT_KEYS:
        if base.get(side) != current.get(side):
            content_changes.append({"field": side, "baseline": base.get(side),
                                    "current": current.get(side)})
    return {"name": name, "drift": drift, "content_changes": content_changes,
            "regressed": bool(drift)}
