# lab/code/src/ — 源码层

项目核心源码所在。模板里为空，落地时这里会放：

- **模型模块**：网络结构、层、前向逻辑。
- **数据模块**：dataset / dataloader / 预处理（与 `../../data/` 的索引配合，不在此存 bytes）。
- **训练模块**：训练循环、优化、调度、checkpoint 逻辑。
- **评估模块**：指标、评测循环（与 `../../evals/` 配合）。

## 常见入口

- 结构地图见 `ANATOMY.md`（当前为意图描述；真实模块落地后补 line-addressed 引用）。
- 配置来自 `../configs/`，实验入口在 `../experiments/`。
