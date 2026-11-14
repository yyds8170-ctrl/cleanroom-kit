# 校验脚本

在此放置复刻项目的校验：纯标准库单测、像素对照断言、页面状态断言等。

- 单测：`python3 -m unittest discover -s tests`
- 对照：`crk compare --orig evidence/orig.png --rebuild evidence/rebuild.png`
- 断言：`crk probe --url http://127.0.0.1:8080/ --assertions assertions.json`
