# human/reviews/results/ — result 评审

agent 完成工作后把**结果**交到这里评审。尤其是影响 `deliverables/` 的产出（论文段落、图表、release），必须经过这里再对外。

## 流程

1. agent 整理结果：改了什么、跑了什么、产物在哪、claim 是否有 evidence 支撑。
2. 在本目录放一条 review 记录，附可验证信息（命令、产物路径、diff、`lab/artifacts/` 指针）。
3. human 核对——特别是 **no overclaim**：结论是否被 `lab/research/evidence.yaml` 支撑。
4. 批准后方可推进交付物状态（见 `deliverables/index.md` 与 `.agent/human-gates.md`）。

## review 应包含

- 结果摘要与对应 brief / plan 指针。
- 支撑证据路径；未证明的部分明确标出。
- human 结论与日期。

批准是 human 的动作，agent 只提交待评审。
