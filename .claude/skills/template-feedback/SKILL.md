---
name: template-feedback
description: 从当前下游 ml-research-project 把「模板需要新增/修改/增强的能力」自动打包成上游 template repo 的 issue；带上模板版本、涉及路径与复现，走 from-downstream 标签。human 不必手写 issue。
---

# template-feedback

下游项目在使用中发现模板缺口时用它。把「真实使用暴露的问题」变成上游可解决的 issue，
解决后再由 `template-sync` 追平回来。这是四站闭环的第②站，见
`.agent/template-versioning-policy.md`。

## 适用边界

适用：当前 repo 是从本模板采用（存在 `.template.toml`）的下游项目，需要向上游反馈框架层缺口。

不适用：在上游 template repo 本身开发（直接建 issue 即可）；反馈的是项目自身实验/数据问题
（那属于项目内部，不该上报模板）。

## 输入 / 输出 artifact

- 输入：human 的一句话诉求（缺什么/要改什么）。
- 输出：上游 template repo 的一个 GitHub issue（`from-downstream` 标签），issue 号回报给 human。

## 步骤

1. **读版本锚点**：读当前 repo 根的 `.template.toml`，取 `origin`（上游 repo slug）与 `version`。
   缺文件 → 说明这不是本模板的下游 repo，停止。
2. **定位框架层路径**：根据诉求，找出涉及的框架层文件（agent/skill/hook/validator/doctrine）。
   分类真源是上游的 `template-manifest.toml`；本地拿不到就凭路径经验判断并在 issue 里注明「待上游确认」。
3. **收集证据**：若有报错/validator 输出/失败命令，抓成最小复现。没有就写清观察到的现象。
4. **判类型**：新增(MINOR) / 修复(PATCH) / 增强 / 破坏性(MAJOR)——只作预期提示，最终判级在上游。
5. **建 issue**（narrow tool boundary：只允许 `gh issue create`，不改本地文件）：

   ```bash
   gh issue create \
     --repo "<origin>" \
     --label from-downstream \
     --title "[downstream] <一句话>" \
     --body "<按 .github/ISSUE_TEMPLATE/downstream-feedback.yml 的字段组织正文>"
   ```

   正文必含：下游当前模板版本、涉及框架层路径、期望改动类型、场景、复现、下游项目名。
6. **回报**：把 issue URL/号返回 human。不在下游本地改任何框架层文件——修复发生在上游。

## human gate（见 `.agent/human-gates.md`）

- `gh issue create` 是对外写操作：**建 issue 前把拟好的 title/body 给 human 过目确认**，再提交。
- 严禁在下游本地「顺手修」框架层来绕过闭环——那会造成下游私自分叉、下次 sync 冲突。

## 与其他能力的关系

- 上游解决后发版：`scripts/bump-template-version.py`（判级见 versioning policy）。
- 下游追平：`scripts/template-sync.py` 会反查「你上报的 issue 这次是否被 closed」，闭合闭环。
