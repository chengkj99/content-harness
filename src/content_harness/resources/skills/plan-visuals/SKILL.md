---
name: plan-visuals
description: Content Harness 成稿已通过两类评审，需要判断是否配图及制定配图计划时使用。
---

# plan-visuals

输入：已通过评审的 manuscript、claims、两类 review。
1. 仅在图比文字更清楚时规划图；没有价值则 images: [] 并写具体 no_images_reason。
2. 每张图填写 path（assets/ 下）、alt、purpose、source、license、location。涉及数据必须回查 claims。
3. 不虚构图中数据，不把装饰图标注为研究结果；来源与授权状态不清楚时先阻塞。
输出：visual-plan。完成标准：每张图都有理解目的、正文位置、来源与许可，或明确无需配图。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
