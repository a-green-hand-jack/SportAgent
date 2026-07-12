# Artifact 政策

repo 需要 artifact memory，因为 human 会忘记「东西在哪里、哪个 run 还有效、哪个 checkpoint 过期、哪个 table 是旧口径」。保持 repo 干净不是洁癖，是研究记忆压缩。

## 索引文件

```
lab/artifacts/result-index.yaml    结果
lab/artifacts/table-index.yaml     表格
lab/artifacts/figure-index.yaml    图
lab/artifacts/trace-index.yaml     agent/实验 trace
lab/artifacts/model-index.yaml     模型（逻辑索引，bytes 不进 Git）
lab/models/checkpoint-index.yaml   checkpoint
lab/data/dataset-index.yaml        dataset split
deliverables/index.md              对外交付物
```

## 每个资产至少回答

- 在哪里（storage path / URI）？怎么看？
- 对应哪个 commit / config / run id？
- 支持哪个 claim / table / figure？
- 状态：`active` / `superseded` / `archived` / `unknown`？
- 缺哪些 metadata？何时该归档或删索引？

## 维护方式

不靠 human 记忆。用 `artifact-librarian` agent + `artifact-indexing` skill，在实验结束、table 更新、figure 生成、checkpoint 选择、paper claim promotion 后主动维护索引。

## 结果进入 evidence 的门槛

只有 run 可定位、config 可复现、metric 来源清楚、与 baseline 比较清楚、caveat 写明、且经 fresh verifier 或本人复核，结果才进 `lab/research/evidence.yaml` / `lab/artifacts/result-index.yaml` / 论文。

## bytes 边界

data / checkpoint / run / wandb bytes 不进 Git，只留 index。删除/移动 bytes 走 human gate；agent 只生成归档提案。
