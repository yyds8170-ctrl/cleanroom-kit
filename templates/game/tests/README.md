# 校验脚本

在此放置游戏复刻的校验：单测、像素对照、交互动作与状态断言。

- 单测：`python3 -m unittest discover -s tests`
- 交互：`crk act --url http://127.0.0.1:8080/ --script actions.json`
- 断言：`crk probe --url http://127.0.0.1:8080/ --assertions assertions.json`
- 对照：`crk compare --orig evidence/orig.png --rebuild evidence/rebuild.png`
