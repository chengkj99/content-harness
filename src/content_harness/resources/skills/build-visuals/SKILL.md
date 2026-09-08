---
name: build-visuals
description: Content Harness 已有配图计划，需要制作或登记文章图片时使用。
---

# build-visuals

输入：已登记 visual-plan。
1. 依据计划用当前客户端可用的画图工具制作图片，或登记已获使用权的本地图片；工具不可用时如实阻塞。
2. 图片置于 artifacts/assets/；不得把外部路径或符号链接作为图像资产。
3. 支持静态 SVG、PNG、JPEG、WebP。实际打开检查可读性、截断、数据和替代文本；CLI 的格式检查不能替代视觉验收。
4. visual-assets 必须与 visual-plan 的条目一致。需要改变图片或许可说明时先更新计划。
输出：visual-assets + 图片文件。完成标准：文件检查和视觉检查都完成；无图分支无需生成装饰图。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
