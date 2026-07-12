---
name: adopt-existing-repo
description: 把一个已有 Git repo 分步、可验证、尽量无人值守地收敛成本模板的完整形态；适用于迁移旧 ML/research repo，而不是从 GitHub template 新建空项目。
---

# adopt-existing-repo

这是 template-converger，不是简单 overlay。目标是让已有 repo 最终拥有本模板的
control plane、目录形态、validator 与 memory/session 纪律，同时保留原 repo 的可追溯
bytes 与测试能力。

## 适用边界

适用：已有 Git repo 想迁移成 `ml-project-repo-agent-native-template` 形态。

不适用：新项目从零开始（直接 Use this template）；需要人工判断的大规模代码重构；需要移动
数据/模型/checkpoint 大 bytes 的迁移。

## 输入 / 输出 artifact

- 输入：已有 Git repo 路径。
- 输出：目标 repo 的 `lab/docs/audits/template-adoption/state/*.json`、`phase-log.jsonl`、
  `lab/docs/audits/template-adoption-report.md`，以及迁移后的 template 目录形态。

## 需要读取的 ledger

- `plans/20260709-adopt-existing-repo.zh.md`：当前 feature contract。
- `.agent/action-boundary.md`：保护路径和外部副作用边界。
- `scripts/ANATOMY.md`：迁移脚本和 validator 的维护点。

## 步骤

1. 在隔离分支/worktree 中操作目标 repo。不要直接在用户的 active branch 上做破坏性尝试。
2. 运行 discover：

   ```bash
   python scripts/adopt-existing-repo.py /path/to/repo --phase discover --project-name <slug>
   ```

3. 运行 baseline，记录 tracked file hash、root entries、原生测试结果：

   ```bash
   python scripts/adopt-existing-repo.py /path/to/repo --phase baseline \
     --test-command "python -m unittest discover"
   ```

4. 运行 scaffold，把模板 control plane 写入目标 repo。冲突文件会先搬到
   `human/imported/adoption-conflicts/`，不会覆盖丢失。
5. 运行 normalize，把原 repo 的 root 项保守移动到 `lab/code/imported/<slug>/`。
   若命中受保护路径或目标冲突，停下并报告。
6. 运行 prove，检查原 tracked bytes 仍存在、template governance 可跑、原生测试可在
   imported root 中运行。
7. 若只想无人值守跑完整保守路径：

   ```bash
   python scripts/adopt-existing-repo.py /path/to/repo --phase all --policy conservative
   python scripts/check-adoption-integrity.py /path/to/repo
   ```

## 验证命令

```bash
python lab/evals/adoption/run-adoption-smoke.py
python scripts/validate-governance.py --strict
git diff --check
```

## 失败时的 handoff

- `normalize` blocked：通常是 protected root path 或目标路径已存在。不要猜；读
  `phase-log.jsonl` 和 report，再决定是否加新的可证明策略。
- integrity failed：说明 baseline tracked bytes 找不到同 hash 副本，优先当作 P0。
- governance failed：先修目标模板形态或本模板脚本，不要忽略。
