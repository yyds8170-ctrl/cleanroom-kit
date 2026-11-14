# {{PROJECT}}

{{DESCRIPTION}}

## 本地运行

```bash
python3 -m http.server 8080
```

浏览器访问 `http://127.0.0.1:8080/`。

## 复刻闭环

- 截图：`crk shot --url http://127.0.0.1:8080/ --out evidence/shot.png`
- 取证：`crk inspect --url http://127.0.0.1:8080/ --out evidence/inspect.json`
- 对照：`crk compare --orig evidence/orig.png --rebuild evidence/rebuild.png`
- 无障碍：`crk a11y --inspect evidence/inspect.json`

## 目录

- `evidence/`：截图、取证、对照等过程证据
- `tests/`：校验脚本与断言
- `js/`：页面脚本（如有）

项目地址：https://github.com/{{GITHUB_USER}}/{{GITHUB_REPO}}

许可证：PolyForm Noncommercial License 1.0.0。Copyright (c) {{YEAR}} {{AUTHOR}}（GitHub: {{GITHUB_USER}}）。
