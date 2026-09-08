---
name: shape-brief
description: Content Harness 需要明确文章读者、问题、核心判断和边界时使用。
---

# shape-brief

输入：idea、sources、claims，以及去重目录中相关文章。
1. 将读者的一个实际问题写清楚，区分用户原观点与研究推断。
2. 填写 brief frontmatter 的 audience、question、thesis、boundaries、action、dedupe；正文列关键来源、可写和不可写的内容。
3. 去重记录已查看的文件和角度差异，未找到材料时如实说明。
输出：brief。check 通过后展示核心判断与限制，停在 brief gate；不能替用户 approve。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
