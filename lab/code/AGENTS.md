# lab/code/ — agent 约束

## 允许

- 在 `src/` 实现与重构模块；在 `configs/` 增改配置；在 `scripts/` 写脚本；在 `experiments/` 建实验。
- 增删测试，保持 `tests/` 与被测代码同步。

## 禁止

- 禁止在代码里硬编码密钥/私密路径——那些属于 `../infra/private/`。
- 禁止把数据 bytes、checkpoint 写进本目录并提交 Git。
- 禁止自行触发训练/评测作业（人类闸门在 `../infra/launch/`）。

## 必须验证

- 改动后跑测试：`tests/`。
- 结构改动（新增模块、改调用关系）同 commit 更新 `src/ANATOMY.md` 与本层 `ANATOMY.md`。
- 治理相关改动后：`python scripts/validate-governance.py`。

## 禁止路径

- 不在本目录持久化任何 gitignore 的 bytes。
