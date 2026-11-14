# 闭环验证报告

总体判定：**fail**（共 6 步，通过 5，失败 1）

目标：http://127.0.0.1:18193/

| 步骤 | 状态 | 产物 | 说明 |
| --- | --- | --- | --- |
| shot | 通过 | shot.png | 1280x900 |
| inspect | 通过 | inspect.json | 元素 54 |
| a11y | 失败 | a11y.json | 失败 34，未核验 0 |
| compare | 通过 | compare.json | 16.764062499999998% minor |
| probe | 跳过 | — | 未提供断言，跳过 |
| baseline | 跳过 | — | 未指定基线，跳过 |
