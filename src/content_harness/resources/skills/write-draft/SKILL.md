---
name: write-draft
description: Content Harness 需要根据简报、提纲与已核验主张生成正文时使用。
---

# write-draft

输入必须同时包含：brief、outline、claims、voice-contract、style-spec。
1. 写作前明确读者、核心判断、不适用边界；brief 始终是独立输入。
2. 按提纲写可阅读正文，在每条主张对应位置加入 <!-- claim:claim-id -->。不得引入台账之外的关键事实；确需新增则先更新 sources/claims。
3. 数字、产品名称、限定词和经历按台账保留。无个人证据不能写“我亲测”“读者反馈”。
4. 应用 Author 与 Scene 的表达规则。个人叙事应让作者持续在场，优先使用已核验的一手经历，不能用假设案例和外部权威替换更相关的生活证据。Polish 的全文润色留给 refine-style。
输出：draft。check 通过且逐段能回到 brief 和 claims 才算完成；引用标记覆盖不等于语义事实已经核验。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、verify-claims、style-promote、style-rollback。
