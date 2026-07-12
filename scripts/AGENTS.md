# scripts/ — AGENTS

## 允许改

- 扩展 validator 的检查项（新增受保护路径、新增必需文件、新增能力索引校验）。
- 每加一条规则，同步更新 `README.md` 与相关 `.agent/` doctrine，说明「为什么」。

## 必须验证

- 改完自测：`python scripts/validate-governance.py`（应对干净 repo 通过）。
- 保持无第三方硬依赖；PyYAML 之类必须 optional（缺失时降级为 warning，不报错）。

## 禁止

- 让 validator 依赖网络或外部服务。
- 把 validator 变成会修改 repo 的脚本——它只读、只报告、只返回退出码。

## 原则

validator 是「agent 能否继续扩展 repo 的护栏」。规则要能对应到 `.agent/action-boundary.md` / `anatomy-protocol.md` / `artifact-policy.md` 里的某条 doctrine。
