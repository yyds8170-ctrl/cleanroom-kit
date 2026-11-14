# 闭环验证报告

总体判定：**pass**（共 6 步，通过 6，失败 0）

目标：https://example.com

| 步骤 | 状态 | 产物 | 说明 |
| --- | --- | --- | --- |
| shot | 通过 | shot.png | 1280x900 |
| inspect | 通过 | inspect.json | 元素 7 |
| a11y | 通过 | a11y.json | 失败 0，未核验 7 |
| compare | 跳过 | — | 无参考图，跳过对照 |
| probe | 跳过 | — | 未提供断言，跳过 |
| baseline | 跳过 | — | 未指定基线，跳过 |
