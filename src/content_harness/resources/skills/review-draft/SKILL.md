---
name: review-draft
description: Content Harness 需要对润色后的成稿做事实、编辑与风格保真审阅时使用。
---

# review-draft

输入：brief、manuscript、claims、style-spec、style-report 及来源摘录。
1. 逐条对照正文、主张和来源；每条 assessment 记录 support 与具体理由。未登记的新事实、限定词丢失、编造第一人称均为 blocker。
2. 单独检查 brief 兑现、读者行动价值与结构；对 draft→manuscript 做语义比较，数字一致不能证明语义一致。
   沿正文追踪读者问题→作者判断→支撑理由→可行行动。若某处跳步，在 editorial-review 的 finding 中标出前后具体句段、缺失的关系和修复方向，并指明应退回 Brief、Outline、Draft 或 Manuscript 中最早出错的一步；仅补连接词不算修复。
   清晰表达审阅至少检查一处最难懂或最关键段落，记录读者能否复述意思及具体证据。十条原则用于检查，不新增固定十项评分或正文模板；有理解障碍时将原句、障碍和等价改法写入 findings，缺口按最早出错资产返工。遗漏事实条件、否定关系或改变操作含义属于 blocker；普通冗余为 warning。全部已清楚时在 summary 写位置和理由，不制造虚假问题。
3. 另写 voice-review，逐项覆盖 voice-contract.required_dimensions。每项必须给出分数、正文位置、证据、理由和必要的修复；个人叙事还需指出一段作者特异性内容，并执行“替换作者后是否仍成立”的通用性测试。
4. 事实评审、编辑评审和声音评审分别保存，input_hashes 按 status 中当前依赖精确填写。
5. findings 必须有 location、reason、fix、severity；有 blocker、维度低于 3 分、通用性测试失败或缺少作者特异性段落时 verdict=fail，不可为了完成流程标 pass。
输出：fact-review、editorial-review、voice-review。完成标准是三者通过；失败时明确回到 Claims、Brief、Outline、Draft 或 Manuscript 中最早出错的资产。

操作前读取 [清晰表达原则](../content-harness/references/clear-expression.md)，按本 Skill 所处阶段执行下述检查。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

## 防止形式合格掩盖语气问题

- 通用性测试先暂时遮住署名、履历、标题与旧引文，再看正文是否仍有具体判断、理由与取舍；仅凭“这句话由作者说过”不能通过全文声音评审。
- 根据本篇体裁检查作者的态度、读者获得的信心和边界是否适量。没有证据写情绪时，不靠虚构情绪补分；引用可追溯不等于中段有作者性。
- 按 voice-contract.dimension_guidance 逐项找证据，同时寻找最薄弱段落。无修改并非错误，但不得用“初稿落盘前已优化”或“无违禁词”证明全部合格。
- 区分不承诺外部结果与支持读者尝试；内部校验通过不等于作者认可。反馈出现新观点、保证性表述或逻辑歧义时分别说明，不能全当成措辞偏好。

遇到缺少输入、stale 依赖或人类审批要求时，展示待确认的具体内容并在聊天中等待用户明确回复。确认后，Agent 可用对应命令的 --chat-confirmed 模式记录决定，传入审阅时的哈希；approve 还要传入资产 revision。内容变化时重新请求确认；不得自行决定或把一般性的“继续”当成确认。
