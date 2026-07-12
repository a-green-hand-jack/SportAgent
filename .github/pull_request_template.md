<!-- PR 是 human gate（见 .agent/human-gates.md）。填完再请 review。 -->

## 目标 / 关联

- Issue / brief:
- Branch base -> target:

## 改了什么

-

## 证据

- Commands run:
- Test result:
- Evidence paths（run id / config / commit / metric source，若涉及实验）:

## 治理 checklist

- [ ] 结构改动已**同 commit**更新相关 `ANATOMY.md` / ledger（same-commit rule）
- [ ] `python scripts/validate-governance.py` 通过
- [ ] 未把 data / checkpoint / run / wandb bytes 加进 Git（只留 index）
- [ ] deliverables 未超过 `lab/research/evidence.yaml` 支持的证据（no overclaim）
- [ ] 若改了能力（agent/skill/hook/permission），已更新对应 doctrine 与理由
- [ ] 外部副作用（push/merge/release/远端作业）已获 human 批准

## 风险 / 回滚

-
