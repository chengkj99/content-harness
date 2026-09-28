---
name: select-style
description: Content Harness 需要编译作者声音契约、设置文章风格或切换风格时使用。
---

# select-style

阶段一输入：claims、project profile、作者资料、项目风格记忆与 reference_files。
1. Brief 之前执行 voice，生成 voice-contract。它必须固化作者资料、场景预设、长期记忆、正反样稿、必评维度与来源哈希；不要手改。
2. 个人叙事使用 personal-narrative-zh；高传播用 wechat-high-engagement；去 AI 味用 natural-human-zh。按场景预设选择，用户显式覆盖优先。需要为当前文章换风格时，在 Brief 前用 `voice --use ...` 重新固化；已有 Brief 会变为 stale。
阶段二输入：已批准 brief、voice-contract 与用户选择。
3. 执行 style，确定性编译 style-spec。检查 Author → Scene → Polish；强度不改变事实约束。
4. 新工作流的 `style` 只能编译 voice-contract 已冻结的选择，不能在 Brief 审批后静默换风格；旧工作流仍可使用 style --reset 或新选择。遇手改冲突先保留并报告，不覆盖。
输出：voice-contract、style-spec。完成标准是两者已登记，且能从自身还原所用作者、样稿、记忆、规则和版本。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，展示待确认的具体内容并在聊天中等待用户明确回复。确认后，Agent 可用对应命令的 --chat-confirmed 模式记录决定，传入审阅时的哈希；approve 还要传入资产 revision。内容变化时重新请求确认；不得自行决定或把一般性的“继续”当成确认。
