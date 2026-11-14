# {{PROJECT}}

{{DESCRIPTION}}

## 本地运行

```bash
python3 -m http.server 8080
```

浏览器访问 `http://127.0.0.1:8080/`（ES module 需走 HTTP，不能直接打开 file://）。

## 复刻闭环

- 截图：`crk shot --url http://127.0.0.1:8080/ --out evidence/shot.png`
- 取证：`crk inspect --url http://127.0.0.1:8080/ --out evidence/inspect.json`
- 交互：`crk act --url http://127.0.0.1:8080/ --script actions.json --out evidence/act-log.json`
- 断言：`crk probe --url http://127.0.0.1:8080/ --assertions assertions.json --out evidence/probe-report.json`
- 对照：`crk compare --orig evidence/orig.png --rebuild evidence/rebuild.png`

## 目录

- `evidence/`：截图、取证、动作日志、断言报告
- `tests/`：校验脚本与断言
- `js/`：ES module 页面脚本

项目地址：https://github.com/{{GITHUB_USER}}/{{GITHUB_REPO}}

许可证：PolyForm Noncommercial License 1.0.0。Copyright (c) {{YEAR}} {{AUTHOR}}（GitHub: {{GITHUB_USER}}）。
