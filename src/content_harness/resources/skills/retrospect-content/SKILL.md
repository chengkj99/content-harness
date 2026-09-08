---
name: retrospect-content
description: Content Harness 用户提供真实发布回执、数据或返工经历，要求复盘时使用。
---

# retrospect-content

M1 的发布接口和指标采集未实现；不要假造 receipt 或声称自动采集。
1. 根据用户给出的可核验回执、指标与 run 内记录，区分事实、推断和未知。
2. 若只有返工过程，则复盘失败资产、失效原因、人工修改和耗时；不推测阅读量效果。
3. 在 run 的 notes/retrospective.md 保存人工复盘与下一步可验证实验；该文件不冒充正式 DAG 发布回执。
4. 有风格价值的修改交给 learn-style 生成候选，不能自动晋升。
完成标准：每条结论能回到证据，未采集数据明确标注，下一篇只建议一项可测改进。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
