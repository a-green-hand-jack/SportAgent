---
description: 把 paper claim 映射到代码并找最小可复现路径
argument-hint: <paper 名/链接>
---

复现 $ARGUMENTS。先只读模式，不改代码、不下载大资产。

三层目标：读懂 claim/method → 找到 repo 中对应实现 → 跑最小 smoke/sanity/metric check。

返回：
1. 与复现相关的 paper claims
2. 实现每个 claim 的代码文件
3. 需要的 data/checkpoints
4. 最小 smoke test
5. 完整复现命令（若有）
6. 缺失/歧义之处

用 `.agent/templates/experiment-card.md` 结构记录；证据表见 `lab/research/`。
进入实际跑实验/整理证据阶段，走 `experiment-workflow` skill（claim→artifact 证据链）。
