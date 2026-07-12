# Repo 编辑护栏

改 repo 的默认流程与防漂移/防膨胀规则。这是外层 Claude Code development harness 的规则（与内层 release agent 行为契约分开，见 `release-agent-boundary.md`）。

## 默认流程（non-trivial edit）

```
issue / task packet
→ 选正确 base branch
→ 短 topic 分支
→ fresh worktree
→ 读 AGENTS / CLAUDE / ANATOMY / current-status
→ 只实现 branch scope
→ 同分支内更新 anatomy / ledger / plan / artifact index（若受影响）
→ 跑定向测试 + repo validator
→ 起草 PR（evidence + risks）
→ main agent / human review
→ merge 到正确 target
→ 归档 branch/worktree 状态
```

## 防漂移 / 防膨胀

- 根目录只保留入口与工具必须发现的文件；长文、报告、实验记录不堆 root。
- 复杂目录才写 `ANATOMY.md`（地图，不是教程）。
- 文件移动/重构/ownership/状态文件/tool routing/workflow 变化，**同 commit** 更新相关 anatomy / ledger。
- 改结构前 grep 被动文件名在所有 `ANATOMY.md` / index YAML / ledger 的引用。
- `lab/runs/`、remote outputs、checkpoints、datasets、logs 默认不进 Git，只写 manifest/index/summary。
- 新能力先登记 contract/manifest 再写实现。
- 外部副作用（push/PR/merge/release/远端作业/删远端产物）必须 human gate。

## 门禁

改动前后跑 `python scripts/validate-governance.py`。validator 检查目录、必需文件、引用、根污染、禁止路径、权限、实验卡与证据链。
