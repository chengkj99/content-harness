---
name: shape-brief
description: Content Harness 需要明确文章读者、问题、核心判断和边界时使用。
---

# shape-brief

输入：idea、sources、claims、voice-contract，以及去重目录中相关文章。
1. 将读者的一个实际问题写清楚，区分用户原观点与研究推断。
2. 先根据 voice-contract 判断本篇是个人叙事、教程、评论还是复盘；作者声音和叙事关系必须在 Brief 阶段决定，不能等到润色时补救。
3. 填写 brief frontmatter 的 audience、question、thesis、boundaries、action、dedupe；正文列关键来源、可写和不可写的内容。
4. 对来源中的关键经历分别列出保留、待核实和排除项及理由。去重的是观点与承诺，不得删除本篇故事的发动机。
5. 去重记录已查看的文件和角度差异，未找到材料时如实说明。
输出：brief。check 通过后展示核心判断与限制，停在 brief gate；不能替用户 approve。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、verify-claims、style-promote、style-rollback。
