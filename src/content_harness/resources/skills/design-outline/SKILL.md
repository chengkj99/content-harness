---
name: design-outline
description: Content Harness 已确认 brief 并需要设计文章提纲时使用。
---

# design-outline

输入：已批准 brief、voice-contract、style-spec。
1. 以 brief 的读者问题为主线，按段落说明这一节解决什么、凭什么、读者得到什么。
2. 使用 Scene 层结构规则：有真实第一人称材料时，优先让人物、动作和冲突进入开头，并让作者经历贯穿后文；不得为了张力补造事件。
3. 个人叙事中，建议应在作者获得发言资格之后出现；不得用外部权威或假设案例替换更相关的一手经验。
4. 为每节标注对应主张与边界，结尾兑现 brief 的 action。必要时指出材料缺口并退回 research-claims。
输出：outline。完成标准：覆盖 brief 的核心判断，章节不偏题，每个需要事实支持的段落都有已登记主张。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，展示待确认的具体内容并在聊天中等待用户明确回复。确认后，Agent 可用对应命令的 --chat-confirmed 模式记录决定，传入审阅时的哈希；approve 还要传入资产 revision。内容变化时重新请求确认；不得自行决定或把一般性的“继续”当成确认。
