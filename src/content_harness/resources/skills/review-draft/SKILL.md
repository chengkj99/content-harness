---
name: review-draft
description: Content Harness 需要对润色后的成稿做事实、编辑与风格保真审阅时使用。
---

# review-draft

输入：brief、manuscript、claims、style-spec、style-report 及来源摘录。
1. 逐条对照正文、主张和来源；每条 assessment 记录 support 与具体理由。未登记的新事实、限定词丢失、编造第一人称均为 blocker。
2. 单独检查 brief 兑现、读者行动价值与结构；对 draft→manuscript 做语义比较，数字一致不能证明语义一致。
3. 另写 voice-review，逐项覆盖 voice-contract.required_dimensions。每项必须给出分数、正文位置、证据、理由和必要的修复；个人叙事还需指出一段作者特异性内容，并执行“替换作者后是否仍成立”的通用性测试。
4. 事实评审、编辑评审和声音评审分别保存，input_hashes 按 status 中当前依赖精确填写。
5. findings 必须有 location、reason、fix、severity；有 blocker、维度低于 3 分、通用性测试失败或缺少作者特异性段落时 verdict=fail，不可为了完成流程标 pass。
输出：fact-review、editorial-review、voice-review。完成标准是三者通过；失败时明确回到 Claims、Brief、Outline、Draft 或 Manuscript 中最早出错的资产。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

## 防止形式合格掩盖语气问题

- 通用性测试先暂时遮住署名、履历、标题与旧引文，再看正文是否仍有具体判断、理由与取舍；仅凭“这句话由作者说过”不能通过全文声音评审。
- 根据本篇体裁检查作者的态度、读者获得的信心和边界是否适量。没有证据写情绪时，不靠虚构情绪补分；引用可追溯不等于中段有作者性。
- 按 voice-contract.dimension_guidance 逐项找证据，同时寻找最薄弱段落。无修改并非错误，但不得用“初稿落盘前已优化”或“无违禁词”证明全部合格。
- 区分不承诺外部结果与支持读者尝试；内部校验通过不等于作者认可。反馈出现新观点、保证性表述或逻辑歧义时分别说明，不能全当成措辞偏好。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、verify-claims、style-promote、style-rollback。
