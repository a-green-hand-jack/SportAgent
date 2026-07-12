---
name: anatomy-drift-control
description: 在改动 repo 结构（新增/改名/移动文件）前后，用来 grep 所有引用并在同一 commit 更新 anatomy，防止结构地图漂移。
---

# anatomy-drift-control

任何触及 repo 结构的改动，都要先查清被动文件在 ANATOMY / index / ledger 里的引用，改完在**同一个 commit**里更新这些地图。

## 适用边界

适用：新增/改名/移动/删除文件或目录、拆分模块、调整结构地图时。
不适用：只改文件内部实现且不影响其在 anatomy 中的描述（但若越过行数阈值仍需更新）。

## 输入 / 输出 artifact

- 输入：将要改动的结构（被动文件名/路径）。
- 输出：更新后的相关 `ANATOMY.md`、index YAML、ledger，与代码改动在同一 commit。

## 需要读取的 ledger

- `.agent/anatomy-protocol.md`（阈值、citation 规则、same-commit rule）。
- 所有 `ANATOMY.md`、index YAML、相关 ledger。

## 允许修改的路径

- 各 `ANATOMY.md`
- 受影响的 index YAML 与 ledger
- 被改动的结构本身（按已批准的 plan）
- 其余一律只读。

## 步骤

1. 改前 grep：对每个被动文件名/路径，在所有 `ANATOMY.md`、index YAML、ledger 中搜出引用点。
2. 评估阈值：文件超过 80 行需在 anatomy 有条目，超过 120 行需 line-addressed citation（指到行）。
3. 执行结构改动。
4. 同步更新 anatomy：修正路径、行号引用、描述；遵守 line-addressed citation。
5. same-commit rule：结构改动与 anatomy 更新放进同一 commit，绝不分离。

## 验证命令

```
python scripts/check-anatomy-drift.py
python scripts/validate-governance.py
```

## 失败时的 handoff

- `check-anatomy-drift.py` 报未同步引用：在本 commit 内补齐，不得绕过。
- 若引用面过大、影响不明：按 `.agent/templates/handoff.md` 升级，先转 interactive-plan-doc 规划改动。
