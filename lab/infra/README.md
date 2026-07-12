# lab/infra/ — 运行环境层

跑作业前的一切环境配置都在这里：权限、路径、存储、启动、探针、私密。想「让代码在这台机器上正确、安全地跑起来」，来这层。

## 子目录

| 目录 | 是什么 |
| --- | --- |
| `permissions/` | 解释 `.claude/settings.json` 与 `.codex/rules/default.rules` 的 deny/ask/allow/prompt 为何这样设（owner + 理由 + 验证） |
| `paths/` | 路径约定：数据/输出/checkpoint 落在哪 |
| `storage/` | 存储后端与配额约定 |
| `launch/` | 可复现的启动命令（**启动是人类闸门**） |
| `probes/` | 环境探针：检查 GPU/依赖/连通性 |
| `private/` | 私密配置与密钥，**永不进 Git** |

## 常见入口

- 要理解某条高危权限为何被 deny/ask，看 `permissions/`。
- 要跑一次作业，用 `launch/` 里的命令；不要绕过人类闸门。
- 密钥只放 `private/`，绝不进代码或 Git。
