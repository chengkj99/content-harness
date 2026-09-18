---
name: refine-style
description: Content Harness 正文需要按风格润色、去 AI 味或生成评审用成稿时使用。
---

# refine-style

输入：draft、style-spec、claims。
1. 没有 Scene/Polish 时，保持 draft 原文成为 manuscript；有选择时按指定强度进行局部编辑。
2. 去 AI 味检查模板过渡、空泛排比、机械总结、无根据断言；保留作者有意的正式表达，不追求检测器分数。
3. 不改数字、日期、链接、引文、事实标记、限定词或 protected_terms。需要事实纠错时返回 draft/claims，不在润色中偷偷改变。
4. 登记 manuscript，再生成 style-report，input_hashes 精确绑定 draft、manuscript、style-spec；每项 changes 写位置、类型、理由，rejected 写未采用建议。
5. style-report 必须逐项记录已选 Scene/Polish 的 rule_assessments。即使无需修改，也要以正文位置说明 already-satisfied；不能用空 changes 代替规则检查。
输出：manuscript 与 style-report。完成标准：两者检查通过；语义含义仍需后续 review 检查，不能只看字符串门禁。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、verify-claims、style-promote、style-rollback。
