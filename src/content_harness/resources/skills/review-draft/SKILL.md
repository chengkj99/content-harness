---
name: review-draft
description: Content Harness 需要对润色后的成稿做事实、编辑与风格保真审阅时使用。
---

# review-draft

输入：brief、manuscript、claims、style-spec、style-report 及来源摘录。
1. 逐条对照正文、主张和来源；每条 assessment 记录 support 与具体理由。未登记的新事实、限定词丢失、编造第一人称均为 blocker。
2. 单独检查 brief 兑现、读者行动价值、结构与作者声音；对 draft→manuscript 做语义比较，数字一致不能证明语义一致。
3. 事实评审与编辑评审分别保存，input_hashes 按 status 中当前依赖精确填写。
4. findings 必须有 location、reason、fix、severity；有 blocker 则 verdict=fail，不可为了完成流程标 pass。
输出：fact-review、editorial-review。完成标准是两者通过；失败时明确回到哪个资产修改。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
