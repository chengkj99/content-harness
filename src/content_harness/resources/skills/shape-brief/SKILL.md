---
name: shape-brief
description: Content Harness 需要明确文章读者、问题、核心判断和边界时使用。
---

# shape-brief

输入：idea、sources、claims、voice-contract，以及去重目录中相关文章。
1. 将读者的一个实际问题写清楚，区分用户原观点与研究推断。
2. 先根据 voice-contract 判断本篇是个人叙事、教程、评论还是复盘；作者声音和叙事关系必须在 Brief 阶段决定，不能等到润色时补救。
3. 填写 brief frontmatter 的 audience、question、thesis、boundaries、action、dedupe；正文列关键来源、可写和不可写的内容。
   在正文说明：读者为何会问这个问题，作者凭什么作出判断，理由怎样引出可行行动。若某一环缺材料，写明缺口，不用口号替代。
   同时在 Brief 正文说明读者已有经验、需要解释的关键术语，以及读完应能复述的判断或执行的动作；仅依据输入填写，未知时标明缺口。教程说明任务与验证点，叙事和评论可交付理解，不强塞操作清单。
4. 对来源中的关键经历分别列出保留、待核实和排除项及理由。去重的是观点与承诺，不得删除本篇故事的发动机。
5. 去重记录已查看的文件和角度差异，未找到材料时如实说明。
输出：brief。check 通过后展示核心判断与限制，停在 brief gate；不能替用户 approve。

操作前读取 [清晰表达原则](../content-harness/references/clear-expression.md)，按本 Skill 所处阶段执行下述检查。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

## 判断与边界的落点

Brief 正文分别写：作者愿意说出的判断、支撑理由、希望读者读完获得的信心，以及边界放在哪里。区别必须出现在读者正文的限定条件与只需内部执行的资料/隐私检查；不要把内部约束逐条复制成免责声明。没有真实故事的观点文可沿判断推进，不强加私人遭遇或脆弱感。

遇到缺少输入、stale 依赖或人类审批要求时，展示待确认的具体内容并在聊天中等待用户明确回复。确认后，Agent 可用对应命令的 --chat-confirmed 模式记录决定，传入审阅时的哈希；approve 还要传入资产 revision。内容变化时重新请求确认；不得自行决定或把一般性的“继续”当成确认。
