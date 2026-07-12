# human/ — agent 规则

`human/` 是 human 与 agent 的协作界面。这里的内容**以 human 为权威来源**；agent 的角色主要是读取、遵守、以及协助整理。

## 允许

- 读取 `briefs/active/` 的 brief 作为任务权威定义，并据此工作。
- 根据 brief 起草 plan、把结果整理成 result、把 recipe 做成小 diff，放到对应 `reviews/` 子目录等待 human 评审。
- 起草 ADR 草稿放 `decisions/`（状态标 `proposed`，由 human 改为 `accepted`/`rejected`）。
- 把 `inbox/` 的零散输入分类、搬到正式位置，并清空。

## 禁止

- 不要自行把 ADR 状态改成 `accepted`——接受/拒绝是 human 的动作。
- 不要绕过 brief 的 scope：`scope forbidden paths` 里的路径不许碰。
- 不要删改 `briefs/completed/` 与已 `accepted` 的 `decisions/`（历史记录）。
- 不要把需要 human 拍板的事「替 human 决定」；拿不准就留在 `reviews/` 等待。

## 必须验证

- 开始任务前，确认对应 `briefs/active/` brief 的 success criteria 与 scope 已读懂。
- 提交 review 前，附上可验证信息（命令、产物路径、diff），让 human 能快速判断。
- brief 完成后，把它从 `active/` 移到 `completed/`，并在 `current-status.md` 留指针。

## 与 gate 的关系

review 与 decision 是 human gate 的载体，配合 `.agent/human-gates.md`。recipe review 针对小 diff，见 `.agent/claude-code-recipe-policy.md`。
